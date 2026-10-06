"""Isolated Wan2.2 TI2V image-to-video worker (Diffusers 0.35.2)."""
import json,os,sys
from pathlib import Path

def emit(p,m):print(json.dumps({'percent':p,'message':m}),flush=True)

def main():
    req=json.loads(Path(sys.argv[1]).read_text('utf-8'))
    sys.path.insert(0,req['packages']);os.environ['HF_HOME']=req['cache']
    import torch
    if not torch.cuda.is_available():raise RuntimeError('CUDA is unavailable. Install/update the NVIDIA driver and the video runtime. Model download has not started.')
    memory=torch.cuda.get_device_properties(0).total_memory
    emit(5,f'{torch.cuda.get_device_name(0)} · {memory/1024**3:.1f} GiB VRAM')
    if memory<22*1024**3:raise RuntimeError('This preset requires a 24 GB-class NVIDIA GPU. Use particle mode on this computer.')
    if req.get('check_only'):return
    from PIL import Image
    from diffusers import WanImageToVideoPipeline,AutoencoderKLWan
    model='Wan-AI/Wan2.2-TI2V-5B-Diffusers'
    emit(8,'Loading/downloading Wan2.2 model; first download can be tens of GB')
    vae=AutoencoderKLWan.from_pretrained(model,subfolder='vae',torch_dtype=torch.float32)
    # Explicit I2V class is required: the repository default WanPipeline is T2V.
    pipe=WanImageToVideoPipeline.from_pretrained(model,vae=vae,torch_dtype=torch.bfloat16,
        image_encoder=None,image_processor=None)
    pipe.enable_model_cpu_offload();pipe.vae.enable_tiling()
    image=Image.open(req['input']).convert('RGB')
    width,height=req['inference_size'];image=image.resize((width,height),Image.Resampling.LANCZOS)
    steps=req['steps']
    def callback(pipeline,step,timestep,kwargs):
        emit(15+int((step+1)/steps*55),f'Generating locally · {step+1}/{steps}')
        return kwargs
    result=pipe(image=image,prompt=req['prompt'],negative_prompt=req['negative'],
        width=width,height=height,num_frames=req['frames'],num_inference_steps=steps,
        guidance_scale=5.0,max_sequence_length=256,
        generator=torch.Generator(device='cpu').manual_seed(req['seed']),
        callback_on_step_end=callback,output_type='pil').frames[0]
    folder=Path(req['frames_dir']);folder.mkdir(exist_ok=True)
    for i,frame in enumerate(result):frame.convert('RGB').save(folder/f'{i:04d}.png',compress_level=1)
    (folder/'frames.json').write_text(json.dumps({'count':len(result),'width':width,'height':height,
        'model':model,'native_fps':24}),encoding='utf-8')
    emit(72,'AI frames saved; restoring unselected original regions')

if __name__=='__main__':main()
