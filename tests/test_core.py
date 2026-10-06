import tempfile,threading,unittest,json,time,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from PIL import Image
from yuwallpaper.imaging import compose,draw_particles,dimensions,load_image
from yuwallpaper.encoder import encode,Cancelled
from yuwallpaper.server import Application,Server

class ImagingTests(unittest.TestCase):
    def test_original_pixels_restored_after_background_processing(self):
        src=Image.new('RGB',(128,256),(12,87,193))
        src.putpixel((15,30),(255,0,0))
        canvas,box=compose(src,(256,512),'preserve',scale=.5)
        self.assertEqual(box[2:],src.size)
        self.assertEqual(canvas.crop((box[0],box[1],box[0]+128,box[1]+256)).tobytes(),src.tobytes())
    def test_crop_is_full_canvas(self):
        src=Image.new('RGB',(900,500),'red')
        im,_=compose(src,(256,512),'crop')
        self.assertEqual(im.size,(256,512));self.assertEqual(im.getpixel((0,0)),(255,0,0))
    def test_animation_periodicity_and_protection(self):
        src=Image.new('RGB',(320,240),(45,78,91))
        for effect in ('snow','fireflies'):
            self.assertEqual(draw_particles(src,0,8,effect).tobytes(),draw_particles(src,8,8,effect).tobytes())
            frame=draw_particles(src,3,8,effect,protect=(.2,.2,.6,.6))
            self.assertEqual(frame.crop((64,48,256,192)).tobytes(),src.crop((64,48,256,192)).tobytes())
    def test_invalid_dimensions(self):
        for size in [(0,1080),(8192,8192),(-1,256),(128,256)]:
            with self.assertRaises(ValueError):dimensions(*size)
    def test_exif_orientation_applied(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'source.jpg';im=Image.new('RGB',(300,500));exif=Image.Exif();exif[274]=6;im.save(p,exif=exif)
            self.assertEqual(load_image(p).size,(500,300))
    def test_video_encoding_and_cancel(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'loop.mp4'
            encode(Image.new('RGB',(320,240),'navy'),target,4,24,'snow',None,threading.Event(),lambda *args:None)
            self.assertGreater(target.stat().st_size,1000)
            cancel=threading.Event();cancel.set()
            with self.assertRaises(Cancelled):
                encode(Image.new('RGB',(320,240),'navy'),Path(td)/'cancelled.mp4',4,24,'snow',None,cancel,lambda *a:None)
            self.assertFalse((Path(td)/'cancelled.mp4').exists())

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.app=Application(cls.tmp.name);cls.server=Server(cls.app)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=cls.server.origin
        cls.cookies=http.cookiejar.CookieJar();cls.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cls.cookies))
        cls.client.open(cls.url+'/?session='+cls.app.token).read()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()
    def test_auth_required(self):
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(self.url+'/api/status')
        self.assertEqual(error.exception.code,403)
    def test_no_cross_origin_mutation(self):
        r=urllib.request.Request(self.url+'/api/settings',data=b'{}',headers={'Origin':'https://evil.example','Cookie':f'yu_session={self.app.token}'})
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(r)
        self.assertEqual(error.exception.code,403)
    def test_no_arbitrary_file_read(self):
        with self.assertRaises(urllib.error.HTTPError):self.client.open(self.url+'/../../main.py')
    def test_upload_export_and_metadata(self):
        import io
        b=io.BytesIO();Image.new('RGB',(320,480),'#445588').save(b,format='PNG')
        r=urllib.request.Request(self.url+'/api/upload',data=b.getvalue())
        upload=json.loads(self.client.open(r).read())
        r=urllib.request.Request(self.url+'/api/jobs',data=json.dumps({'kind':'image','upload':upload['id'],'width':512,'height':768,'mode':'preserve'}).encode(),headers={'Content-Type':'application/json'})
        job=json.loads(self.client.open(r).read())
        deadline=time.time()+15
        while time.time()<deadline:
            jobs=json.loads(self.client.open(self.url+'/api/status').read())['jobs']
            if jobs[0]['state'] in {'done','failed'}:break
            time.sleep(.05)
        self.assertEqual(jobs[0]['state'],'done',jobs[0])
        metadata=json.loads(self.client.open(self.url+f'/output/{job["id"]}/metadata.json').read())
        self.assertEqual(metadata['output_size'],[512,768]);self.assertFalse(metadata['cloud_inference'])
        request=urllib.request.Request(self.url+f'/output/{job["id"]}/YuWallpaper.png',headers={'Range':'bytes=0-7'})
        with self.client.open(request) as response:
            self.assertEqual(response.status,206)
            self.assertEqual(response.read(),b'\x89PNG\r\n\x1a\n')
        from yuwallpaper.jobs import Jobs
        resumed=Jobs(self.tmp.name)
        self.assertEqual(resumed.items[job['id']].state,'done')
    def test_queue_cancel(self):
        job=self.app.jobs.submit('image',{'upload':'invalid'})
        self.app.jobs.cancel_job(job['id'])
        deadline=time.time()+3
        while time.time()<deadline:
            item=self.app.jobs.items[job['id']]
            if item.state in {'failed','cancelled'}:break
            time.sleep(.02)
        self.assertIn(item.state,('failed','cancelled'))

if __name__=='__main__':unittest.main()
