from __future__ import annotations
import json,queue,threading,time,uuid
from dataclasses import dataclass,field
from pathlib import Path
from PIL import Image
from .imaging import load_image,compose,dimensions,preview_size
from .encoder import encode,Cancelled
from . import ai,motion

@dataclass
class Job:
    id:str
    kind:str
    options:dict
    state:str='queued'
    percent:int=0
    message:str='Queued'
    artifacts:list=field(default_factory=list)
    cancel:threading.Event=field(default_factory=threading.Event)
    created:float=field(default_factory=time.time)
    def public(self):
        return {k:getattr(self,k) for k in ('id','kind','state','percent','message','artifacts','created')}

class Jobs:
    def __init__(self,data_dir):
        self.data_dir=Path(data_dir);self.items={};self.queue=queue.Queue();self.lock=threading.Lock()
        for p in ('uploads','outputs','work'): (self.data_dir/p).mkdir(parents=True,exist_ok=True)
        # Reload completed exports; interrupted work is never promoted as complete.
        for directory in sorted((self.data_dir/'outputs').iterdir(),key=lambda p:p.stat().st_mtime):
            if not directory.is_dir():continue
            try:
                meta=json.loads((directory/'metadata.json').read_text('utf-8'))
                kind='video' if (directory/'YuWallpaper.mp4').is_file() else 'image'
                primary='YuWallpaper.mp4' if kind=='video' else 'YuWallpaper.png'
                if not (directory/primary).is_file() or not (directory/'preview.jpg').is_file():continue
                j=Job(directory.name,kind,{},state='done',percent=100,message='Completed',created=meta['created_at'])
                j.artifacts=[{'name':n,'bytes':(directory/n).stat().st_size} for n in [primary,'preview.jpg','metadata.json']+(['motion-mask.png'] if (directory/'motion-mask.png').exists() else [])]
                self.items[j.id]=j
            except (OSError,ValueError,KeyError):continue
        threading.Thread(target=self._worker,daemon=True).start()
    def submit(self,kind,options):
        if kind not in {'image','video','install-ai','install-video','check-video'}:raise ValueError('Unknown task.')
        with self.lock:
            if sum(x.state in {'queued','running'} for x in self.items.values())>=4:
                raise ValueError('Queue is full. Wait for an existing task.')
            j=Job(uuid.uuid4().hex,kind,options);self.items[j.id]=j
        self.queue.put(j);return j.public()
    def progress(self,j,percent,message):
        with self.lock:
            if percent is not None:j.percent=int(percent)
            j.message=message
    def snapshot(self):
        with self.lock:return [j.public() for j in reversed(list(self.items.values()))]
    def busy(self):
        with self.lock:return any(j.state in {'queued','running'} for j in self.items.values())
    def artifact(self,job_id,name):
        with self.lock:
            j=self.items.get(job_id)
            if not j or j.state!='done' or name not in [a['name'] for a in j.artifacts]:
                raise FileNotFoundError('Output is not available.')
        return self.data_dir/'outputs'/job_id/name
    def cancel_job(self,job_id):
        with self.lock:
            if job_id not in self.items:raise ValueError('Unknown task.')
            j=self.items[job_id]
            if j.state in {'queued','running'}:j.cancel.set()
    def _worker(self):
        while True:
            j=self.queue.get()
            try:
                if j.cancel.is_set():raise Cancelled()
                with self.lock:j.state='running'
                self._run(j)
                if j.cancel.is_set():raise Cancelled()
                with self.lock:
                    j.state='done';j.percent=100
                    if j.kind!='check-video':j.message='Completed'
            except Cancelled:
                with self.lock:j.state='cancelled';j.message='Cancelled';j.artifacts=[]
                import shutil
                shutil.rmtree(self.data_dir/'outputs'/j.id,ignore_errors=True)
            except Exception as e:
                with self.lock:j.state='failed';j.message=str(e)[:2000];j.artifacts=[]
                import shutil
                shutil.rmtree(self.data_dir/'outputs'/j.id,ignore_errors=True)
            finally:
                import shutil
                shutil.rmtree(self.data_dir/'work'/j.id,ignore_errors=True)
                self.queue.task_done()
    def _run(self,j):
        progress=lambda p,m:self.progress(j,p,m)
        if j.kind=='install-ai':
            ai.install_ai(self.data_dir,j.cancel,progress);return
        if j.kind=='install-video':
            motion.install_video(self.data_dir,j.cancel,progress);return
        if j.kind=='check-video':
            work=self.data_dir/'work'/j.id;work.mkdir()
            motion.check_gpu(self.data_dir,work,j.cancel,progress);return
        o=j.options
        upload=str(o.get('upload',''))
        if len(upload)!=32 or any(x not in '0123456789abcdef' for x in upload):raise ValueError('Invalid image reference.')
        src=load_image(self.data_dir/'uploads'/f'{upload}.png')
        size=dimensions(o.get('width',7680),o.get('height',4320))
        position=(float(o.get('x',.5)),float(o.get('y',.5)))
        if any(not 0<=x<=1 for x in position):raise ValueError('Position must be 0–1.')
        scale=float(o.get('scale',1))
        if not .25<=scale<=1:raise ValueError('Scale must be 0.25–1.')
        mode=o.get('mode','preserve')
        output=self.data_dir/'outputs'/j.id;output.mkdir()
        work=self.data_dir/'work'/j.id;work.mkdir()
        meta={'application':'YuWallpaper','source_size':list(src.size),'output_size':list(size),
              'layout':mode,'export_detail':'Resampled original; exported pixel dimensions do not imply native 8K detail.',
              'cloud_inference':False,'device':o.get('device','custom'),'created_at':time.time()}
        progress(5,'Preparing original image')
        if mode=='ai':
            base,info=ai.expand(src,size,position,scale,
                str(o.get('prompt','quiet scenic background, coherent lighting, no people'))[:1000],
                self.data_dir,work,j.cancel,progress)
            meta['ai']=info
        else:base,_=compose(src,size,mode,position,scale)
        if j.cancel.is_set():raise Cancelled()
        if j.kind=='image':
            name='YuWallpaper.png';progress(92,'Saving full-resolution PNG')
            base.save(output/name,compress_level=3)
        else:
            # Deliberate independent video resolution: default 4K, optional full size.
            edge=int(o.get('video_edge',3840))
            if edge not in {1920,3840,7680,8192}:raise ValueError('Unsupported video resolution.')
            vs=preview_size(size,edge);vs=tuple(x-x%2 for x in vs)
            frame=base.resize(vs,Image.Resampling.LANCZOS) if vs!=size else base
            name='YuWallpaper.mp4'
            protect=o.get('protect')
            if protect is not None:
                if len(protect)!=4 or any(not 0<=float(v)<=1 for v in protect):raise ValueError('Invalid protected region.')
                protect=[float(v) for v in protect]
                if protect[0]+protect[2]>1.001 or protect[1]+protect[3]>1.001:raise ValueError('Protected region exceeds canvas.')
            effect=o.get('effect','snow')
            meta.update({'output_size':list(vs),'duration':int(o.get('duration',8)),
                         'fps':int(o.get('fps',30)),'effect':effect,'protected_region':protect,
                         'video_method':'Deterministic local compositing, not generative video.'})
            if o.get('video_engine','particles')=='wan':
                meta['video_method']='Local Wan2.2 image-to-video with selected-region original restoration'
                meta['ai_video']=motion.generate(frame,output/name,o,self.data_dir,work,j.cancel,progress)
            else:
                encode(frame,output/name,meta['duration'],meta['fps'],effect,protect,j.cancel,progress)
        thumbnail=base.copy();thumbnail.thumbnail((1280,1280));thumbnail.save(output/'preview.jpg',quality=92)
        (output/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        with self.lock:j.artifacts=[{'name':n,'bytes':(output/n).stat().st_size} for n in [name,'preview.jpg','metadata.json']+(['motion-mask.png'] if (output/'motion-mask.png').exists() else [])]
