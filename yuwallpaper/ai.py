import json,os,subprocess,sys,threading
from pathlib import Path
from PIL import Image,ImageDraw
from .imaging import compose,preview_size
from .encoder import Cancelled

PACKAGES=['torch==2.7.1','diffusers==0.35.2','transformers==4.57.1','accelerate==1.10.1','safetensors==0.6.2']

def run_process(command,cancel,progress,env=None):
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,
                          encoding='utf-8',errors='replace',env=env,creationflags=flags)
    def watchdog():
        while proc.poll() is None:
            if cancel.wait(.3):
                try:proc.terminate()
                except OSError:pass
                return
    threading.Thread(target=watchdog,daemon=True).start()
    lines=[]
    for line in proc.stdout:
        lines.append(line.strip());lines=lines[-20:]
        try:
            item=json.loads(line)
            if isinstance(item,dict) and 'percent' in item:progress(item['percent'],item['message'])
        except (ValueError,KeyError):
            if line.strip():progress(None,line.strip()[-250:])
    code=proc.wait();proc.stdout.close()
    if cancel.is_set():raise Cancelled()
    if code:raise RuntimeError('\n'.join(lines)[-1800:])

def python_exe():
    executable=Path(sys.executable)
    if executable.name.lower()=='pythonw.exe':return str(executable.with_name('python.exe'))
    return str(executable)

def install_ai(data_dir,cancel,progress):
    target=data_dir/'ai-packages';target.mkdir(exist_ok=True)
    # An explicit button starts the download; no installation on application launch.
    progress(5,'Installing optional local AI dependencies; download can be several GB')
    run_process([python_exe(),'-m','pip','install','--only-binary=:all:','--upgrade',
                 '--target',str(target),*PACKAGES],cancel,progress)
    (target/'.ready').write_text('YuWallpaper local AI runtime 0.1\n')
    progress(100,'Local AI dependencies installed. The model downloads on first AI generation.')

def expand(src,size,position,scale,prompt,data_dir,work_dir,cancel,progress):
    packages=data_dir/'ai-packages'
    if not (packages/'.ready').exists():raise ValueError('Install the optional local AI runtime from Settings first.')
    # Inference stays small; export dimensions never claim native AI 8K detail.
    work_size=preview_size(size,768)
    work_size=tuple(max(64,round(x/8)*8) for x in work_size)
    canvas,box=compose(src,work_size,'preserve',position,scale)
    mask=Image.new('L',work_size,255);x,y,w,h=box
    ImageDraw.Draw(mask).rectangle((x,y,x+w-1,y+h-1),fill=0)
    canvas.save(work_dir/'canvas.png');mask.save(work_dir/'mask.png')
    req={'packages':str(packages),'cache':str(data_dir/'models'),
         'canvas':str(work_dir/'canvas.png'),'mask':str(work_dir/'mask.png'),
         'output':str(work_dir/'ai.png'),'prompt':prompt,'steps':24}
    request=work_dir/'request.json';request.write_text(json.dumps(req),encoding='utf-8')
    env=os.environ.copy();env['PYTHONPATH']=str(packages);env['PYTHONUNBUFFERED']='1'
    run_process([python_exe(),str(Path(__file__).with_name('ai_worker.py')),str(request)],cancel,progress,env)
    result=Image.open(work_dir/'ai.png').convert('RGB').resize(size,Image.Resampling.LANCZOS)
    # Paste ORIGINAL at full export resolution after AI. Model cannot alter the foreground.
    from .imaging import placement
    x,y,w,h=placement(src.size,size,position,scale)
    result.paste(src.resize((w,h),Image.Resampling.LANCZOS),(x,y))
    return result,{'inference_width':work_size[0],'inference_height':work_size[1],
                   'model':'stable-diffusion-v1-5/stable-diffusion-inpainting','foreground_restored':True}
