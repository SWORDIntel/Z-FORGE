#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Resource Monitor and Thermal Protection System
Advanced system resource monitoring with intelligent thermal protection
"""

import os
import time
import json
import logging
import threading
import subprocess
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import psutil

class ThermalState(Enum):
    """Thermal protection states"""
    NORMAL = "normal"           # < 75°C
    ELEVATED = "elevated"       # 75-85°C
    WARNING = "warning"         # 85-95°C
    CRITICAL = "critical"       # 95-100°C
    EMERGENCY = "emergency"     # > 100°C

class ResourceState(Enum):
    """Resource availability states"""
    OPTIMAL = "optimal"         # < 70% usage
    ACCEPTABLE = "acceptable"   # 70-85% usage
    STRESSED = "stressed"       # 85-95% usage
    CRITICAL = "critical"       # > 95% usage

@dataclass
class ThermalReading:
    """Single thermal sensor reading"""
    sensor_name: str
    temperature: float
    critical_temp: float = 100.0
    max_temp: float = 0.0
    timestamp: float = field(default_factory=time.time)

@dataclass
class ResourceMetrics:
    """Complete system resource metrics"""
    # CPU metrics
    cpu_usage_percent: float = 0.0
    cpu_frequency_mhz: float = 0.0
    cpu_cores_physical: int = 0
    cpu_cores_logical: int = 0
    load_average_1m: float = 0.0
    load_average_5m: float = 0.0
    load_average_15m: float = 0.0
    
    # Memory metrics
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0
    
    # Thermal metrics
    cpu_temperature: float = 0.0
    gpu_temperature: float = 0.0
    thermal_sensors: List[ThermalReading] = field(default_factory=list)
    thermal_state: ThermalState = ThermalState.NORMAL
    
    # Disk metrics
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0
    disk_io_read_mb: float = 0.0
    disk_io_write_mb: float = 0.0
    
    # Network metrics
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    network_packets_sent: int = 0
    network_packets_recv: int = 0
    
    # Process metrics
    active_processes: int = 0
    compilation_processes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Performance metrics
    compilation_efficiency: float = 100.0  # Percentage of optimal performance
    estimated_slowdown: float = 1.0        # Performance multiplier (1.0 = no slowdown)
    
    # Timestamp
    timestamp: float = field(default_factory=time.time)

@dataclass
class ThermalProtectionAction:
    """Thermal protection action taken"""
    action_type: str            # "throttle", "pause", "reduce_jobs", "emergency_stop"
    trigger_temperature: float
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class HPCResourceMonitor:
    """
    Advanced resource monitor for HPC compilation
    
    Features:
    - Real-time system resource monitoring
    - Thermal protection with automatic throttling
    - Memory pressure detection and management
    - Compilation process monitoring
    - Performance optimization recommendations
    - Emergency protection protocols
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Monitoring configuration
        self.update_interval = config.get('update_interval_seconds', 1.0)
        self.thermal_threshold_warning = config.get('thermal_threshold_celsius', 85)
        self.thermal_threshold_critical = config.get('thermal_critical_celsius', 95)
        self.memory_threshold_warning = config.get('memory_threshold_percent', 85)
        self.memory_threshold_critical = config.get('memory_critical_percent', 95)
        
        # State tracking
        self.current_metrics = ResourceMetrics()
        self.metrics_history: List[ResourceMetrics] = []
        self.max_history_size = 300  # 5 minutes at 1 second intervals
        
        # Thermal protection
        self.thermal_actions: List[ThermalProtectionAction] = []
        self.thermal_state = ThermalState.NORMAL
        self.throttled_processes: List[int] = []
        
        # Threading
        self.monitoring_thread = None
        self.should_stop = False
        self.metrics_lock = threading.Lock()
        
        # Process tracking
        self.compilation_pids: List[int] = []
        
        # Callbacks for thermal events
        self.thermal_callbacks: Dict[ThermalState, List[callable]] = {
            state: [] for state in ThermalState
        }
        
        # Initialize thermal sensor detection
        self.thermal_sensors = self._detect_thermal_sensors()
        
        # Initialize baseline metrics
        self._initialize_baseline_metrics()
    
    def start_monitoring(self):
        """Start resource monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.should_stop = False
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.should_stop = True
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)
        
        self.logger.info("Resource monitoring stopped")
    
    def add_thermal_callback(self, state: ThermalState, callback: callable):
        """Add callback for thermal state changes"""
        self.thermal_callbacks[state].append(callback)
    
    def register_compilation_process(self, pid: int):
        """Register a compilation process for monitoring"""
        if pid not in self.compilation_pids:
            self.compilation_pids.append(pid)
            self.logger.info(f"Registered compilation process: {pid}")
    
    def unregister_compilation_process(self, pid: int):
        """Unregister a compilation process"""
        if pid in self.compilation_pids:
            self.compilation_pids.remove(pid)
            self.logger.info(f"Unregistered compilation process: {pid}")
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics (thread-safe)"""
        with self.metrics_lock:
            return self.current_metrics
    
    def get_metrics_history(self) -> List[ResourceMetrics]:
        """Get metrics history (thread-safe)"""
        with self.metrics_lock:
            return self.metrics_history.copy()
    
    def get_thermal_recommendation(self) -> Dict[str, Any]:
        """Get thermal protection recommendation"""
        current_temp = self.current_metrics.cpu_temperature
        
        if current_temp >= self.thermal_threshold_critical:
            return {
                'action': 'emergency_throttle',
                'severity': 'critical',
                'message': f'CPU temperature {current_temp:.1f}°C critical - emergency throttling required',
                'recommended_parallel_jobs': 1,
                'pause_compilation': True
            }
        elif current_temp >= self.thermal_threshold_warning:
            recommended_jobs = max(1, self.current_metrics.cpu_cores_physical // 2)
            return {
                'action': 'reduce_parallelism',
                'severity': 'warning', 
                'message': f'CPU temperature {current_temp:.1f}°C elevated - reduce parallel jobs',
                'recommended_parallel_jobs': recommended_jobs,
                'pause_compilation': False
            }
        else:
            return {
                'action': 'normal',
                'severity': 'normal',
                'message': f'CPU temperature {current_temp:.1f}°C normal',
                'recommended_parallel_jobs': self.current_metrics.cpu_cores_physical,
                'pause_compilation': False
            }
    
    def get_memory_recommendation(self) -> Dict[str, Any]:
        """Get memory usage recommendation"""
        mem_percent = self.current_metrics.memory_percent
        
        if mem_percent >= self.memory_threshold_critical:
            return {
                'action': 'emergency_reduce_jobs',
                'severity': 'critical',
                'message': f'Memory usage {mem_percent:.1f}% critical - reduce compilation jobs',
                'recommended_parallel_jobs': 1
            }
        elif mem_percent >= self.memory_threshold_warning:
            recommended_jobs = max(1, self.current_metrics.cpu_cores_physical // 2)
            return {
                'action': 'reduce_parallelism',
                'severity': 'warning',
                'message': f'Memory usage {mem_percent:.1f}% high - reduce parallel jobs',
                'recommended_parallel_jobs': recommended_jobs
            }
        else:
            return {
                'action': 'normal',
                'severity': 'normal',
                'message': f'Memory usage {mem_percent:.1f}% normal',
                'recommended_parallel_jobs': self.current_metrics.cpu_cores_physical
            }
    
    def get_performance_analysis(self) -> Dict[str, Any]:
        """Analyze current performance and provide recommendations"""
        thermal_rec = self.get_thermal_recommendation()
        memory_rec = self.get_memory_recommendation()
        
        # Determine limiting factor
        limiting_factors = []
        recommended_jobs = self.current_metrics.cpu_cores_physical
        
        if thermal_rec['severity'] in ['warning', 'critical']:
            limiting_factors.append('thermal')
            recommended_jobs = min(recommended_jobs, thermal_rec['recommended_parallel_jobs'])
        
        if memory_rec['severity'] in ['warning', 'critical']:
            limiting_factors.append('memory')
            recommended_jobs = min(recommended_jobs, memory_rec['recommended_parallel_jobs'])
        
        # Calculate efficiency
        efficiency = 100.0
        if limiting_factors:
            thermal_penalty = 20.0 if 'thermal' in limiting_factors else 0.0
            memory_penalty = 15.0 if 'memory' in limiting_factors else 0.0
            efficiency = max(50.0, 100.0 - thermal_penalty - memory_penalty)
        
        # Performance recommendations
        recommendations = []
        
        if self.current_metrics.cpu_temperature > 85:
            recommendations.append("Consider improving system cooling for better performance")
        
        if self.current_metrics.memory_percent > 80:
            recommendations.append("Close unnecessary applications to free memory")
        
        if self.current_metrics.disk_percent > 90:
            recommendations.append("Free disk space to prevent build failures")
        
        if not recommendations:
            recommendations.append("System resources optimal for compilation")
        
        return {
            'efficiency_percent': efficiency,
            'limiting_factors': limiting_factors,
            'recommended_parallel_jobs': recommended_jobs,
            'thermal_state': self.thermal_state.value,
            'recommendations': recommendations,
            'performance_impact': {
                'thermal': thermal_rec,
                'memory': memory_rec
            }
        }
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while not self.should_stop:
                start_time = time.time()
                
                # Update metrics
                new_metrics = self._collect_system_metrics()
                
                with self.metrics_lock:
                    self.current_metrics = new_metrics
                    self.metrics_history.append(new_metrics)
                    
                    # Trim history
                    if len(self.metrics_history) > self.max_history_size:
                        self.metrics_history = self.metrics_history[-self.max_history_size:]
                
                # Check thermal state changes
                self._check_thermal_state_changes(new_metrics)
                
                # Apply thermal protection if needed
                self._apply_thermal_protection(new_metrics)
                
                # Sleep for remaining interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed)
                time.sleep(sleep_time)
                
        except Exception as e:
            self.logger.error(f"Monitoring loop error: {e}")
    
    def _collect_system_metrics(self) -> ResourceMetrics:
        """Collect comprehensive system metrics"""
        metrics = ResourceMetrics()
        
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            cpu_count_logical = psutil.cpu_count(logical=True)
            load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)
            
            metrics.cpu_usage_percent = cpu_percent
            metrics.cpu_frequency_mhz = cpu_freq.current if cpu_freq else 0
            metrics.cpu_cores_physical = cpu_count
            metrics.cpu_cores_logical = cpu_count_logical
            metrics.load_average_1m = load_avg[0]
            metrics.load_average_5m = load_avg[1]
            metrics.load_average_15m = load_avg[2]
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            metrics.memory_total_gb = memory.total / (1024**3)
            metrics.memory_used_gb = memory.used / (1024**3)
            metrics.memory_available_gb = memory.available / (1024**3)
            metrics.memory_percent = memory.percent
            metrics.swap_total_gb = swap.total / (1024**3)
            metrics.swap_used_gb = swap.used / (1024**3)
            metrics.swap_percent = swap.percent
            
            # Thermal metrics
            thermal_readings = self._read_thermal_sensors()
            metrics.thermal_sensors = thermal_readings
            
            # Find CPU temperature
            cpu_temps = [r.temperature for r in thermal_readings if 'cpu' in r.sensor_name.lower()]
            if cpu_temps:
                metrics.cpu_temperature = max(cpu_temps)
            else:
                # Fallback to any temperature sensor
                all_temps = [r.temperature for r in thermal_readings]
                metrics.cpu_temperature = max(all_temps) if all_temps else 0.0
            
            # GPU temperature (if available)
            gpu_temps = [r.temperature for r in thermal_readings if 'gpu' in r.sensor_name.lower()]
            metrics.gpu_temperature = max(gpu_temps) if gpu_temps else 0.0
            
            # Determine thermal state
            metrics.thermal_state = self._determine_thermal_state(metrics.cpu_temperature)
            
            # Disk metrics
            disk_usage = psutil.disk_usage('/')
            disk_io = psutil.disk_io_counters()
            
            metrics.disk_total_gb = disk_usage.total / (1024**3)
            metrics.disk_used_gb = disk_usage.used / (1024**3)
            metrics.disk_free_gb = disk_usage.free / (1024**3)
            metrics.disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            if disk_io:
                metrics.disk_io_read_mb = disk_io.read_bytes / (1024**2)
                metrics.disk_io_write_mb = disk_io.write_bytes / (1024**2)
            
            # Network metrics
            network_io = psutil.net_io_counters()
            if network_io:
                metrics.network_bytes_sent = network_io.bytes_sent
                metrics.network_bytes_recv = network_io.bytes_recv
                metrics.network_packets_sent = network_io.packets_sent
                metrics.network_packets_recv = network_io.packets_recv
            
            # Process metrics
            all_processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
            metrics.active_processes = len(all_processes)
            
            # Compilation processes
            compilation_processes = []
            for proc in all_processes:
                try:
                    if proc.info['pid'] in self.compilation_pids:
                        compilation_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc.info['cpu_percent'],
                            'memory_percent': proc.info['memory_percent']
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            metrics.compilation_processes = compilation_processes
            
            # Performance calculation
            efficiency = 100.0
            slowdown = 1.0
            
            # Thermal impact
            if metrics.cpu_temperature > 95:
                efficiency *= 0.6  # 40% penalty
                slowdown *= 1.8
            elif metrics.cpu_temperature > 85:
                efficiency *= 0.8  # 20% penalty
                slowdown *= 1.3
            elif metrics.cpu_temperature > 75:
                efficiency *= 0.9  # 10% penalty
                slowdown *= 1.1
            
            # Memory impact
            if metrics.memory_percent > 95:
                efficiency *= 0.7  # 30% penalty
                slowdown *= 1.5
            elif metrics.memory_percent > 85:
                efficiency *= 0.85  # 15% penalty
                slowdown *= 1.2
            
            metrics.compilation_efficiency = efficiency
            metrics.estimated_slowdown = slowdown
            
        except Exception as e:
            self.logger.warning(f"Error collecting metrics: {e}")
        
        return metrics
    
    def _detect_thermal_sensors(self) -> List[str]:
        """Detect available thermal sensors"""
        sensors = []
        
        # Common thermal sensor paths
        thermal_paths = [
            '/sys/class/thermal/thermal_zone*/temp',
            '/sys/devices/platform/coretemp.*/hwmon/hwmon*/temp*_input',
            '/sys/devices/pci*/*/*/hwmon/hwmon*/temp*_input'
        ]
        
        for path_pattern in thermal_paths:
            for path in glob.glob(path_pattern):
                try:
                    # Test if readable
                    with open(path, 'r') as f:
                        f.read().strip()
                    sensors.append(path)
                except:
                    pass
        
        self.logger.info(f"Detected {len(sensors)} thermal sensors")
        return sensors
    
    def _read_thermal_sensors(self) -> List[ThermalReading]:
        """Read all thermal sensors"""
        readings = []
        
        for sensor_path in self.thermal_sensors:
            try:
                with open(sensor_path, 'r') as f:
                    temp_raw = int(f.read().strip())
                    
                # Convert to Celsius
                if temp_raw > 1000:
                    temperature = temp_raw / 1000.0  # millidegree to degree
                else:
                    temperature = float(temp_raw)  # already in degrees
                
                # Determine sensor name
                sensor_name = self._get_sensor_name(sensor_path)
                
                # Get critical temperature if available
                critical_temp = self._get_critical_temp(sensor_path)
                
                reading = ThermalReading(
                    sensor_name=sensor_name,
                    temperature=temperature,
                    critical_temp=critical_temp
                )
                
                readings.append(reading)
                
            except Exception as e:
                self.logger.debug(f"Error reading sensor {sensor_path}: {e}")
        
        return readings
    
    def _get_sensor_name(self, sensor_path: str) -> str:
        """Get human-readable sensor name"""
        if 'thermal_zone' in sensor_path:
            zone_num = sensor_path.split('thermal_zone')[1].split('/')[0]
            return f"thermal_zone{zone_num}"
        elif 'coretemp' in sensor_path:
            if 'temp1' in sensor_path:
                return "cpu_package"
            elif 'temp2' in sensor_path:
                return "cpu_core0"
            elif 'temp3' in sensor_path:
                return "cpu_core1"
            else:
                return "cpu_temp"
        elif 'hwmon' in sensor_path:
            return f"hwmon_sensor"
        else:
            return "unknown_sensor"
    
    def _get_critical_temp(self, sensor_path: str) -> float:
        """Get critical temperature for sensor"""
        critical_path = sensor_path.replace('_input', '_crit')
        
        try:
            with open(critical_path, 'r') as f:
                crit_raw = int(f.read().strip())
                return crit_raw / 1000.0 if crit_raw > 1000 else float(crit_raw)
        except:
            return 100.0  # Default critical temperature
    
    def _determine_thermal_state(self, temperature: float) -> ThermalState:
        """Determine thermal state from temperature"""
        if temperature >= 100:
            return ThermalState.EMERGENCY
        elif temperature >= 95:
            return ThermalState.CRITICAL
        elif temperature >= 85:
            return ThermalState.WARNING
        elif temperature >= 75:
            return ThermalState.ELEVATED
        else:
            return ThermalState.NORMAL
    
    def _check_thermal_state_changes(self, metrics: ResourceMetrics):
        """Check for thermal state changes and trigger callbacks"""
        new_state = metrics.thermal_state
        
        if new_state != self.thermal_state:
            old_state = self.thermal_state
            self.thermal_state = new_state
            
            self.logger.info(f"Thermal state changed: {old_state.value} -> {new_state.value}")
            
            # Trigger callbacks
            for callback in self.thermal_callbacks[new_state]:
                try:
                    callback(old_state, new_state, metrics)
                except Exception as e:
                    self.logger.error(f"Thermal callback error: {e}")
    
    def _apply_thermal_protection(self, metrics: ResourceMetrics):
        """Apply thermal protection measures"""
        temp = metrics.cpu_temperature
        
        if temp >= 100:  # Emergency
            self._emergency_thermal_protection(metrics)
        elif temp >= 95:  # Critical
            self._critical_thermal_protection(metrics)
        elif temp >= 85:  # Warning
            self._warning_thermal_protection(metrics)
    
    def _emergency_thermal_protection(self, metrics: ResourceMetrics):
        """Emergency thermal protection - immediate action required"""
        action = ThermalProtectionAction(
            action_type="emergency_stop",
            trigger_temperature=metrics.cpu_temperature,
            description=f"Emergency thermal protection at {metrics.cpu_temperature:.1f}°C",
            parameters={'forced_stop': True}
        )
        
        self.thermal_actions.append(action)
        self.logger.critical(f"EMERGENCY THERMAL PROTECTION: {action.description}")
        
        # Pause all compilation processes
        self._throttle_compilation_processes(pause=True)
    
    def _critical_thermal_protection(self, metrics: ResourceMetrics):
        """Critical thermal protection - severe throttling"""
        action = ThermalProtectionAction(
            action_type="severe_throttle",
            trigger_temperature=metrics.cpu_temperature,
            description=f"Critical thermal throttling at {metrics.cpu_temperature:.1f}°C",
            parameters={'max_processes': 1, 'priority_reduction': 19}
        )
        
        self.thermal_actions.append(action)
        self.logger.warning(f"CRITICAL THERMAL PROTECTION: {action.description}")
        
        # Reduce compilation to single process
        self._throttle_compilation_processes(max_processes=1)
    
    def _warning_thermal_protection(self, metrics: ResourceMetrics):
        """Warning thermal protection - moderate throttling"""
        max_processes = max(1, metrics.cpu_cores_physical // 2)
        
        action = ThermalProtectionAction(
            action_type="moderate_throttle", 
            trigger_temperature=metrics.cpu_temperature,
            description=f"Thermal throttling at {metrics.cpu_temperature:.1f}°C",
            parameters={'max_processes': max_processes, 'priority_reduction': 10}
        )
        
        self.thermal_actions.append(action)
        self.logger.warning(f"THERMAL PROTECTION: {action.description}")
        
        # Reduce compilation processes
        self._throttle_compilation_processes(max_processes=max_processes)
    
    def _throttle_compilation_processes(self, max_processes: Optional[int] = None, pause: bool = False):
        """Throttle compilation processes for thermal protection"""
        for pid in self.compilation_pids.copy():
            try:
                process = psutil.Process(pid)
                
                if pause:
                    # Suspend process
                    process.suspend()
                    if pid not in self.throttled_processes:
                        self.throttled_processes.append(pid)
                elif max_processes is not None:
                    # Reduce priority
                    process.nice(10)  # Lower priority
                    if pid not in self.throttled_processes:
                        self.throttled_processes.append(pid)
                
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.logger.debug(f"Could not throttle process {pid}: {e}")
                self.compilation_pids.remove(pid)
    
    def _initialize_baseline_metrics(self):
        """Initialize baseline system metrics"""
        try:
            self.current_metrics = self._collect_system_metrics()
            self.logger.info("Baseline metrics initialized")
        except Exception as e:
            self.logger.error(f"Error initializing baseline metrics: {e}")


# Test the monitor
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Test configuration
    config = {
        'update_interval_seconds': 2.0,
        'thermal_threshold_celsius': 85,
        'thermal_critical_celsius': 95,
        'memory_threshold_percent': 85,
        'memory_critical_percent': 95
    }
    
    # Create monitor
    monitor = HPCResourceMonitor(config)
    
    def thermal_callback(old_state, new_state, metrics):
        print(f"Thermal state changed: {old_state.value} -> {new_state.value} at {metrics.cpu_temperature:.1f}°C")
    
    # Add thermal callback
    monitor.add_thermal_callback(ThermalState.WARNING, thermal_callback)
    monitor.add_thermal_callback(ThermalState.CRITICAL, thermal_callback)
    
    # Start monitoring
    print("Starting HPC Resource Monitor test...")
    monitor.start_monitoring()
    
    try:
        # Run for 30 seconds
        for i in range(15):
            time.sleep(2)
            
            # Get current metrics
            metrics = monitor.get_current_metrics()
            
            print(f"\n=== Metrics Update {i+1} ===")
            print(f"CPU: {metrics.cpu_usage_percent:.1f}% @ {metrics.cpu_temperature:.1f}°C")
            print(f"Memory: {metrics.memory_percent:.1f}% ({metrics.memory_used_gb:.1f}/{metrics.memory_total_gb:.1f} GB)")
            print(f"Disk: {metrics.disk_percent:.1f}% ({metrics.disk_free_gb:.1f} GB free)")
            print(f"Thermal State: {metrics.thermal_state.value}")
            
            # Get performance analysis
            analysis = monitor.get_performance_analysis()
            print(f"Performance Efficiency: {analysis['efficiency_percent']:.1f}%")
            print(f"Recommended Parallel Jobs: {analysis['recommended_parallel_jobs']}")
            
            if analysis['limiting_factors']:
                print(f"Limiting Factors: {', '.join(analysis['limiting_factors'])}")
            
            if analysis['recommendations']:
                print("Recommendations:")
                for rec in analysis['recommendations']:
                    print(f"  - {rec}")
    
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    finally:
        monitor.stop_monitoring()
        print("Monitor stopped.")