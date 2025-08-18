#!/usr/bin/env python3
"""
TMPFS Sync Back Module for Z-FORGE
Syncs data from tmpfs (RAM disk) back to permanent storage
"""

import os
import subprocess
import shutil
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
import logging


class TmpfsSyncBack:
    """Syncs data from tmpfs back to permanent storage"""
    
    def __init__(self, workspace: Path, config: Dict):
        """
        Initialize tmpfs sync back module
        
        Args:
            workspace: Path to workspace root (fallback location)
            config: Build configuration dictionary
        """
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Get sync configuration from build spec
        module_config = config.get('config', {})
        self.sync_mappings = module_config.get('sync_mappings', [])
        
        # Get global tmpfs config
        tmpfs_config = config.get('tmpfs_config', {})
        self.sync_back_dirs = tmpfs_config.get('sync_back_dirs', [])
        
        # Combine both sources of sync configuration
        self.all_sync_mappings = self.sync_mappings + [
            {'source': item['source'], 'dest': item['dest']} 
            for item in self.sync_back_dirs
        ]
        
        # Default sync mappings if none configured
        if not self.all_sync_mappings:
            self.all_sync_mappings = [
                {'source': '/tmp/zforge_tmpfs_workspace/output', 'dest': str(workspace / 'output')},
                {'source': '/tmp/zforge_tmpfs_workspace/logs', 'dest': str(workspace / 'logs')},
            ]
        
        # Performance settings  
        self.use_rsync = config.get('use_rsync', True)
        self.preserve_permissions = config.get('preserve_permissions', True)
        self.compress_during_sync = config.get('compress_during_sync', False)
        self.verify_sync_enabled = config.get('verify_sync', True)
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """
        Sync data from tmpfs to disk with resume capability
        
        Args:
            resume_data: Optional checkpoint data to resume from
            lockfile: Optional BuildLockfile instance
            
        Returns:
            Dict with status and checkpoint information
        """
        self.logger.info("Syncing data from tmpfs to permanent storage...")
        
        checkpoints = {
            'sync_mappings_validated': False,
            'directories_prepared': False,
            'data_synced': False,
            'permissions_fixed': False,
            'cleanup_completed': False
        }
        
        # Load previous progress if resuming
        if resume_data:
            checkpoints = resume_data
            self.logger.info(f"Resuming tmpfs sync from checkpoint: {checkpoints}")
            
        sync_results = []
        
        try:
            if not checkpoints.get('sync_mappings_validated'):
                valid_mappings = self._validate_sync_mappings()
                if not valid_mappings:
                    self.logger.warning("No valid tmpfs data found to sync")
                    return {
                        'status': 'success',
                        'mode': 'no_sync_needed',
                        'reason': 'no_tmpfs_data_found',
                        'module_checkpoint_data': checkpoints,
                        'version': '1.0'
                    }
                checkpoints['sync_mappings_validated'] = True
                
            if not checkpoints.get('directories_prepared'):
                self._prepare_destination_directories()
                checkpoints['directories_prepared'] = True
                
            if not checkpoints.get('data_synced'):
                sync_results = self._perform_sync_operations()
                checkpoints['data_synced'] = True
                
            if not checkpoints.get('permissions_fixed'):
                self._fix_destination_permissions()
                checkpoints['permissions_fixed'] = True
                
            if not checkpoints.get('cleanup_completed'):
                self._cleanup_tmpfs_if_safe()
                checkpoints['cleanup_completed'] = True
            
            # Calculate total synced size
            total_synced_mb = sum(result.get('size_mb', 0) for result in sync_results)
            
            self.logger.info(f"tmpfs sync completed successfully. Synced {total_synced_mb:.1f}MB across {len(sync_results)} directories")
            
            return {
                'status': 'success',
                'mode': 'sync_completed',
                'sync_results': sync_results,
                'total_synced_mb': total_synced_mb,
                'mappings_processed': len(self.all_sync_mappings),
                'module_checkpoint_data': checkpoints,
                'version': '1.0'
            }
            
        except Exception as e:
            self.logger.error(f"tmpfs sync failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'sync_results': sync_results,
                'module_checkpoint_data': checkpoints,
                'module': self.__class__.__name__
            }
    
    def _validate_sync_mappings(self) -> bool:
        """Validate that source directories exist and have data"""
        valid_count = 0
        
        for mapping in self.all_sync_mappings:
            source_path = Path(mapping['source'])
            
            if source_path.exists() and self._directory_has_content(source_path):
                self.logger.info(f"Valid sync source found: {source_path}")
                valid_count += 1
            else:
                self.logger.debug(f"Skipping empty or missing source: {source_path}")
                
        self.logger.info(f"Found {valid_count} valid sync mappings out of {len(self.all_sync_mappings)}")
        return valid_count > 0
    
    def _directory_has_content(self, path: Path) -> bool:
        """Check if directory has any content to sync"""
        try:
            return path.is_dir() and any(path.iterdir())
        except (OSError, PermissionError):
            return False
    
    def _prepare_destination_directories(self):
        """Create destination directories with proper permissions"""
        for mapping in self.all_sync_mappings:
            dest_path = Path(mapping['dest'])
            
            # Create destination directory
            subprocess.run(['sudo', 'mkdir', '-p', str(dest_path)], check=True)
            subprocess.run(['sudo', 'chmod', '755', str(dest_path)], check=True)
            
            self.logger.debug(f"Prepared destination directory: {dest_path}")
    
    def _perform_sync_operations(self) -> List[Dict]:
        """Perform the actual sync operations with progress monitoring"""
        sync_results = []
        
        for i, mapping in enumerate(self.all_sync_mappings, 1):
            source_path = Path(mapping['source'])
            dest_path = Path(mapping['dest'])
            
            if not source_path.exists():
                self.logger.debug(f"Source does not exist, skipping: {source_path}")
                continue
                
            if not self._directory_has_content(source_path):
                self.logger.debug(f"Source has no content, skipping: {source_path}")
                continue
            
            self.logger.info(f"Syncing ({i}/{len(self.all_sync_mappings)}): {source_path} -> {dest_path}")
            
            start_time = time.time()
            
            try:
                # Get size before sync
                source_size_mb = self._get_directory_size_mb(source_path)
                
                # Perform sync with rsync for efficiency and progress
                sync_result = self._rsync_with_progress(source_path, dest_path)
                
                end_time = time.time()
                duration = end_time - start_time
                
                result = {
                    'source': str(source_path),
                    'dest': str(dest_path),
                    'size_mb': source_size_mb,
                    'duration_seconds': round(duration, 2),
                    'status': 'success' if sync_result else 'partial',
                    'transfer_rate_mb_s': round(source_size_mb / duration if duration > 0 else 0, 2)
                }
                
                sync_results.append(result)
                self.logger.info(f"Synced {source_size_mb:.1f}MB in {duration:.1f}s ({result['transfer_rate_mb_s']:.1f}MB/s)")
                
            except Exception as e:
                self.logger.error(f"Failed to sync {source_path}: {e}")
                sync_results.append({
                    'source': str(source_path),
                    'dest': str(dest_path),
                    'status': 'error',
                    'error': str(e)
                })
                
        return sync_results
    
    def _get_directory_size_mb(self, path: Path) -> float:
        """Get directory size in MB"""
        try:
            result = subprocess.run(
                ['du', '-sm', str(path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return float(result.stdout.split()[0])
        except (subprocess.SubprocessError, ValueError, OSError):
            pass
        return 0.0
    
    def _rsync_with_progress(self, source: Path, dest: Path) -> bool:
        """Perform rsync with progress monitoring"""
        try:
            # Ensure source path ends with / for rsync directory sync
            source_str = f"{source}/"
            dest_str = str(dest)
            
            rsync_cmd = [
                'sudo', 'rsync',
                '-av',                    # archive mode, verbose
                '--progress',             # show progress
                '--update',               # skip files that are newer on dest
                '--human-readable',       # human readable numbers
                source_str,
                dest_str
            ]
            
            self.logger.debug(f"Running: {' '.join(rsync_cmd)}")
            
            # Run rsync with real-time output
            process = subprocess.Popen(
                rsync_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor progress
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    # Log progress lines that show transfer info
                    if any(indicator in line for indicator in ['%', 'MB/s', 'kB/s', 'GB/s']):
                        self.logger.info(f"Sync progress: {line}")
                    else:
                        self.logger.debug(f"rsync: {line}")
            
            process.wait()
            
            if process.returncode == 0:
                return True
            else:
                self.logger.warning(f"rsync completed with return code {process.returncode}")
                return False
                
        except Exception as e:
            self.logger.error(f"rsync failed: {e}")
            return False
    
    def _fix_destination_permissions(self):
        """Fix permissions on synced files"""
        for mapping in self.all_sync_mappings:
            dest_path = Path(mapping['dest'])
            
            if dest_path.exists():
                try:
                    # Set reasonable permissions on the destination
                    subprocess.run(['sudo', 'chmod', '-R', '755', str(dest_path)], 
                                 check=False, capture_output=True)
                    
                    # Make sure user can access the files
                    subprocess.run(['sudo', 'chown', '-R', f"{os.getuid()}:{os.getgid()}", str(dest_path)],
                                 check=False, capture_output=True)
                    
                    self.logger.debug(f"Fixed permissions for: {dest_path}")
                    
                except subprocess.SubprocessError as e:
                    self.logger.warning(f"Could not fix permissions for {dest_path}: {e}")
    
    def _cleanup_tmpfs_if_safe(self):
        """Clean up tmpfs mounts if it's safe to do so"""
        try:
            # Check if we're in a tmpfs cleanup scenario
            tmpfs_mounts = ['/tmp/zforge_tmpfs_workspace', '/tmp/zforge_ccache', '/tmp/zforge_package_cache']
            
            for mount_path in tmpfs_mounts:
                mount_path_obj = Path(mount_path)
                
                if self._is_mounted(mount_path_obj):
                    self.logger.info(f"Unmounting tmpfs: {mount_path}")
                    
                    # Try lazy unmount first
                    result = subprocess.run(
                        ['sudo', 'umount', '-l', mount_path],
                        capture_output=True,
                        timeout=30
                    )
                    
                    if result.returncode == 0:
                        self.logger.info(f"Successfully unmounted {mount_path}")
                    else:
                        self.logger.warning(f"Failed to unmount {mount_path}: {result.stderr.decode()}")
                        
        except Exception as e:
            self.logger.warning(f"tmpfs cleanup warning: {e}")
    
    def _is_mounted(self, path: Path) -> bool:
        """Check if a path is mounted"""
        try:
            result = subprocess.run(
                ['mountpoint', '-q', str(path)],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, OSError):
            return False
    
    def get_sync_summary(self) -> Dict:
        """Get a summary of sync operations for reporting"""
        tmpfs_usage = {}
        
        try:
            # Check tmpfs usage
            for mount_path in ['/tmp/zforge_tmpfs_workspace', '/tmp/zforge_ccache']:
                mount_path_obj = Path(mount_path)
                if mount_path_obj.exists():
                    usage = shutil.disk_usage(mount_path_obj)
                    tmpfs_usage[mount_path] = {
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round((usage.total - usage.free) / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'usage_percent': round((usage.total - usage.free) / usage.total * 100, 1)
                    }
        except Exception as e:
            self.logger.debug(f"Could not get tmpfs usage: {e}")
            
        return {
            'sync_mappings_count': len(self.all_sync_mappings),
            'tmpfs_usage': tmpfs_usage,
            'timestamp': time.time()
        }
