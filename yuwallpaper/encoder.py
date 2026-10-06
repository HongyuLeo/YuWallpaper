from __future__ import annotations
import os, shutil, subprocess, threading
from pathlib import Path
from .imaging import draw_particles

class Cancelled(Exception): pass

def ffmpeg_path():
    bundled=Path(__file__).resolve().parent.parent/'runtime'/'ffmpeg.exe'
    if bundled.is_file(): return str(bundled)
    found=shutil.which('ffmpeg')
    if found:return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError('FFmpeg is missing. Install imageio-ffmpeg or use the Windows portable release.')

def encode(base,target,duration,fps,effect,protect,cancel,progress):
    duration=int(duration); fps=int(fps)
    if duration not in {4,8,16} or fps not in {24,30,60}:
        raise ValueError('Unsupported duration or frame rate.')
    count=duration*fps
    frames=(draw_particles(base,i/fps,duration,effect=effect,protect=protect) for i in range(count))
    return encode_frames(frames,base.size,target,fps,count,cancel,progress)

def encode_frames(frames,size,target,fps,count,cancel,progress):
    w,h=size
    if w%2 or h%2: raise ValueError('Video dimensions must be even.')
    cmd=[ffmpeg_path(),'-hide_banner','-loglevel','error','-y','-f','rawvideo',
         '-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0',
         '-an','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',
         '-movflags','+faststart',str(target)]
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
    errors=bytearray()
    def drain():
        for chunk in iter(lambda:proc.stderr.read(4096),b''):
            errors.extend(chunk)
            if len(errors)>16384:del errors[:-16384]
    reader=threading.Thread(target=drain,daemon=True);reader.start()
    def watchdog():
        while proc.poll() is None:
            if cancel.wait(.25):
                try:proc.terminate()
                except OSError:pass
                return
    threading.Thread(target=watchdog,daemon=True).start()
    try:
        written=0
        for i,frame in enumerate(frames):
            if cancel.is_set():raise Cancelled()
            if frame.size!=size:raise ValueError("Unexpected generated frame size.")
            proc.stdin.write(frame.tobytes());written+=1
            if i%3==0:progress(10+int(i/count*86),'Encoding locally')
        if written!=count:raise ValueError("Generated frame count mismatch.")
        proc.stdin.close()
        code=proc.wait();reader.join(timeout=2)
        if cancel.is_set():raise Cancelled()
        if code:raise RuntimeError(errors.decode(errors='replace')[-1200:] or 'FFmpeg failed.')
    except BaseException as exc:
        proc.kill();proc.wait()
        try:target.unlink(missing_ok=True)
        except OSError:pass
        if cancel.is_set():raise Cancelled() from exc
        raise
    finally:
        if proc.stdin and not proc.stdin.closed:proc.stdin.close()
        proc.stderr.close()
