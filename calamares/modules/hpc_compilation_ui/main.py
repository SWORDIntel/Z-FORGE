#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Compilation UI Module for Calamares
Provides comprehensive UI for extended HPC driver compilation during installation
"""

import sys
import os
import time
import json
import logging
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Add calamares path for imports
sys.path.insert(0, '/usr/lib/calamares/modules')

try:
    import libcalamares
    from PyQt5 import QtCore, QtWidgets, QtGui
    from PyQt5.QtCore import QThread, QTimer, QObject, pyqtSignal, QProcess
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *
except ImportError as e:
    # Fallback for development/testing
    class MockLibCalamares:
        def debug(self, msg): print(f"DEBUG: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
        def job_progress(self, percent): pass
        def check_target_env_call(self, cmd): return 0
        
    libcalamares = MockLibCalamares()
    from PyQt5 import QtCore, QtWidgets, QtGui
    from PyQt5.QtCore import QThread, QTimer, QObject, pyqtSignal, QProcess
    from PyQt5.QtWidgets import *
    from PyQt5.QtGui import *

@dataclass
class CompilationZone:
    """Compilation zone information"""
    name: str
    size_gb: float
    components: List[str]
    compile_time_estimate: int  # minutes
    status: str = "pending"  # pending, compiling, completed, failed
    progress: int = 0  # 0-100
    current_component: str = ""
    error_message: str = ""

@dataclass
class SystemMetrics:
    """System resource metrics"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_total_gb: float = 0.0
    cpu_temperature: float = 0.0
    disk_usage: float = 0.0
    compilation_speed: float = 0.0  # components/hour

class CompilationWorker(QObject):
    """Worker thread for HPC compilation with progress monitoring"""
    
    # Signals
    progress_update = pyqtSignal(str, int, str)  # zone_name, percent, message
    zone_started = pyqtSignal(str)  # zone_name
    zone_completed = pyqtSignal(str, bool)  # zone_name, success
    compilation_finished = pyqtSignal(bool, str)  # success, message
    error_occurred = pyqtSignal(str, str)  # zone_name, error_message
    metrics_update = pyqtSignal(dict)  # system metrics
    compiler_output = pyqtSignal(str)  # compiler output line
    
    def __init__(self, zones: List[CompilationZone], config: Dict[str, Any]):
        super().__init__()
        self.zones = zones
        self.config = config
        self.is_paused = False
        self.should_stop = False
        self.current_zone_index = 0
        self.start_time = time.time()
        
        # Setup logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Metrics monitoring
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self._update_metrics)
        
    def start_compilation(self):
        """Start the compilation process"""
        self.logger.info("Starting HPC compilation process...")
        self.metrics_timer.start(1000)  # Update metrics every second
        
        try:
            self._execute_compilation_plan()
        except Exception as e:
            self.error_occurred.emit("system", str(e))
            self.compilation_finished.emit(False, f"Compilation failed: {e}")
        finally:
            self.metrics_timer.stop()
    
    def pause_compilation(self):
        """Pause compilation"""
        self.is_paused = True
        self.logger.info("Compilation paused by user")
    
    def resume_compilation(self):
        """Resume compilation"""
        self.is_paused = False
        self.logger.info("Compilation resumed by user")
    
    def stop_compilation(self):
        """Stop compilation"""
        self.should_stop = True
        self.logger.info("Compilation stop requested by user")
    
    def skip_current_zone(self):
        """Skip current compilation zone"""
        if self.current_zone_index < len(self.zones):
            zone = self.zones[self.current_zone_index]
            zone.status = "skipped"
            self.logger.warning(f"Skipping zone: {zone.name}")
            self.zone_completed.emit(zone.name, False)
    
    def _execute_compilation_plan(self):
        """Execute compilation plan with progress tracking"""
        total_zones = len(self.zones)
        
        for zone_index, zone in enumerate(self.zones):
            if self.should_stop:
                break
                
            self.current_zone_index = zone_index
            
            # Wait if paused
            while self.is_paused and not self.should_stop:
                time.sleep(0.1)
            
            if self.should_stop:
                break
            
            self.logger.info(f"Starting zone: {zone.name}")
            zone.status = "compiling"
            self.zone_started.emit(zone.name)
            
            # Compile zone
            try:
                success = self._compile_zone(zone)
                
                if success:
                    zone.status = "completed"
                    self.zone_completed.emit(zone.name, True)
                    self.logger.info(f"Completed zone: {zone.name}")
                else:
                    zone.status = "failed"
                    self.zone_completed.emit(zone.name, False)
                    self.logger.error(f"Failed zone: {zone.name}")
                    
                    # Check if it's a critical zone
                    if zone.name in ["cuda_toolkit", "base_system"]:
                        self.compilation_finished.emit(False, f"Critical zone {zone.name} failed")
                        return
                        
            except Exception as e:
                zone.status = "failed"
                zone.error_message = str(e)
                self.error_occurred.emit(zone.name, str(e))
                self.logger.error(f"Zone {zone.name} failed with exception: {e}")
        
        # Compilation completed
        successful_zones = len([z for z in self.zones if z.status == "completed"])
        total_time = time.time() - self.start_time
        
        if successful_zones == total_zones:
            message = f"All {total_zones} zones compiled successfully in {total_time/3600:.1f} hours"
            self.compilation_finished.emit(True, message)
        else:
            failed_zones = total_zones - successful_zones
            message = f"Compilation completed with {failed_zones} failures in {total_time/3600:.1f} hours"
            self.compilation_finished.emit(False, message)
    
    def _compile_zone(self, zone: CompilationZone) -> bool:
        """Compile a specific zone"""
        try:
            component_count = len(zone.components)
            
            for i, component in enumerate(zone.components):
                if self.should_stop:
                    return False
                
                # Wait if paused
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)
                
                if self.should_stop:
                    return False
                
                zone.current_component = component
                progress = int((i / component_count) * 100)
                zone.progress = progress
                
                self.progress_update.emit(
                    zone.name, 
                    progress, 
                    f"Compiling: {component}"
                )
                
                # Simulate compilation (in real implementation, this would call actual build tools)
                success = self._compile_component(component, zone)
                
                if not success:
                    zone.error_message = f"Failed to compile {component}"
                    return False
                
                # Emit compiler output (mock)
                self.compiler_output.emit(f"[{component}] Compilation successful")
            
            # Final progress update
            zone.progress = 100
            self.progress_update.emit(zone.name, 100, f"Zone completed: {len(zone.components)} components")
            
            return True
            
        except Exception as e:
            zone.error_message = str(e)
            self.logger.error(f"Zone {zone.name} compilation failed: {e}")
            return False
    
    def _compile_component(self, component: str, zone: CompilationZone) -> bool:
        """Compile individual component (mock implementation)"""
        try:
            # Mock compilation time (scaled for demo)
            import random
            compile_time = random.uniform(0.5, 2.0)  # 0.5-2 seconds instead of minutes
            
            # Emit periodic progress during component compilation
            steps = 10
            for step in range(steps):
                if self.should_stop:
                    return False
                
                while self.is_paused and not self.should_stop:
                    time.sleep(0.1)
                
                time.sleep(compile_time / steps)
                
                step_progress = int((step / steps) * 100)
                step_message = f"Building {component}: {step_progress}%"
                
                # Emit compiler output
                if step % 3 == 0:  # Emit output every few steps
                    self.compiler_output.emit(f"  {component}: {step_message}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Component {component} failed: {e}")
            return False
    
    def _update_metrics(self):
        """Update system metrics"""
        try:
            # CPU usage
            with open('/proc/loadavg', 'r') as f:
                load = float(f.read().split()[0])
                cpu_usage = min(load * 25, 100)  # Rough approximation
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
                
            mem_total = int([line for line in meminfo.split('\n') 
                           if line.startswith('MemTotal:')][0].split()[1])
            mem_available = int([line for line in meminfo.split('\n') 
                               if line.startswith('MemAvailable:')][0].split()[1])
            
            memory_total_gb = mem_total / (1024 * 1024)
            memory_usage = ((mem_total - mem_available) / mem_total) * 100
            
            # CPU temperature (if available)
            cpu_temp = 0.0
            temp_files = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/devices/platform/coretemp.0/hwmon/hwmon*/temp1_input'
            ]
            
            for temp_file in temp_files:
                try:
                    with open(temp_file, 'r') as f:
                        cpu_temp = float(f.read().strip()) / 1000.0
                    break
                except:
                    continue
            
            # Disk usage for workspace
            import shutil
            workspace_stat = shutil.disk_usage('/tmp')
            disk_usage = ((workspace_stat.total - workspace_stat.free) / workspace_stat.total) * 100
            
            # Compilation speed (components per hour)
            elapsed_hours = (time.time() - self.start_time) / 3600
            completed_components = sum(1 for zone in self.zones 
                                     for _ in zone.components 
                                     if zone.status == "completed")
            compilation_speed = completed_components / elapsed_hours if elapsed_hours > 0 else 0
            
            metrics = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'memory_total_gb': memory_total_gb,
                'cpu_temperature': cpu_temp,
                'disk_usage': disk_usage,
                'compilation_speed': compilation_speed
            }
            
            self.metrics_update.emit(metrics)
            
        except Exception as e:
            self.logger.warning(f"Could not update metrics: {e}")

class HPCCompilationWidget(QWidget):
    """Main HPC compilation UI widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = {}
        self.zones = []
        self.worker = None
        self.worker_thread = None
        self.advanced_mode = False
        self.start_time = None
        
        self.setupUI()
        self.load_configuration()
        self.setup_compilation_zones()
        
    def setupUI(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header = self.create_header()
        layout.addWidget(header)
        
        # Main content with tabs
        self.tab_widget = QTabWidget()
        
        # Simple mode tab
        self.simple_tab = self.create_simple_tab()
        self.tab_widget.addTab(self.simple_tab, "Overview")
        
        # Advanced mode tab
        self.advanced_tab = self.create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, "Advanced")
        
        # System monitoring tab
        self.monitoring_tab = self.create_monitoring_tab()
        self.tab_widget.addTab(self.monitoring_tab, "System Monitor")
        
        # Logs tab
        self.logs_tab = self.create_logs_tab()
        self.tab_widget.addTab(self.logs_tab, "Compiler Output")
        
        layout.addWidget(self.tab_widget)
        
        # Control buttons
        controls = self.create_controls()
        layout.addWidget(controls)
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        self.setLayout(layout)
        
    def create_header(self) -> QWidget:
        """Create header widget"""
        header = QWidget()
        layout = QHBoxLayout(header)
        
        # Title and description
        title_layout = QVBoxLayout()
        title = QLabel("High-Performance Computing Driver Compilation")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50;")
        
        description = QLabel("Compiling CUDA, Intel MKL, HPC libraries and drivers with hardware-specific optimizations")
        description.setStyleSheet("color: #7f8c8d; margin-bottom: 10px;")
        
        title_layout.addWidget(title)
        title_layout.addWidget(description)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Mode toggle
        mode_group = QWidget()
        mode_layout = QHBoxLayout(mode_group)
        
        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Simple", "Advanced"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.mode_combo)
        
        layout.addWidget(mode_group)
        
        return header
    
    def create_simple_tab(self) -> QWidget:
        """Create simple mode tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Overall progress
        progress_group = QGroupBox("Compilation Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                width: 10px;
                margin: 1px;
            }
        """)
        
        self.overall_status = QLabel("Ready to begin compilation...")
        self.overall_status.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        # Time estimates
        time_info = QWidget()
        time_layout = QHBoxLayout(time_info)
        
        self.elapsed_time = QLabel("Elapsed: 0:00")
        self.estimated_remaining = QLabel("Remaining: 2:30")
        self.total_estimated = QLabel("Total: 2:30")
        
        for label in [self.elapsed_time, self.estimated_remaining, self.total_estimated]:
            label.setStyleSheet("font-family: monospace; background: #ecf0f1; padding: 5px; border-radius: 3px;")
        
        time_layout.addWidget(self.elapsed_time)
        time_layout.addWidget(self.estimated_remaining)
        time_layout.addWidget(self.total_estimated)
        
        progress_layout.addWidget(self.overall_progress)
        progress_layout.addWidget(self.overall_status)
        progress_layout.addWidget(time_info)
        
        layout.addWidget(progress_group)
        
        # Current zone progress
        current_group = QGroupBox("Current Zone")
        current_layout = QVBoxLayout(current_group)
        
        self.current_zone_name = QLabel("Zone: Not started")
        self.current_zone_name.setStyleSheet("font-weight: bold; color: #2c3e50;")
        
        self.current_zone_progress = QProgressBar()
        self.current_component = QLabel("Component: Ready")
        
        current_layout.addWidget(self.current_zone_name)
        current_layout.addWidget(self.current_zone_progress)
        current_layout.addWidget(self.current_component)
        
        layout.addWidget(current_group)
        
        # Zone overview
        zones_group = QGroupBox("Compilation Zones")
        zones_layout = QVBoxLayout(zones_group)
        
        # Create scrollable zone list
        scroll_area = QScrollArea()
        self.zones_widget = QWidget()
        self.zones_layout = QVBoxLayout(self.zones_widget)
        
        scroll_area.setWidget(self.zones_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)
        
        zones_layout.addWidget(scroll_area)
        layout.addWidget(zones_group)
        
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """Create advanced mode tab"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Left side - detailed zone info
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Zone selection
        zone_group = QGroupBox("Compilation Zones")
        zone_layout = QVBoxLayout(zone_group)
        
        self.zone_list = QListWidget()
        self.zone_list.currentItemChanged.connect(self.on_zone_selected)
        
        zone_layout.addWidget(self.zone_list)
        left_layout.addWidget(zone_group)
        
        # Zone details
        details_group = QGroupBox("Zone Details")
        details_layout = QVBoxLayout(details_group)
        
        self.zone_details = QTextEdit()
        self.zone_details.setMaximumHeight(150)
        self.zone_details.setReadOnly(True)
        
        details_layout.addWidget(self.zone_details)
        left_layout.addWidget(details_group)
        
        layout.addWidget(left_panel)
        
        # Right side - controls and settings
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Compilation settings
        settings_group = QGroupBox("Compilation Settings")
        settings_layout = QFormLayout(settings_group)
        
        self.parallel_jobs_spin = QSpinBox()
        self.parallel_jobs_spin.setRange(1, 32)
        self.parallel_jobs_spin.setValue(0)  # 0 = auto
        self.parallel_jobs_spin.setSpecialValueText("Auto")
        
        self.thermal_threshold_spin = QSpinBox()
        self.thermal_threshold_spin.setRange(60, 100)
        self.thermal_threshold_spin.setValue(85)
        self.thermal_threshold_spin.setSuffix("°C")
        
        self.memory_threshold_spin = QSpinBox()
        self.memory_threshold_spin.setRange(50, 95)
        self.memory_threshold_spin.setValue(85)
        self.memory_threshold_spin.setSuffix("%")
        
        settings_layout.addRow("Parallel Jobs:", self.parallel_jobs_spin)
        settings_layout.addRow("Thermal Threshold:", self.thermal_threshold_spin)
        settings_layout.addRow("Memory Threshold:", self.memory_threshold_spin)
        
        right_layout.addWidget(settings_group)
        
        # Zone controls
        zone_controls_group = QGroupBox("Zone Controls")
        zone_controls_layout = QVBoxLayout(zone_controls_group)
        
        self.skip_zone_btn = QPushButton("Skip Current Zone")
        self.skip_zone_btn.clicked.connect(self.skip_current_zone)
        self.skip_zone_btn.setEnabled(False)
        
        self.retry_zone_btn = QPushButton("Retry Failed Zone")
        self.retry_zone_btn.clicked.connect(self.retry_current_zone)
        self.retry_zone_btn.setEnabled(False)
        
        zone_controls_layout.addWidget(self.skip_zone_btn)
        zone_controls_layout.addWidget(self.retry_zone_btn)
        
        right_layout.addWidget(zone_controls_group)
        
        right_layout.addStretch()
        
        layout.addWidget(right_panel)
        
        return widget
    
    def create_monitoring_tab(self) -> QWidget:
        """Create system monitoring tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Resource usage
        resources_group = QGroupBox("System Resources")
        resources_layout = QGridLayout(resources_group)
        
        # CPU usage
        cpu_label = QLabel("CPU Usage:")
        self.cpu_progress = QProgressBar()
        self.cpu_value = QLabel("0%")
        
        # Memory usage
        memory_label = QLabel("Memory Usage:")
        self.memory_progress = QProgressBar()
        self.memory_value = QLabel("0% of 0GB")
        
        # CPU temperature
        temp_label = QLabel("CPU Temperature:")
        self.temp_progress = QProgressBar()
        self.temp_progress.setRange(0, 100)
        self.temp_value = QLabel("0°C")
        
        # Disk usage
        disk_label = QLabel("Disk Usage:")
        self.disk_progress = QProgressBar()
        self.disk_value = QLabel("0%")
        
        # Compilation speed
        speed_label = QLabel("Compilation Speed:")
        self.speed_value = QLabel("0 components/hour")
        
        resources_layout.addWidget(cpu_label, 0, 0)
        resources_layout.addWidget(self.cpu_progress, 0, 1)
        resources_layout.addWidget(self.cpu_value, 0, 2)
        
        resources_layout.addWidget(memory_label, 1, 0)
        resources_layout.addWidget(self.memory_progress, 1, 1)
        resources_layout.addWidget(self.memory_value, 1, 2)
        
        resources_layout.addWidget(temp_label, 2, 0)
        resources_layout.addWidget(self.temp_progress, 2, 1)
        resources_layout.addWidget(self.temp_value, 2, 2)
        
        resources_layout.addWidget(disk_label, 3, 0)
        resources_layout.addWidget(self.disk_progress, 3, 1)
        resources_layout.addWidget(self.disk_value, 3, 2)
        
        resources_layout.addWidget(speed_label, 4, 0)
        resources_layout.addWidget(self.speed_value, 4, 1, 1, 2)
        
        layout.addWidget(resources_group)
        
        # Thermal protection
        thermal_group = QGroupBox("Thermal Protection")
        thermal_layout = QVBoxLayout(thermal_group)
        
        self.thermal_status = QLabel("Status: Normal")
        self.thermal_status.setStyleSheet("color: green; font-weight: bold;")
        
        self.thermal_actions = QLabel("No thermal throttling active")
        
        thermal_layout.addWidget(self.thermal_status)
        thermal_layout.addWidget(self.thermal_actions)
        
        layout.addWidget(thermal_group)
        
        # Warnings and alerts
        alerts_group = QGroupBox("Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_list = QListWidget()
        self.alerts_list.setMaximumHeight(100)
        
        alerts_layout.addWidget(self.alerts_list)
        layout.addWidget(alerts_group)
        
        return widget
    
    def create_logs_tab(self) -> QWidget:
        """Create compiler output logs tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Log controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        self.auto_scroll_check = QCheckBox("Auto-scroll")
        self.auto_scroll_check.setChecked(True)
        
        self.clear_logs_btn = QPushButton("Clear Logs")
        self.clear_logs_btn.clicked.connect(self.clear_compiler_logs)
        
        self.save_logs_btn = QPushButton("Save Logs")
        self.save_logs_btn.clicked.connect(self.save_compiler_logs)
        
        controls_layout.addWidget(self.auto_scroll_check)
        controls_layout.addStretch()
        controls_layout.addWidget(self.clear_logs_btn)
        controls_layout.addWidget(self.save_logs_btn)
        
        layout.addWidget(controls)
        
        # Log display
        self.compiler_logs = QTextEdit()
        self.compiler_logs.setReadOnly(True)
        self.compiler_logs.setFont(QFont("Consolas", 10))
        self.compiler_logs.setStyleSheet("""
            QTextEdit {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        """)
        
        layout.addWidget(self.compiler_logs)
        
        return widget
    
    def create_controls(self) -> QWidget:
        """Create control buttons"""
        controls = QWidget()
        layout = QHBoxLayout(controls)
        
        self.start_btn = QPushButton("Start Compilation")
        self.start_btn.clicked.connect(self.start_compilation)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_compilation)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        self.skip_all_btn = QPushButton("Use Prebuilt Packages")
        self.skip_all_btn.clicked.connect(self.use_prebuilt_packages)
        
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch()
        layout.addWidget(self.skip_all_btn)
        
        return controls
    
    def load_configuration(self):
        """Load module configuration"""
        try:
            # In real Calamares, this would use libcalamares.job.configuration
            self.config = {
                "enable_advanced_mode": True,
                "enable_simple_mode": True,
                "enable_thermal_monitoring": True,
                "max_parallel_jobs": 0,
                "compilation_timeout_hours": 4.0,
                "thermal_throttle_threshold": 85,
                "memory_usage_threshold_percent": 85,
                "update_interval_ms": 500,
                "show_compiler_output": False,
                "log_level": "INFO"
            }
        except Exception as e:
            libcalamares.warning(f"Could not load configuration: {e}")
    
    def setup_compilation_zones(self):
        """Setup compilation zones based on detected hardware"""
        # Mock zones for demonstration
        self.zones = [
            CompilationZone(
                name="base_system",
                size_gb=1.0,
                components=["Debian Trixie base", "ZFS kernel modules", "Boot system"],
                compile_time_estimate=10
            ),
            CompilationZone(
                name="cuda_toolkit",
                size_gb=8.0,
                components=["CUDA 11.8", "cuDNN 8.6", "NCCL 2.15", "Tesla drivers"],
                compile_time_estimate=45
            ),
            CompilationZone(
                name="intel_parallel_studio",
                size_gb=6.0,
                components=["Intel MKL", "Intel MPI", "Intel TBB", "VTune Profiler"],
                compile_time_estimate=60
            ),
            CompilationZone(
                name="hpc_libraries",
                size_gb=4.0,
                components=["OpenMPI", "FFTW", "OpenBLAS", "ScaLAPACK", "HDF5"],
                compile_time_estimate=40
            ),
            CompilationZone(
                name="scientific_python",
                size_gb=3.0,
                components=["NumPy", "SciPy", "CuPy", "Numba", "Pandas"],
                compile_time_estimate=35
            )
        ]
        
        # Update UI with zones
        self.update_zone_displays()
    
    def update_zone_displays(self):
        """Update UI with zone information"""
        # Update simple mode zones
        for i in reversed(range(self.zones_layout.count())):
            child = self.zones_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        for zone in self.zones:
            zone_widget = self.create_zone_widget(zone)
            self.zones_layout.addWidget(zone_widget)
        
        # Update advanced mode zone list
        self.zone_list.clear()
        for zone in self.zones:
            item = QListWidgetItem(f"{zone.name} ({zone.size_gb}GB)")
            item.setData(QtCore.Qt.UserRole, zone)
            
            if zone.status == "completed":
                item.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
            elif zone.status == "failed":
                item.setIcon(self.style().standardIcon(QStyle.SP_DialogCancelButton))
            elif zone.status == "compiling":
                item.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
            else:
                item.setIcon(self.style().standardIcon(QStyle.SP_DialogHelpButton))
            
            self.zone_list.addItem(item)
    
    def create_zone_widget(self, zone: CompilationZone) -> QWidget:
        """Create widget for zone display in simple mode"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Zone name and status
        name_label = QLabel(zone.name.replace('_', ' ').title())
        name_label.setMinimumWidth(150)
        
        # Progress bar
        progress = QProgressBar()
        progress.setValue(zone.progress)
        progress.setMinimumWidth(200)
        
        # Status indicator
        status_label = QLabel(zone.status.title())
        
        # Status colors
        if zone.status == "completed":
            status_label.setStyleSheet("color: green; font-weight: bold;")
        elif zone.status == "failed":
            status_label.setStyleSheet("color: red; font-weight: bold;")
        elif zone.status == "compiling":
            status_label.setStyleSheet("color: blue; font-weight: bold;")
        else:
            status_label.setStyleSheet("color: gray;")
        
        layout.addWidget(name_label)
        layout.addWidget(progress)
        layout.addWidget(status_label)
        
        return widget
    
    # Event handlers
    def on_mode_changed(self, mode: str):
        """Handle mode change between simple and advanced"""
        self.advanced_mode = (mode == "Advanced")
        
        if self.advanced_mode:
            self.tab_widget.setCurrentWidget(self.advanced_tab)
        else:
            self.tab_widget.setCurrentWidget(self.simple_tab)
    
    def on_zone_selected(self, current, previous):
        """Handle zone selection in advanced mode"""
        if current:
            zone = current.data(QtCore.Qt.UserRole)
            if zone:
                details = f"""
Zone: {zone.name}
Size: {zone.size_gb}GB
Status: {zone.status}
Estimated Time: {zone.compile_time_estimate} minutes
Components ({len(zone.components)}):
""" + "\n".join(f"  • {comp}" for comp in zone.components)
                
                if zone.error_message:
                    details += f"\n\nError: {zone.error_message}"
                
                self.zone_details.setText(details)
    
    def start_compilation(self):
        """Start the compilation process"""
        try:
            self.start_time = time.time()
            
            # Setup worker thread
            self.worker = CompilationWorker(self.zones, self.config)
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            
            # Connect signals
            self.worker.progress_update.connect(self.on_progress_update)
            self.worker.zone_started.connect(self.on_zone_started)
            self.worker.zone_completed.connect(self.on_zone_completed)
            self.worker.compilation_finished.connect(self.on_compilation_finished)
            self.worker.error_occurred.connect(self.on_error_occurred)
            self.worker.metrics_update.connect(self.on_metrics_update)
            self.worker.compiler_output.connect(self.on_compiler_output)
            
            self.worker_thread.started.connect(self.worker.start_compilation)
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.skip_zone_btn.setEnabled(True)
            
            # Start worker thread
            self.worker_thread.start()
            
            libcalamares.debug("HPC compilation started")
            
        except Exception as e:
            libcalamares.warning(f"Failed to start compilation: {e}")
    
    def toggle_pause(self):
        """Toggle pause/resume compilation"""
        if self.worker:
            if self.pause_btn.text() == "Pause":
                self.worker.pause_compilation()
                self.pause_btn.setText("Resume")
            else:
                self.worker.resume_compilation()
                self.pause_btn.setText("Pause")
    
    def stop_compilation(self):
        """Stop compilation"""
        if self.worker:
            self.worker.stop_compilation()
    
    def skip_current_zone(self):
        """Skip current compilation zone"""
        if self.worker:
            self.worker.skip_current_zone()
    
    def retry_current_zone(self):
        """Retry current zone (placeholder)"""
        # Implementation would restart current zone
        pass
    
    def use_prebuilt_packages(self):
        """Use prebuilt packages instead of compilation"""
        reply = QMessageBox.question(
            self, 
            "Use Prebuilt Packages",
            "This will skip HPC driver compilation and use prebuilt packages instead.\n\n"
            "Performance may be reduced compared to native compilation.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Signal to use prebuilt packages
            if self.worker:
                self.worker.stop_compilation()
            
            # Implementation would call prebuilt installation
            self.status_bar.showMessage("Using prebuilt packages...")
    
    def clear_compiler_logs(self):
        """Clear compiler output logs"""
        self.compiler_logs.clear()
    
    def save_compiler_logs(self):
        """Save compiler logs to file"""
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Save Compiler Logs", 
            "hpc_compilation_logs.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.compiler_logs.toPlainText())
                
                QMessageBox.information(self, "Logs Saved", f"Compiler logs saved to:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Save Failed", f"Could not save logs:\n{e}")
    
    # Signal handlers
    def on_progress_update(self, zone_name: str, percent: int, message: str):
        """Handle progress update from worker"""
        # Find and update zone
        for zone in self.zones:
            if zone.name == zone_name:
                zone.progress = percent
                break
        
        # Update UI
        self.current_zone_name.setText(f"Zone: {zone_name.replace('_', ' ').title()}")
        self.current_zone_progress.setValue(percent)
        self.current_component.setText(f"Component: {message}")
        
        # Update overall progress
        total_progress = sum(zone.progress for zone in self.zones) / len(self.zones)
        self.overall_progress.setValue(int(total_progress))
        
        # Update status
        self.overall_status.setText(f"Compiling: {message}")
        
        # Update time estimates
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.elapsed_time.setText(f"Elapsed: {elapsed/60:.0f}:{elapsed%60:02.0f}")
        
        # Update Calamares progress
        libcalamares.job.setprogress(total_progress / 100.0)
        
        # Refresh zone displays
        self.update_zone_displays()
    
    def on_zone_started(self, zone_name: str):
        """Handle zone started"""
        for zone in self.zones:
            if zone.name == zone_name:
                zone.status = "compiling"
                break
        
        self.update_zone_displays()
        self.status_bar.showMessage(f"Starting zone: {zone_name}")
    
    def on_zone_completed(self, zone_name: str, success: bool):
        """Handle zone completion"""
        for zone in self.zones:
            if zone.name == zone_name:
                zone.status = "completed" if success else "failed"
                if success:
                    zone.progress = 100
                break
        
        self.update_zone_displays()
        
        status = "completed" if success else "failed"
        self.status_bar.showMessage(f"Zone {zone_name} {status}")
    
    def on_compilation_finished(self, success: bool, message: str):
        """Handle compilation completion"""
        # Update UI
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.skip_zone_btn.setEnabled(False)
        
        # Cleanup worker thread
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
            self.worker_thread = None
            self.worker = None
        
        # Show completion message
        if success:
            self.overall_status.setText("Compilation completed successfully!")
            self.status_bar.showMessage("HPC compilation completed successfully")
            
            QMessageBox.information(
                self, 
                "Compilation Complete",
                f"HPC driver compilation completed successfully!\n\n{message}"
            )
        else:
            self.overall_status.setText("Compilation failed")
            self.status_bar.showMessage("HPC compilation failed")
            
            QMessageBox.warning(
                self, 
                "Compilation Failed",
                f"HPC driver compilation failed:\n\n{message}\n\n"
                "You can retry with different settings or use prebuilt packages."
            )
    
    def on_error_occurred(self, zone_name: str, error_message: str):
        """Handle compilation error"""
        for zone in self.zones:
            if zone.name == zone_name:
                zone.error_message = error_message
                zone.status = "failed"
                break
        
        self.update_zone_displays()
        
        # Add to alerts
        alert_item = QListWidgetItem(f"Error in {zone_name}: {error_message}")
        alert_item.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxWarning))
        self.alerts_list.addItem(alert_item)
    
    def on_metrics_update(self, metrics: Dict[str, Any]):
        """Handle system metrics update"""
        try:
            # Update CPU usage
            cpu_usage = metrics.get('cpu_usage', 0.0)
            self.cpu_progress.setValue(int(cpu_usage))
            self.cpu_value.setText(f"{cpu_usage:.1f}%")
            
            # Update memory usage
            memory_usage = metrics.get('memory_usage', 0.0)
            memory_total = metrics.get('memory_total_gb', 0.0)
            self.memory_progress.setValue(int(memory_usage))
            self.memory_value.setText(f"{memory_usage:.1f}% of {memory_total:.1f}GB")
            
            # Update CPU temperature
            cpu_temp = metrics.get('cpu_temperature', 0.0)
            self.temp_progress.setValue(int(cpu_temp))
            self.temp_value.setText(f"{cpu_temp:.1f}°C")
            
            # Temperature warnings
            threshold = self.config.get('thermal_throttle_threshold', 85)
            if cpu_temp > threshold:
                self.thermal_status.setText("Status: THERMAL WARNING")
                self.thermal_status.setStyleSheet("color: red; font-weight: bold;")
                self.thermal_actions.setText(f"Temperature {cpu_temp:.1f}°C exceeds {threshold}°C threshold")
            else:
                self.thermal_status.setText("Status: Normal")
                self.thermal_status.setStyleSheet("color: green; font-weight: bold;")
                self.thermal_actions.setText("No thermal throttling active")
            
            # Update disk usage
            disk_usage = metrics.get('disk_usage', 0.0)
            self.disk_progress.setValue(int(disk_usage))
            self.disk_value.setText(f"{disk_usage:.1f}%")
            
            # Update compilation speed
            speed = metrics.get('compilation_speed', 0.0)
            self.speed_value.setText(f"{speed:.1f} components/hour")
            
        except Exception as e:
            libcalamares.warning(f"Error updating metrics: {e}")
    
    def on_compiler_output(self, output: str):
        """Handle compiler output"""
        try:
            # Add timestamp
            timestamp = time.strftime("%H:%M:%S")
            formatted_output = f"[{timestamp}] {output}"
            
            # Append to logs
            self.compiler_logs.append(formatted_output)
            
            # Auto-scroll if enabled
            if self.auto_scroll_check.isChecked():
                scrollbar = self.compiler_logs.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
        except Exception as e:
            libcalamares.warning(f"Error handling compiler output: {e}")


class HPCCompilationViewStep:
    """Main view step class for Calamares"""
    
    def __init__(self):
        self.widget = None
    
    def createWidget(self):
        """Create and return the main widget"""
        self.widget = HPCCompilationWidget()
        return self.widget
    
    def isNextEnabled(self):
        """Check if next button should be enabled"""
        if self.widget:
            # Enable next if compilation is finished or skipped
            return True  # Allow proceeding
        return False
    
    def isBackEnabled(self):
        """Check if back button should be enabled"""
        return False  # Don't allow going back during compilation
    
    def onActivate(self):
        """Called when the page becomes active"""
        libcalamares.debug("HPC Compilation UI module activated")
        return None
    
    def onLeave(self):
        """Called when leaving the page"""
        libcalamares.debug("HPC Compilation UI module deactivated")
        return None


def run():
    """Main entry point for Calamares module"""
    return HPCCompilationViewStep()