#!/usr/bin/env python3
"""
tmpfs Sync Back Module for Z-FORGE
Syncs data from tmpfs to permanent storage after build completion
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple
import time

class TmpfsSyncBack:
    """Module for syncing tmpfs data back to permanent storage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Get sync mappings from config
        self.sync_mappings = config.get('sync_mappings', [
            {'source': '/tmp/zforge_tmpfs_workspace/output', 'dest': '/home/john/zforge_workspace/output'},
            {'source': '/tmp/zforge_tmpfs_workspace/logs', 'dest': '/home/john/zforge_workspace/logs'}
        ])
        
        # Performance settings
        self.use_rsync = config.get('use_rsync', True)
        self.preserve_permissions = config.get('preserve_permissions', True)
        self.compress_during_sync = config.get('compress_during_sync', False)
        self.verify_sync = config.get('verify_sync', True)
        
    def calculate_sync_size(self) -> int:
        """Calculate total size of data to sync"""
        total_size = 0
        
        for mapping in self.sync_mappings:
            source_path = Path(mapping['source'])
            if source_path.exists():
                try:
                    # Get directory size
                    for root, dirs, files in os.walk(source_path):
                        for file in files:
                            file_path = Path(root) / file
                            if file_path.exists():
                                total_size += file_path.stat().st_size
                except Exception as e:
                    self.logger.warning(f"Error calculating size for {source_path}: {e}")
                    
        return total_size
        
    def check_destination_space(self) -> bool:
        """Check if destination has enough space for sync"""
        try:
            total_size = self.calculate_sync_size()
            
            # Check space on each destination
            for mapping in self.sync_mappings:
                dest_path = Path(mapping['dest'])
                
                # Get parent directory if dest doesn't exist
                check_path = dest_path.parent if not dest_path.exists() else dest_path
                
                # Get available space
                statvfs = os.statvfs(check_path)
                available_space = statvfs.f_bavail * statvfs.f_frsize
                
                if available_space < total_size * 1.1:  # 10% buffer
                    self.logger.error(f"Insufficient space at {dest_path}")
                    self.logger.error(f"Need: {total_size / (1024**3):.1f}GB, Available: {available_space / (1024**3):.1f}GB")
                    return False
                    
            self.logger.info(f"Sync size: {total_size / (1024**3):.1f}GB - sufficient space available")
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking destination space: {e}")
            return False
            
    def sync_with_rsync(self, source: Path, dest: Path) -> bool:
        """Sync using rsync for efficiency"""
        try:
            # Prepare rsync command
            rsync_cmd = [
                'rsync',
                '-av',  # archive mode, verbose
                '--progress',  # show progress
                '--update',  # skip files that are newer in destination
            ]
            
            if self.preserve_permissions:
                rsync_cmd.extend(['-p', '--chmod=Du+rwx,go+rx,Fugo+r'])
                
            if self.compress_during_sync:
                rsync_cmd.append('-z')
                
            # Add source and destination
            rsync_cmd.extend([f"{source}/", str(dest)])
            
            self.logger.info(f"Syncing {source} -> {dest}")
            self.logger.debug(f"rsync command: {' '.join(rsync_cmd)}")
            
            # Execute rsync
            start_time = time.time()
            result = subprocess.run(
                rsync_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            sync_time = time.time() - start_time
            
            if result.returncode == 0:
                self.logger.info(f"✅ Sync completed in {sync_time:.1f}s")
                if result.stdout:
                    # Log summary line from rsync
                    lines = result.stdout.strip().split('\n')
                    if lines:
                        summary_line = [line for line in lines if 'total size' in line]
                        if summary_line:
                            self.logger.info(f"rsync: {summary_line[0]}")
                return True
            else:
                self.logger.error(f"rsync failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error("rsync timeout - sync taking too long")
            return False
        except Exception as e:
            self.logger.error(f"rsync error: {e}")
            return False
            
    def sync_with_cp(self, source: Path, dest: Path) -> bool:
        """Fallback sync using cp command"""
        try:
            self.logger.info(f"Copying {source} -> {dest} (fallback method)")
            
            # Use cp with progress indication
            cp_cmd = [
                'cp', '-r', '-u', '-v',  # recursive, update, verbose
                str(source), str(dest.parent)
            ]
            
            start_time = time.time()
            result = subprocess.run(cp_cmd, capture_output=True, text=True, timeout=3600)
            sync_time = time.time() - start_time
            
            if result.returncode == 0:
                self.logger.info(f"✅ Copy completed in {sync_time:.1f}s")
                return True
            else:
                self.logger.error(f"cp failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"cp error: {e}")
            return False
            
    def verify_sync(self, source: Path, dest: Path) -> bool:
        """Verify that sync was successful"""
        try:
            # Quick verification - check if key files exist
            if not dest.exists():
                self.logger.error(f"Destination {dest} doesn't exist after sync")
                return False
                
            # Check ISO file specifically
            iso_files = list(dest.glob("*.iso"))
            if not iso_files:
                self.logger.warning("No ISO files found in destination")
            else:
                for iso_file in iso_files:
                    size_mb = iso_file.stat().st_size / (1024**2)
                    self.logger.info(f"✅ ISO found: {iso_file.name} ({size_mb:.0f}MB)")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Verification error: {e}")
            return False
            
    def create_manifest(self):
        """Create a manifest of synced files"""
        try:
            manifest_path = Path('/home/john/zforge_workspace/tmpfs_sync_manifest.txt')
            
            with open(manifest_path, 'w') as f:
                f.write(f"Z-FORGE tmpfs Sync Manifest\n")
                f.write(f"Sync time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"=" * 50 + "\n\n")
                
                for mapping in self.sync_mappings:
                    source = Path(mapping['source'])
                    dest = Path(mapping['dest'])
                    
                    f.write(f"Sync: {source} -> {dest}\n")
                    
                    if dest.exists():
                        # List important files
                        for pattern in ['*.iso', '*.log', '*.deb']:
                            files = list(dest.glob(pattern))
                            for file in files[:10]:  # Limit to first 10
                                size_mb = file.stat().st_size / (1024**2)
                                f.write(f"  {file.name} ({size_mb:.1f}MB)\n")
                    f.write("\n")
                    
            self.logger.info(f"✅ Sync manifest created: {manifest_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to create manifest: {e}")
            
    def execute(self) -> bool:
        """Main execution method"""
        self.logger.info("Starting tmpfs sync back to permanent storage...")
        
        # Check if we have tmpfs data to sync
        has_data = False
        for mapping in self.sync_mappings:
            source_path = Path(mapping['source'])
            if source_path.exists() and any(source_path.iterdir()):
                has_data = True
                break
                
        if not has_data:
            self.logger.info("No tmpfs data found to sync")
            return True
            
        # Check destination space
        if not self.check_destination_space():
            self.logger.error("Insufficient space for sync")
            return False
            
        # Perform sync operations
        success_count = 0
        total_mappings = len(self.sync_mappings)
        
        for i, mapping in enumerate(self.sync_mappings, 1):
            source = Path(mapping['source'])
            dest = Path(mapping['dest'])
            
            self.logger.info(f"Sync {i}/{total_mappings}: {source.name}")
            
            # Skip if source doesn't exist or is empty
            if not source.exists():
                self.logger.info(f"Source {source} doesn't exist, skipping")
                continue
                
            try:
                # Check if source has content
                if not any(source.iterdir()):
                    self.logger.info(f"Source {source} is empty, skipping")
                    continue
            except Exception:
                self.logger.warning(f"Cannot check {source} contents, attempting sync anyway")
                
            # Create destination directory
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Attempt sync with rsync first, fallback to cp
            sync_success = False
            
            if self.use_rsync and shutil.which('rsync'):
                sync_success = self.sync_with_rsync(source, dest)
            
            if not sync_success:
                self.logger.info("Trying fallback copy method...")
                sync_success = self.sync_with_cp(source, dest)
                
            if sync_success:
                # Verify sync if requested
                if self.verify_sync:
                    if self.verify_sync(source, dest):
                        success_count += 1
                    else:
                        self.logger.warning(f"Sync verification failed for {source}")
                else:
                    success_count += 1
            else:
                self.logger.error(f"Failed to sync {source} -> {dest}")
                
        # Create manifest
        self.create_manifest()
        
        # Report results
        self.logger.info(f"Sync completed: {success_count}/{len(self.sync_mappings)} successful")
        
        if success_count == len(self.sync_mappings):
            self.logger.info("✅ All tmpfs data successfully synced to permanent storage")
            return True
        elif success_count > 0:
            self.logger.warning("⚠️  Partial sync success - some data may be missing")
            return True
        else:
            self.logger.error("❌ Sync failed - no data was saved to permanent storage")
            return False


def main():
    """Standalone execution for testing"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    config = {
        'sync_mappings': [
            {'source': '/tmp/zforge_tmpfs_workspace/output', 'dest': '/home/john/zforge_workspace/output'},
            {'source': '/tmp/zforge_tmpfs_workspace/logs', 'dest': '/home/john/zforge_workspace/logs'}
        ]
    }
    
    sync_back = TmpfsSyncBack(config)
    sync_back.execute()


if __name__ == '__main__':
    main()