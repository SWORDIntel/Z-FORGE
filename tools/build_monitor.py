#!/usr/bin/env python3
"""
Z-FORGE Build Monitor
Real-time build monitoring with progress tracking and detailed output
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import argparse

class ZForgeBuildMonitor:
    def __init__(self, workspace_path="/root/zforge_workspace"):
        self.workspace_path = Path(workspace_path)
        self.progress_file = self.workspace_path / "build_progress.json"
        self.running = True
        self.last_progress = {}
        
    def get_build_process(self):
        """Find the running build process"""
        try:
            result = subprocess.run(['pgrep', '-f', 'python3.*build.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return int(result.stdout.strip().split('\n')[0])
            return None
        except:
            return None
    
    def get_progress(self):
        """Get current build progress"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def get_workspace_stats(self):
        """Get workspace disk usage and file counts"""
        try:
            if not self.workspace_path.exists():
                return {"size": "0", "files": 0, "chroot_size": "0"}
                
            # Get workspace size
            result = subprocess.run(['du', '-sh', str(self.workspace_path)], 
                                  capture_output=True, text=True)
            workspace_size = result.stdout.split()[0] if result.returncode == 0 else "Unknown"
            
            # Get chroot size if it exists
            chroot_path = self.workspace_path / "chroot"
            if chroot_path.exists():
                result = subprocess.run(['du', '-sh', str(chroot_path)], 
                                      capture_output=True, text=True)
                chroot_size = result.stdout.split()[0] if result.returncode == 0 else "Unknown"
            else:
                chroot_size = "N/A"
            
            # Count files in workspace
            result = subprocess.run(['find', str(self.workspace_path), '-type', 'f'], 
                                  capture_output=True, text=True)
            file_count = len(result.stdout.strip().split('\n')) if result.returncode == 0 and result.stdout.strip() else 0
            
            return {
                "workspace_size": workspace_size,
                "chroot_size": chroot_size,
                "files": file_count
            }
        except:
            return {"workspace_size": "Unknown", "chroot_size": "Unknown", "files": 0}
    
    def format_progress_display(self, progress, stats):
        """Format progress information for display"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Header
        output = [
            "=" * 80,
            f"Z-FORGE BUILD MONITOR - {timestamp}",
            "=" * 80,
            ""
        ]
        
        # Build status
        if progress:
            current_module = progress.get('current_module', 'Unknown')
            total_modules = progress.get('total_modules', 0)
            completed_modules = progress.get('completed_modules', [])
            failed_modules = progress.get('failed_modules', [])
            
            output.extend([
                f"📦 Current Module: {current_module}",
                f"✅ Completed: {len(completed_modules)}/{total_modules}",
                f"❌ Failed: {len(failed_modules)}",
                ""
            ])
            
            # Module progress
            if completed_modules:
                output.append("Completed Modules:")
                for module in completed_modules[-5:]:  # Show last 5
                    output.append(f"  ✅ {module}")
                output.append("")
            
            if failed_modules:
                output.append("Failed Modules:")
                for module in failed_modules:
                    output.append(f"  ❌ {module}")
                output.append("")
        else:
            output.append("📦 Waiting for build progress data...")
            output.append("")
        
        # Workspace stats
        output.extend([
            f"💾 Workspace Size: {stats['workspace_size']}",
            f"🗂️  Chroot Size: {stats['chroot_size']}",
            f"📁 Total Files: {stats['files']}",
            ""
        ])
        
        # Process info
        pid = self.get_build_process()
        if pid:
            try:
                # Get process info
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if str(pid) in line and 'python3' in line:
                        parts = line.split()
                        if len(parts) >= 11:
                            cpu = parts[2]
                            mem = parts[3]
                            time_used = parts[9]
                            output.append(f"🔧 Build Process: PID {pid} | CPU: {cpu}% | MEM: {mem}% | Time: {time_used}")
                            break
                else:
                    output.append(f"🔧 Build Process: PID {pid} (active)")
            except:
                output.append(f"🔧 Build Process: PID {pid} (active)")
        else:
            output.append("⏹️  Build Process: Not running")
        
        output.extend(["", "=" * 80])
        return '\n'.join(output)
    
    def monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                progress = self.get_progress()
                stats = self.get_workspace_stats()
                
                # Clear screen and show progress
                os.system('clear')
                print(self.format_progress_display(progress, stats))
                
                # Check if build completed or failed
                if progress and progress.get('status') in ['completed', 'failed']:
                    print(f"\n🎯 Build {progress['status'].upper()}!")
                    if progress['status'] == 'failed':
                        print(f"❌ Error: {progress.get('error', 'Unknown error')}")
                    break
                
                # Check if process is still running
                if not self.get_build_process():
                    print("\n⚠️  Build process not found - may have completed or failed")
                    break
                
                time.sleep(5)  # Update every 5 seconds
                
            except KeyboardInterrupt:
                print("\n\n🛑 Monitor stopped by user")
                break
            except Exception as e:
                print(f"\n❌ Monitor error: {e}")
                time.sleep(5)
    
    def tail_build_output(self):
        """Tail the build process output (if available)"""
        pid = self.get_build_process()
        if not pid:
            print("❌ No build process found")
            return
        
        try:
            # Try to read process stdout
            stdout_path = f"/proc/{pid}/fd/1"
            if os.path.exists(stdout_path):
                subprocess.run(['tail', '-f', stdout_path])
            else:
                print(f"❌ Cannot access process output for PID {pid}")
        except KeyboardInterrupt:
            print("\n🛑 Output monitoring stopped")
        except Exception as e:
            print(f"❌ Error monitoring output: {e}")

def main():
    parser = argparse.ArgumentParser(description='Z-FORGE Build Monitor')
    parser.add_argument('--workspace', default='/root/zforge_workspace',
                       help='Path to build workspace')
    parser.add_argument('--tail', action='store_true',
                       help='Show live build output instead of progress')
    parser.add_argument('--once', action='store_true',
                       help='Show status once and exit')
    
    args = parser.parse_args()
    
    monitor = ZForgeBuildMonitor(args.workspace)
    
    if args.tail:
        monitor.tail_build_output()
    elif args.once:
        progress = monitor.get_progress()
        stats = monitor.get_workspace_stats()
        print(monitor.format_progress_display(progress, stats))
    else:
        print("🚀 Starting Z-FORGE Build Monitor")
        print("Press Ctrl+C to stop")
        time.sleep(2)
        monitor.monitor_loop()

if __name__ == "__main__":
    main()