"""Refresh source files in an already-built bundle, retaining verified runtimes."""
from pathlib import Path
import shutil,zipfile,hashlib,json
ROOT=Path(__file__).resolve().parents[1];dist=ROOT/'dist';bundle=dist/'YuWallpaper-Windows-x64'
for name in ('main.py','Start-YuWallpaper.bat','Start-YuWallpaper.vbs','README.md','README.zh-CN.md','LICENSE','THIRD_PARTY.md'):
 shutil.copy2(ROOT/name,bundle/name)
for name in ('yuwallpaper','docs'):
 shutil.rmtree(bundle/name,ignore_errors=True)
 shutil.copytree(ROOT/name,bundle/name,ignore=shutil.ignore_patterns('__pycache__'))
portable=dist/'YuWallpaper-v0.2.0-Windows-x64-portable.zip'
with zipfile.ZipFile(portable,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(bundle.rglob('*')):
  if p.is_file():z.write(p,p.relative_to(dist))
source=dist/'YuWallpaper-v0.2.0-source.zip'
with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(ROOT.rglob('*')):
  relative=p.relative_to(ROOT)
  if not p.is_file() or any(x in {'.git','dist','__pycache__','runtime','.venv'} for x in relative.parts):continue
  z.write(p,Path('YuWallpaper')/relative)
for p in (portable,source):
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
 print(p.name,round(p.stat().st_size/1024/1024,2),'MiB')
checksums='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in (portable,source))+'\n'
(dist/'SHA256SUMS.txt').write_text(checksums)
