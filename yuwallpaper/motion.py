"""Local AI motion contracts and protected-region compositor."""
import base64,io,json,math,os
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter,ImageChops
from .imaging import preview_size
from .ai import run_process,python_exe,PACKAGES
from .encoder import encode_frames,Cancelled

VIDEO_PACKAGES=[p for p in PACKAGES if not p.startswith('torch')]+['torch==2.7.1+cu128','torchvision==0.22.1+cu128','ftfy==6.3.1','sentencepiece==0.2.1']

def install_video(data_dir,cancel,progress):
    target=data_dir/'video-packages';target.mkdir(exist_ok=True)
    progress(5,'Installing CUDA video runtime; several GB download, independent from image runtime')
    run_process([python_exe(),'-m','pip','install','--only-binary=:all:','--upgrade','--target',str(target),
        '--extra-index-url','https://download.pytorch.org/whl/cu128',*VIDEO_PACKAGES],cancel,progress)
    (target/'.ready').write_text('YuWallpaper Wan video runtime 0.2\n')
    progress(100,'Video runtime installed. Check GPU before downloading the model.')

def inference_size(size,quality):
    edge=768 if quality=='draft' else 1280
    w,h=preview_size(size,edge)
    return max(64,round(w/32)*32),max(64,round(h/32)*32)

def load_mask(data,size,protect=None):
    if not isinstance(data,str) or not data.startswith('data:image/png;base64,') or len(data)>1_000_000:
        raise ValueError('Paint the hair/eye motion regions on the preview first.')
    try:
        payload=base64.b64decode(data.split(',',1)[1],validate=True)
        with Image.open(io.BytesIO(payload)) as im:
            if im.width>1600 or im.height>1600:raise ValueError('Motion mask too large.')
            im.load();hard=im.convert('L').resize(size,Image.Resampling.NEAREST)
    except (OSError,ValueError) as e:raise ValueError('Invalid motion mask.') from e
    if protect:
        x,y,w,h=protect
        ImageDraw.Draw(hard).rectangle((round(x*size[0]),round(y*size[1]),round((x+w)*size[0]),round((y+h)*size[1])),fill=0)
    if hard.getbbox() is None:raise ValueError('No selected motion region remains after protection.')
    # Feather inwards only: pixels outside the selection remain EXACTLY original.
    return ImageChops.multiply(hard,hard.filter(ImageFilter.GaussianBlur(max(size)/350)))

def frame_schedule(count,output_count,loop):
    if count<2 or output_count<2:raise ValueError('Not enough frames.')
    for i in range(output_count):
        phase=i/output_count
        if loop=='pingpong':
            u=(1-math.cos(2*math.pi*phase))/2
            yield min(count-1,round(u*(count-1))),1.
        elif loop=='fade':
            # Original-image envelope, not a double-exposed last/first-frame crossfade.
            envelope=min(1.,phase/.1,(1-phase)/.1)
            envelope=.5-.5*math.cos(math.pi*max(0,envelope))
            yield min(count-1,round(phase*(count-1))),envelope
        else:raise ValueError('Invalid loop method.')

def request_for(base,options,data_dir,work_dir):
    quality=options.get('ai_quality','draft')
    if quality not in {'draft','standard'}:raise ValueError('Invalid AI quality.')
    blink=bool(options.get('blink',False))
    prompt='Locked camera, identical framing, stationary head and torso, gentle natural breeze moving loose hair strands, stable background and lighting.'
    prompt+=(' One slow natural blink, eyelids close fully and reopen smoothly.' if blink else ' Eyes remain open, no blinking, fixed expression.')
    prompt+=' '+str(options.get('motion_prompt',''))[:800]
    base.save(work_dir/'video-input.png',compress_level=1)
    return {'packages':str(data_dir/'video-packages'),'cache':str(data_dir/'models'),
        'input':str(work_dir/'video-input.png'),'frames_dir':str(work_dir/'frames'),
        'inference_size':inference_size(base.size,quality),'frames':49 if quality=='draft' else 97,
        'steps':24 if quality=='draft' else 40,'seed':int(options.get('seed',23)),
        'prompt':prompt,'negative':'camera motion, head turning, body movement, deformed face, changing identity, flicker, ghosting, duplicate features, unnatural eyes, extra limbs, text, watermark'}

def check_gpu(data_dir,work_dir,cancel,progress):
    req={'packages':str(data_dir/'video-packages'),'cache':str(data_dir/'models'),'check_only':True}
    run_worker(req,work_dir,cancel,progress)

def run_worker(req,work_dir,cancel,progress):
    request=work_dir/'video-request.json';request.write_text(json.dumps(req),encoding='utf-8')
    env=os.environ.copy();env['PYTHONUNBUFFERED']='1'
    run_process([python_exe(),str(Path(__file__).with_name('video_worker.py')),str(request)],cancel,progress,env)

def generate(base,target,options,data_dir,work_dir,cancel,progress):
    if not (data_dir/'video-packages'/'.ready').exists():raise ValueError('Install the local AI video runtime in Settings first.')
    mask=load_mask(options.get('motion_mask'),base.size,options.get('protect'))
    req=request_for(base,options,data_dir,work_dir)
    run_worker(req,work_dir,cancel,progress)
    info=json.loads((work_dir/'frames'/'frames.json').read_text('utf-8'))
    duration=int(options.get('duration',8));fps=int(options.get('fps',30));loop=options.get('loop_method','pingpong')
    if duration not in {4,8,16} or fps not in {24,30,60}:raise ValueError('Unsupported video timing.')
    def frames():
        previous=-1;image=None
        for index,amount in frame_schedule(info['count'],duration*fps,loop):
            if cancel.is_set():raise Cancelled()
            if index!=previous:
                with Image.open(work_dir/'frames'/f'{index:04d}.png') as source:
                    image=source.convert('RGB').resize(base.size,Image.Resampling.LANCZOS)
                previous=index
            animated=Image.composite(image,base,mask)
            yield Image.blend(base,animated,amount) if amount<1 else animated
    encode_frames(frames(),base.size,target,fps,duration*fps,cancel,
        lambda p,m:progress(72+round(p*.27),m))
    mask.save(target.parent/'motion-mask.png')
    return {**info,'loop_method':loop,'blink_requested':bool(options.get('blink',False)),
        'static_pixels_restored':True,'unselected_pixels_unchanged_before_encoding':True,
        'blink_quality_verified':False,'inference_steps':req['steps'],'seed':req['seed']}
