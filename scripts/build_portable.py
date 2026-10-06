"""Build Windows x64 portable bundle on Linux or Windows, without Wine.
Downloads only official Python/PyPI artifacts. Wheels are SHA-256 verified.
"""
import hashlib,json,shutil,sys,tempfile,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/'dist';BUNDLE=DIST/'YuWallpaper-Windows-x64'

def get(url):
    request=urllib.request.Request(url,headers={'User-Agent':'YuWallpaper-build/0.1'})
    with urllib.request.urlopen(request,timeout=120) as r:return r.read()

def wheel(package,version,selector):
    metadata=json.loads(get(f'https://pypi.org/pypi/{package}/{version}/json'))
    files=[f for f in metadata['urls'] if selector(f['filename'])]
    if len(files)!=1:raise RuntimeError(f'Expected one wheel for {package}, got {len(files)}')
    item=files[0];print(f'Downloading {item["filename"]}',flush=True)
    payload=get(item['url'])
    digest=hashlib.sha256(payload).hexdigest()
    if digest!=item['digests']['sha256']:raise RuntimeError('Wheel checksum mismatch.')
    return payload,{'package':package,'version':version,'file':item['filename'],'sha256':digest,'url':item['url']}

def main():
    DIST.mkdir(exist_ok=True)
    if BUNDLE.exists():shutil.rmtree(BUNDLE)
    BUNDLE.mkdir()
    for name in ('main.py','Start-YuWallpaper.bat','Start-YuWallpaper.vbs','README.md','README.zh-CN.md','LICENSE','THIRD_PARTY.md'):
        shutil.copy2(ROOT/name,BUNDLE/name)
    shutil.copytree(ROOT/'yuwallpaper',BUNDLE/'yuwallpaper',ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'docs',BUNDLE/'docs')
    runtime=BUNDLE/'runtime';runtime.mkdir()
    url='https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip'
    print('Downloading official Python 3.12.10 Windows runtime',flush=True)
    payload=get(url);manifest=[{'package':'Python','version':'3.12.10','url':url,'sha256':hashlib.sha256(payload).hexdigest()}]
    with tempfile.TemporaryDirectory() as td:
        archive=Path(td)/'python.zip';archive.write_bytes(payload)
        with zipfile.ZipFile(archive) as z:z.extractall(runtime)
        site=runtime/'site-packages';site.mkdir()
        for package,version,selector in [
            ('Pillow','11.3.0',lambda n:'cp312-cp312-win_amd64.whl' in n),
            ('pip','25.2',lambda n:n.endswith('py3-none-any.whl')),
            ('imageio-ffmpeg','0.6.0',lambda n:n.endswith('win_amd64.whl'))]:
            payload,item=wheel(package,version,selector);manifest.append(item)
            archive.write_bytes(payload)
            with zipfile.ZipFile(archive) as z:z.extractall(site)
        exe=next((site/'imageio_ffmpeg'/'binaries').glob('*.exe'))
        shutil.copy2(exe,runtime/'ffmpeg.exe')
        # Remove duplicate binary after retaining the package's license metadata.
        exe.unlink()
    (runtime/'python312._pth').write_text('python312.zip\n.\n..\nsite-packages\nimport site\n')
    (BUNDLE/'build-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    target=DIST/'YuWallpaper-v0.2.0-Windows-x64-portable.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(BUNDLE.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(DIST))
    print(f'Built {target} ({target.stat().st_size/1024/1024:.1f} MiB)',flush=True)

if __name__=='__main__':main()
