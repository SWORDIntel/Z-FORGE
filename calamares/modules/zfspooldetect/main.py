#!/usr/bin/env python3
"""
ZFS Pool Detection Module for Calamares
Detects existing ZFS pools on the system
"""

import subprocess
import json
from typing import Dict, List, Optional

class ZfspooldetectJob:
    """Calamares job for detecting ZFS pools"""
    
    def __init__(self):
        self.config = {}
        self.pools = []
        
    def detect_pools(self) -> List[Dict]:
        """Detect all ZFS pools on the system"""
        pools = []
        
        try:
            # Get list of pools
            result = subprocess.run(
                ['zpool', 'list', '-H', '-o', 'name,size,alloc,free,health'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 5:
                            pools.append({
                                'name': parts[0],
                                'size': parts[1],
                                'allocated': parts[2],
                                'free': parts[3],
                                'health': parts[4]
                            })
            
            # Get detailed pool information
            for pool in pools:
                self._get_pool_details(pool)
                
        except Exception as e:
            print(f"Error detecting pools: {e}")
            
        return pools
    
    def _get_pool_details(self, pool: Dict) -> None:
        """Get detailed information about a pool"""
        try:
            # Get pool properties
            result = subprocess.run(
                ['zpool', 'get', 'all', pool['name'], '-H'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                properties = {}
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        properties[parts[1]] = parts[2]
                pool['properties'] = properties
                
            # Get datasets in pool
            result = subprocess.run(
                ['zfs', 'list', '-H', '-r', '-o', 'name,used,avail,mountpoint', pool['name']],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                datasets = []
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 4:
                        datasets.append({
                            'name': parts[0],
                            'used': parts[1],
                            'available': parts[2],
                            'mountpoint': parts[3]
                        })
                pool['datasets'] = datasets
                
        except Exception as e:
            print(f"Error getting pool details: {e}")
    
    def run(self) -> Optional[str]:
        """Main execution method for Calamares"""
        try:
            self.pools = self.detect_pools()
            
            # Store detected pools for other modules
            import libcalamares
            libcalamares.globalstorage.insert("zfsPools", self.pools)
            
            print(f"Detected {len(self.pools)} ZFS pools")
            for pool in self.pools:
                print(f"  - {pool['name']}: {pool['size']} ({pool['health']})")
            
            return None  # Success
            
        except Exception as e:
            return f"Failed to detect ZFS pools: {str(e)}"

# Module metadata
def main():
    """Entry point for testing"""
    job = ZfspooldetectJob({})
    pools = job.detect_pools()
    print(f"Found {len(pools)} pools")
    for pool in pools:
        print(f"  {pool}")

if __name__ == "__main__":
    main()
