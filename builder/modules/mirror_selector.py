#!/usr/bin/env python3
"""
Mirror Selector Module for Z-FORGE
Automatically selects fastest Debian mirrors for downloads
"""

import subprocess
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
import concurrent.futures
from urllib.parse import urlparse

class MirrorSelector:
    """Select fastest mirrors for package downloads"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        # Store mirrors in home directory cache instead of workspace
        self.cache_dir = Path.home() / ".cache" / "zforge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.mirrors_file = self.cache_dir / "selected_mirrors.txt"
        
        # Common Debian mirrors to test
        self.debian_mirrors = [
            "http://deb.debian.org/debian/",
            "http://ftp.us.debian.org/debian/",
            "http://ftp.de.debian.org/debian/",
            "http://ftp.uk.debian.org/debian/",
            "http://ftp.jp.debian.org/debian/",
            "http://ftp.fr.debian.org/debian/",
            "http://ftp.ca.debian.org/debian/",
            "http://ftp.au.debian.org/debian/",
            "http://ftp.br.debian.org/debian/",
            "http://ftp.nl.debian.org/debian/",
            "http://mirror.csclub.uwaterloo.ca/debian/",
            "http://mirrors.kernel.org/debian/",
            "http://mirror.steadfast.net/debian/",
            "http://mirror.dal.nexril.ca/debian/",
            "http://debian.mirror.rafal.ca/debian/",
        ]
        
        # Proxmox mirrors
        self.proxmox_mirrors = [
            "http://download.proxmox.com/debian/",
            "http://ftp.us.proxmox.com/debian/",
            "http://ftp.eu.proxmox.com/debian/",
        ]
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Test mirrors and select fastest ones"""
        try:
            self.logger.info("Testing mirrors for fastest download speeds...")
            
            # Test Debian mirrors
            debian_results = self._test_mirrors(self.debian_mirrors, "Debian")
            fastest_debian = self._select_fastest(debian_results, count=3)
            
            # Test Proxmox mirrors if needed
            proxmox_results = []
            if self.config.get('proxmox_config', {}).get('version'):
                proxmox_results = self._test_mirrors(self.proxmox_mirrors, "Proxmox")
            
            # Save results
            self._save_mirror_selection(fastest_debian, proxmox_results)
            
            return {
                'status': 'success',
                'debian_mirrors': fastest_debian,
                'proxmox_mirrors': proxmox_results,
                'config_updated': self._update_configs(fastest_debian[0][0] if fastest_debian else None)
            }
            
        except Exception as e:
            self.logger.error(f"Mirror selection failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def _test_mirrors(self, mirrors: List[str], mirror_type: str) -> List[Tuple[str, float]]:
        """Test mirrors in parallel and return speeds"""
        results = []
        
        self.logger.info(f"Testing {len(mirrors)} {mirror_type} mirrors...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_mirror = {
                executor.submit(self._test_single_mirror, mirror): mirror 
                for mirror in mirrors
            }
            
            for future in concurrent.futures.as_completed(future_to_mirror):
                mirror = future_to_mirror[future]
                try:
                    speed = future.result()
                    if speed > 0:
                        results.append((mirror, speed))
                        self.logger.debug(f"{mirror}: {speed:.2f} MB/s")
                except Exception as e:
                    self.logger.debug(f"{mirror}: Failed - {e}")
        
        # Sort by speed (fastest first)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _test_single_mirror(self, mirror: str) -> float:
        """Test a single mirror's download speed"""
        # Use a small file for testing (Packages.gz from main)
        test_url = mirror.rstrip('/') + '/dists/stable/main/binary-amd64/Packages.gz'
        
        try:
            start_time = time.time()
            
            # Download with timeout
            result = subprocess.run(
                ['curl', '-f', '-s', '-m', '5', '-o', '/dev/null', '-w', '%{size_download}', test_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return 0.0
            
            elapsed = time.time() - start_time
            size_bytes = int(result.stdout.strip())
            
            if elapsed > 0 and size_bytes > 0:
                # Calculate MB/s
                speed_mbps = (size_bytes / (1024 * 1024)) / elapsed
                return speed_mbps
            
            return 0.0
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return 0.0
    
    def _select_fastest(self, results: List[Tuple[str, float]], count: int = 3) -> List[Tuple[str, float]]:
        """Select the fastest mirrors"""
        if not results:
            self.logger.warning("No working mirrors found!")
            return []
        
        fastest = results[:count]
        
        self.logger.info("Fastest mirrors:")
        for mirror, speed in fastest:
            self.logger.info(f"  {mirror} - {speed:.2f} MB/s")
        
        return fastest
    
    def _save_mirror_selection(self, debian_mirrors: List[Tuple[str, float]], 
                             proxmox_mirrors: List[Tuple[str, float]]):
        """Save selected mirrors to file"""
        with open(self.mirrors_file, 'w') as f:
            f.write("# Selected mirrors based on speed test\n")
            f.write(f"# Generated at {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("# Debian mirrors (URL, Speed MB/s)\n")
            for mirror, speed in debian_mirrors:
                f.write(f"{mirror} # {speed:.2f} MB/s\n")
            
            if proxmox_mirrors:
                f.write("\n# Proxmox mirrors\n")
                for mirror, speed in proxmox_mirrors:
                    f.write(f"{mirror} # {speed:.2f} MB/s\n")
    
    def _update_configs(self, fastest_mirror: str) -> bool:
        """Update configuration files with fastest mirror"""
        if not fastest_mirror:
            return False
        
        try:
            # Update debootstrap module's mirror
            self.config.setdefault('mirror_overrides', {})
            self.config['mirror_overrides']['debian'] = fastest_mirror
            
            self.logger.info(f"Configuration updated to use fastest mirror: {fastest_mirror}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def get_mirror_for_release(self, release: str) -> str:
        """Get the selected mirror for a specific release"""
        if self.mirrors_file.exists():
            try:
                with open(self.mirrors_file, 'r') as f:
                    for line in f:
                        if line.startswith('http://') or line.startswith('https://'):
                            return line.split('#')[0].strip()
            except:
                pass
        
        # Default fallback
        return "http://deb.debian.org/debian/"