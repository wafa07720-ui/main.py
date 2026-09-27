import subprocess
import os
import sys
import time


if __name__ == '__main__':
    print("🚀 Starting Xvfb on display :99...")
    
    # ═══ نشغل Xvfb ═══
    xvfb = subprocess.Popen([
        'Xvfb',
        ':99',
        '-screen', '0', '1920x1080x24',
        '-ac',
        '+extension', 'RANDR'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    time.sleep(3)
    
    # تحقق
    check = subprocess.run(['xdpyinfo', '-display', ':99'], 
                          capture_output=True, text=True)
    
    if check.returncode == 0:
        print("✅ Xvfb running successfully")
    else:
        print(f"⚠️ Xvfb check: {check.stderr[:200]}")
    
    # ═══ نضبط DISPLAY ═══
    os.environ['DISPLAY'] = ':99'
    
    print("🚀 Starting main.py...")
    sys.stdout.flush()
    
    # ═══ نشغل main.py ═══
    os.execv(sys.executable, [sys.executable, '-u', 'main.py'])
