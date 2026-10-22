"""Generate a redistributable sample with editable Korean type and vector shapes."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bridge.engine import PhotoCraft

def create(root):
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    with PhotoCraft(root) as pc:
        pc.rpc('doc.new',width=1080,height=1350,background='#14273e',name='새로운 시작')
        pc.run('shape.create',kind='rect',rect=[72,72,8,55],fill='#f88922',name='Accent')
        pc.run('type.create',x=108,y=112,text='PSD BRIDGE',font='Malgun Gothic',size=30,color='#d5e1ef',name='Kicker')
        pc.run('type.create',x=72,y=286,text='새로운 시작',font='Malgun Gothic',size=86,color='#ffffff',name='Title')
        pc.run('type.create',x=76,y=373,text='익숙한 작업을 그대로',font='Malgun Gothic',size=44,color='#b9ccdf',name='Subtitle')
        pc.run('shape.create',kind='roundedRect',rect=[72,470,936,610],radii=28,fill='#eaf0f6',name='Canvas')
        pc.run('shape.create',kind='roundedRect',rect=[226,562,378,342],radii=20,fill='#a7bbd0',name='Back sheet')
        pc.run('shape.create',kind='roundedRect',rect=[420,676,386,296],radii=20,fill='#f88922',name='Front sheet')
        pc.run('type.create',x=482,y=846,text='편집 가능',font='Malgun Gothic',size=43,color='#14273e',name='Editable label')
        pc.run('type.create',x=76,y=1196,text='글자 · 레이어 · 다음 작업',font='Malgun Gothic',size=32,color='#ffffff',name='Footer')
        pc.rpc('doc.save',path=str(root/'새로운 시작.psd'))
        pc.rpc('doc.save',path=str(root/'sample-preview.png'))
    return root/'새로운 시작.psd'

if __name__=='__main__': print(create(Path(__file__).resolve().parents[1]/'samples'))
