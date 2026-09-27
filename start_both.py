import subprocess
import time
import os
import sys

def start_flaresolverr():
    """شغل FlareSolverr من /app"""
    print("🚀 Starting FlareSolverr...")
    
    fs_path = '/app/flaresolverr'
    
    print(f"   Binary: {fs_path}")
    
    # تحقق من وجود الملف
    if not os.path.exists(fs_path):
        print(f"❌ {fs_path} NOT FOUND")
        try:
            print("Content of /app:")
            for f in os.listdir('/app'):
                p = os.path.join('/app', f)
                st = os.stat(p)
                print(f"   - {f} (mode: {oct(st.st_mode)[-3:]})")
        except Exception as e:
            print(f"Error listing: {e}")
        return None
    
    # معلومات عن الملف
    st = os.stat(fs_path)
    print(f"   Size: {st.st_size}")
    print(f"   Mode: {oct(st.st_mode)[-3:]}")
    
    # تحقق من قابلية التنفيذ
    if not os.access(fs_path, os.X_OK):
        print("❌ Not executable, trying chmod...")
        try:
            os.chmod(fs_path, 0o755)
            print("✅ chmod 755 done")
        except Exception as e:
            print(f"❌ chmod failed: {e}")
            return None
    
    # شغل FlareSolverr
    try:
        process = subprocess.Popen(
            [fs_path, '--port', '8191'],
            cwd='/app',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                **os.environ,
                'LOG_LEVEL': 'info',
                'CHROME_BIN': '/usr/bin/chromium',
                'CHROMEDRIVER_PATH': '/app/chromedriver',
            }
        )
        print(f"✅ FlareSolverr started, PID: {process.pid}")
        return process
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        import traceback
        traceback.print_exc()
        return None


def wait_flaresolverr(max_wait=90):
    """استنى FlareSolverr يشتغل"""
    import requests
    
    print(f"⏳ Waiting for FlareSolverr (max {max_wait}s)...")
    
    for i in range(max_wait):
        try:
            r = requests.post('http://localhost:8191/v1', json={
                'cmd': 'sessions.list'
            }, timeout=3)
            if r.status_code == 200:
                print(f"✅ FlareSolverr ready after {i}s")
                return True
        except:
            pass
        
        if i % 15 == 0 and i > 0:
            print(f"   Still waiting... {i}s")
        
        time.sleep(1)
    
    return False


if __name__ == '__main__':
    # Start FlareSolverr
    fs_process = start_flaresolverr()
    
    if fs_process is None:
        print("❌ FlareSolverr failed to start")
        sys.exit(1)
    
    # Wait
    if not wait_flaresolverr():
        print("❌ FlareSolverr didn't respond in time")
        try:
            fs_process.terminate()
            time.sleep(2)
            stdout, stderr = fs_process.communicate(timeout=5)
            print("STDOUT:", stdout.decode()[:1000])
            print("STDERR:", stderr.decode()[:1000])
        except:
            pass
        sys.exit(1)
    
    # Start main bot
    print("🚀 Starting Bot...")
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
