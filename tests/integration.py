"""Real engine integration. No company assets required. Run from the project root."""
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge.pipeline import prepare
from bridge.engine import PhotoCraft, layers
from bridge.paths import digest, ROOT

def main():
    sample=ROOT/'samples'/'새로운 시작.psd'; before=digest(sample)
    with tempfile.TemporaryDirectory(prefix='PSD Bridge 한글 ') as temp:
        root=Path(temp)
        result=prepare(sample,root)
        assert result['verification']['text_edit_save'] and result['source_unchanged']
        assert result['text_count']==5 and result['layer_count']==10
        assert digest(sample)==before==digest(Path(result['directory'])/'원본.psd')
        again=prepare(sample,root)
        assert again['directory']!=result['directory']
        with PhotoCraft(root) as pc:
            pc.rpc('doc.open',path=result['output'])
            title=next(l for l in layers(pc.rpc('doc.inspect')['layers']) if l['name']=='Title')
            pc.run('type.edit',layer=title['id'],text='다음 작업도 편집 가능')
            changed=root/'실제 수정.pcraft';pc.rpc('doc.save',path=str(changed));pc.rpc('doc.close');pc.rpc('doc.open',path=str(changed))
            title=next(l for l in layers(pc.rpc('doc.inspect')['layers']) if l['name']=='Title')
            assert title['text']['text']=='다음 작업도 편집 가능'
            pc.rpc('doc.close');pc.rpc('doc.new',width=600,height=400,background='#ffffff')
            pc.run('type.create',x=50,y=100,text='누락된 글꼴',font='Bridge Missing Font 987654',size=36,name='Missing')
            missing=root/'누락 글꼴.psd';pc.rpc('doc.save',path=str(missing))
        missing_result=prepare(missing,root)
        assert missing_result['status']=='확인 필요' and any(f['status']=='누락' for f in missing_result['fonts']),missing_result
        bad=root/'손상.psd';bad.write_bytes(b'not a psd')
        status=root/'bad-status.json';config=root/'bad-job.json';config.write_text(json.dumps({'source':str(bad),'output':str(root),'status':str(status)}),encoding='utf-8')
        p=subprocess.run([sys.executable,str(ROOT/'main.py'),'--worker',str(config)],timeout=20,capture_output=True)
        assert p.returncode==1 and json.loads(status.read_text(encoding='utf-8'))['state']=='failed'
        rgb16=root/'16bit.psd';data=bytearray(sample.read_bytes());data[22:24]=struct.pack('>H',16);rgb16.write_bytes(data)
        try: prepare(rgb16,root)
        except ValueError as e: assert '8비트' in str(e)
        else: raise AssertionError('16-bit input was not rejected')
        print(json.dumps({'passed':True,'layers':result['layer_count'],'texts':result['text_count'], 'original_compare':result['comparison'],'missing_font':missing_result['fonts']},ensure_ascii=False))

if __name__=='__main__': main()
