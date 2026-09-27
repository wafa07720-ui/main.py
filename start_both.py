import subprocess
import time
import os
import sys

def start_flaresolverr():
    """شغل FlareSolverr من /app"""
    print("🚀 Starting FlareSolverr...")
    
    fs_path = '/app/flaresolverr'
    
    print(f"   Binary: {fs_path}")
    
    if not os.path.exists(fs_path):
        print(f"❌ {fs_path} NOT FOUND")
        return None
    
    st = os.stat(fs_path)
    print(f"   Size: {st.st_size}")
    print(f"   Mode: {oct(st.st_mode)[-3:]}")
    
    # ═══ تأكد من Xvfb ═══
    xvfb_check = subprocess.run(['which', 'Xvfb'], capture_output=True, text=True)
    print(f"   Xvfb: {xvfb_check.stdout.strip() or 'NOT FOUND'}")
    
    # ═══ استخدم Chrome اللي جوه FlareSolverr bundle ═══
    chrome_in_bundle = '/app/chrome/chrome'
    chromedriver_in_bundle = '/app/chromedriver'
    
    if os.path.exists(chrome_in_bundle):
        print(f"   Using bundled Chrome: {chrome_in_bundle}")
        chrome_bin = chrome_in_bundle
    else:
        chrome_bin = '/usr/bin/chromium'
        print(f"   Using system Chrome: {chrome_bin}")
    
    if os.path.exists(chromedriver_in_bundle):
        driver_path = chromedriver_in_bundle
    else:
        driver_path = '/usr/bin/chromedriver'
    
    try:
        process = subprocess.Popen(
            [fs_path, '--port', '8191'],
            cwd='/app',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                **os.environ,
                'LOG_LEVEL': 'info',
                'CHROME_BIN': chrome_bin,
                'CHROMEDRIVER_PATH': driver_path,
                'PORT': '8191',
            }
        )
        print(f"✅ FlareSolverr started, PID: {process.pid}")
        return process
    except Exception as e:
        print(f"❌ Failed to start: {e}")
        import traceback
        traceback.print_exc()
        return None


def wait_flaresolverr(max_wait=120):
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
    fs_process = start_flaresolverr()
    
    if fs_process is None:
        print("❌ FlareSolverr failed to start")
        sys.exit(1)
    
    if not wait_flaresolverr():
        print("❌ FlareSolverr didn't respond in time")
        try:
            fs_process.terminate()
            time.sleep(2)
            stdout, stderr = fs_process.communicate(timeout=5)
            print("STDOUT:", stdout.decode()[:3000])
            print("STDERR:", stderr.decode()[:3000])
        except:
            pass
        sys.exit(1)
    
    print("🚀 Starting Bot...")
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
