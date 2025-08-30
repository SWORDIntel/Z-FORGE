#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Compilation TUI (Text User Interface) for Z-FORGE
Fallback interface for text-mode installations or GUI failures
"""

import sys
import os
import time
import json
import threading
import subprocess
import signal
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import curses
    import curses.textpad
except ImportError:
    print("ERROR: curses library not available. Install with: apt-get install python3-dev")
    sys.exit(1)

@dataclass
class CompilationZone:
    """Compilation zone for TUI display"""
    name: str
    size_gb: float
    components: List[str]
    compile_time_estimate: int
    status: str = "pending"
    progress: int = 0
    current_component: str = ""
    error_message: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None

@dataclass
class SystemMetrics:
    """System resource metrics for TUI display"""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_total_gb: float = 0.0
    cpu_temperature: float = 0.0
    disk_usage: float = 0.0
    compilation_speed: float = 0.0

class HPCCompilationTUI:
    """
    Text-based UI for HPC compilation process
    
    Features:
    - Real-time compilation progress
    - System resource monitoring
    - Thermal protection warnings
    - User interaction (pause/resume/skip)
    - Compiler output viewing
    - Error handling and retry options
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.zones = []
        self.current_zone_index = 0
        self.compilation_active = False
        self.is_paused = False
        self.start_time = None
        self.metrics = SystemMetrics()
        self.compiler_output = []
        self.alerts = []
        
        # TUI state
        self.stdscr = None
        self.height = 0
        self.width = 0
        self.current_screen = "main"  # main, details, logs, help
        self.selected_zone = 0
        self.log_scroll_pos = 0
        self.update_interval = 0.5  # 500ms
        
        # Threading
        self.compilation_thread = None
        self.metrics_thread = None
        self.ui_lock = threading.Lock()
        self.should_exit = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler('/tmp/hpc_compilation_tui.log')]
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Setup compilation zones
        self.setup_compilation_zones()
        
        # Signal handling
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.should_exit = True
        if self.compilation_thread and self.compilation_thread.is_alive():
            self.logger.info("Stopping compilation due to signal")
    
    def setup_compilation_zones(self):
        """Setup compilation zones based on hardware detection"""
        # Mock zones for demonstration - in real implementation, 
        # this would interface with HPC hardware detector
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
                components=["CUDA 11.8", "cuDNN 8.6", "NCCL 2.15", "Tesla K40 drivers"],
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
            ),
            CompilationZone(
                name="monitoring_tools",
                size_gb=2.0,
                components=["Ganglia", "Nagios", "Intel VTune", "NVIDIA Nsight"],
                compile_time_estimate=20
            )
        ]
    
    def run(self):
        """Main TUI application loop"""
        try:
            # Initialize curses
            self.stdscr = curses.initscr()
            self.init_curses()
            
            # Start metrics monitoring thread
            self.metrics_thread = threading.Thread(target=self.metrics_monitor_loop)
            self.metrics_thread.daemon = True
            self.metrics_thread.start()
            
            # Main UI loop
            self.main_loop()
            
        except KeyboardInterrupt:
            self.should_exit = True
        except Exception as e:
            self.logger.error(f"TUI error: {e}")
        finally:
            self.cleanup()
    
    def init_curses(self):
        """Initialize curses settings"""
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(100)  # 100ms timeout for getch()
        
        # Initialize colors
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)    # Success/OK
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)      # Error/Warning
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)   # Warning/Active
            curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)     # Info/Selected
            curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)     # Headers
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)    # Normal text
            curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # Progress
        
        self.height, self.width = self.stdscr.getmaxyx()
    
    def main_loop(self):
        """Main UI event loop"""
        while not self.should_exit:
            try:
                with self.ui_lock:
                    self.draw_screen()
                
                # Handle input
                key = self.stdscr.getch()
                if key != -1:  # Key pressed
                    self.handle_input(key)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                break
    
    def draw_screen(self):
        """Draw the current screen"""
        self.stdscr.clear()
        
        if self.current_screen == "main":
            self.draw_main_screen()
        elif self.current_screen == "details":
            self.draw_details_screen()
        elif self.current_screen == "logs":
            self.draw_logs_screen()
        elif self.current_screen == "help":
            self.draw_help_screen()
        
        self.stdscr.refresh()
    
    def draw_main_screen(self):
        """Draw main compilation overview screen"""
        # Title
        title = "Z-FORGE HPC Driver Compilation (Text Mode)"
        self.draw_centered_text(0, title, curses.color_pair(5) | curses.A_BOLD)
        
        # Subtitle
        subtitle = f"Compiling CUDA, Intel MKL, HPC libraries with native optimizations"
        self.draw_centered_text(1, subtitle, curses.color_pair(6))
        
        # Separator
        self.stdscr.hline(2, 0, '-', self.width)
        
        # Overall progress
        self.draw_overall_progress(4)
        
        # Zone list
        self.draw_zone_list(8)
        
        # System metrics
        self.draw_system_metrics(self.height - 12)
        
        # Status line
        status_line = self.get_status_line()
        self.stdscr.addstr(self.height - 3, 0, status_line[:self.width-1], curses.color_pair(6))
        
        # Controls help
        controls = "[S]tart [P]ause [Q]uit [D]etails [L]ogs [H]elp [↑↓] Select zone"
        self.stdscr.addstr(self.height - 1, 0, controls[:self.width-1], curses.color_pair(4))
    
    def draw_overall_progress(self, start_row: int):
        """Draw overall compilation progress"""
        # Progress calculation
        total_zones = len(self.zones)
        completed_zones = len([z for z in self.zones if z.status == "completed"])
        failed_zones = len([z for z in self.zones if z.status == "failed"])
        
        overall_progress = sum(zone.progress for zone in self.zones) / total_zones if total_zones > 0 else 0
        
        # Time calculations
        if self.start_time:
            elapsed = time.time() - self.start_time
            elapsed_str = f"{elapsed//3600:02.0f}:{(elapsed%3600)//60:02.0f}:{elapsed%60:02.0f}"
            
            # Estimate remaining time
            if overall_progress > 5:  # Only estimate after 5% completion
                estimated_total = elapsed / (overall_progress / 100)
                remaining = estimated_total - elapsed
                remaining_str = f"{remaining//3600:02.0f}:{(remaining%3600)//60:02.0f}:{remaining%60:02.0f}"
            else:
                remaining_str = "Calculating..."
        else:
            elapsed_str = "00:00:00"
            remaining_str = "02:30:00"  # Default estimate
        
        # Overall status
        if failed_zones > 0:
            status_text = f"Overall Status: {completed_zones} completed, {failed_zones} failed"
            status_color = curses.color_pair(2)
        elif self.compilation_active:
            status_text = f"Overall Status: Compiling ({completed_zones}/{total_zones} zones)"
            status_color = curses.color_pair(3)
        elif completed_zones == total_zones:
            status_text = f"Overall Status: All zones completed successfully!"
            status_color = curses.color_pair(1)
        else:
            status_text = f"Overall Status: Ready to begin ({total_zones} zones)"
            status_color = curses.color_pair(6)
        
        self.stdscr.addstr(start_row, 0, status_text, status_color)
        
        # Progress bar
        progress_width = min(60, self.width - 20)
        progress_text = f"Progress: [{self.draw_progress_bar(int(overall_progress), progress_width)}] {overall_progress:5.1f}%"
        self.stdscr.addstr(start_row + 1, 0, progress_text, curses.color_pair(6))
        
        # Time information
        time_text = f"Elapsed: {elapsed_str}  Remaining: {remaining_str}"
        self.stdscr.addstr(start_row + 2, 0, time_text, curses.color_pair(6))
    
    def draw_zone_list(self, start_row: int):
        """Draw compilation zones list"""
        self.stdscr.addstr(start_row, 0, "Compilation Zones:", curses.color_pair(5) | curses.A_BOLD)
        
        header = f"{'Zone':<20} {'Size':<8} {'Status':<12} {'Progress':<20} {'Component':<25}"
        self.stdscr.addstr(start_row + 1, 0, header[:self.width-1], curses.color_pair(4))
        
        # Separator
        self.stdscr.hline(start_row + 2, 0, '-', min(len(header), self.width))
        
        for i, zone in enumerate(self.zones):
            row = start_row + 3 + i
            if row >= self.height - 8:  # Leave space for metrics and controls
                break
            
            # Zone name
            zone_name = zone.name.replace('_', ' ').title()[:19]
            
            # Size
            size_str = f"{zone.size_gb:.1f}GB"
            
            # Status with color
            status_color = curses.color_pair(6)
            if zone.status == "completed":
                status_color = curses.color_pair(1)
            elif zone.status == "failed":
                status_color = curses.color_pair(2)
            elif zone.status == "compiling":
                status_color = curses.color_pair(3)
            
            # Progress bar
            progress_bar = self.draw_progress_bar(zone.progress, 15)
            progress_str = f"[{progress_bar}] {zone.progress:3d}%"
            
            # Current component
            component = zone.current_component[:24] if zone.current_component else ""
            
            # Selection indicator
            selection_marker = ">" if i == self.selected_zone else " "
            
            line = f"{selection_marker}{zone_name:<20} {size_str:<8} {zone.status:<12} {progress_str:<20} {component:<25}"
            
            # Highlight selected zone
            if i == self.selected_zone:
                attrs = curses.color_pair(4) | curses.A_REVERSE
            else:
                attrs = curses.color_pair(6)
            
            self.stdscr.addstr(row, 0, line[:self.width-1], attrs)
            
            # Add status color for status column
            self.stdscr.addstr(row, 30, zone.status, status_color)
    
    def draw_system_metrics(self, start_row: int):
        """Draw system resource metrics"""
        if start_row >= self.height - 6:
            return
        
        self.stdscr.addstr(start_row, 0, "System Resources:", curses.color_pair(5) | curses.A_BOLD)
        
        # CPU usage
        cpu_bar = self.draw_progress_bar(int(self.metrics.cpu_usage), 20)
        cpu_text = f"CPU:  [{cpu_bar}] {self.metrics.cpu_usage:5.1f}%"
        self.stdscr.addstr(start_row + 1, 0, cpu_text, curses.color_pair(6))
        
        # Memory usage
        mem_bar = self.draw_progress_bar(int(self.metrics.memory_usage), 20)
        mem_text = f"RAM:  [{mem_bar}] {self.metrics.memory_usage:5.1f}% of {self.metrics.memory_total_gb:.1f}GB"
        self.stdscr.addstr(start_row + 2, 0, mem_text, curses.color_pair(6))
        
        # CPU temperature
        temp_color = curses.color_pair(6)
        if self.metrics.cpu_temperature > 85:
            temp_color = curses.color_pair(2) | curses.A_BOLD
        elif self.metrics.cpu_temperature > 75:
            temp_color = curses.color_pair(3)
        
        temp_text = f"Temp: {self.metrics.cpu_temperature:5.1f}°C"
        self.stdscr.addstr(start_row + 3, 0, temp_text, temp_color)
        
        # Compilation speed
        speed_text = f"Speed: {self.metrics.compilation_speed:.1f} components/hour"
        self.stdscr.addstr(start_row + 3, 25, speed_text, curses.color_pair(6))
        
        # Thermal warnings
        if self.metrics.cpu_temperature > 85:
            warning_text = "WARNING: HIGH CPU TEMPERATURE! Compilation may be throttled."
            self.stdscr.addstr(start_row + 4, 0, warning_text[:self.width-1], 
                             curses.color_pair(2) | curses.A_BLINK)
    
    def draw_details_screen(self):
        """Draw zone details screen"""
        if not self.zones or self.selected_zone >= len(self.zones):
            return
        
        zone = self.zones[self.selected_zone]
        
        # Title
        title = f"Zone Details: {zone.name.replace('_', ' ').title()}"
        self.draw_centered_text(0, title, curses.color_pair(5) | curses.A_BOLD)
        
        # Separator
        self.stdscr.hline(1, 0, '-', self.width)
        
        row = 3
        
        # Basic info
        info_lines = [
            f"Zone Name: {zone.name}",
            f"Size: {zone.size_gb}GB",
            f"Status: {zone.status}",
            f"Progress: {zone.progress}%",
            f"Estimated Time: {zone.compile_time_estimate} minutes",
            f"Components: {len(zone.components)}",
        ]
        
        if zone.current_component:
            info_lines.append(f"Current Component: {zone.current_component}")
        
        if zone.start_time:
            elapsed = time.time() - zone.start_time
            info_lines.append(f"Zone Elapsed Time: {elapsed/60:.1f} minutes")
        
        if zone.error_message:
            info_lines.append(f"Error: {zone.error_message}")
        
        for line in info_lines:
            if row >= self.height - 3:
                break
            self.stdscr.addstr(row, 0, line[:self.width-1], curses.color_pair(6))
            row += 1
        
        row += 1
        
        # Components list
        self.stdscr.addstr(row, 0, "Components:", curses.color_pair(5) | curses.A_BOLD)
        row += 1
        
        for i, component in enumerate(zone.components):
            if row >= self.height - 3:
                break
                
            # Component status
            if zone.status == "completed" or (zone.status == "compiling" and component == zone.current_component):
                status = "✓" if zone.status == "completed" else "→"
                color = curses.color_pair(1) if zone.status == "completed" else curses.color_pair(3)
            else:
                status = "○"
                color = curses.color_pair(6)
            
            component_line = f"  {status} {component}"
            self.stdscr.addstr(row, 0, component_line[:self.width-1], color)
            row += 1
        
        # Controls
        controls = "[B]ack to main screen [↑↓] Select zone [S]kip zone [R]etry zone"
        self.stdscr.addstr(self.height - 1, 0, controls[:self.width-1], curses.color_pair(4))
    
    def draw_logs_screen(self):
        """Draw compiler logs screen"""
        # Title
        title = "Compiler Output Logs"
        self.draw_centered_text(0, title, curses.color_pair(5) | curses.A_BOLD)
        
        # Separator
        self.stdscr.hline(1, 0, '-', self.width)
        
        # Log display area
        log_area_height = self.height - 4
        log_start_row = 2
        
        # Display logs with scrolling
        visible_logs = self.compiler_output[self.log_scroll_pos:self.log_scroll_pos + log_area_height]
        
        for i, log_line in enumerate(visible_logs):
            row = log_start_row + i
            if row >= self.height - 2:
                break
            
            # Color coding for different types of output
            color = curses.color_pair(6)
            if "ERROR" in log_line or "FAILED" in log_line:
                color = curses.color_pair(2)
            elif "WARNING" in log_line:
                color = curses.color_pair(3)
            elif "SUCCESS" in log_line or "COMPLETED" in log_line:
                color = curses.color_pair(1)
            
            self.stdscr.addstr(row, 0, log_line[:self.width-1], color)
        
        # Scroll indicator
        if len(self.compiler_output) > log_area_height:
            scroll_info = f"[{self.log_scroll_pos + 1}-{min(self.log_scroll_pos + log_area_height, len(self.compiler_output))} of {len(self.compiler_output)}]"
            self.stdscr.addstr(self.height - 2, self.width - len(scroll_info) - 1, scroll_info, curses.color_pair(4))
        
        # Controls
        controls = "[B]ack [↑↓] Scroll [PageUp/PageDown] Fast scroll [C]lear logs"
        self.stdscr.addstr(self.height - 1, 0, controls[:self.width-1], curses.color_pair(4))
    
    def draw_help_screen(self):
        """Draw help screen"""
        # Title
        title = "HPC Compilation TUI - Help"
        self.draw_centered_text(0, title, curses.color_pair(5) | curses.A_BOLD)
        
        # Separator
        self.stdscr.hline(1, 0, '-', self.width)
        
        help_text = [
            "KEYBOARD CONTROLS:",
            "",
            "Main Screen:",
            "  S - Start compilation",
            "  P - Pause/Resume compilation", 
            "  Q - Quit (with confirmation)",
            "  D - View zone details",
            "  L - View compiler logs",
            "  H - This help screen",
            "  ↑↓ - Select compilation zone",
            "",
            "Details Screen:",
            "  B - Back to main screen",
            "  S - Skip current zone",
            "  R - Retry failed zone",
            "",
            "Logs Screen:",
            "  B - Back to main screen",
            "  ↑↓ - Scroll up/down",
            "  PageUp/PageDown - Fast scroll",
            "  C - Clear logs",
            "",
            "COMPILATION ZONES:",
            "- base_system: Core ZFS and boot system",
            "- cuda_toolkit: NVIDIA CUDA for Tesla GPUs",
            "- intel_parallel_studio: Intel HPC tools",
            "- hpc_libraries: Scientific computing libraries",
            "- scientific_python: Python stack with CUDA",
            "- monitoring_tools: System monitoring",
            "",
            "Press any key to return..."
        ]
        
        row = 3
        for line in help_text:
            if row >= self.height - 1:
                break
            
            if line.endswith(":") and line != "":
                color = curses.color_pair(5) | curses.A_BOLD
            elif line.startswith("  "):
                color = curses.color_pair(6)
            else:
                color = curses.color_pair(4) if line.startswith("-") else curses.color_pair(6)
            
            self.stdscr.addstr(row, 0, line[:self.width-1], color)
            row += 1
    
    def handle_input(self, key: int):
        """Handle keyboard input"""
        try:
            if self.current_screen == "main":
                self.handle_main_input(key)
            elif self.current_screen == "details":
                self.handle_details_input(key)
            elif self.current_screen == "logs":
                self.handle_logs_input(key)
            elif self.current_screen == "help":
                self.current_screen = "main"  # Any key returns from help
                
        except Exception as e:
            self.logger.error(f"Input handling error: {e}")
    
    def handle_main_input(self, key: int):
        """Handle input on main screen"""
        if key == ord('q') or key == ord('Q'):
            if self.compilation_active:
                # Confirm quit during compilation
                self.show_confirmation("Quit during compilation?")
            else:
                self.should_exit = True
                
        elif key == ord('s') or key == ord('S'):
            if not self.compilation_active:
                self.start_compilation()
            else:
                # Stop compilation
                self.stop_compilation()
                
        elif key == ord('p') or key == ord('P'):
            if self.compilation_active:
                self.toggle_pause()
                
        elif key == ord('d') or key == ord('D'):
            self.current_screen = "details"
            
        elif key == ord('l') or key == ord('L'):
            self.current_screen = "logs"
            
        elif key == ord('h') or key == ord('H'):
            self.current_screen = "help"
            
        elif key == curses.KEY_UP and self.selected_zone > 0:
            self.selected_zone -= 1
            
        elif key == curses.KEY_DOWN and self.selected_zone < len(self.zones) - 1:
            self.selected_zone += 1
    
    def handle_details_input(self, key: int):
        """Handle input on details screen"""
        if key == ord('b') or key == ord('B'):
            self.current_screen = "main"
            
        elif key == ord('s') or key == ord('S'):
            self.skip_current_zone()
            
        elif key == ord('r') or key == ord('R'):
            self.retry_current_zone()
            
        elif key == curses.KEY_UP and self.selected_zone > 0:
            self.selected_zone -= 1
            
        elif key == curses.KEY_DOWN and self.selected_zone < len(self.zones) - 1:
            self.selected_zone += 1
    
    def handle_logs_input(self, key: int):
        """Handle input on logs screen"""
        if key == ord('b') or key == ord('B'):
            self.current_screen = "main"
            
        elif key == ord('c') or key == ord('C'):
            self.compiler_output.clear()
            self.log_scroll_pos = 0
            
        elif key == curses.KEY_UP and self.log_scroll_pos > 0:
            self.log_scroll_pos -= 1
            
        elif key == curses.KEY_DOWN and self.log_scroll_pos < len(self.compiler_output) - (self.height - 4):
            self.log_scroll_pos += 1
            
        elif key == curses.KEY_PPAGE:  # Page Up
            self.log_scroll_pos = max(0, self.log_scroll_pos - (self.height - 4))
            
        elif key == curses.KEY_NPAGE:  # Page Down
            max_pos = max(0, len(self.compiler_output) - (self.height - 4))
            self.log_scroll_pos = min(max_pos, self.log_scroll_pos + (self.height - 4))
    
    def start_compilation(self):
        """Start the HPC compilation process"""
        if self.compilation_active:
            return
        
        self.compilation_active = True
        self.start_time = time.time()
        
        # Reset zone states
        for zone in self.zones:
            zone.status = "pending"
            zone.progress = 0
            zone.current_component = ""
            zone.error_message = ""
            zone.start_time = None
            zone.end_time = None
        
        # Start compilation thread
        self.compilation_thread = threading.Thread(target=self.compilation_worker)
        self.compilation_thread.daemon = True
        self.compilation_thread.start()
        
        self.add_log("HPC compilation started")
        self.logger.info("HPC compilation started")
    
    def stop_compilation(self):
        """Stop the compilation process"""
        self.compilation_active = False
        self.add_log("HPC compilation stopped by user")
        self.logger.info("HPC compilation stopped by user")
    
    def toggle_pause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        
        if self.is_paused:
            self.add_log("Compilation paused by user")
        else:
            self.add_log("Compilation resumed by user")
    
    def skip_current_zone(self):
        """Skip the current compilation zone"""
        if self.compilation_active and self.current_zone_index < len(self.zones):
            zone = self.zones[self.current_zone_index]
            zone.status = "skipped"
            self.add_log(f"Zone {zone.name} skipped by user")
    
    def retry_current_zone(self):
        """Retry the current zone (placeholder)"""
        if self.selected_zone < len(self.zones):
            zone = self.zones[self.selected_zone]
            if zone.status == "failed":
                zone.status = "pending"
                zone.progress = 0
                zone.error_message = ""
                self.add_log(f"Zone {zone.name} marked for retry")
    
    def compilation_worker(self):
        """Worker thread for compilation process"""
        try:
            for i, zone in enumerate(self.zones):
                if not self.compilation_active:
                    break
                
                self.current_zone_index = i
                
                # Wait if paused
                while self.is_paused and self.compilation_active:
                    time.sleep(0.1)
                
                if not self.compilation_active:
                    break
                
                # Start zone compilation
                zone.status = "compiling"
                zone.start_time = time.time()
                zone.progress = 0
                
                self.add_log(f"Starting zone: {zone.name}")
                
                # Compile each component
                for j, component in enumerate(zone.components):
                    if not self.compilation_active:
                        break
                    
                    # Wait if paused
                    while self.is_paused and self.compilation_active:
                        time.sleep(0.1)
                    
                    if not self.compilation_active:
                        break
                    
                    zone.current_component = component
                    
                    self.add_log(f"  Compiling: {component}")
                    
                    # Mock compilation (replace with real build calls)
                    success = self.mock_component_compilation(component, zone)
                    
                    if not success:
                        zone.status = "failed"
                        zone.error_message = f"Failed to compile {component}"
                        self.add_log(f"ERROR: Failed to compile {component}")
                        
                        # For critical zones, stop compilation
                        if zone.name in ["base_system", "cuda_toolkit"]:
                            self.compilation_active = False
                            self.add_log(f"CRITICAL: Zone {zone.name} failed - stopping compilation")
                            return
                        else:
                            break  # Skip to next zone
                    
                    # Update progress
                    zone.progress = int(((j + 1) / len(zone.components)) * 100)
                
                # Zone completion
                if zone.status != "failed":
                    zone.status = "completed"
                    zone.progress = 100
                    zone.end_time = time.time()
                    elapsed = zone.end_time - zone.start_time
                    self.add_log(f"Completed zone: {zone.name} ({elapsed/60:.1f} minutes)")
            
            # Overall completion
            if self.compilation_active:
                completed_zones = len([z for z in self.zones if z.status == "completed"])
                total_time = time.time() - self.start_time
                
                self.add_log(f"Compilation finished: {completed_zones}/{len(self.zones)} zones completed ({total_time/3600:.1f} hours)")
                
            self.compilation_active = False
            
        except Exception as e:
            self.logger.error(f"Compilation worker error: {e}")
            self.add_log(f"ERROR: Compilation failed - {e}")
            self.compilation_active = False
    
    def mock_component_compilation(self, component: str, zone: CompilationZone) -> bool:
        """Mock component compilation (replace with real build calls)"""
        try:
            # Simulate compilation time
            import random
            compile_time = random.uniform(1.0, 5.0)  # 1-5 seconds for demo
            
            # Simulate compilation steps with progress updates
            steps = 10
            for step in range(steps):
                if not self.compilation_active:
                    return False
                
                # Wait if paused
                while self.is_paused and self.compilation_active:
                    time.sleep(0.1)
                
                time.sleep(compile_time / steps)
                
                # Add periodic compiler output
                if step % 3 == 0:
                    self.add_log(f"    [{component}] Build step {step+1}/{steps}")
            
            # Random success/failure for testing (90% success rate)
            return random.random() > 0.1
            
        except Exception as e:
            self.logger.error(f"Mock compilation error: {e}")
            return False
    
    def metrics_monitor_loop(self):
        """Background thread for system metrics monitoring"""
        while not self.should_exit:
            try:
                self.update_system_metrics()
                time.sleep(1.0)  # Update every second
            except Exception as e:
                self.logger.error(f"Metrics monitoring error: {e}")
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        try:
            # CPU usage
            with open('/proc/loadavg', 'r') as f:
                load = float(f.read().split()[0])
                self.metrics.cpu_usage = min(load * 25, 100)
            
            # Memory usage
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            mem_total = int([line for line in meminfo.split('\n') 
                           if line.startswith('MemTotal:')][0].split()[1])
            mem_available = int([line for line in meminfo.split('\n') 
                               if line.startswith('MemAvailable:')][0].split()[1])
            
            self.metrics.memory_total_gb = mem_total / (1024 * 1024)
            self.metrics.memory_usage = ((mem_total - mem_available) / mem_total) * 100
            
            # CPU temperature (if available)
            temp_files = [
                '/sys/class/thermal/thermal_zone0/temp',
                '/sys/devices/platform/coretemp.0/hwmon/hwmon*/temp1_input'
            ]
            
            for temp_file in temp_files:
                try:
                    with open(temp_file, 'r') as f:
                        self.metrics.cpu_temperature = float(f.read().strip()) / 1000.0
                    break
                except:
                    continue
            
            # Disk usage
            import shutil
            workspace_stat = shutil.disk_usage('/tmp')
            self.metrics.disk_usage = ((workspace_stat.total - workspace_stat.free) / workspace_stat.total) * 100
            
            # Compilation speed
            if self.start_time:
                elapsed_hours = (time.time() - self.start_time) / 3600
                completed_components = sum(1 for zone in self.zones 
                                         for _ in zone.components 
                                         if zone.status == "completed")
                self.metrics.compilation_speed = completed_components / elapsed_hours if elapsed_hours > 0 else 0
            
            # Thermal alerts
            if self.metrics.cpu_temperature > 85 and "thermal_warning" not in self.alerts:
                self.alerts.append("thermal_warning")
                self.add_log(f"WARNING: CPU temperature {self.metrics.cpu_temperature:.1f}°C exceeds 85°C threshold")
            
        except Exception as e:
            self.logger.warning(f"Could not update metrics: {e}")
    
    def add_log(self, message: str):
        """Add message to compiler output logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        with self.ui_lock:
            self.compiler_output.append(log_entry)
            
            # Keep only last 1000 log entries
            if len(self.compiler_output) > 1000:
                self.compiler_output = self.compiler_output[-1000:]
    
    def draw_progress_bar(self, percent: int, width: int) -> str:
        """Draw a text progress bar"""
        filled = int((percent / 100) * width)
        bar = '█' * filled + '░' * (width - filled)
        return bar
    
    def draw_centered_text(self, row: int, text: str, attrs: int = 0):
        """Draw centered text"""
        col = max(0, (self.width - len(text)) // 2)
        self.stdscr.addstr(row, col, text[:self.width-1], attrs)
    
    def get_status_line(self) -> str:
        """Get current status line"""
        if self.compilation_active:
            if self.is_paused:
                return f"Status: PAUSED - Zone {self.current_zone_index + 1}/{len(self.zones)}"
            else:
                zone = self.zones[self.current_zone_index] if self.current_zone_index < len(self.zones) else None
                if zone:
                    return f"Status: Compiling {zone.name} - {zone.current_component}"
                else:
                    return "Status: Finishing compilation..."
        else:
            completed = len([z for z in self.zones if z.status == "completed"])
            failed = len([z for z in self.zones if z.status == "failed"])
            
            if completed + failed == 0:
                return "Status: Ready - Press 'S' to start compilation"
            elif failed > 0:
                return f"Status: Completed with {failed} failures - Press 'S' to restart"
            elif completed == len(self.zones):
                return "Status: All zones completed successfully!"
            else:
                return f"Status: Stopped - {completed}/{len(self.zones)} zones completed"
    
    def show_confirmation(self, message: str) -> bool:
        """Show confirmation dialog (placeholder)"""
        # In a real implementation, this would show a proper dialog
        # For now, just return True to allow quit
        return True
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            self.should_exit = True
            
            if self.compilation_thread and self.compilation_thread.is_alive():
                self.compilation_thread.join(timeout=2.0)
            
            if self.metrics_thread and self.metrics_thread.is_alive():
                self.metrics_thread.join(timeout=1.0)
            
            if self.stdscr:
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
                
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")


def main():
    """Main entry point for TUI application"""
    try:
        # Configuration (normally loaded from Calamares)
        config = {
            "enable_thermal_monitoring": True,
            "max_parallel_jobs": 0,
            "compilation_timeout_hours": 4.0,
            "thermal_throttle_threshold": 85,
            "memory_usage_threshold_percent": 85
        }
        
        # Create and run TUI
        tui = HPCCompilationTUI(config)
        tui.run()
        
    except Exception as e:
        print(f"TUI Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())