import subprocess
import time
import os
import sys

def start_flaresolverr():
    """شغل FlareSolverr في الخلفية"""
    print("🚀 Starting FlareSolverr...")
    print(f"   Working dir: /opt/flaresolverr")
    print(f"   Binary: /opt/flaresolverr/flaresolverr")
    
    # تحقق من وجود الملف
    if not os.path.exists('/opt/flaresolverr/flaresolverr'):
        print("❌ /opt/flaresolverr/flaresolverr NOT FOUND")
        # اطبع محتوى المجلد
        try:
            print("Content of /opt/flaresolverr:")
            for f in os.listdir('/opt/flaresolverr'):
                print(f"   - {f}")
        except:
            pass
        return None
    
    # تحقق من قابلية التنفيذ
    if not os.access('/opt/flaresolverr/flaresolverr', os.X_OK):
        print("❌ Not executable, trying chmod...")
        try:
            os.chmod('/opt/flaresolverr/flaresolverr', 0o755)
        except Exception as e:
            print(f"❌ chmod failed: {e}")
            return None
    
    # شغل FlareSolverr
    try:
        process = subprocess.Popen(
            ['./flaresolverr', '--port', '8191'],
            cwd='/opt/flaresolverr',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, 'LOG_LEVEL': 'info'}
        )
        print(f"✅ FlareSolverr process started, PID: {process.pid}")
        return process
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        return None


def wait_flaresolverr(max_wait=60):
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
        
        if i % 10 == 0 and i > 0:
            print(f"   Still waiting... {i}s")
        
        time.sleep(1)
    
    return False


if __name__ == '__main__':
    # Start FlareSolverr
    fs_process = start_flaresolverr()
    
    if fs_process is None:
        print("❌ FlareSolverr failed to start")
        sys.exit(1)
    
    # Wait for it to be ready
    if not wait_flaresolverr():
        print("❌ FlareSolverr didn't respond in time")
        # اطبع الـ output
        try:
            fs_process.terminate()
            stdout, stderr = fs_process.communicate(timeout=5)
            print("STDOUT:", stdout.decode()[:500])
            print("STDERR:", stderr.decode()[:500])
        except:
            pass
        sys.exit(1)
    
    # Start main bot
    print("🚀 Starting Bot...")
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
