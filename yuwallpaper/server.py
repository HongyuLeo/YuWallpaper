from __future__ import annotations
import argparse,http.cookies,json,mimetypes,os,secrets,subprocess,sys,threading,time,uuid,webbrowser
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from .imaging import load_image,compose,preview_size,dimensions
from .jobs import Jobs
from .wallpaper import apply_wallpaper,open_folder

WEB=Path(__file__).parent/'web'

def data_directory():
    override=os.environ.get('YUWALLPAPER_DATA')
    if override:return Path(override)
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local'/'share')))/'YuWallpaper'

class Application:
    def __init__(self,data_dir):
        self.data_dir=Path(data_dir);self.data_dir.mkdir(parents=True,exist_ok=True)
        self.jobs=Jobs(self.data_dir);self.token=secrets.token_urlsafe(32)
        self.last_seen=time.time();self.settings={};self.preview_lock=threading.Lock()
        self.devices=json.loads((Path(__file__).parent/'devices.json').read_text('utf-8'))
        try:self.settings=json.loads((self.data_dir/'settings.json').read_text('utf-8'))
        except (OSError,ValueError):pass
    def status(self):
        return {'name':'YuWallpaper','version':'0.2.0','platform':sys.platform,
            'video_ready':(self.data_dir/'video-packages'/'.ready').exists(),
            'ai_ready':(self.data_dir/'ai-packages'/'.ready').exists(),
            'outputs':str(self.data_dir/'outputs'),'settings':self.settings,
            'devices':self.devices,'jobs':self.jobs.snapshot()}

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,app):
        super().__init__(('127.0.0.1',0),Handler);self.app=app
        self.origin=f'http://127.0.0.1:{self.server_port}'

class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args):pass
    def send(self,code,body=b'',ctype='application/json; charset=utf-8',headers=None):
        if isinstance(body,dict):body=json.dumps(body,ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        for k,v in (headers or {}).items():self.send_header(k,v)
        self.end_headers()
        try:self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
    def authorized(self):
        if self.headers.get('Host')!=self.server.origin.split('//')[1]:return False
        if self.headers.get('Origin') not in (None,self.server.origin):return False
        cookie=http.cookies.SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except http.cookies.CookieError:return False
        return 'yu_session' in cookie and secrets.compare_digest(cookie['yu_session'].value,self.server.app.token)
    def stream_file(self,file,download=False):
        total=file.stat().st_size;start,end=0,total-1;code=200
        requested=self.headers.get('Range')
        if requested:
            import re
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',requested)
            if not match or not any(match.groups()):
                self.send(416,b'',headers={'Content-Range':f'bytes */{total}'});return
            first,last=match.groups()
            if first:
                start=int(first);end=min(int(last),end) if last else end
            else:start=max(0,total-int(last))
            if start>end or start>=total:
                self.send(416,b'',headers={'Content-Range':f'bytes */{total}'});return
            code=206
        self.send_response(code)
        self.send_header('Content-Type',mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(end-start+1))
        self.send_header('Accept-Ranges','bytes')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','private, max-age=0')
        if code==206:self.send_header('Content-Range',f'bytes {start}-{end}/{total}')
        if download:self.send_header('Content-Disposition',f'attachment; filename="{file.name}"')
        self.end_headers()
        try:
            with file.open('rb') as stream:
                stream.seek(start);remaining=end-start+1
                while remaining:
                    chunk=stream.read(min(remaining,262144))
                    if not chunk:break
                    self.wfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError):pass
    def read_body(self,limit=1_100_000):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValueError('Invalid content length.')
        if not 0<n<=limit:raise ValueError('Request too large or empty.')
        self.connection.settimeout(60)
        data=self.rfile.read(n)
        if len(data)!=n:raise ValueError('Incomplete request.')
        return data
    def do_GET(self):
        parts=urlsplit(self.path);path=parts.path;qs=parse_qs(parts.query)
        if self.headers.get('Host')!=self.server.origin.split('//')[1]:self.send(403,{'error':'Invalid host'});return
        if path=='/' and 'session' in qs:
            if secrets.compare_digest(qs['session'][0],self.server.app.token):
                self.send(302,b'',headers={'Location':'/','Set-Cookie':f'yu_session={self.server.app.token}; HttpOnly; SameSite=Strict; Path=/'})
                return
        if not self.authorized():self.send(403,{'error':'Open YuWallpaper using its launcher.'});return
        self.server.app.last_seen=time.time()
        try:
            if path=='/api/status':self.send(200,self.server.app.status());return
            if path.startswith('/output/'):
                _,_,job_id,name=path.split('/')
                file=self.server.app.jobs.artifact(job_id,name)
                self.stream_file(file,bool(qs.get('download')))
                return
            if path.startswith('/upload/'):
                image_id=path.split('/')[-1]
                if len(image_id)!=32 or any(x not in '0123456789abcdef' for x in image_id):raise ValueError('Invalid image.')
                self.send(200,(self.server.app.data_dir/'uploads'/f'{image_id}.jpg').read_bytes(),'image/jpeg');return
            files={'/':'index.html','/app.js':'app.js','/style.css':'style.css','/logo.svg':'logo.svg'}
            if path not in files:self.send(404,{'error':'Not found'});return
            file=WEB/files[path]
            self.send(200,file.read_bytes(),mimetypes.guess_type(file.name)[0] or 'text/plain')
        except (OSError,ValueError) as e:self.send(400,{'error':str(e)})
    def do_POST(self):
        if not self.authorized():self.send(403,{'error':'Unauthorized'});return
        self.server.app.last_seen=time.time();path=urlsplit(self.path).path
        try:
            if path=='/api/upload':
                raw=self.read_body(50*1024*1024);image_id=uuid.uuid4().hex
                root=self.server.app.data_dir/'uploads';tmp=root/f'{image_id}.tmp'
                try:
                    tmp.write_bytes(raw);src=load_image(tmp)
                    src.save(root/f'{image_id}.png',compress_level=3)
                    thumb=src.copy();thumb.thumbnail((1600,1600));thumb.save(root/f'{image_id}.jpg',quality=94)
                finally:tmp.unlink(missing_ok=True)
                self.send(200,{'id':image_id,'width':src.width,'height':src.height});return
            data=json.loads(self.read_body())
            if not isinstance(data,dict):raise ValueError('Expected object.')
            if path=='/api/jobs':self.send(200,self.server.app.jobs.submit(data['kind'],data));return
            if path=='/api/cancel':self.server.app.jobs.cancel_job(data['id']);self.send(200,{'ok':True});return
            if path=='/api/preview':
                image_id=str(data['upload'])
                if len(image_id)!=32 or any(x not in '0123456789abcdef' for x in image_id):raise ValueError('Invalid image.')
                size=dimensions(data['width'],data['height'])
                # Return a true composition preview, never an 8K preview allocation.
                with self.server.app.preview_lock:
                    src=load_image(self.server.app.data_dir/'uploads'/f'{image_id}.png')
                    mode='preserve' if data['mode']=='ai' else data['mode']
                    x,y=float(data.get('x',.5)),float(data.get('y',.5))
                    if not(0<=x<=1 and 0<=y<=1):raise ValueError('Invalid position.')
                    im,_=compose(src,preview_size(size),mode,(x,y),data.get('scale',1))
                    import io
                    buff=io.BytesIO();im.save(buff,format='JPEG',quality=93)
                self.send(200,buff.getvalue(),'image/jpeg');return
            if path=='/api/settings':
                settings={'lively':str(data.get('lively',''))[:1000], 'language':data.get('language','zh') if data.get('language','zh') in {'en','zh'} else 'zh'}
                self.server.app.settings=settings
                (self.server.app.data_dir/'settings.json').write_text(json.dumps(settings),encoding='utf-8')
                self.send(200,{'ok':True});return
            if path=='/api/apply':
                artifact=self.server.app.jobs.artifact(data['id'],data['name'])
                if artifact.suffix.lower() not in {'.png','.mp4'}:raise ValueError('Not a wallpaper.')
                apply_wallpaper(artifact,self.server.app.settings.get('lively',''))
                self.send(200,{'ok':True});return
            if path=='/api/open':open_folder(self.server.app.data_dir/'outputs');self.send(200,{'ok':True});return
            if path=='/api/heartbeat':self.send(200,{'ok':True});return
            self.send(404,{'error':'Not found'})
        except (ValueError,KeyError,OSError,RuntimeError,subprocess.SubprocessError) as e:
            self.send(400,{'error':str(e)})
        except Exception as e:
            self.send(500,{'error':f'{type(e).__name__}: {e}'})

def open_app(url):
    if os.name=='nt':
        roots=[os.environ.get('ProgramFiles(x86)',''),os.environ.get('ProgramFiles','')]
        for root in roots:
            edge=Path(root)/'Microsoft'/'Edge'/'Application'/'msedge.exe'
            if edge.is_file():
                subprocess.Popen([str(edge),f'--app={url}','--window-size=1360,920'],creationflags=subprocess.CREATE_NO_WINDOW)
                return
    webbrowser.open(url)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--data-dir',type=Path);args=parser.parse_args()
    app=Application(args.data_dir or data_directory());server=Server(app)
    url=f'{server.origin}/?session={app.token}'
    print(f'YuWallpaper listening on {server.origin}',flush=True)
    # Session URL is deliberately never printed; only launcher hands it to the UI.
    if not args.no_browser:
        open_app(url)
        def stop_when_closed():
            while True:
                time.sleep(10)
                if time.time()-app.last_seen>60 and not app.jobs.busy():server.shutdown();return
        threading.Thread(target=stop_when_closed,daemon=True).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
