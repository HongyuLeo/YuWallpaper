import ctypes, os, shutil, subprocess
from pathlib import Path

def apply_wallpaper(path,lively=''):
    path=Path(path).resolve()
    if os.name!='nt':raise RuntimeError('Wallpaper application is supported on Windows. Other systems can export files.')
    if path.suffix.lower()=='.mp4':
        candidates=[lively,shutil.which('livelycu.exe') or '',
            str(Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Lively Wallpaper'/'livelycu.exe'),
            str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Lively Wallpaper'/'livelycu.exe')]
        executable=next((x for x in candidates if x and Path(x).is_file()),None)
        if not executable:raise RuntimeError('Install Lively Wallpaper and select livelycu.exe in Settings to apply video wallpapers.')
        subprocess.run([executable,'setwp','--file',str(path)],check=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        # Windows uses a stable BMP file, independent of downloaded PNG lifetime.
        bmp=path.with_suffix('.wallpaper.bmp')
        from PIL import Image
        with Image.open(path) as im:im.convert('RGB').save(bmp)
        if not ctypes.windll.user32.SystemParametersInfoW(20,0,str(bmp),3):
            raise ctypes.WinError()

def open_folder(path):
    path=str(Path(path).resolve())
    if os.name=='nt':os.startfile(path)
    elif shutil.which('xdg-open'):subprocess.Popen(['xdg-open',path],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    else:raise RuntimeError('Use the download buttons to save your files.')
