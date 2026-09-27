import subprocess
import time
import os
import sys


def start_flaresolverr():
    print("🚀 Starting FlareSolverr...")
    
    fs_path = '/app/flaresolverr'
    
    if not os.path.exists(fs_path):
        print(f"❌ {fs_path} NOT FOUND")
        return None
    
    # ═══ استخدم Chrome اللي في bundle ═══
    chrome_bin = '/app/chrome/chrome'
    driver_path = '/app/chromedriver'
    
    # تأكد من وجودهم
    if not os.path.exists(chrome_bin):
        print(f"❌ {chrome_bin} NOT FOUND, fallback to system")
        chrome_bin = '/usr/bin/chromium'
    
    if not os.path.exists(driver_path):
        print(f"❌ {driver_path} NOT FOUND, fallback to system")
        driver_path = '/usr/bin/chromedriver'
    
    print(f"   CHROME_BIN: {chrome_bin}")
    print(f"   CHROMEDRIVER_PATH: {driver_path}")
    
    try:
        chrome_version = subprocess.check_output([chrome_bin, '--version'], timeout=5).decode().strip()
        print(f"   Chrome version: {chrome_version}")
    except Exception as e:
        print(f"   ⚠️ Chrome version check failed: {e}")
    
    try:
        driver_version = subprocess.check_output([driver_path, '--version'], timeout=5).decode().strip()
        print(f"   Driver version: {driver_version}")
    except Exception as e:
        print(f"   ⚠️ Driver version check failed: {e}")
    
    try:
        process = subprocess.Popen(
            [fs_path, '--port', '8191'],
            cwd='/app',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                **os.environ,
                'LOG_LEVEL': 'debug',
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
            print("STDOUT:", stdout.decode()[:5000])
            print("STDERR:", stderr.decode()[:5000])
        except:
            pass
        sys.exit(1)
    
    print("🚀 Starting Bot...")
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
