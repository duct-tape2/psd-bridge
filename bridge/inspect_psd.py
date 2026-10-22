import struct
from collections import Counter
from pathlib import Path
from psd_tools import PSDImage


def normalize_text(text):
    return text.replace('\r\n', '\n').replace('\r', '\n').rstrip('\x00')


def inspect_psd(path, preview_path):
    path = Path(path)
    if path.suffix.lower() != '.psd':
        raise ValueError('이번 버전은 PSD 파일을 지원합니다. Photoshop에서 PSD로 저장한 파일을 선택해 주세요.')
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('첫 버전은 256MB 이하 PSD를 지원합니다. 작은 복사본으로 다시 시도해 주세요.')
    with path.open('rb') as f: header = f.read(26)
    if len(header) < 26 or header[:4] != b'8BPS':
        raise ValueError('올바른 PSD 파일이 아니거나 파일이 손상됐습니다.')
    version, channels, height, width, depth, mode = struct.unpack('>H6xHIIHH', header[4:])
    if version != 1 or mode != 3 or depth != 8:
        raise ValueError('첫 버전은 RGB · 8비트 PSD만 지원합니다. 원본은 보존하고 Photoshop에서 별도 복사본을 만들어 주세요.')
    if not width or not height or width*height > 32_000_000 or max(width, height) > 16000:
        raise ValueError('첫 버전의 이미지 크기 한도를 넘었습니다. 최대 3,200만 화소, 한 변 16,000px입니다.')
    psd = PSDImage.open(path)
    all_layers = list(psd.descendants())
    if len(all_layers) > 500:
        raise ValueError('첫 버전은 레이어 500개 이하를 지원합니다.')
    found = []
    warnings = []
    references = []
    def tree(group):
        return [{'name':l.name,'group':l.is_group(),'visible':l.visible,
                 'mask':l.has_mask(),'vector_mask':l.has_vector_mask(),
                 'children':tree(l) if l.is_group() else []} for l in reversed(list(group))]
    hierarchy=tree(psd)
    for layer in all_layers:
        item = {'name': layer.name, 'kind': layer.kind, 'visible': layer.visible, 'bbox': list(layer.bbox)}
        if layer.kind == 'type':
            item['text'] = normalize_text(layer.text)
        if layer.kind == 'smartobject':
            try:
                obj = layer.smart_object
                ref = {'layer': layer.name, 'kind': obj.kind, 'filename': obj.filename}
                if obj.kind != 'data':
                    references.append(ref)
                    warnings.append(f'「{layer.name}」: 외부 연결 스마트 오브젝트입니다. 원본 파일 연결은 PhotoCraft에서 확인해 주세요. 이 버전은 외부 자원을 자동 수집하지 않습니다.')
            except Exception:
                warnings.append(f'「{layer.name}」: 스마트 오브젝트 자원 정보를 읽지 못했습니다.')
        found.append(item)
    cached = False
    if psd.has_preview():
        try:
            preview = psd.topil(apply_icc=True)
            if preview is not None:
                preview.save(preview_path); cached = True
        except Exception:
            warnings.append('PSD에 저장된 합성 미리보기를 읽지 못했습니다. 원본 외관 비교는 하지 않았습니다.')
    return {'width': width, 'height': height, 'depth': depth, 'mode': 'RGB', 'layers': found,
            'references': references, 'warnings': warnings, 'cached_preview': cached, 'hierarchy':hierarchy}


def verify_import(source, imported):
    from .engine import layers
    actual = list(layers(imported['layers']))
    if (imported['width'], imported['height']) != (source['width'], source['height']):
        raise ValueError('가져오기 중 문서 크기가 변경되어 작업을 중단했습니다.')
    if Counter(l['name'] for l in actual) != Counter(l['name'] for l in source['layers']):
        raise ValueError('가져온 레이어 목록이 원본과 다릅니다. 일부 레이어가 누락되거나 변경되어 작업을 중단했습니다.')
    expected = Counter((l['name'], l['text']) for l in source['layers'] if l['kind'] == 'type')
    result = Counter((l['name'], normalize_text(l.get('text', {}).get('text', ''))) for l in actual if l['kind'] == 'Type')
    if expected != result:
        raise ValueError('일부 텍스트가 편집 가능한 글자로 유지되지 않았습니다. 완료 처리하지 않고 작업을 중단했습니다.')
    def skeleton(items, native=False):
        return [{'name':l['name'],'group':l.get('kind')=='Group' if native else l['group'],
                 'visible':l['visible'],'children':skeleton(l.get('children',[]),native)} for l in items]
    if skeleton(source['hierarchy']) != skeleton(imported['layers'],True):
        raise ValueError('가져오기 중 레이어 순서·그룹 또는 표시 상태가 달라져 작업을 중단했습니다.')
    def masks(items):
        for l in items:
            yield l
            yield from masks(l.get('children',[]))
    src=list(masks(source['hierarchy']))
    for a,b in zip(src,actual):
        # PSD shape paths are vector masks; PhotoCraft stores them as editable
        # Shape geometry instead of a separate vector-mask flag.
        native_vector=bool(b.get('hasVectorMask')) or b.get('kind')=='Shape'
        if bool(a['mask'])!=bool(b.get('hasMask')) or bool(a['vector_mask'])!=native_vector:
            source['warnings'].append('「'+a['name']+'」: 마스크 구조가 다릅니다. 작업본의 마스크 편집을 확인해 주세요.')
