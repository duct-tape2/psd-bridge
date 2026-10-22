import html
import json
import shutil
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from . import VERSION
from .engine import PhotoCraft, layers, structure
from .inspect_psd import inspect_psd, verify_import
from .paths import digest, safe_name, write_json


def compare_images(a, b):
    with Image.open(a) as ia, Image.open(b) as ib:
        if ia.size != ib.size:
            return {'same_size': False, 'mean_error': None, 'changed_percent': 100.0}
        # Compare against white consistently; this is diagnostic, not a fidelity score.
        def opaque(im):
            rgba = im.convert('RGBA'); bg = Image.new('RGBA', rgba.size, 'white'); bg.alpha_composite(rgba)
            return bg.convert('RGB')
        delta = ImageChops.difference(opaque(ia), opaque(ib))
        mean = sum(ImageStat.Stat(delta).mean)/3
        r,g,b = delta.split()
        maximum = ImageChops.lighter(ImageChops.lighter(r,g),b)
        hist = maximum.histogram()
        changed = sum(hist[13:])*100/(ia.width*ia.height)
        return {'same_size': True, 'mean_error': round(mean,4), 'changed_percent': round(changed,3)}


def type_snapshot(pc, document):
    return [pc.run('type.info', layer=l['id']) for l in layers(document['layers']) if l['kind']=='Type']


def style_snapshot(info):
    return {k: info.get(k) for k in ('text','runs','paragraphs','shape','transform','orientation','warp','antialias','pxPerPt')}


def font_report(pc, types):
    missing = pc.run('type.resolveMissingFonts').get('missing', []) if types else []
    families = {}
    result = []
    seen = set()
    for info in types:
        for run in info.get('runs', []):
            style = run['style']; family = style.get('font_family',''); ps = style.get('postscript_name')
            key = (family, ps, style.get('weight'), style.get('italic'))
            if key in seen: continue
            seen.add(key)
            if family not in families:
                families[family] = pc.run('type.fonts', family=family).get('faces', [])
            faces = families[family]
            exact = next((f for f in faces if ps and f.get('postscriptName')==ps), None)
            if not ps:
                exact = next((f for f in faces if abs(f.get('weight',400)-style.get('weight',400))<1 and f.get('italic',False)==style.get('italic',False)),None)
            state = '확인됨' if exact else ('누락' if family in missing or not faces else '글꼴 굵기 확인 필요')
            result.append({'family':family,'postscript_name':ps,'weight':style.get('weight'), 'status':state})
    return result


def prepare(source_path, output_root, progress=lambda *args: None):
    source_path = Path(source_path).resolve(strict=True)
    if not source_path.is_file(): raise ValueError('PSD 파일을 선택해 주세요.')
    progress(8, '원본 PSD를 확인하고 있어요.')
    before_hash = digest(source_path)
    stamp = datetime.now(timezone(timedelta(hours=9)))
    job = Path(output_root).resolve()/stamp.strftime('%y%m%d')/(safe_name(source_path.stem)+'_'+stamp.strftime('%H%M%S')+'_'+uuid.uuid4().hex[:6])
    job.mkdir(parents=True, exist_ok=False)
    scratch = job/'검사용'; scratch.mkdir()
    report = {'version':VERSION,'source':str(source_path),'source_sha256':before_hash,'directory':str(job),'status':'처리 중','warnings':[]}
    write_json(job/'report.json',report)
    try:
        original_preview = job/'원본 저장 미리보기.png'
        source = inspect_psd(source_path,original_preview)
        report['source_document'] = source
        warnings = report['warnings']; warnings.extend(source['warnings'])
        # The source copy is byte-identical. Never save the engine over this file.
        original = job/'원본.psd'; shutil.copy2(source_path, original)
        if digest(original)!=before_hash or digest(source_path)!=before_hash:
            raise RuntimeError('읽는 동안 원본 파일이 변경됐습니다. Photoshop에서 저장을 마친 후 다시 시도해 주세요.')
        progress(24,'레이어와 글꼴을 읽고 있어요.')
        output = job/(safe_name(source_path.stem)+'.pcraft')
        preview = job/'작업본 미리보기.png'
        with PhotoCraft(job) as pc:
            pc.rpc('doc.open',path=str(original))
            imported=pc.rpc('doc.inspect')
            verify_import(source,imported)
            warnings.extend(source['warnings'])
            types=type_snapshot(pc,imported)
            fonts=font_report(pc,types)
            report['fonts']=fonts
            for f in fonts:
                if f['status']!='확인됨': warnings.append(f"{f['family']} ({f.get('postscript_name') or f.get('weight')}): {f['status']}. 글꼴을 설치한 후 원본으로 다시 준비해 주세요. 임의의 대체 글꼴은 지정하지 않았습니다.")
            for warning in imported.get('warnings',[]): warnings.append(str(warning))
            complicated=[l['name'] for l in layers(imported['layers']) if l.get('effects') or l.get('smartFilters') or l['kind']=='Smart Object' or l.get('hasVectorMask') or l['kind'] not in {'Type','Pixel','Shape','Group'}]
            if complicated:
                warnings.append('효과·스마트 오브젝트 등 세부 편집은 직접 확인해 주세요: '+', '.join(complicated[:8])+(' 외' if len(complicated)>8 else ''))
            progress(45,'편집 가능한 작업본을 저장하고 있어요.')
            pc.rpc('doc.save',path=str(output))
            pc.rpc('doc.save',path=str(preview))
        progress(64,'저장한 파일을 다시 열어 검사하고 있어요.')
        with PhotoCraft(job) as pc:
            pc.rpc('doc.open',path=str(output))
            reopened=pc.rpc('doc.inspect')
            if structure(imported['layers'])!=structure(reopened['layers']):
                raise RuntimeError('저장 후 레이어 구조가 바뀌었습니다. 편집 가능한 작업본으로 검증하지 못했습니다.')
            after_types=type_snapshot(pc,reopened)
            if [style_snapshot(t) for t in types]!=[style_snapshot(t) for t in after_types]:
                raise RuntimeError('저장 후 텍스트 또는 스타일이 바뀌었습니다. 작업본을 완료 처리하지 않았습니다.')
            reopened_preview=scratch/'reopened.png'; pc.rpc('doc.save',path=str(reopened_preview))
            saved_compare=compare_images(preview,reopened_preview)
            if saved_compare['mean_error']!=0:
                raise RuntimeError('저장 후 다시 연 작업본의 표시가 달라졌습니다. 완료 처리하지 않았습니다.')
            active_compare=None
            if after_types:
                # Force live glyph layout in a scratch session, leaving the delivered
                # work file untouched. Cached Photoshop text alone is not proof.
                pc.run('type.updateAllTextLayers')
                active_preview=scratch/'live-text.png'; pc.rpc('doc.save',path=str(active_preview))
                active_compare=compare_images(preview,active_preview)
                if not active_compare['same_size'] or active_compare['mean_error']>2 or active_compare['changed_percent']>2:
                    warnings.append('텍스트를 다시 계산하면 표시가 달라집니다. PhotoCraft에서 글자를 수정하기 전에 원본 미리보기와 비교해 주세요.')
                progress(79,'텍스트 수정과 재저장을 검사하고 있어요.')
                for text in after_types:
                    n=len(text['text'])
                    pc.run('type.edit',layer=text['layer'],replace={'start':n,'end':n,'text':' '})
                edited=scratch/'edit-check.pcraft'; pc.rpc('doc.save',path=str(edited))
                pc.rpc('doc.close')
                pc.rpc('doc.open',path=str(edited))
                edited_types=type_snapshot(pc,pc.rpc('doc.inspect'))
                if [t['text'] for t in edited_types]!=[t['text']+' ' for t in after_types]:
                    raise RuntimeError('텍스트 수정·재저장 검사에 실패했습니다. 편집 가능 여부를 확인하지 못했습니다.')
        progress(91,'미리보기와 검사 결과를 정리하고 있어요.')
        comparison=compare_images(original_preview,preview) if source['cached_preview'] else None
        if comparison and (not comparison['same_size'] or comparison['mean_error']>2 or comparison['changed_percent']>2):
            warnings.append('PSD에 저장된 원본 미리보기와 표시 차이가 있습니다. 효과·색상·텍스트 위치를 확인해 주세요.')
        if not comparison: warnings.append('비교할 원본 저장 미리보기가 없어 원본 외관 비교를 하지 않았습니다.')
        if digest(source_path)!=before_hash or digest(original)!=before_hash:
            raise RuntimeError('원본 보존 검사에 실패했습니다. 파일을 확인해 주세요.')
        report.update(status='확인 필요' if warnings else '준비 완료', output=str(output), preview=str(preview),
                      original_preview=str(original_preview) if source['cached_preview'] else None,
                      layer_count=len(source['layers']), text_count=len(types), comparison=comparison,
                      live_text_comparison=active_compare, source_unchanged=True,
                      verification={'reopened':True,'text_edit_save':bool(types),'same_engine_render':True,
                                    'reference':'PSD에 저장된 합성 이미지' if comparison else None,
                                    'photoshop_render_verified':False})
        report['warnings']=list(dict.fromkeys(warnings))
        write_json(job/'report.json',report)
        write_html(job/'검사 결과.html',report)
        progress(100,'작업본이 준비됐어요. PhotoCraft에서 이어서 편집하세요.')
        return report
    except Exception as e:
        report.update(status='실패',error=str(e)); write_json(job/'report.json',report)
        raise
    finally:
        # Only generated scratch files in this unique job are removed.
        for name in ('reopened.png','live-text.png','edit-check.pcraft'):
            (scratch/name).unlink(missing_ok=True)
        try: scratch.rmdir()
        except OSError: pass


def write_html(path,r):
    esc=lambda value:html.escape(str(value))
    notes=''.join('<li>'+esc(w)+'</li>' for w in r['warnings']) or '<li>자동 검사에서 추가 확인 항목이 발견되지 않았습니다.</li>'
    font_rows=''.join('<tr><td>'+esc(f['family'])+'</td><td>'+esc(f.get('postscript_name') or '')+'</td><td>'+esc(f['status'])+'</td></tr>' for f in r['fonts'])
    Path(path).write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>PSD Bridge 검사 결과</title><style>body{font:16px/1.7 sans-serif;background:#f0f3f7;color:#172b43;max-width:900px;margin:48px auto;padding:32px;background:white}h1{color:#142b46}td,th{padding:10px;text-align:left;border-bottom:1px solid #d9e1ea}li{margin:10px 0}img{max-width:420px;max-height:600px}</style>'
        +'<h1>'+esc(r['status'])+'</h1><p>'+esc(Path(r['source']).name)+'</p><p>레이어 '+str(r['layer_count'])+'개 / 편집 가능한 텍스트 '+str(r['text_count'])+'개</p>'
        +'<h2>검사한 내용</h2><p>원본 해시 보존 · 레이어와 텍스트 유지 · 저장 후 재열기'+(' · 텍스트 수정 및 재저장' if r['text_count'] else ' · 편집 가능한 텍스트 없음')+'</p><p>원본 외관 비교는 PSD에 저장된 합성 미리보기 기준입니다. Photoshop을 실행한 렌더링 검증이나 모든 효과의 동일성을 보장하지 않습니다.</p>'
        +'<h2>확인할 내용</h2><ul>'+notes+'</ul><h2>글꼴</h2><table><tr><th>글꼴</th><th>요청된 글꼴 이름</th><th>상태</th></tr>'+font_rows+'</table>'
        +'<h2>작업본 미리보기</h2><img src="작업본 미리보기.png" alt="작업본"><p>PSD Bridge '+VERSION+'</p></html>',encoding='utf-8')
