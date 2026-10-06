import unittest,tempfile,json,threading,base64,io,sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw
from yuwallpaper import motion
class MotionTests(unittest.TestCase):
 def mask(self,empty=False):
  im=Image.new('L',(256,256))
  if not empty:ImageDraw.Draw(im).rectangle((80,60,180,150),fill=255)
  b=io.BytesIO();im.save(b,format='PNG');return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
 def test_mask_preserves_outside_and_protected_region(self):
  m=motion.load_mask(self.mask(),(512,512),(.4,.3,.1,.1))
  self.assertEqual(m.getpixel((159,130)),0);self.assertEqual(m.getpixel((230,175)),0);self.assertGreater(m.getpixel((300,250)),0)
 def test_invalid_and_empty_masks(self):
  for data in [None,'file:///etc/passwd','data:image/png;base64,!!!',self.mask(True)]:
   with self.assertRaises(ValueError):motion.load_mask(data,(256,256))
 def test_loop_boundary(self):
  seq=list(motion.frame_schedule(49,240,'pingpong'));self.assertEqual(seq[0][0],0);self.assertEqual(seq[-1][0],0)
  self.assertLessEqual(max(abs(a[0]-b[0]) for a,b in zip(seq,seq[1:])),1)
  fade=list(motion.frame_schedule(49,240,'fade'));self.assertEqual(fade[0][1],0);self.assertLess(fade[-1][1],.01)
 def test_synthetic_pipeline_preserves_original(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'video-packages').mkdir();(root/'video-packages'/'.ready').touch();work=root/'work';work.mkdir()
   base=Image.new('RGB',(256,256),(20,60,90));captured=[]
   def worker(req,work,cancel,progress):
    folder=work/'frames';folder.mkdir()
    for i,color in enumerate(('red','green')):Image.new('RGB',(256,256),color).save(folder/f'{i:04d}.png')
    (folder/'frames.json').write_text(json.dumps({'count':2,'width':256,'height':256,'model':'TEST_DOUBLE','native_fps':24}))
   def encoder(frames,size,target,fps,count,cancel,progress):
    for im in frames:
     self.assertEqual(im.crop((0,0,75,256)).tobytes(),base.crop((0,0,75,256)).tobytes());captured.append(im)
    self.assertEqual(len(captured),count)
   opts={'motion_mask':self.mask(),'duration':4,'fps':24,'loop_method':'fade','blink':True,'ai_quality':'draft'}
   with patch.object(motion,'run_worker',worker),patch.object(motion,'encode_frames',encoder):
    info=motion.generate(base,root/'out.mp4',opts,root,work,threading.Event(),lambda *a:None)
   self.assertEqual(captured[0].tobytes(),base.tobytes());self.assertTrue(info['blink_requested']);self.assertFalse(info['blink_quality_verified'])
 def test_no_cuda_before_model_download(self):
  from yuwallpaper import video_worker
  with tempfile.TemporaryDirectory() as td:
   req=Path(td)/'request.json';req.write_text(json.dumps({'packages':td,'cache':td,'check_only':True}))
   fake=type('Torch',(),{'cuda':type('Cuda',(),{'is_available':staticmethod(lambda:False)})})()
   with patch.dict(sys.modules,{'torch':fake}),patch.object(sys,'argv',['worker',str(req)]):
    with self.assertRaisesRegex(RuntimeError,'Model download has not started'):video_worker.main()
 def test_request_contract(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);req=motion.request_for(Image.new('RGB',(768,432)),{'blink':False,'ai_quality':'standard'},root,root)
   self.assertEqual((req['frames']-1)%4,0);self.assertTrue(all(x%32==0 for x in req['inference_size']));self.assertIn('no blinking',req['prompt'])
if __name__=='__main__':unittest.main()
