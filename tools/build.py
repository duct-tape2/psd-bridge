"""Windows portable build. Outputs only into this project's dist directory."""
import hashlib
import importlib.metadata
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','PSDBridge',
          '--distpath',str(ROOT/'dist'),'--workpath',str(ROOT/'build'),'--specpath',str(ROOT/'build')]
    for module in ('scipy','skimage','matplotlib','pandas','IPython','pytest','tkinter','torch','tensorflow','cv2','PySide6.QtWebEngineCore','PySide6.QtQuick','PySide6.QtQml','PySide6.QtNetwork','PySide6.QtOpenGL','PySide6.QtPdf','PySide6.QtMultimedia'):
        args+=['--exclude-module',module]
    for package in ('psd-tools','Pillow','numpy','fonttools','attrs','PySide6_Essentials','shiboken6'):
        args+=['--copy-metadata',package]
    args.append(str(ROOT/'main.py'))
    subprocess.run(args,cwd=ROOT,check=True)
    out=ROOT/'dist'/'PSDBridge'
    # These host ICU DLLs shadow Windows' own ICU used by Qt and caused startup
    # failures in the predecessor app. They are not Qt's versioned ICU runtime.
    for name in ('icuuc.dll','icudt78.dll'): (out/'_internal'/name).unlink(missing_ok=True)
    for directory in ('assets','licenses','samples'):
        shutil.copytree(ROOT/directory,out/directory,dirs_exist_ok=True)
    vendor=out/'vendor'/'photocraft';vendor.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'vendor'/'photocraft').iterdir():
        if p.is_file() and (p.suffix in ('.exe','.txt','.md') or p.name.startswith(('LICENSE','NOTICE'))): shutil.copy2(p,vendor/p.name)
    for name in ('START.bat','README.md','LICENSE','THIRD_PARTY_NOTICES.md'): shutil.copy2(ROOT/name,out/name)
    license_root=out/'licenses'/'runtime';license_root.mkdir(parents=True,exist_ok=True)
    for package in ('PySide6_Essentials','shiboken6','psd-tools','Pillow','numpy','fonttools','attrs','pyinstaller'):
        dist=importlib.metadata.distribution(package)
        for f in dist.files or []:
            if any(k in f.name.lower() for k in ('license','copying','notice')):
                p=Path(dist.locate_file(f))
                if p.is_file():
                    target=license_root/package/str(f).replace('../','').replace('..\\','')
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    pylicense=Path(sys.base_prefix)/'LICENSE.txt'
    if pylicense.is_file(): shutil.copy2(pylicense,license_root/'Python-LICENSE.txt')
    archive=ROOT/'dist'/'PSD-Bridge-0.1.0-Windows-x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(out.rglob('*')):
            if p.is_file(): z.write(p,Path('PSD-Bridge')/p.relative_to(out))
    checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
    (ROOT/'dist'/'SHA256SUMS.txt').write_text(checksum+'  '+archive.name+'\n',encoding='utf-8')
    print(str(archive),archive.stat().st_size,checksum)

if __name__=='__main__': main()
