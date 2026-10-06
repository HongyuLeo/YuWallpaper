"""Optional isolated local inference worker. No API keys or cloud inference."""
import argparse,json,os,sys
from pathlib import Path

def emit(percent,message):print(json.dumps({'percent':percent,'message':message}),flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('request');args=p.parse_args()
    data=json.loads(Path(args.request).read_text('utf-8'))
    sys.path.insert(0,data['packages'])
    os.environ['HF_HOME']=data['cache']
    import torch
    from PIL import Image,ImageOps
    from diffusers import StableDiffusionInpaintPipeline
    emit(12,'Loading / downloading local inpainting model (several GB on first use)')
    device='cuda' if torch.cuda.is_available() else 'cpu'
    dtype=torch.float16 if device=='cuda' else torch.float32
    pipe=StableDiffusionInpaintPipeline.from_pretrained(
        'stable-diffusion-v1-5/stable-diffusion-inpainting',torch_dtype=dtype,
        use_safetensors=True)
    pipe=pipe.to(device);pipe.enable_attention_slicing()
    if device=='cuda':pipe.enable_vae_slicing()
    im=Image.open(data['canvas']).convert('RGB')
    mask=Image.open(data['mask']).convert('L')
    def step_callback(pipeline,step,timestep,kwargs):
        emit(20+int((step+1)/data['steps']*65),f'Local AI inference · {device} · step {step+1}/{data["steps"]}')
        return kwargs
    emit(20,'Generating background locally')
    result=pipe(prompt=data['prompt'],negative_prompt='people, face, body, text, watermark, blurry, low quality',
                image=im,mask_image=mask,width=im.width,height=im.height,
                num_inference_steps=data['steps'],guidance_scale=7.5,
                generator=torch.Generator(device=device).manual_seed(23),
                callback_on_step_end=step_callback).images[0]
    # Do not treat a filtered all-black model result as a usable wallpaper.
    if result.getextrema()==((0,0),(0,0),(0,0)):
        raise RuntimeError('The local model did not return a usable image.')
    result.save(data['output']);emit(90,'Background generated; restoring original image')

if __name__=='__main__':main()
