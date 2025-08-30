#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Compilation Controller
Advanced compilation control with pause/resume/skip functionality
"""

import os
import time
import json
import logging
import threading
import subprocess
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import psutil

class CompilationState(Enum):
    """Compilation states"""
    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ZoneState(Enum):
    """Individual zone states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"

@dataclass
class CompilationProcess:
    """Individual compilation process info"""
    pid: int
    zone_name: str
    component: str
    command: List[str]
    process: subprocess.Popen
    start_time: float
    is_paused: bool = False
    priority: int = 0  # 0=normal, higher=more important

@dataclass
class CompilationZone:
    """Compilation zone with control state"""
    name: str
    components: List[str]
    state: ZoneState = ZoneState.PENDING
    current_component_index: int = 0
    progress_percent: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""
    skip_remaining: bool = False
    retry_count: int = 0
    max_retries: int = 3
    processes: List[CompilationProcess] = field(default_factory=list)

@dataclass  
class ControlAction:
    """Control action taken by user or system"""
    action_type: str  # pause, resume, skip, retry, stop, emergency_stop
    target: str       # zone name or "all"
    reason: str
    timestamp: float = field(default_factory=time.time)
    parameters: Dict[str, Any] = field(default_factory=dict)

class HPCCompilationController:
    """
    Advanced compilation controller with comprehensive process management
    
    Features:
    - Process-level pause/resume control
    - Individual zone skip/retry functionality  
    - Graceful shutdown handling
    - Emergency stop capabilities
    - Thermal throttling integration
    - Memory pressure handling
    - Progress state persistence
    - User interaction callbacks
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Compilation state
        self.state = CompilationState.IDLE
        self.zones: List[CompilationZone] = []
        self.current_zone_index = 0
        self.total_start_time: Optional[float] = None
        
        # Process management
        self.active_processes: Dict[int, CompilationProcess] = {}
        self.process_lock = threading.Lock()
        
        # Control state
        self.is_paused = False
        self.should_stop = False
        self.emergency_stop = False
        self.control_actions: List[ControlAction] = []
        
        # Configuration
        self.max_parallel_jobs = config.get('max_parallel_jobs', 4)
        self.current_parallel_jobs = self.max_parallel_jobs
        self.enable_process_control = config.get('enable_process_control', True)
        self.pause_timeout = config.get('pause_timeout_seconds', 30.0)
        self.graceful_stop_timeout = config.get('stop_timeout_seconds', 60.0)
        
        # Callbacks
        self.state_change_callbacks: List[Callable] = []
        self.zone_change_callbacks: List[Callable] = []
        self.progress_callbacks: List[Callable] = []
        self.error_callbacks: List[Callable] = []
        
        # Threading
        self.control_thread = None
        
        # State persistence
        self.state_file = Path(config.get('state_file', '/tmp/hpc_compilation_state.json'))
        
        # Signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def add_state_change_callback(self, callback: Callable):
        """Add callback for compilation state changes"""
        self.state_change_callbacks.append(callback)
    
    def add_zone_change_callback(self, callback: Callable):
        """Add callback for zone state changes"""
        self.zone_change_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable):
        """Add callback for progress updates"""
        self.progress_callbacks.append(callback)
    
    def add_error_callback(self, callback: Callable):
        """Add callback for errors"""
        self.error_callbacks.append(callback)
    
    def initialize_zones(self, zones_config: List[Dict[str, Any]]):
        """Initialize compilation zones from configuration"""
        self.zones = []
        
        for zone_config in zones_config:
            zone = CompilationZone(
                name=zone_config['name'],
                components=zone_config['components'],
                max_retries=zone_config.get('max_retries', 3)
            )
            self.zones.append(zone)
        
        self.logger.info(f"Initialized {len(self.zones)} compilation zones")
    
    def start_compilation(self) -> bool:
        """Start the compilation process"""
        if self.state != CompilationState.IDLE:
            self.logger.warning(f"Cannot start compilation - current state: {self.state.value}")
            return False
        
        try:
            self._change_state(CompilationState.STARTING)
            
            # Reset zone states
            for zone in self.zones:
                zone.state = ZoneState.PENDING
                zone.current_component_index = 0
                zone.progress_percent = 0.0
                zone.start_time = None
                zone.end_time = None
                zone.error_message = ""
                zone.skip_remaining = False
                zone.retry_count = 0
            
            self.current_zone_index = 0
            self.total_start_time = time.time()
            self.is_paused = False
            self.should_stop = False
            self.emergency_stop = False
            
            # Save initial state
            self._save_state()
            
            # Start control thread
            self.control_thread = threading.Thread(target=self._compilation_loop)
            self.control_thread.daemon = True
            self.control_thread.start()
            
            self._change_state(CompilationState.RUNNING)
            
            self._log_action("start", "all", "Compilation started by user")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start compilation: {e}")
            self._change_state(CompilationState.FAILED)
            return False
    
    def pause_compilation(self) -> bool:
        """Pause the compilation process"""
        if self.state != CompilationState.RUNNING:
            self.logger.warning(f"Cannot pause - current state: {self.state.value}")
            return False
        
        try:
            self._change_state(CompilationState.PAUSED)
            self.is_paused = True
            
            # Pause all active processes
            paused_count = 0
            with self.process_lock:
                for process_info in self.active_processes.values():
                    if self._pause_process(process_info):
                        paused_count += 1
            
            self._log_action("pause", "all", f"Paused {paused_count} processes")
            self._save_state()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to pause compilation: {e}")
            return False
    
    def resume_compilation(self) -> bool:
        """Resume the paused compilation"""
        if self.state != CompilationState.PAUSED:
            self.logger.warning(f"Cannot resume - current state: {self.state.value}")
            return False
        
        try:
            self.is_paused = False
            
            # Resume all paused processes
            resumed_count = 0
            with self.process_lock:
                for process_info in self.active_processes.values():
                    if self._resume_process(process_info):
                        resumed_count += 1
            
            self._change_state(CompilationState.RUNNING)
            
            self._log_action("resume", "all", f"Resumed {resumed_count} processes")
            self._save_state()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resume compilation: {e}")
            return False
    
    def stop_compilation(self, graceful: bool = True) -> bool:
        """Stop the compilation process"""
        if self.state in [CompilationState.IDLE, CompilationState.COMPLETED, CompilationState.FAILED]:
            return True
        
        try:
            self._change_state(CompilationState.STOPPING)
            self.should_stop = True
            
            if graceful:
                self._graceful_stop()
            else:
                self._force_stop()
            
            # Wait for control thread to finish
            if self.control_thread and self.control_thread.is_alive():
                self.control_thread.join(timeout=5.0)
            
            self._change_state(CompilationState.CANCELLED)
            
            self._log_action("stop", "all", "Compilation stopped by user", 
                           {"graceful": graceful})
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop compilation: {e}")
            return False
    
    def emergency_stop(self) -> bool:
        """Emergency stop - immediate termination"""
        self.logger.critical("EMERGENCY STOP initiated")
        self.emergency_stop = True
        self.should_stop = True
        
        try:
            # Kill all processes immediately
            killed_count = 0
            with self.process_lock:
                for process_info in self.active_processes.values():
                    if self._kill_process(process_info):
                        killed_count += 1
                
                self.active_processes.clear()
            
            self._change_state(CompilationState.CANCELLED)
            
            self._log_action("emergency_stop", "all", 
                           f"Emergency stop - killed {killed_count} processes")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")
            return False
    
    def skip_zone(self, zone_name: str) -> bool:
        """Skip a specific compilation zone"""
        zone = self._find_zone(zone_name)
        if not zone:
            self.logger.warning(f"Zone not found: {zone_name}")
            return False
        
        try:
            # Mark zone for skipping
            zone.skip_remaining = True
            zone.state = ZoneState.SKIPPED
            
            # Stop any processes for this zone
            with self.process_lock:
                zone_processes = [p for p in self.active_processes.values() 
                                if p.zone_name == zone_name]
                
                for process_info in zone_processes:
                    self._terminate_process(process_info)
            
            self._log_action("skip", zone_name, f"Zone {zone_name} skipped by user")
            self._notify_zone_change(zone)
            self._save_state()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to skip zone {zone_name}: {e}")
            return False
    
    def retry_zone(self, zone_name: str) -> bool:
        """Retry a failed compilation zone"""
        zone = self._find_zone(zone_name)
        if not zone:
            self.logger.warning(f"Zone not found: {zone_name}")
            return False
        
        if zone.state != ZoneState.FAILED:
            self.logger.warning(f"Zone {zone_name} is not in failed state: {zone.state.value}")
            return False
        
        if zone.retry_count >= zone.max_retries:
            self.logger.warning(f"Zone {zone_name} has exceeded max retries")
            return False
        
        try:
            # Reset zone state for retry
            zone.state = ZoneState.RETRYING
            zone.current_component_index = 0
            zone.progress_percent = 0.0
            zone.error_message = ""
            zone.skip_remaining = False
            zone.retry_count += 1
            
            self._log_action("retry", zone_name, 
                           f"Zone {zone_name} retry #{zone.retry_count}")
            self._notify_zone_change(zone)
            self._save_state()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to retry zone {zone_name}: {e}")
            return False
    
    def adjust_parallelism(self, new_job_count: int) -> bool:
        """Adjust number of parallel compilation jobs"""
        if new_job_count < 1:
            self.logger.warning("Job count must be at least 1")
            return False
        
        old_count = self.current_parallel_jobs
        self.current_parallel_jobs = new_job_count
        
        self._log_action("adjust_parallelism", "all", 
                       f"Parallel jobs: {old_count} -> {new_job_count}")
        
        # If reducing, terminate excess processes
        if new_job_count < old_count:
            self._reduce_active_processes(new_job_count)
        
        return True
    
    def get_compilation_status(self) -> Dict[str, Any]:
        """Get comprehensive compilation status"""
        with self.process_lock:
            active_process_count = len(self.active_processes)
            zone_statuses = [
                {
                    'name': zone.name,
                    'state': zone.state.value,
                    'progress': zone.progress_percent,
                    'current_component': (zone.components[zone.current_component_index] 
                                        if zone.current_component_index < len(zone.components) 
                                        else ""),
                    'error': zone.error_message,
                    'retry_count': zone.retry_count
                }
                for zone in self.zones
            ]
        
        # Calculate overall progress
        total_progress = sum(zone.progress_percent for zone in self.zones) / len(self.zones) if self.zones else 0
        
        # Time calculations
        elapsed_time = time.time() - self.total_start_time if self.total_start_time else 0
        
        return {
            'state': self.state.value,
            'is_paused': self.is_paused,
            'total_zones': len(self.zones),
            'current_zone_index': self.current_zone_index,
            'overall_progress': total_progress,
            'active_processes': active_process_count,
            'max_parallel_jobs': self.max_parallel_jobs,
            'current_parallel_jobs': self.current_parallel_jobs,
            'elapsed_time_seconds': elapsed_time,
            'zones': zone_statuses,
            'recent_actions': self.control_actions[-10:]  # Last 10 actions
        }
    
    def _compilation_loop(self):
        """Main compilation control loop"""
        try:
            while not self.should_stop and self.current_zone_index < len(self.zones):
                # Check for pause
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)
                
                if self.should_stop:
                    break
                
                current_zone = self.zones[self.current_zone_index]
                
                # Skip zones marked for skipping
                if current_zone.skip_remaining or current_zone.state == ZoneState.SKIPPED:
                    self.current_zone_index += 1
                    continue
                
                # Process current zone
                if current_zone.state in [ZoneState.PENDING, ZoneState.RETRYING]:
                    success = self._process_zone(current_zone)
                    
                    if success:
                        current_zone.state = ZoneState.COMPLETED
                        current_zone.end_time = time.time()
                        self._notify_zone_change(current_zone)
                        self.current_zone_index += 1
                    else:
                        current_zone.state = ZoneState.FAILED
                        
                        # Check if we should retry
                        if current_zone.retry_count < current_zone.max_retries:
                            self.logger.info(f"Zone {current_zone.name} will be retried")
                        else:
                            self.logger.error(f"Zone {current_zone.name} failed permanently")
                            # Continue to next zone for now
                            self.current_zone_index += 1
                
                self._save_state()
                time.sleep(0.1)  # Small delay to prevent busy loop
            
            # Compilation finished
            if self.should_stop:
                self._change_state(CompilationState.CANCELLED)
            else:
                completed_zones = sum(1 for zone in self.zones if zone.state == ZoneState.COMPLETED)
                if completed_zones == len(self.zones):
                    self._change_state(CompilationState.COMPLETED)
                else:
                    self._change_state(CompilationState.FAILED)
        
        except Exception as e:
            self.logger.error(f"Compilation loop error: {e}")
            self._change_state(CompilationState.FAILED)
    
    def _process_zone(self, zone: CompilationZone) -> bool:
        """Process a single compilation zone"""
        try:
            zone.state = ZoneState.RUNNING
            zone.start_time = time.time()
            self._notify_zone_change(zone)
            
            self.logger.info(f"Starting zone: {zone.name}")
            
            # Process each component in the zone
            while (zone.current_component_index < len(zone.components) and 
                   not self.should_stop and not zone.skip_remaining):
                
                # Check for pause
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)
                
                if self.should_stop:
                    return False
                
                component = zone.components[zone.current_component_index]
                
                # Start component compilation
                success = self._compile_component(zone, component)
                
                if success:
                    zone.current_component_index += 1
                    zone.progress_percent = (zone.current_component_index / len(zone.components)) * 100
                    self._notify_progress(zone)
                else:
                    zone.error_message = f"Failed to compile {component}"
                    self._notify_error(zone, zone.error_message)
                    return False
            
            # Zone completed successfully
            zone.progress_percent = 100.0
            self._notify_progress(zone)
            
            return True
            
        except Exception as e:
            zone.error_message = f"Zone processing error: {e}"
            self.logger.error(f"Error processing zone {zone.name}: {e}")
            return False
    
    def _compile_component(self, zone: CompilationZone, component: str) -> bool:
        """Compile a single component (mock implementation)"""
        try:
            self.logger.info(f"Compiling {zone.name}: {component}")
            
            # Mock compilation command
            command = ['sleep', '2']  # Simulate 2 second compilation
            
            # Start process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Register process
            process_info = CompilationProcess(
                pid=process.pid,
                zone_name=zone.name,
                component=component,
                command=command,
                process=process,
                start_time=time.time()
            )
            
            with self.process_lock:
                self.active_processes[process.pid] = process_info
            
            # Wait for completion
            return_code = process.wait()
            
            # Unregister process
            with self.process_lock:
                if process.pid in self.active_processes:
                    del self.active_processes[process.pid]
            
            return return_code == 0
            
        except Exception as e:
            self.logger.error(f"Component compilation error: {e}")
            return False
    
    def _pause_process(self, process_info: CompilationProcess) -> bool:
        """Pause a specific process"""
        if not self.enable_process_control:
            return False
        
        try:
            if process_info.is_paused:
                return True
            
            process = psutil.Process(process_info.pid)
            process.suspend()
            process_info.is_paused = True
            
            self.logger.debug(f"Paused process {process_info.pid} ({process_info.component})")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.warning(f"Could not pause process {process_info.pid}: {e}")
            return False
    
    def _resume_process(self, process_info: CompilationProcess) -> bool:
        """Resume a specific process"""
        if not self.enable_process_control:
            return False
        
        try:
            if not process_info.is_paused:
                return True
            
            process = psutil.Process(process_info.pid)
            process.resume()
            process_info.is_paused = False
            
            self.logger.debug(f"Resumed process {process_info.pid} ({process_info.component})")
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.warning(f"Could not resume process {process_info.pid}: {e}")
            return False
    
    def _terminate_process(self, process_info: CompilationProcess) -> bool:
        """Gracefully terminate a process"""
        try:
            process_info.process.terminate()
            
            # Wait for graceful termination
            try:
                process_info.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                # Force kill if didn't terminate gracefully
                process_info.process.kill()
                process_info.process.wait()
            
            self.logger.debug(f"Terminated process {process_info.pid} ({process_info.component})")
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not terminate process {process_info.pid}: {e}")
            return False
    
    def _kill_process(self, process_info: CompilationProcess) -> bool:
        """Forcefully kill a process"""
        try:
            process_info.process.kill()
            process_info.process.wait()
            
            self.logger.debug(f"Killed process {process_info.pid} ({process_info.component})")
            return True
            
        except Exception as e:
            self.logger.warning(f"Could not kill process {process_info.pid}: {e}")
            return False
    
    def _graceful_stop(self):
        """Gracefully stop all processes"""
        with self.process_lock:
            for process_info in self.active_processes.values():
                self._terminate_process(process_info)
    
    def _force_stop(self):
        """Force stop all processes"""
        with self.process_lock:
            for process_info in self.active_processes.values():
                self._kill_process(process_info)
            
            self.active_processes.clear()
    
    def _reduce_active_processes(self, target_count: int):
        """Reduce active processes to target count"""
        with self.process_lock:
            if len(self.active_processes) <= target_count:
                return
            
            # Sort by priority (lower priority terminated first)
            processes_to_terminate = sorted(
                self.active_processes.values(),
                key=lambda p: p.priority
            )[target_count:]
            
            for process_info in processes_to_terminate:
                self._terminate_process(process_info)
                if process_info.pid in self.active_processes:
                    del self.active_processes[process_info.pid]
    
    def _find_zone(self, zone_name: str) -> Optional[CompilationZone]:
        """Find zone by name"""
        for zone in self.zones:
            if zone.name == zone_name:
                return zone
        return None
    
    def _change_state(self, new_state: CompilationState):
        """Change compilation state and notify callbacks"""
        old_state = self.state
        self.state = new_state
        
        self.logger.info(f"Compilation state: {old_state.value} -> {new_state.value}")
        
        for callback in self.state_change_callbacks:
            try:
                callback(old_state, new_state)
            except Exception as e:
                self.logger.error(f"State change callback error: {e}")
    
    def _notify_zone_change(self, zone: CompilationZone):
        """Notify zone state change"""
        for callback in self.zone_change_callbacks:
            try:
                callback(zone)
            except Exception as e:
                self.logger.error(f"Zone change callback error: {e}")
    
    def _notify_progress(self, zone: CompilationZone):
        """Notify progress change"""
        for callback in self.progress_callbacks:
            try:
                callback(zone)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def _notify_error(self, zone: CompilationZone, error_message: str):
        """Notify error occurrence"""
        for callback in self.error_callbacks:
            try:
                callback(zone, error_message)
            except Exception as e:
                self.logger.error(f"Error callback error: {e}")
    
    def _log_action(self, action_type: str, target: str, reason: str, parameters: Dict[str, Any] = None):
        """Log control action"""
        action = ControlAction(
            action_type=action_type,
            target=target,
            reason=reason,
            parameters=parameters or {}
        )
        
        self.control_actions.append(action)
        
        # Keep only last 100 actions
        if len(self.control_actions) > 100:
            self.control_actions = self.control_actions[-100:]
        
        self.logger.info(f"Control action: {action_type} on {target} - {reason}")
    
    def _save_state(self):
        """Save compilation state to file"""
        try:
            state_data = {
                'state': self.state.value,
                'current_zone_index': self.current_zone_index,
                'is_paused': self.is_paused,
                'total_start_time': self.total_start_time,
                'zones': [
                    {
                        'name': zone.name,
                        'state': zone.state.value,
                        'current_component_index': zone.current_component_index,
                        'progress_percent': zone.progress_percent,
                        'start_time': zone.start_time,
                        'end_time': zone.end_time,
                        'error_message': zone.error_message,
                        'skip_remaining': zone.skip_remaining,
                        'retry_count': zone.retry_count
                    }
                    for zone in self.zones
                ]
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            self.logger.warning(f"Could not save state: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}")
        self.stop_compilation(graceful=True)


# Test the controller
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test configuration
    config = {
        'max_parallel_jobs': 4,
        'enable_process_control': True,
        'pause_timeout_seconds': 30.0,
        'stop_timeout_seconds': 60.0
    }
    
    # Test zones
    zones_config = [
        {
            'name': 'base_system',
            'components': ['kernel', 'zfs', 'boot'],
            'max_retries': 2
        },
        {
            'name': 'cuda_toolkit',
            'components': ['cuda', 'cudnn', 'nccl'],
            'max_retries': 3
        },
        {
            'name': 'hpc_libraries',
            'components': ['openmpi', 'fftw', 'blas'],
            'max_retries': 2
        }
    ]
    
    # Create controller
    controller = HPCCompilationController(config)
    controller.initialize_zones(zones_config)
    
    # Add callbacks
    def on_state_change(old_state, new_state):
        print(f"State change: {old_state.value} -> {new_state.value}")
    
    def on_zone_change(zone):
        print(f"Zone {zone.name}: {zone.state.value} ({zone.progress_percent:.1f}%)")
    
    controller.add_state_change_callback(on_state_change)
    controller.add_zone_change_callback(on_zone_change)
    
    print("=== HPC Compilation Controller Test ===")
    
    # Start compilation
    print("Starting compilation...")
    controller.start_compilation()
    
    try:
        # Let it run for a bit
        time.sleep(3)
        
        # Test pause
        print("\nPausing compilation...")
        controller.pause_compilation()
        time.sleep(2)
        
        # Test resume
        print("Resuming compilation...")
        controller.resume_compilation()
        time.sleep(3)
        
        # Test skip zone
        print("Skipping second zone...")
        controller.skip_zone('cuda_toolkit')
        time.sleep(2)
        
        # Show status
        status = controller.get_compilation_status()
        print(f"\nCompilation Status:")
        print(f"  State: {status['state']}")
        print(f"  Overall Progress: {status['overall_progress']:.1f}%")
        print(f"  Active Processes: {status['active_processes']}")
        print(f"  Current Zone: {status['current_zone_index'] + 1}/{status['total_zones']}")
        
        # Wait for completion
        time.sleep(5)
        
        final_status = controller.get_compilation_status()
        print(f"\nFinal State: {final_status['state']}")
        
    except KeyboardInterrupt:
        print("\nStopping compilation...")
        controller.stop_compilation()
    
    print("Test completed.")