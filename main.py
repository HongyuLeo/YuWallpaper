import traceback
from yuwallpaper.server import main, data_directory
if __name__=='__main__':
    try:
        main()
    except Exception:
        error=traceback.format_exc()
        folder=data_directory();folder.mkdir(parents=True,exist_ok=True)
        (folder/'startup-error.log').write_text(error,encoding='utf-8')
        import os
        if os.name=='nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,'YuWallpaper could not start. Details: '+str(folder/'startup-error.log'),'YuWallpaper',16)
        else:
            raise
