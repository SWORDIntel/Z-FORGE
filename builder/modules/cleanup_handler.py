#!/usr/bin/env python3
"""
Cleanup Handler Module for Z-FORGE
Ensures proper cleanup even on build failures
"""

import os
import subprocess
import signal
import atexit
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
import logging

# Try to import psutil, but make it optional
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

class CleanupHandler:
    """Handles cleanup of build artifacts and mounted filesystems"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mounted_paths: Set[Path] = set()
        self.loop_devices: Set[str] = set()
        self.temp_files: Set[Path] = set()
        
        # Register cleanup handlers
        atexit.register(self._emergency_cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Perform cleanup operations"""
        try:
            self.logger.info("Running cleanup operations...")
            
            results = {
                'unmounted': self._unmount_all(),
                'loops_detached': self._detach_loop_devices(),
                'files_removed': self._remove_temp_files(),
                'processes_killed': self._kill_chroot_processes()
            }
            
            self.logger.info("Cleanup completed successfully")
            return {
                'status': 'success',
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def register_mount(self, path: Path):
        """Register a mounted path for cleanup"""
        self.mounted_paths.add(path)
        
    def register_loop_device(self, device: str):
        """Register a loop device for cleanup"""
        self.loop_devices.add(device)
        
    def register_temp_file(self, path: Path):
        """Register a temporary file for cleanup"""
        self.temp_files.add(path)
    
    def _unmount_all(self) -> List[str]:
        """Unmount all registered paths"""
        unmounted = []
        
        # Get all mounts from system
        try:
            result = subprocess.run(
                ['findmnt', '-rno', 'TARGET'],
                capture_output=True,
                text=True
            )
            system_mounts = set(result.stdout.strip().split('\n'))
        except:
            system_mounts = set()
        
        # Add any mounts under workspace
        workspace_str = str(self.workspace)
        for mount in system_mounts:
            if mount.startswith(workspace_str):
                self.mounted_paths.add(Path(mount))
        
        # Sort by path length (deepest first)
        sorted_mounts = sorted(self.mounted_paths, key=lambda p: len(str(p)), reverse=True)
        
        for mount_path in sorted_mounts:
            if self._is_mounted(mount_path):
                try:
                    self.logger.info(f"Unmounting {mount_path}")
                    # Try lazy unmount first
                    subprocess.run(
                        ['sudo', 'umount', '-l', str(mount_path)],
                        check=True,
                        capture_output=True
                    )
                    unmounted.append(str(mount_path))
                except subprocess.CalledProcessError:
                    # Force unmount if lazy fails
                    try:
                        subprocess.run(
                            ['sudo', 'umount', '-f', str(mount_path)],
                            check=False,
                            capture_output=True
                        )
                        unmounted.append(str(mount_path))
                    except:
                        self.logger.warning(f"Failed to unmount {mount_path}")
                        
        return unmounted
    
    def _detach_loop_devices(self) -> List[str]:
        """Detach all loop devices"""
        detached = []
        
        # Find all loop devices
        try:
            result = subprocess.run(
                ['losetup', '-j', str(self.workspace)],
                capture_output=True,
                text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line:
                    device = line.split(':')[0]
                    self.loop_devices.add(device)
        except:
            pass
        
        for device in self.loop_devices:
            try:
                self.logger.info(f"Detaching loop device {device}")
                subprocess.run(
                    ['sudo', 'losetup', '-d', device],
                    check=True,
                    capture_output=True
                )
                detached.append(device)
            except:
                self.logger.warning(f"Failed to detach {device}")
                
        return detached
    
    def _kill_chroot_processes(self) -> List[int]:
        """Kill any processes still running in chroot"""
        killed = []
        chroot_path = self.workspace / "chroot"
        
        if not chroot_path.exists():
            return killed
            
        if not HAS_PSUTIL:
            # Fallback method using lsof
            try:
                result = subprocess.run(
                    ["lsof", "+D", str(chroot_path)],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout:
                    # Parse lsof output to find PIDs
                    for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                        parts = line.split()
                        if len(parts) > 1:
                            try:
                                pid = int(parts[1])
                                self.logger.warning(f"Killing process {pid} in chroot")
                                os.kill(pid, signal.SIGTERM)
                                killed.append(pid)
                            except (ValueError, OSError):
                                pass
            except Exception as e:
                self.logger.debug(f"Failed to use lsof fallback: {e}")
            return killed
            
        try:
            # Find processes with root directory in chroot
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    # Check if process is running in our chroot
                    proc_root = Path(f"/proc/{proc.info['pid']}/root")
                    if proc_root.exists() and proc_root.samefile(chroot_path):
                        self.logger.warning(f"Killing process {proc.info['pid']} ({proc.info['name']}) in chroot")
                        os.kill(proc.info['pid'], signal.SIGTERM)
                        killed.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                    pass
        except Exception as e:
            self.logger.error(f"Error killing chroot processes: {e}")
            
        return killed
    
    def _remove_temp_files(self) -> List[str]:
        """Remove temporary files"""
        removed = []
        
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    if temp_file.is_dir():
                        subprocess.run(
                            ['sudo', 'rm', '-rf', str(temp_file)],
                            check=True
                        )
                    else:
                        subprocess.run(
                            ['sudo', 'rm', '-f', str(temp_file)],
                            check=True
                        )
                    removed.append(str(temp_file))
            except:
                self.logger.warning(f"Failed to remove {temp_file}")
                
        return removed
    
    def _is_mounted(self, path: Path) -> bool:
        """Check if a path is mounted"""
        try:
            result = subprocess.run(
                ['mountpoint', '-q', str(path)],
                capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    def _emergency_cleanup(self):
        """Emergency cleanup on exit"""
        try:
            self.logger.warning("Running emergency cleanup...")
            self.execute()
        except:
            pass
    
    def _signal_handler(self, signum, frame):
        """Handle signals for cleanup"""
        self.logger.warning(f"Received signal {signum}, running cleanup...")
        self._emergency_cleanup()
        exit(1)