#!/usr/bin/env python3
import json
import subprocess
import os
from datetime import datetime

def get_build_status():
    try:
        # Get progress
        result = subprocess.run(['sudo', 'cat', '/root/zforge_workspace/build_progress.json'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            progress = json.loads(result.stdout)
        else:
            progress = {}
        
        # Get workspace stats
        result = subprocess.run(['sudo', 'du', '-sh', '/root/zforge_workspace/chroot'], 
                              capture_output=True, text=True)
        chroot_size = result.stdout.split()[0] if result.returncode == 0 else "Unknown"
        
        # Get process info
        result = subprocess.run(['pgrep', '-f', 'python3.*build.py'], 
                              capture_output=True, text=True)
        pid = result.stdout.strip() if result.returncode == 0 else None
        
        # Display
        print("=" * 60)
        print(f"Z-FORGE BUILD STATUS - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        
        if progress:
            completed = [k for k, v in progress.items() if v.get('status') == 'success']
            print(f"✅ Completed Modules ({len(completed)}):")
            for module in completed:
                print(f"   • {module}")
            print()
        
        print(f"💾 Chroot Size: {chroot_size}")
        print(f"🔧 Build Process: {'Active (PID ' + pid + ')' if pid else 'Not running'}")
        
        # Current activity from log
        try:
            result = subprocess.run(['sudo', 'tail', '-n', '3', '/proc/' + pid + '/fd/1'], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                print("\n🔄 Recent Activity:")
                for line in result.stdout.strip().split('\n')[-3:]:
                    if line.strip():
                        print(f"   {line.strip()}")
        except:
            pass
        
        print("=" * 60)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_build_status()