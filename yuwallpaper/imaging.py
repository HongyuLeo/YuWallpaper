from __future__ import annotations
import math
from PIL import Image, ImageOps, ImageFilter, ImageDraw

Image.MAX_IMAGE_PIXELS = 100_000_000

def dimensions(width, height):
    w, h = int(width), int(height)
    if not (256 <= w <= 8192 and 256 <= h <= 8192 and w*h <= 40_000_000):
        raise ValueError('Dimensions must be 256–8192 pixels, up to 40 megapixels.')
    return w, h

def load_image(path):
    with Image.open(path) as src:
        if src.format not in {'PNG', 'JPEG', 'WEBP', 'BMP'}:
            raise ValueError('Please use PNG, JPEG, WebP or BMP.')
        src.load()
        src = ImageOps.exif_transpose(src)
        if src.mode in ('RGBA', 'LA') or 'transparency' in src.info:
            bg = Image.new('RGBA', src.size, '#e9e9e9')
            src = Image.alpha_composite(bg, src.convert('RGBA'))
        return src.convert('RGB')

def placement(src_size, size, position=(0.5,0.5), scale=1.):
    sw, sh = src_size; w, h = size
    ratio = min(w/sw,h/sh)*max(.25,min(1.,float(scale)))
    pw, ph = max(1, round(sw*ratio)), max(1, round(sh*ratio))
    x = round((w-pw)*max(0.,min(1.,float(position[0]))))
    y = round((h-ph)*max(0.,min(1.,float(position[1]))))
    return x,y,pw,ph

def compose(src, size, mode='preserve', position=(.5,.5), scale=1.):
    size = dimensions(*size)
    if mode == 'crop':
        ratio = max(size[0]/src.width, size[1]/src.height)
        pw,ph = round(src.width*ratio),round(src.height*ratio)
        im = src.resize((pw,ph),Image.Resampling.LANCZOS)
        x=round((pw-size[0])*position[0]); y=round((ph-size[1])*position[1])
        return im.crop((x,y,x+size[0],y+size[1])), (0,0,*size)
    if mode not in {'preserve','ai'}:
        raise ValueError('Unknown layout mode.')
    # Background-only blur; original foreground is pasted after all processing.
    background = ImageOps.fit(src,size,method=Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(max(size)/70))
    box = placement(src.size,size,position,scale)
    x,y,pw,ph=box
    background.paste(src.resize((pw,ph),Image.Resampling.LANCZOS),(x,y))
    return background,box

def preview_size(size, edge=1280):
    ratio=min(1,edge/max(size))
    return max(1,round(size[0]*ratio)),max(1,round(size[1]*ratio))

def draw_particles(base,t,duration,effect='snow',amount=90,seed=23,protect=None):
    """Toroidal particles repeat exactly at t=duration; never warp the source."""
    if effect == 'none': return base.copy()
    if effect not in {'snow','fireflies'}: raise ValueError('Unknown effect.')
    def rand():
        nonlocal seed
        seed=(1664525*seed+1013904223)&0xffffffff
        return seed/4294967296
    w,h=base.size
    overlay=Image.new('RGBA',base.size)
    draw=ImageDraw.Draw(overlay)
    phase=(float(t)/duration)%1
    for i in range(amount):
        px,py=rand(),rand()
        r=max(1,round((.0008+rand()*.0015)*min(w,h)))
        if effect == 'snow':
            # Integral turns make both position and drift periodic.
            turns=1+int(rand()*2)
            x=(px+.025*math.sin(2*math.pi*(phase+py)))%1*w
            y=((py+phase*turns)%1)*h
            color=(255,255,255,round(75+rand()*95))
        else:
            x=(px+.02*math.sin(2*math.pi*(phase+py)))*w
            y=(py+.025*math.cos(2*math.pi*(phase+px)))*h
            a=round(130*(.35+.65*(.5+.5*math.sin(2*math.pi*(phase+px)))))
            color=(255,216,146,a)
        draw.ellipse((x-r,y-r,x+r,y+r),fill=color)
    if protect:
        x,y,bw,bh=protect
        draw.rectangle((round(x*w),round(y*h),round((x+bw)*w),round((y+bh)*h)),fill=(0,0,0,0))
    return Image.alpha_composite(base.convert('RGBA'),overlay).convert('RGB')
