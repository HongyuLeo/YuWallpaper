"""Create original procedural demonstration artwork."""
from pathlib import Path
import math,random
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]/'docs';w,h=2400,1500
im=Image.new('RGB',(w,h));pixels=im.load()
for y in range(h):
 f=y/h
 for x in range(w):pixels[x,y]=(round(229-44*f),round(226-22*f),round(207-11*f))
d=ImageDraw.Draw(im);d.ellipse((1600,175,1738,313),fill=(246,242,220));rng=random.Random(8)
for level,(base,color,amp) in enumerate([(690,(174,189,171),85),(800,(139,163,150),110),(980,(91,129,116),160)]):
 points=[(x,base+amp*math.sin(x/400+level)+amp*.2*math.sin(x/140+level)) for x in range(-100,w+101,30)]
 d.polygon(points+[(w,h),(0,h)],fill=color)
d.polygon([(0,1050),(w,1000),(w,h),(0,h)],fill=(148,176,165))
for i in range(140):
 y=rng.randrange(1060,h);x=rng.randrange(w);length=rng.randrange(15,180)
 d.line((x,y,x+length,y),fill=(179,199,181) if i%3 else (132,166,157),width=rng.randrange(1,4))
d.polygon([(0,1290),(700,1210),(960,1240),(920,h),(0,h)],fill=(69,101,87));d.line((450,1350,475,710),fill=(50,83,67),width=20)
for cx,cy,r in [(480,710,140),(395,770,125),(570,780,120),(475,855,130)]:d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(61,96,73))
root.mkdir(exist_ok=True);im.save(root/'demo-landscape.png')
