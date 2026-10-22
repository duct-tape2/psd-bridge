"""Create small release assets and a one-click downloader without changing OS policy."""
import hashlib,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist'
BASE='https://github.com/duct-tape2/psd-bridge/releases/download/v0.1.0/'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    archive=DIST/'PSD-Bridge-0.1.0-Windows-x64.zip'
    release=DIST/'upload';release.mkdir(exist_ok=True)
    manifest={'version':'0.1.0','archive':archive.name,'sha256':sha(archive),'base_url':BASE,'parts':[]}
    with archive.open('rb') as f:
        i=0
        while chunk:=f.read(32*1024*1024):
            i+=1;p=release/f'PSD-Bridge-0.1.0.part{i:02d}'
            if not p.exists() or sha(p)!=hashlib.sha256(chunk).hexdigest(): p.write_bytes(chunk)
            manifest['parts'].append({'name':p.name,'sha256':sha(p),'size':len(chunk)})
    setup=DIST/'setup';setup.mkdir(exist_ok=True)
    (setup/'download.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Executed as ordinary PowerShell commands, without ExecutionPolicy overrides,
    # IEX, admin elevation, persistence, or changes to system settings.
    command="""$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; $taskRoot=(Get-Location).Path; try { $m=Get-Content -LiteralPath (Join-Path $taskRoot 'download.json') -Raw | ConvertFrom-Json; $folder=Join-Path $taskRoot 'PSD-Bridge-0.1.0'; $app=Join-Path $folder 'PSD-Bridge/PSDBridge.exe'; $marker=Join-Path $folder 'installed.sha256'; if ((Test-Path -LiteralPath $app) -and (Test-Path -LiteralPath $marker) -and ((Get-Content -LiteralPath $marker -Raw).Trim() -eq $m.sha256)) { Start-Process -FilePath $app; exit 0 }; $cache=Join-Path $taskRoot 'downloads'; New-Item -ItemType Directory -Force -Path $cache | Out-Null; $client=New-Object Net.WebClient; foreach ($part in $m.parts) { $file=Join-Path $cache $part.name; $ok=(Test-Path -LiteralPath $file) -and ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -eq $part.sha256); if (!$ok) { Write-Host ('Downloading '+$part.name); $downloaded=$false; for ($attempt=1; $attempt -le 3; $attempt++) { try { $client.DownloadFile(($m.base_url+$part.name),$file); if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $part.sha256) { throw 'Checksum mismatch' }; $downloaded=$true; break } catch { if ($attempt -eq 3) { throw }; Start-Sleep -Seconds 2 } }; if (!$downloaded) { throw 'Download failed' } } }; $client.Dispose(); $zip=Join-Path $taskRoot $m.archive; $stream=[IO.File]::Create($zip); try { foreach ($part in $m.parts) { $inputStream=[IO.File]::OpenRead((Join-Path $cache $part.name)); try { $inputStream.CopyTo($stream) } finally { $inputStream.Dispose() } } } finally { $stream.Dispose() }; if ((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash -ne $m.sha256) { throw 'Package checksum mismatch' }; Write-Host 'Extracting PSD Bridge...'; Expand-Archive -LiteralPath $zip -DestinationPath $folder -Force; if (!(Test-Path -LiteralPath $app)) { throw 'Application is missing after extraction' }; Set-Content -LiteralPath $marker -Value $m.sha256 -Encoding ASCII; Write-Host 'Ready. The complete ZIP can now be copied to an offline PC.'; Start-Process -FilePath $app; exit 0 } catch { Write-Host ('Setup failed: '+$_.Exception.Message); Write-Host 'Check your connection and run START.bat again. Verified downloads are reused.'; exit 1 }"""
    # Built-in .NET APIs also work when a parent application's PSModulePath omits
    # the optional Get-FileHash/Archive modules.
    command="function HashFile($p) { $s=[IO.File]::OpenRead($p); try { $h=[Security.Cryptography.SHA256]::Create(); try { return ([BitConverter]::ToString($h.ComputeHash($s))).Replace('-','').ToLowerInvariant() } finally { $h.Dispose() } } finally { $s.Dispose() } }; "+command
    command=command.replace('(Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash','(HashFile $file)')
    command=command.replace('(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash','(HashFile $zip)')
    command=command.replace('Expand-Archive -LiteralPath $zip -DestinationPath $folder -Force',"Add-Type -AssemblyName System.IO.Compression.FileSystem; [IO.Directory]::CreateDirectory($folder) | Out-Null; $z=[IO.Compression.ZipFile]::OpenRead($zip); try { foreach ($entry in $z.Entries) { $dest=[IO.Path]::GetFullPath((Join-Path $folder $entry.FullName)); if (!$dest.StartsWith(($folder+[IO.Path]::DirectorySeparatorChar),[StringComparison]::OrdinalIgnoreCase)) { throw 'Invalid archive path' }; if ($entry.Name -eq '') { [IO.Directory]::CreateDirectory($dest) | Out-Null } else { [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest)) | Out-Null; [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$dest,$true) } } } finally { $z.Dispose() }")
    if len(command)>7000: raise RuntimeError('Installer command exceeds the safe batch length')
    bat='@echo off\r\nsetlocal DisableDelayedExpansion\r\ncd /d "%~dp0"\r\necho PSD Bridge 0.1.0 - First setup downloads about 145 MB.\r\npowershell.exe -NoLogo -NoProfile -Command "'+command+'"\r\nif errorlevel 1 (\r\n  pause\r\n  exit /b 1\r\n)\r\nexit /b 0\r\n'
    (setup/'START.bat').write_bytes(bat.encode('ascii'))
    (setup/'README.txt').write_text('PSD Bridge 0.1.0\n\n1. Extract this ZIP completely.\n2. Double-click START.bat.\n3. The first run downloads and verifies about 145 MB from this GitHub release.\n4. After setup, all PSD processing is offline.\n\nYour PSD files are never uploaded. No administrator or Python installation is required.\nThe full Windows ZIP is kept next to START.bat for copying to another offline PC.\nIf setup fails, rerun START.bat to reuse verified downloads.\n\nhttps://github.com/duct-tape2/psd-bridge\n',encoding='utf-8')
    installer=release/'PSD-Bridge-0.1.0-Setup.zip'
    with zipfile.ZipFile(installer,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(setup.iterdir()):z.write(p,Path('PSD-Bridge-Setup')/p.name)
    (release/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(release.iterdir()) if p.name!='SHA256SUMS.txt')+manifest['sha256']+'  '+archive.name+'\n',encoding='utf-8')
    print(json.dumps({'installer':str(installer),'parts':len(manifest['parts']),'sha256':manifest['sha256']},ensure_ascii=False))

if __name__=='__main__':main()
