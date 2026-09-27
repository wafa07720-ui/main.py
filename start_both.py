import subprocess
import time
import os
import sys
import threading

def start_flaresolverr():
    """شغل FlareSolverr في الخلفية"""
    print("🚀 Starting FlareSolverr...")
    return subprocess.Popen(
        ['/opt/flaresolverr'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def wait_flaresolverr(max_wait=30):
    """استنى FlareSolverr يشتغل"""
    import requests
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
        time.sleep(1)
    return False

if __name__ == '__main__':
    # Start FlareSolverr
    fs_process = start_flaresolverr()
    
    # Wait for it
    if not wait_flaresolverr():
        print("❌ FlareSolverr failed to start")
        fs_process.terminate()
        sys.exit(1)
    
    # Start main bot
    print("🚀 Starting Bot...")
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
