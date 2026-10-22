"""Download the pinned official engine archive; verify before extracting files."""
import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

URL='https://github.com/storytold/photocraft/releases/download/v0.11.1/photocraft-0.11.1-windows-x64-portable.zip'
SHA256='00570cb1a2da18a5677b28296f6cefae46dfad3011f51b8369146dcc73a2777a'

def main():
    root=Path(__file__).resolve().parents[1]/'vendor'/'photocraft';root.mkdir(parents=True,exist_ok=True)
    data=urllib.request.urlopen(URL,timeout=120).read()
    if hashlib.sha256(data).hexdigest()!=SHA256: raise RuntimeError('Official archive checksum mismatch; nothing was installed.')
    wanted={'photocraft.exe','photocraft-cli.exe','portable.txt'}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            base=Path(name).name
            if base in wanted: (root/base).write_bytes(archive.read(name));wanted.remove(base)
    if wanted: raise RuntimeError('Archive is missing '+', '.join(wanted))
    print('PhotoCraft 0.11.1 verified and ready.')

if __name__=='__main__': main()
