#!/usr/bin/env python3
"""
Progress Monitor Module for Z-FORGE
Provides real-time progress tracking and ETA calculations
"""

import time
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

class ProgressMonitor:
    """Monitor build progress and provide estimates"""
    
    def __init__(self, workspace: Path, config: Dict):
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(__name__)
        # Store progress in cache directory instead of workspace
        self.cache_dir = Path.home() / ".cache" / "zforge"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.cache_dir / "build_progress_monitor.json"
        self.start_time = None
        self.module_times = {}
        
    def execute(self, resume_data: Optional[Dict] = None, lockfile: Optional[Any] = None) -> Dict:
        """Initialize progress monitoring"""
        try:
            self.logger.info("Initializing progress monitoring...")
            
            self.start_time = time.time()
            
            # Load historical data if available
            self._load_historical_data()
            
            # Initialize progress tracking
            self._init_progress()
            
            return {
                'status': 'success',
                'start_time': self.start_time,
                'estimated_duration': self._estimate_total_time()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to initialize progress monitoring: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'module': self.__class__.__name__
            }
    
    def update_module_start(self, module_name: str):
        """Mark module as started"""
        self.module_times[module_name] = {
            'start': time.time(),
            'status': 'running'
        }
        self._save_progress()
        self._log_progress(f"Started module: {module_name}")
    
    def update_module_complete(self, module_name: str, status: str = 'success'):
        """Mark module as completed"""
        if module_name in self.module_times:
            self.module_times[module_name]['end'] = time.time()
            self.module_times[module_name]['duration'] = (
                self.module_times[module_name]['end'] - 
                self.module_times[module_name]['start']
            )
            self.module_times[module_name]['status'] = status
        self._save_progress()
        self._log_progress(f"Completed module: {module_name} ({status})")
    
    def get_progress_report(self) -> Dict:
        """Get current progress report with ETA"""
        if not self.start_time:
            return {'status': 'not_started'}
        
        elapsed = time.time() - self.start_time
        
        # Get module statuses
        completed = [m for m, t in self.module_times.items() if t.get('status') in ['success', 'skipped']]
        failed = [m for m, t in self.module_times.items() if t.get('status') == 'error']
        running = [m for m, t in self.module_times.items() if t.get('status') == 'running']
        
        # Calculate ETA
        eta_seconds = self._calculate_eta()
        
        return {
            'elapsed_time': elapsed,
            'elapsed_formatted': str(timedelta(seconds=int(elapsed))),
            'modules_completed': len(completed),
            'modules_failed': len(failed),
            'modules_running': running,
            'eta_seconds': eta_seconds,
            'eta_formatted': str(timedelta(seconds=int(eta_seconds))) if eta_seconds else 'Unknown',
            'estimated_completion': (
                datetime.now() + timedelta(seconds=eta_seconds)
            ).strftime('%H:%M:%S') if eta_seconds else 'Unknown'
        }
    
    def _init_progress(self):
        """Initialize progress tracking"""
        progress_data = {
            'start_time': self.start_time,
            'modules': self.module_times,
            'build_id': datetime.now().strftime('%Y%m%d_%H%M%S')
        }
        self._save_progress(progress_data)
    
    def _save_progress(self, data: Optional[Dict] = None):
        """Save progress to file"""
        if data is None:
            data = {
                'start_time': self.start_time,
                'modules': self.module_times,
                'last_update': time.time()
            }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save progress: {e}")
    
    def _load_historical_data(self):
        """Load historical build times"""
        history_file = self.cache_dir / "build_history.json"
        
        try:
            if history_file.exists():
                with open(history_file, 'r') as f:
                    self.historical_data = json.load(f)
            else:
                self.historical_data = {'builds': []}
        except:
            self.historical_data = {'builds': []}
    
    def _estimate_total_time(self) -> float:
        """Estimate total build time based on history"""
        if self.historical_data.get('builds'):
            # Average of last 5 builds
            recent_builds = self.historical_data['builds'][-5:]
            total_times = [b.get('total_time', 0) for b in recent_builds if b.get('total_time')]
            
            if total_times:
                return sum(total_times) / len(total_times)
        
        # Default estimate if no history
        return 1800  # 30 minutes
    
    def _calculate_eta(self) -> Optional[float]:
        """Calculate estimated time remaining"""
        # Get list of all modules from config
        all_modules = [m['name'] for m in self.config.get('modules', []) if m.get('enabled', True)]
        
        completed = [m for m, t in self.module_times.items() if t.get('status') in ['success', 'skipped']]
        
        if not completed:
            return self._estimate_total_time()
        
        # Calculate average time per module
        completed_times = [
            t['duration'] for m, t in self.module_times.items() 
            if t.get('duration') and t.get('status') == 'success'
        ]
        
        if completed_times:
            avg_time = sum(completed_times) / len(completed_times)
            remaining_modules = len(all_modules) - len(completed)
            return remaining_modules * avg_time * 1.1  # Add 10% buffer
        
        return None
    
    def _log_progress(self, message: str):
        """Log progress with timestamp"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        elapsed_str = str(timedelta(seconds=int(elapsed)))
        self.logger.info(f"[{elapsed_str}] {message}")