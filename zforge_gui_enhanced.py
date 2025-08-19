#!/usr/bin/env python3
"""
Z-FORGE GUI Builder - Enhanced Edition
With automatic failure recovery and intelligent analysis
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import os
import sys
import yaml
import json
import re
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psutil
import queue
import time
import shutil
try:
    import docker
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None

# Add project modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'builder'))
sys.path.insert(0, str(Path(__file__).parent / 'tools'))

# Import our diagnostic and recovery tools from tools directory
from build_diagnostic_tool import BuildDiagnosticTool
from build_recovery_tool import BuildRecoveryTool

class ZForgeGUIEnhanced:
    def __init__(self, root):
        self.root = root
        self.root.title("Z-FORGE RAM Server Build System v3.0 - Enhanced Edition")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # Apply dark theme
        self.setup_dark_theme()
        
        # Build specifications mapping - ALL BUILDS NOW USE RAM WORKSPACES AND FULL PROXMOX VE 9
        self.build_specs = {
            "Outside Packages Build (Fastest - 95% Success)": {
                "file": "build_specs/build_spec_outside_packages.yml", 
                "description": "RAM-based server build with prebuilt packages. Full Proxmox VE 9 + ZFS 2.3.3 on Debian Trixie.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "ZFS 2.3.3 + encryption", "Debian Trixie base"],
                "success_rate": 95
            },
            "Minimal Proxmox Build (90% Success)": {
                "file": "build_specs/build_spec_minimal_proxmox.yml",
                "description": "RAM-based server build with minimal Proxmox components. Fastest full server deployment.",
                "features": ["RAM workspace (/dev/shm)", "Minimal Proxmox VE 9", "ZFS 2.3.3 + compression", "Optimized performance"],
                "success_rate": 90
            },
            "TMPFS High Performance Build (85% Success)": {
                "file": "build_specs/build_spec_tmpfs.yml",
                "description": "Full RAM-based server build for maximum performance. Complete Proxmox VE 9 infrastructure.",
                "features": ["Full RAM filesystem", "Complete Proxmox VE 9", "3-5x build speed", "Enterprise features"],
                "success_rate": 85,
                "ram_required": "16GB"
            },
            "Working Server Build (85% Success)": {
                "file": "build_specs/build_spec_working.yml",
                "description": "Proven RAM-based server configuration. Full Proxmox VE 9 with all ZFS features.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "ZFS encryption + compression", "Hardware optimization"],
                "success_rate": 85
            },
            "No /tmp Server Build (80% Success)": {
                "file": "build_specs/build_spec_no_tmp.yml",
                "description": "RAM-based server avoiding /tmp usage. Full Proxmox VE 9 with workspace isolation.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "Workspace isolation", "Permission handling"],
                "success_rate": 80
            },
            "Proxmox 9 Server Build (75% Success)": {
                "file": "build_specs/build_spec_proxmox9.yml", 
                "description": "RAM-based specialized Proxmox VE 9 server build. Enterprise clustering and networking.",
                "features": ["RAM workspace (/dev/shm)", "Proxmox VE 9.0 server", "Enterprise clustering", "Advanced networking"],
                "success_rate": 75
            },
            "Proxmox Full Server Build (75% Success)": {
                "file": "build_specs/build_spec_proxmox_full.yml",
                "description": "RAM-based complete Proxmox integration. Full enterprise server with all features.",
                "features": ["RAM workspace (/dev/shm)", "Complete Proxmox suite", "High availability server", "Management interfaces"],
                "success_rate": 75
            },
            "Full Featured Server Build (70% Success)": {
                "file": "build_specs/build_spec.yml",
                "description": "RAM-based complete server distribution. Full Proxmox VE 9 with all enterprise features.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "Complete ZFS suite", "All bootloaders"],
                "success_rate": 70
            },
            "Trixie Clean Server Build (60% Success)": {
                "file": "build_specs/build_spec_trixie_clean.yml",
                "description": "RAM-based clean Debian Trixie server. Latest packages with full Proxmox VE 9 integration.",
                "features": ["RAM workspace (/dev/shm)", "Debian Trixie server", "Latest kernel 6.14.8", "Full Proxmox VE 9"],
                "success_rate": 60
            }
        }
        
        # System info
        self.cpu_count = multiprocessing.cpu_count()
        self.memory_gb = round(psutil.virtual_memory().total / (1024**3))
        self.disk_free_gb = round(psutil.disk_usage('/').free / (1024**3))
        
        # Build process
        self.build_process = None
        self.build_running = False
        self.build_paused = False
        self.auto_recovery_enabled = True
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
        # Error tracking
        self.errors_detected = []
        self.warnings_detected = []
        self.recovery_history = []
        
        # Diagnostic and recovery tools
        self.diagnostic_tool = BuildDiagnosticTool()
        self.recovery_tool = BuildRecoveryTool()
        
        # Message queue for thread-safe GUI updates
        self.message_queue = queue.Queue()
        
        # Build statistics
        self.build_stats = {
            "total_attempts": 0,
            "successful_builds": 0,
            "failed_builds": 0,
            "recovered_builds": 0,
            "average_time": 0
        }
        
        # Docker integration
        self.docker_client = None
        self.container_status = "disconnected"
        self.always_on_enabled = False
        self.container_queue = queue.Queue()
        
        # Load saved statistics
        self.load_statistics()
        
        self.setup_ui()
        self.start_message_processor()
        
        # Setup Docker after UI is ready
        self.root.after(500, self.setup_docker_client)
        
        # Run initial diagnostics
        self.root.after(1000, self.run_pre_build_validation)
        
    def setup_dark_theme(self):
        """Configure dark theme for the application"""
        # Define color scheme
        self.colors = {
            'bg': '#1e1e1e',           # Dark background
            'fg': '#e0e0e0',           # Light text
            'select_bg': '#3c3c3c',    # Selected item background
            'select_fg': '#ffffff',    # Selected item text
            'button_bg': '#2d2d2d',    # Button background
            'button_fg': '#e0e0e0',    # Button text
            'button_active': '#404040', # Button hover
            'entry_bg': '#2d2d2d',     # Entry background
            'entry_fg': '#e0e0e0',     # Entry text
            'frame_bg': '#252525',     # Frame background
            'label_bg': '#1e1e1e',     # Label background
            'success': '#4CAF50',      # Success green
            'warning': '#FFA726',      # Warning orange
            'error': '#EF5350',        # Error red
            'info': '#42A5F5',         # Info blue
            'accent': '#7C4DFF',       # Accent purple
            'recovery': '#00BCD4'      # Recovery cyan
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Configure ttk style
        self.style = ttk.Style()
        
        # Configure all widget styles (same as original)
        self.configure_ttk_styles()
        
    def configure_ttk_styles(self):
        """Configure all ttk widget styles"""
        # Notebook (tabs)
        self.style.configure('TNotebook', 
                           background=self.colors['bg'],
                           borderwidth=0)
        self.style.configure('TNotebook.Tab',
                           background=self.colors['button_bg'],
                           foreground=self.colors['fg'],
                           padding=[20, 10],
                           borderwidth=0)
        self.style.map('TNotebook.Tab',
                      background=[('selected', self.colors['select_bg']),
                                ('active', self.colors['button_active'])],
                      foreground=[('selected', self.colors['select_fg'])])
        
        # Frames
        self.style.configure('TFrame',
                           background=self.colors['frame_bg'],
                           borderwidth=0)
        
        # Labels
        self.style.configure('TLabel',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        
        # Buttons
        self.style.configure('TButton',
                           background=self.colors['button_bg'],
                           foreground=self.colors['button_fg'],
                           borderwidth=1,
                           relief='flat',
                           padding=6)
        self.style.map('TButton',
                      background=[('active', self.colors['button_active']),
                                ('pressed', self.colors['select_bg'])])
        
        # Special button styles
        self.style.configure('Accent.TButton',
                           background=self.colors['accent'],
                           foreground='white')
        self.style.configure('Success.TButton',
                           background=self.colors['success'],
                           foreground='white')
        self.style.configure('Recovery.TButton',
                           background=self.colors['recovery'],
                           foreground='white')
        
        # Other widgets
        self.style.configure('TEntry',
                           fieldbackground=self.colors['entry_bg'],
                           foreground=self.colors['entry_fg'])
        self.style.configure('TRadiobutton',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        self.style.configure('TCheckbutton',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        self.style.configure('TLabelframe',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        self.style.configure('TProgressbar',
                           background=self.colors['accent'],
                           troughcolor=self.colors['button_bg'])
        
    def setup_ui(self):
        """Setup the enhanced user interface"""
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create left panel for build selection and diagnostics
        left_panel = ttk.Frame(main_container, width=400)
        left_panel.pack(side='left', fill='both', expand=False, padx=(0, 5))
        
        # Create right panel for output and monitoring
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side='right', fill='both', expand=True)
        
        # Setup left panel
        self.setup_left_panel(left_panel)
        
        # Setup right panel
        self.setup_right_panel(right_panel)
        
        # Create status bar
        self.setup_status_bar()
        
    def setup_left_panel(self, parent):
        """Setup left panel with build selection and diagnostics"""
        # Title
        title_label = ttk.Label(parent, text="Z-FORGE RAM Server Build System v3.0", 
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # System status indicator
        self.status_indicator = ttk.Label(parent, text="⚪ System Status: Checking...",
                                        font=('Arial', 10))
        self.status_indicator.pack(pady=5)
        
        # Create notebook for organized sections
        left_notebook = ttk.Notebook(parent)
        left_notebook.pack(fill='both', expand=True)
        
        # Build Selection Tab
        build_frame = ttk.Frame(left_notebook)
        left_notebook.add(build_frame, text="Build Selection")
        self.setup_build_selection(build_frame)
        
        # Diagnostics Tab
        diag_frame = ttk.Frame(left_notebook)
        left_notebook.add(diag_frame, text="Diagnostics")
        self.setup_diagnostics(diag_frame)
        
        # Recovery Tab
        recovery_frame = ttk.Frame(left_notebook)
        left_notebook.add(recovery_frame, text="Recovery")
        self.setup_recovery(recovery_frame)
        
        # Container Management Tab
        container_frame = ttk.Frame(left_notebook)
        left_notebook.add(container_frame, text="Containers")
        self.setup_container_management(container_frame)
        
        # Statistics Tab
        stats_frame = ttk.Frame(left_notebook)
        left_notebook.add(stats_frame, text="Statistics")
        self.setup_statistics(stats_frame)
        
    def setup_build_selection(self, parent):
        """Setup build selection interface"""
        # Build type selection with success rate
        self.selected_build = tk.StringVar(value="Outside Packages Build (Fastest - 95% Success)")
        
        # Scrollable frame for build options
        canvas = tk.Canvas(parent, bg=self.colors['frame_bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Build option cards with success rate
        for build_name, build_info in self.build_specs.items():
            self.create_enhanced_build_card(scrollable_frame, build_name, build_info)
            
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=10)
        
        self.build_button = ttk.Button(
            button_frame, 
            text="🚀 Start Build", 
            command=self.start_build,
            style='Accent.TButton'
        )
        self.build_button.pack(side='left', padx=5)
        
        self.validate_button = ttk.Button(
            button_frame,
            text="✓ Validate",
            command=self.run_pre_build_validation
        )
        self.validate_button.pack(side='left', padx=5)
        
        self.stop_button = ttk.Button(
            button_frame,
            text="⏹ Stop",
            command=self.stop_build,
            state='disabled'
        )
        self.stop_button.pack(side='left', padx=5)
        
        # Container build option
        self.container_build_button = ttk.Button(
            button_frame,
            text="🐳 Container Build",
            command=self.start_container_build,
            style='Accent.TButton'
        )
        self.container_build_button.pack(side='right', padx=5)
        
        # Build mode selection
        mode_frame = ttk.Frame(parent)
        mode_frame.pack(fill='x', pady=5)
        
        self.build_mode_var = tk.StringVar(value="direct")
        ttk.Radiobutton(mode_frame, text="Direct Build", variable=self.build_mode_var, 
                       value="direct").pack(side='left', padx=10)
        ttk.Radiobutton(mode_frame, text="Container Build", variable=self.build_mode_var, 
                       value="container").pack(side='left', padx=10)
        
    def create_enhanced_build_card(self, parent, build_name, build_info):
        """Create enhanced build selection card with success rate"""
        # Main card frame
        card_frame = ttk.LabelFrame(parent, text="", padding=10)
        card_frame.pack(fill='x', pady=5, padx=10)
        
        # Header with radio button and success rate
        header_frame = ttk.Frame(card_frame)
        header_frame.pack(fill='x', pady=(0, 5))
        
        radio = ttk.Radiobutton(
            header_frame,
            text=build_name,
            variable=self.selected_build,
            value=build_name
        )
        radio.pack(side='left')
        
        # Success rate indicator
        success_rate = build_info.get('success_rate', 0)
        color = self.colors['success'] if success_rate >= 80 else \
                self.colors['warning'] if success_rate >= 60 else \
                self.colors['error']
        
        rate_label = ttk.Label(header_frame, 
                              text=f"Success: {success_rate}%",
                              foreground=color)
        rate_label.pack(side='right')
        
        # Description
        desc_label = ttk.Label(card_frame, text=build_info['description'], 
                             wraplength=350)
        desc_label.pack(fill='x', pady=(0, 5))
        
        # Features
        for feature in build_info['features'][:2]:  # Show first 2 features
            feature_label = ttk.Label(card_frame, text=f"• {feature}", 
                                    font=('Arial', 8))
            feature_label.pack(anchor='w', padx=(10, 0))
            
    def setup_diagnostics(self, parent):
        """Setup diagnostics interface"""
        # Diagnostic results display
        self.diag_text = scrolledtext.ScrolledText(
            parent, 
            height=20, 
            width=45,
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg'],
            insertbackground=self.colors['fg']
        )
        self.diag_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configure tags for colored output
        self.diag_text.tag_config('success', foreground=self.colors['success'])
        self.diag_text.tag_config('warning', foreground=self.colors['warning'])
        self.diag_text.tag_config('error', foreground=self.colors['error'])
        self.diag_text.tag_config('info', foreground=self.colors['info'])
        
        # Diagnostic buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            button_frame,
            text="Run Full Diagnostics",
            command=self.run_full_diagnostics
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Quick Check",
            command=self.run_quick_check
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Clear",
            command=lambda: self.diag_text.delete('1.0', tk.END)
        ).pack(side='left', padx=5)
        
    def setup_recovery(self, parent):
        """Setup recovery interface"""
        # Recovery options
        options_frame = ttk.LabelFrame(parent, text="Recovery Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=10)
        
        self.auto_recovery_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Enable Automatic Recovery",
            variable=self.auto_recovery_var,
            command=self.toggle_auto_recovery
        ).pack(anchor='w')
        
        self.aggressive_recovery_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Aggressive Recovery Mode",
            variable=self.aggressive_recovery_var
        ).pack(anchor='w')
        
        # Recovery history
        history_frame = ttk.LabelFrame(parent, text="Recovery History", padding=10)
        history_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.recovery_listbox = tk.Listbox(
            history_frame,
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg'],
            selectbackground=self.colors['select_bg']
        )
        self.recovery_listbox.pack(fill='both', expand=True)
        
        # Manual recovery buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            button_frame,
            text="Fix APT Issues",
            command=lambda: self.manual_recovery("apt_lock")
        ).pack(side='left', padx=2)
        
        ttk.Button(
            button_frame,
            text="Fix Packages",
            command=lambda: self.manual_recovery("broken_packages")
        ).pack(side='left', padx=2)
        
        ttk.Button(
            button_frame,
            text="Fix Space",
            command=lambda: self.manual_recovery("disk_space")
        ).pack(side='left', padx=2)
        
    def setup_statistics(self, parent):
        """Setup statistics display"""
        # Statistics display
        self.stats_text = scrolledtext.ScrolledText(
            parent, 
            height=15, 
            width=45,
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg']
        )
        self.stats_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Update statistics display
        self.update_statistics_display()
        
        # Reset button
        ttk.Button(
            parent,
            text="Reset Statistics",
            command=self.reset_statistics
        ).pack(pady=5)
        
    def setup_right_panel(self, parent):
        """Setup right panel with output and monitoring"""
        # Create notebook for different views
        right_notebook = ttk.Notebook(parent)
        right_notebook.pack(fill='both', expand=True)
        
        # Build Output Tab
        output_frame = ttk.Frame(right_notebook)
        right_notebook.add(output_frame, text="Build Output")
        self.setup_build_output(output_frame)
        
        # Error Analysis Tab
        analysis_frame = ttk.Frame(right_notebook)
        right_notebook.add(analysis_frame, text="Error Analysis")
        self.setup_error_analysis(analysis_frame)
        
        # Progress Monitoring Tab
        progress_frame = ttk.Frame(right_notebook)
        right_notebook.add(progress_frame, text="Progress")
        self.setup_progress_monitoring(progress_frame)
        
    def setup_build_output(self, parent):
        """Setup build output display"""
        # Output display with enhanced coloring
        self.output_text = scrolledtext.ScrolledText(
            parent, 
            height=35, 
            state='disabled',
            bg='#0c0c0c',
            fg='#00ff00',
            insertbackground='#00ff00',
            font=('Consolas', 10)
        )
        self.output_text.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure text tags for colored output
        self.output_text.tag_config('error', foreground=self.colors['error'])
        self.output_text.tag_config('warning', foreground=self.colors['warning'])
        self.output_text.tag_config('success', foreground=self.colors['success'])
        self.output_text.tag_config('info', foreground=self.colors['info'])
        self.output_text.tag_config('recovery', foreground=self.colors['recovery'])
        
        # Control buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            button_frame,
            text="Clear Output",
            command=self.clear_output
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Save Output",
            command=self.save_output
        ).pack(side='left', padx=5)
        
        ttk.Button(
            button_frame,
            text="Analyze Errors",
            command=self.analyze_current_errors
        ).pack(side='left', padx=5)
        
    def setup_error_analysis(self, parent):
        """Setup error analysis display"""
        # Error summary
        summary_frame = ttk.LabelFrame(parent, text="Error Summary", padding=10)
        summary_frame.pack(fill='x', padx=10, pady=10)
        
        self.error_summary_label = ttk.Label(summary_frame, 
                                            text="No errors detected yet")
        self.error_summary_label.pack()
        
        # Error details
        self.error_tree = ttk.Treeview(parent, columns=('Time', 'Type', 'Module', 'Status'),
                                      show='tree headings')
        self.error_tree.heading('#0', text='Error')
        self.error_tree.heading('Time', text='Time')
        self.error_tree.heading('Type', text='Type')
        self.error_tree.heading('Module', text='Module')
        self.error_tree.heading('Status', text='Status')
        
        self.error_tree.column('#0', width=300)
        self.error_tree.column('Time', width=100)
        self.error_tree.column('Type', width=100)
        self.error_tree.column('Module', width=100)
        self.error_tree.column('Status', width=100)
        
        self.error_tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Error action buttons
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', pady=5)
        
        ttk.Button(
            action_frame,
            text="Auto Fix Selected",
            command=self.auto_fix_selected_error
        ).pack(side='left', padx=5)
        
        ttk.Button(
            action_frame,
            text="View Details",
            command=self.view_error_details
        ).pack(side='left', padx=5)
        
    def setup_progress_monitoring(self, parent):
        """Setup progress monitoring display"""
        # Overall progress
        progress_frame = ttk.LabelFrame(parent, text="Build Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=10)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, 
                                           variable=self.progress_var,
                                           maximum=100)
        self.progress_bar.pack(fill='x', pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to build")
        self.progress_label.pack()
        
        # Module progress
        module_frame = ttk.LabelFrame(parent, text="Module Progress", padding=10)
        module_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.module_tree = ttk.Treeview(module_frame, 
                                       columns=('Status', 'Time', 'Details'),
                                       show='tree headings')
        self.module_tree.heading('#0', text='Module')
        self.module_tree.heading('Status', text='Status')
        self.module_tree.heading('Time', text='Time')
        self.module_tree.heading('Details', text='Details')
        
        self.module_tree.pack(fill='both', expand=True)
        
    def setup_status_bar(self):
        """Setup status bar at bottom"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side='bottom', fill='x', pady=(5, 0))
        
        self.status_label = ttk.Label(status_frame, 
                                     text="Ready | No build running",
                                     relief='sunken')
        self.status_label.pack(side='left', fill='x', expand=True, padx=5)
        
        self.recovery_status = ttk.Label(status_frame,
                                        text="Recovery: Enabled",
                                        relief='sunken')
        self.recovery_status.pack(side='right', padx=5)
        
    def run_pre_build_validation(self):
        """Run pre-build validation checks"""
        def validate():
            self.append_diagnostic("Running pre-build validation...\n", 'info')
            
            # Run diagnostic checks
            results = self.diagnostic_tool.run_all_checks()
            
            # Update status indicator
            if results['summary']['ready_to_build']:
                self.update_status_indicator('success', "✅ System Ready")
                self.append_diagnostic("\n✅ SYSTEM READY TO BUILD\n", 'success')
            else:
                self.update_status_indicator('error', "❌ Issues Detected")
                self.append_diagnostic("\n❌ ISSUES DETECTED:\n", 'error')
                
                for issue in results['summary']['critical_issues']:
                    self.append_diagnostic(f"  • {issue}\n", 'error')
                    
            # Show warnings
            if results['summary']['warnings']:
                self.append_diagnostic("\n⚠️ WARNINGS:\n", 'warning')
                for warning in results['summary']['warnings'][:5]:
                    self.append_diagnostic(f"  • {warning}\n", 'warning')
                    
            # Show recommendations
            self.append_diagnostic("\n📋 RECOMMENDATIONS:\n", 'info')
            for rec in results['summary']['recommendations'][:5]:
                self.append_diagnostic(f"{rec}\n", 'info')
                
        threading.Thread(target=validate, daemon=True).start()
        
    def run_full_diagnostics(self):
        """Run comprehensive diagnostics"""
        def diagnose():
            self.diag_text.delete('1.0', tk.END)
            self.append_diagnostic("=" * 60 + "\n", 'info')
            self.append_diagnostic("FULL SYSTEM DIAGNOSTICS\n", 'info')
            self.append_diagnostic("=" * 60 + "\n", 'info')
            
            results = self.diagnostic_tool.run_all_checks()
            
            # Display detailed results
            checks = [
                ("System Requirements", results['system']),
                ("Dependencies", results['dependencies']),
                ("Workspace", results['workspace']),
                ("Network", results['network']),
                ("APT System", results['apt']),
                ("Kernel", results['kernel']),
                ("ZFS", results['zfs']),
                ("Dracut", results['dracut']),
                ("Permissions", results['permissions']),
                ("Build Specs", results['build_specs'])
            ]
            
            for name, check in checks:
                status = check.get('status', 'UNKNOWN')
                if status == 'PASS':
                    self.append_diagnostic(f"✅ {name}: PASS\n", 'success')
                elif status == 'FAIL':
                    self.append_diagnostic(f"❌ {name}: FAIL\n", 'error')
                else:
                    self.append_diagnostic(f"⚠️ {name}: {status}\n", 'warning')
                    
        threading.Thread(target=diagnose, daemon=True).start()
        
    def run_quick_check(self):
        """Run quick system check"""
        self.diag_text.delete('1.0', tk.END)
        self.append_diagnostic("Quick System Check:\n\n", 'info')
        
        # Check disk space
        if self.disk_free_gb < 30:
            self.append_diagnostic(f"⚠️ Low disk space: {self.disk_free_gb}GB\n", 'warning')
        else:
            self.append_diagnostic(f"✅ Disk space: {self.disk_free_gb}GB\n", 'success')
            
        # Check memory
        if self.memory_gb < 4:
            self.append_diagnostic(f"⚠️ Low memory: {self.memory_gb}GB\n", 'warning')
        else:
            self.append_diagnostic(f"✅ Memory: {self.memory_gb}GB\n", 'success')
            
        # Check network
        try:
            subprocess.run(["ping", "-c", "1", "-W", "2", "8.8.8.8"],
                         capture_output=True, timeout=3, check=True)
            self.append_diagnostic("✅ Network: Connected\n", 'success')
        except:
            self.append_diagnostic("❌ Network: No connection\n", 'error')
            
        # Check RAM workspace
        workspace = Path("/dev/shm/zforge-workspace")
        if workspace.exists():
            self.append_diagnostic(f"✅ RAM Workspace: {workspace}\n", 'success')
        else:
            self.append_diagnostic(f"⚠️ RAM Workspace not found: {workspace}\n", 'warning')
            self.append_diagnostic("Creating RAM workspace for 3-5x performance...\n", 'info')
            try:
                workspace.mkdir(parents=True, exist_ok=True)
                self.append_diagnostic(f"✅ RAM Workspace created: {workspace}\n", 'success')
            except Exception as e:
                self.append_diagnostic(f"❌ Failed to create RAM workspace: {e}\n", 'error')
            
    def start_build(self):
        """Start the build process with enhanced monitoring"""
        if self.build_running:
            messagebox.showwarning("Build Running", "A build is already in progress!")
            return
            
        # Get selected build
        selected_build = self.selected_build.get()
        if not selected_build:
            messagebox.showerror("No Selection", "Please select a build type!")
            return
            
        build_file = self.build_specs[selected_build]['file']
        
        # Check if build spec exists
        if not Path(build_file).exists():
            messagebox.showerror("File Not Found", f"Build specification {build_file} not found!")
            return
            
        # Run pre-build validation
        self.append_output("Running pre-build validation...\n", 'info')
        results = self.diagnostic_tool.run_all_checks()
        
        if not results['summary']['ready_to_build']:
            if not messagebox.askyesno("Issues Detected", 
                                      "System has issues. Continue anyway?"):
                return
                
        # Confirm build start
        if not messagebox.askyesno(
            "Confirm Build", 
            f"Start {selected_build}?\n\n"
            f"Auto-recovery is {'ENABLED' if self.auto_recovery_enabled else 'DISABLED'}\n\n"
            f"Continue?"
        ):
            return
            
        # Reset error tracking
        self.errors_detected = []
        self.warnings_detected = []
        self.recovery_attempts = 0
        
        # Update statistics
        self.build_stats['total_attempts'] += 1
        
        # Prepare build command
        cmd = [sys.executable, 'build.py', '--spec', build_file]
        workspace = "/dev/shm/zforge-workspace"  # All builds now use RAM workspace
        cmd.extend(['--workspace', workspace])
        
        # Prepare environment
        env = os.environ.copy()
        env['MAKEFLAGS'] = f'-j{min(4, self.cpu_count)}'
        
        # Start build
        self.build_running = True
        self.build_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Clear output
        self.clear_output()
        self.append_output(f"Starting build: {' '.join(cmd)}\n\n", 'info')
        
        # Update status
        self.status_label.config(text=f"Building: {selected_build}")
        self.progress_var.set(0)
        self.progress_label.config(text="Starting build...")
        
        # Start build process
        threading.Thread(target=self.run_build_with_monitoring, 
                        args=(cmd, env), daemon=True).start()
        
    def run_build_with_monitoring(self, cmd, env):
        """Run build with intelligent monitoring and recovery"""
        build_start_time = time.time()
        current_module = "initialization"
        
        try:
            # Start process
            self.build_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor output
            for line in iter(self.build_process.stdout.readline, ''):
                if not self.build_running:
                    break
                    
                # Update output display
                self.message_queue.put(('output', line))
                
                # Detect current module
                module_match = re.search(r"Executing module: (\w+)", line)
                if module_match:
                    current_module = module_match.group(1)
                    self.message_queue.put(('module', current_module))
                    
                # Detect errors
                if self.detect_error(line):
                    error_info = self.analyze_error(line, current_module)
                    self.message_queue.put(('error', error_info))
                    
                    # Attempt recovery if enabled
                    if self.auto_recovery_enabled and self.recovery_attempts < self.max_recovery_attempts:
                        self.attempt_automatic_recovery(error_info)
                        
                # Detect warnings
                if self.detect_warning(line):
                    self.message_queue.put(('warning', line))
                    
                # Update progress
                progress = self.estimate_progress(current_module)
                self.message_queue.put(('progress', progress))
                
            # Wait for process to complete
            self.build_process.wait()
            
            # Handle completion
            build_time = time.time() - build_start_time
            
            if self.build_process.returncode == 0:
                self.build_stats['successful_builds'] += 1
                self.message_queue.put(('success', f"Build completed in {build_time:.1f}s"))
            else:
                self.build_stats['failed_builds'] += 1
                self.message_queue.put(('failure', f"Build failed after {build_time:.1f}s"))
                
                # Try final recovery
                if self.auto_recovery_enabled:
                    self.attempt_final_recovery()
                    
        except Exception as e:
            self.message_queue.put(('error', str(e)))
            
        finally:
            self.build_running = False
            self.build_process = None
            self.message_queue.put(('complete', None))
            self.save_statistics()
            
    def detect_error(self, line):
        """Detect if line contains an error"""
        error_patterns = [
            r"ERROR",
            r"FAILED", 
            r"error:",
            r"failed:",
            r"returned non-zero exit status",
            r"dpkg returned an error code",
            r"No space left",
            r"Permission denied",
            r"not found",
            r"Unable to"
        ]
        
        for pattern in error_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
        
    def detect_warning(self, line):
        """Detect if line contains a warning"""
        warning_patterns = [
            r"WARNING",
            r"warning:",
            r"deprecated",
            r"insecure"
        ]
        
        for pattern in warning_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
        
    def analyze_error(self, line, module):
        """Analyze error and determine type"""
        error_info = {
            'line': line,
            'module': module,
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'unknown',
            'recoverable': False
        }
        
        # Determine error type
        if "dpkg returned an error code" in line:
            error_info['type'] = 'dpkg_error'
            error_info['recoverable'] = True
        elif "Could not get lock" in line or "Unable to acquire" in line:
            error_info['type'] = 'apt_lock'
            error_info['recoverable'] = True
        elif "broken packages" in line.lower():
            error_info['type'] = 'broken_packages'
            error_info['recoverable'] = True
        elif "No space left" in line:
            error_info['type'] = 'disk_space'
            error_info['recoverable'] = True
        elif "not found" in line.lower():
            error_info['type'] = 'missing_file'
            error_info['recoverable'] = False
        elif "Permission denied" in line:
            error_info['type'] = 'permission'
            error_info['recoverable'] = False
            
        return error_info
        
    def attempt_automatic_recovery(self, error_info):
        """Attempt automatic recovery from error"""
        if not error_info['recoverable']:
            return False
            
        self.recovery_attempts += 1
        
        self.message_queue.put(('recovery', 
                              f"Attempting recovery for {error_info['type']}..."))
        
        # Pause build if possible
        if self.build_process:
            self.build_process.send_signal(subprocess.signal.SIGSTOP)
            
        # Run recovery
        success = self.recovery_tool.recover_from_failure(error_info['type'])
        
        # Record recovery attempt
        self.recovery_history.append({
            'time': error_info['time'],
            'type': error_info['type'],
            'success': success
        })
        
        # Update recovery display
        status = "✅ Fixed" if success else "❌ Failed"
        self.recovery_listbox.insert(tk.END, 
                                    f"{error_info['time']} - {error_info['type']}: {status}")
        
        # Resume build if successful
        if success and self.build_process:
            self.build_process.send_signal(subprocess.signal.SIGCONT)
            self.build_stats['recovered_builds'] += 1
            
        return success
        
    def attempt_final_recovery(self):
        """Attempt final recovery after build failure"""
        self.message_queue.put(('recovery', "Attempting final recovery..."))
        
        # Try common fixes
        fixes_attempted = []
        
        if self.recovery_tool.fix_apt_locks():
            fixes_attempted.append("APT locks")
        if self.recovery_tool.fix_dpkg_errors():
            fixes_attempted.append("dpkg errors")
        if self.recovery_tool.fix_disk_space():
            fixes_attempted.append("disk space")
            
        if fixes_attempted:
            self.message_queue.put(('recovery', 
                                  f"Fixed: {', '.join(fixes_attempted)}"))
            
            # Suggest retry
            self.message_queue.put(('info', 
                                  "Recovery complete. Try building again."))
            
    def estimate_progress(self, module):
        """Estimate build progress based on current module"""
        module_weights = {
            'initialization': 5,
            'workspace_setup': 10,
            'debootstrap': 25,
            'kernel_acquisition': 40,
            'dracut_config': 45,
            'zfs_build': 60,
            'live_environment': 75,
            'iso_generation': 90,
            'cleanup': 95,
            'complete': 100
        }
        
        return module_weights.get(module, 50)
        
    def manual_recovery(self, error_type):
        """Manual recovery trigger"""
        success = self.recovery_tool.recover_from_failure(error_type)
        
        if success:
            self.append_diagnostic(f"✅ Successfully fixed {error_type}\n", 'success')
        else:
            self.append_diagnostic(f"❌ Failed to fix {error_type}\n", 'error')
            
        # Update recovery history
        self.recovery_history.append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': error_type,
            'success': success
        })
        
    def analyze_current_errors(self):
        """Analyze errors in current output"""
        output_content = self.output_text.get('1.0', tk.END)
        
        # Clear error tree
        for item in self.error_tree.get_children():
            self.error_tree.delete(item)
            
        # Find and categorize errors
        error_count = 0
        for line_num, line in enumerate(output_content.split('\n'), 1):
            if self.detect_error(line):
                error_info = self.analyze_error(line, "unknown")
                error_count += 1
                
                # Add to error tree
                status = "Recoverable" if error_info['recoverable'] else "Manual fix needed"
                self.error_tree.insert('', 'end', 
                                      text=line[:50] + "...",
                                      values=(error_info['time'], 
                                            error_info['type'],
                                            error_info['module'],
                                            status))
                                            
        # Update summary
        self.error_summary_label.config(
            text=f"Found {error_count} errors ({len([e for e in self.errors_detected if e.get('recoverable')])} recoverable)"
        )
        
    def auto_fix_selected_error(self):
        """Attempt to fix selected error"""
        selection = self.error_tree.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select an error to fix")
            return
            
        item = self.error_tree.item(selection[0])
        error_type = item['values'][1]  # Get error type from values
        
        self.manual_recovery(error_type)
        
    def view_error_details(self):
        """View details of selected error"""
        selection = self.error_tree.selection()
        if not selection:
            return
            
        item = self.error_tree.item(selection[0])
        details = f"""
Error Details:
--------------
Time: {item['values'][0]}
Type: {item['values'][1]}
Module: {item['values'][2]}
Status: {item['values'][3]}

Error Text:
{item['text']}

Suggested Solutions:
"""
        
        # Add solutions based on error type
        error_type = item['values'][1]
        if error_type == 'dpkg_error':
            details += """
1. Run: sudo dpkg --configure -a
2. Fix broken packages: sudo apt-get install -f
3. Clean cache: sudo apt-get clean
"""
        elif error_type == 'apt_lock':
            details += """
1. Check for running apt processes
2. Remove lock files if safe
3. Restart apt service
"""
            
        messagebox.showinfo("Error Details", details)
        
    def toggle_auto_recovery(self):
        """Toggle automatic recovery"""
        self.auto_recovery_enabled = self.auto_recovery_var.get()
        status = "Enabled" if self.auto_recovery_enabled else "Disabled"
        self.recovery_status.config(text=f"Recovery: {status}")
        
    def update_status_indicator(self, status_type, text):
        """Update system status indicator"""
        colors = {
            'success': self.colors['success'],
            'warning': self.colors['warning'],
            'error': self.colors['error'],
            'info': self.colors['info']
        }
        
        self.status_indicator.config(text=text, foreground=colors.get(status_type, 'white'))
        
    def append_output(self, text, tag=None):
        """Append text to output display"""
        self.output_text.config(state='normal')
        
        if tag:
            self.output_text.insert(tk.END, text, tag)
        else:
            # Auto-detect tag
            if 'ERROR' in text or 'FAILED' in text:
                self.output_text.insert(tk.END, text, 'error')
            elif 'WARNING' in text:
                self.output_text.insert(tk.END, text, 'warning')
            elif 'SUCCESS' in text or '✅' in text:
                self.output_text.insert(tk.END, text, 'success')
            elif 'INFO' in text or '===' in text:
                self.output_text.insert(tk.END, text, 'info')
            elif 'RECOVERY' in text or 'Attempting recovery' in text:
                self.output_text.insert(tk.END, text, 'recovery')
            else:
                self.output_text.insert(tk.END, text)
                
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')
        
    def append_diagnostic(self, text, tag=None):
        """Append text to diagnostic display"""
        if tag:
            self.diag_text.insert(tk.END, text, tag)
        else:
            self.diag_text.insert(tk.END, text)
        self.diag_text.see(tk.END)
        
    def clear_output(self):
        """Clear output display"""
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state='disabled')
        
    def save_output(self):
        """Save output to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Build Output",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.output_text.get('1.0', tk.END))
                messagebox.showinfo("Saved", f"Output saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")

    def start_container_build(self):
        """Start build in Docker container"""
        if not self.docker_client:
            messagebox.showerror("Docker Error", "Docker not available. Please install Docker first.")
            return
            
        if self.build_running:
            messagebox.showwarning("Build Running", "A build is already in progress!")
            return
            
        # Get selected build
        selected_build = self.selected_build.get()
        if not selected_build:
            messagebox.showerror("No Selection", "Please select a build type!")
            return
            
        build_file = self.build_specs[selected_build]['file']
        
        # Check if container image exists
        try:
            self.docker_client.images.get('zforge:latest')
        except:
            if messagebox.askyesno("Container Missing", 
                                  "Z-FORGE container not found. Build it now?"):
                self.build_container()
                return
            else:
                return
        
        # Confirm container build
        if not messagebox.askyesno(
            "Confirm Container Build",
            f"Start containerized build:\n\n"
            f"Build: {selected_build}\n"
            f"Spec: {build_file}\n"
            f"Mode: RAM Container (20GB tmpfs)\n\n"
            f"This will use Docker with privileged access."
        ):
            return
            
        def container_build_thread():
            try:
                self.build_running = True
                self.build_button.config(state='disabled')
                self.container_build_button.config(state='disabled')
                self.stop_button.config(state='normal')
                
                self.append_output("🐳 Starting containerized build...\n", 'info')
                self.append_output(f"Build spec: {build_file}\n", 'info')
                
                # Prepare output directory
                output_dir = Path.cwd() / 'output'
                output_dir.mkdir(exist_ok=True)
                
                # Run container build
                container = self.docker_client.containers.run(
                    'zforge:latest',
                    detach=True,
                    privileged=True,
                    tmpfs={'/workspace': 'rw,size=20G,exec'},
                    volumes={
                        str(output_dir): {'bind': '/output', 'mode': 'rw'},
                        str(Path.cwd()): {'bind': '/zforge', 'mode': 'ro'}
                    },
                    working_dir='/zforge',
                    command=f'python3 build.py --spec {build_file} '
                           f'--workspace /workspace/zforge-build '
                           f'--output /output/zforge-container-{int(time.time())}.iso '
                           f'--auto-confirm'
                )
                
                self.append_output("🐳 Container started, monitoring build...\n", 'info')
                
                # Stream container output
                for log in container.logs(stream=True, follow=True):
                    if not self.build_running:
                        container.stop()
                        break
                    self.append_output(log.decode('utf-8'), 'normal')
                
                # Wait for completion
                result = container.wait()
                
                if result['StatusCode'] == 0:
                    self.append_output("\n🎉 Container build completed successfully!\n", 'success')
                    self.build_stats['successful_builds'] += 1
                else:
                    self.append_output(f"\n❌ Container build failed with code {result['StatusCode']}\n", 'error')
                    self.build_stats['failed_builds'] += 1
                    
                # Cleanup
                container.remove()
                
            except Exception as e:
                self.append_output(f"\n❌ Container build error: {str(e)}\n", 'error')
                self.build_stats['failed_builds'] += 1
            finally:
                self.build_running = False
                self.build_button.config(state='normal')
                self.container_build_button.config(state='normal')
                self.stop_button.config(state='disabled')
                
                self.build_stats['total_attempts'] += 1
                self.save_statistics()
                self.update_statistics_display()
        
        # Start container build in background
        threading.Thread(target=container_build_thread, daemon=True).start()
                
    def stop_build(self):
        """Stop the running build"""
        if self.build_process and self.build_running:
            if messagebox.askyesno("Confirm Stop", "Stop the running build?"):
                self.build_running = False
                try:
                    self.build_process.terminate()
                    self.append_output("\n\n=== BUILD STOPPED BY USER ===\n", 'warning')
                except:
                    pass
                    
    def start_message_processor(self):
        """Process messages from build thread"""
        def process_messages():
            try:
                while True:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                    
                    if msg_type == 'output':
                        self.append_output(data)
                    elif msg_type == 'error':
                        self.errors_detected.append(data)
                        self.append_output(f"\n❌ ERROR: {data['line']}", 'error')
                    elif msg_type == 'warning':
                        self.warnings_detected.append(data)
                        self.append_output(f"⚠️ WARNING: {data}", 'warning')
                    elif msg_type == 'recovery':
                        self.append_output(f"\n🔧 RECOVERY: {data}\n", 'recovery')
                    elif msg_type == 'module':
                        self.progress_label.config(text=f"Running: {data}")
                        # Add to module tree
                        self.module_tree.insert('', 'end', text=data,
                                              values=('Running', 
                                                    datetime.now().strftime('%H:%M:%S'),
                                                    ''))
                    elif msg_type == 'progress':
                        self.progress_var.set(data)
                    elif msg_type == 'success':
                        self.append_output(f"\n\n✅ SUCCESS: {data}\n", 'success')
                        messagebox.showinfo("Build Complete", data)
                    elif msg_type == 'failure':
                        self.append_output(f"\n\n❌ FAILURE: {data}\n", 'error')
                        messagebox.showerror("Build Failed", data)
                    elif msg_type == 'complete':
                        self.build_button.config(state='normal')
                        self.stop_button.config(state='disabled')
                        self.status_label.config(text="Ready | No build running")
                        self.update_statistics_display()
                        
            except queue.Empty:
                pass
            except Exception as e:
                print(f"Message processor error: {e}")
                
            # Schedule next check
            self.root.after(100, process_messages)
            
        # Start processing
        self.root.after(100, process_messages)
        
    def load_statistics(self):
        """Load saved statistics"""
        stats_file = Path("logs/build_statistics.json")
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    self.build_stats = json.load(f)
            except:
                pass
                
    def save_statistics(self):
        """Save statistics to file"""
        stats_file = Path("logs/build_statistics.json")
        try:
            with open(stats_file, 'w') as f:
                json.dump(self.build_stats, f, indent=2)
        except:
            pass
            
    def update_statistics_display(self):
        """Update statistics display"""
        self.stats_text.delete('1.0', tk.END)
        
        total = self.build_stats['total_attempts']
        successful = self.build_stats['successful_builds']
        failed = self.build_stats['failed_builds']
        recovered = self.build_stats['recovered_builds']
        
        success_rate = (successful / total * 100) if total > 0 else 0
        recovery_rate = (recovered / failed * 100) if failed > 0 else 0
        
        stats = f"""
BUILD STATISTICS
================

Total Attempts: {total}
Successful: {successful}
Failed: {failed}
Recovered: {recovered}

Success Rate: {success_rate:.1f}%
Recovery Rate: {recovery_rate:.1f}%

Errors Detected: {len(self.errors_detected)}
Warnings: {len(self.warnings_detected)}
Recovery Attempts: {self.recovery_attempts}

RECOMMENDATIONS:
"""
        
        self.stats_text.insert('1.0', stats)
        
        # Add recommendations based on statistics
        if success_rate < 50:
            self.stats_text.insert(tk.END, 
                                  "• Use 'Outside Packages Build' for better success rate\n")
        if recovery_rate < 50 and failed > 0:
            self.stats_text.insert(tk.END, 
                                  "• Enable aggressive recovery mode\n")
        if len(self.errors_detected) > 10:
            self.stats_text.insert(tk.END, 
                                  "• Run full diagnostics before next build\n")
            
    def reset_statistics(self):
        """Reset all statistics"""
        if messagebox.askyesno("Reset Statistics", "Reset all build statistics?"):
            self.build_stats = {
                "total_attempts": 0,
                "successful_builds": 0,
                "failed_builds": 0,
                "recovered_builds": 0,
                "average_time": 0
            }
            self.save_statistics()
            self.update_statistics_display()

    def setup_docker_client(self):
        """Initialize Docker client"""
        if not DOCKER_AVAILABLE:
            self.docker_client = None
            self.container_status = "unavailable"
            self.append_output("❌ Docker library not available. Install with: apt install python3-docker\n", 'error')
            return
            
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            self.container_status = "connected"
            self.append_output("✅ Docker client connected\n", 'info')
        except Exception as e:
            self.docker_client = None
            self.container_status = "error"
            self.append_output(f"❌ Docker connection failed: {str(e)}\n", 'error')

    def setup_container_management(self, parent):
        """Setup container management interface"""
        # Container status
        status_frame = ttk.LabelFrame(parent, text="Container Status", padding=10)
        status_frame.pack(fill='x', pady=(0, 10))
        
        self.container_status_label = ttk.Label(status_frame, text="⚪ Checking Docker...")
        self.container_status_label.pack(anchor='w')
        
        self.always_on_status_label = ttk.Label(status_frame, text="⚪ Always-On: Disabled")
        self.always_on_status_label.pack(anchor='w')
        
        # Container controls
        control_frame = ttk.LabelFrame(parent, text="Container Controls", padding=10)
        control_frame.pack(fill='x', pady=(0, 10))
        
        # Build container button
        self.build_container_btn = ttk.Button(
            control_frame, 
            text="🔨 Build Container", 
            command=self.build_container
        )
        self.build_container_btn.pack(fill='x', pady=2)
        
        # Start always-on service
        self.always_on_btn = ttk.Button(
            control_frame, 
            text="🚀 Start Always-On Service", 
            command=self.toggle_always_on
        )
        self.always_on_btn.pack(fill='x', pady=2)
        
        # Container build queue
        queue_frame = ttk.LabelFrame(parent, text="Build Queue", padding=10)
        queue_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Queue build options
        queue_options_frame = ttk.Frame(queue_frame)
        queue_options_frame.pack(fill='x', pady=(0, 5))
        
        self.queue_spec_var = tk.StringVar(value="build_spec_outside_packages.yml")
        queue_combo = ttk.Combobox(queue_options_frame, textvariable=self.queue_spec_var, 
                                  values=list(self.build_specs.keys()), state='readonly')
        queue_combo.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        ttk.Button(queue_options_frame, text="➕ Queue Build", 
                  command=self.queue_container_build).pack(side='right')
        
        # Queue display
        self.queue_display = scrolledtext.ScrolledText(queue_frame, height=8, width=40)
        self.queue_display.pack(fill='both', expand=True)
        
        # Update status
        self.update_container_status()

    def build_container(self):
        """Build the Z-FORGE Docker container"""
        if not self.docker_client:
            messagebox.showerror("Docker Error", "Docker not available. Please install Docker.")
            return
            
        def build_thread():
            try:
                self.append_output("🔨 Building Z-FORGE container...\n", 'info')
                self.build_container_btn.config(text="🔨 Building...", state='disabled')
                
                # Run docker build
                result = subprocess.run([
                    'docker', 'build', '-t', 'zforge:latest', '.'
                ], capture_output=True, text=True, cwd=os.getcwd())
                
                if result.returncode == 0:
                    self.append_output("✅ Container built successfully!\n", 'success')
                    self.container_status = "ready"
                else:
                    self.append_output(f"❌ Container build failed: {result.stderr}\n", 'error')
                    
            except Exception as e:
                self.append_output(f"❌ Container build error: {str(e)}\n", 'error')
            finally:
                self.build_container_btn.config(text="🔨 Build Container", state='normal')
                self.update_container_status()
        
        threading.Thread(target=build_thread, daemon=True).start()

    def toggle_always_on(self):
        """Toggle always-on container service"""
        if not self.always_on_enabled:
            self.start_always_on_service()
        else:
            self.stop_always_on_service()

    def start_always_on_service(self):
        """Start always-on container service"""
        if not self.docker_client:
            messagebox.showerror("Docker Error", "Docker not available")
            return
            
        def start_service():
            try:
                self.append_output("🚀 Starting always-on container service...\n", 'info')
                self.always_on_btn.config(text="⏸️ Stop Always-On", state='disabled')
                
                # Create directories
                os.makedirs('/tmp/zforge/logs', exist_ok=True)
                os.makedirs('/tmp/zforge/output', exist_ok=True)
                os.makedirs('/tmp/zforge/queue', exist_ok=True)
                
                # Start always-on container
                container = self.docker_client.containers.run(
                    'zforge:latest',
                    name='zforge-always-on',
                    detach=True,
                    remove=True,
                    privileged=True,
                    tmpfs={'/workspace': 'rw,size=20G,exec'},
                    volumes={
                        '/tmp/zforge/output': {'bind': '/output', 'mode': 'rw'},
                        '/tmp/zforge/queue': {'bind': '/queue', 'mode': 'rw'}
                    },
                    command='/bin/bash -c "while true; do '
                           'JOB=$(ls /queue/*.job 2>/dev/null | head -1); '
                           'if [ -n \"$JOB\" ]; then '
                           '  SPEC=$(cat $JOB); '
                           '  rm $JOB; '
                           '  python3 build.py --spec $SPEC '
                           '    --workspace /workspace/zforge '
                           '    --output /output/zforge-$(date +%s).iso; '
                           'fi; '
                           'sleep 5; '
                           'done"'
                )
                
                self.always_on_enabled = True
                self.append_output("✅ Always-on service started!\n", 'success')
                self.always_on_btn.config(text="⏸️ Stop Always-On", state='normal')
                
            except Exception as e:
                self.append_output(f"❌ Failed to start always-on service: {str(e)}\n", 'error')
                self.always_on_btn.config(text="🚀 Start Always-On", state='normal')
            
            self.update_container_status()
        
        threading.Thread(target=start_service, daemon=True).start()

    def stop_always_on_service(self):
        """Stop always-on container service"""
        def stop_service():
            try:
                self.append_output("⏸️ Stopping always-on service...\n", 'info')
                
                # Stop container
                container = self.docker_client.containers.get('zforge-always-on')
                container.stop()
                
                self.always_on_enabled = False
                self.append_output("✅ Always-on service stopped\n", 'info')
                
            except Exception as e:
                self.append_output(f"❌ Error stopping service: {str(e)}\n", 'error')
            finally:
                self.always_on_btn.config(text="🚀 Start Always-On", state='normal')
                self.update_container_status()
        
        threading.Thread(target=stop_service, daemon=True).start()

    def queue_container_build(self):
        """Add build to container queue"""
        if not self.always_on_enabled:
            messagebox.showerror("Service Error", "Always-on service must be running to queue builds")
            return
            
        selected_build = self.queue_spec_var.get()
        if selected_build in self.build_specs:
            spec_file = self.build_specs[selected_build]['file']
            
            # Create job file
            job_id = f"job_{int(time.time())}"
            job_file = f"/tmp/zforge/queue/{job_id}.job"
            
            try:
                with open(job_file, 'w') as f:
                    f.write(spec_file)
                
                self.append_output(f"✅ Build queued: {selected_build}\n", 'info')
                self.update_queue_display()
                
            except Exception as e:
                self.append_output(f"❌ Failed to queue build: {str(e)}\n", 'error')

    def update_queue_display(self):
        """Update the queue display"""
        try:
            queue_dir = Path("/tmp/zforge/queue")
            if queue_dir.exists():
                jobs = list(queue_dir.glob("*.job"))
                queue_text = f"Queued builds: {len(jobs)}\n\n"
                
                for job in sorted(jobs):
                    with open(job, 'r') as f:
                        spec = f.read().strip()
                    queue_text += f"• {job.stem}: {spec}\n"
                
                self.queue_display.delete(1.0, tk.END)
                self.queue_display.insert(1.0, queue_text)
            
        except Exception as e:
            pass

    def update_container_status(self):
        """Update container status display"""
        if not DOCKER_AVAILABLE:
            self.container_status_label.config(text="❌ Docker: Library Missing")
            self.always_on_status_label.config(text="❌ Install python3-docker")
        elif self.docker_client:
            try:
                # Check if container exists
                try:
                    self.docker_client.images.get('zforge:latest')
                    container_ready = "✅ Container: Ready"
                except:
                    container_ready = "⚪ Container: Not Built"
                
                # Check always-on status
                always_on_text = "✅ Always-On: Running" if self.always_on_enabled else "⚪ Always-On: Stopped"
                
                self.container_status_label.config(text=container_ready)
                self.always_on_status_label.config(text=always_on_text)
                
            except Exception as e:
                self.container_status_label.config(text="❌ Docker Error")
                self.always_on_status_label.config(text="❌ Service Error")
        else:
            self.container_status_label.config(text="❌ Docker: Not Available")
            self.always_on_status_label.config(text="❌ Always-On: Unavailable")
        
        # Schedule next update
        self.root.after(5000, self.update_container_status)
        self.update_queue_display()

def main():
    """Main function"""
    # Check if we're in the Z-FORGE directory
    if not Path('build.py').exists():
        messagebox.showerror(
            "Wrong Directory", 
            "Please run this GUI from the Z-FORGE root directory\n"
            "(where build.py is located)"
        )
        return
        
    # Create and run enhanced GUI
    root = tk.Tk()
    app = ZForgeGUIEnhanced(root)
    
    # Handle window close
    def on_closing():
        if app.build_running:
            if messagebox.askyesno("Build Running", "A build is in progress. Stop and exit?"):
                app.stop_build()
                root.after(1000, root.destroy)
            else:
                return
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()