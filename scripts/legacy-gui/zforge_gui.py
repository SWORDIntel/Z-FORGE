#!/usr/bin/env python3
"""
Z-FORGE GUI Builder
A graphical interface for selecting and configuring Z-FORGE builds
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import subprocess
import os
import sys
import yaml
import multiprocessing
from pathlib import Path
from typing import Dict, List, Optional
import psutil

class ZForgeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Z-FORGE RAM Server Build System v3.0")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # Apply dark theme
        self.setup_dark_theme()
        
        # Build specifications mapping - ALL RAM-BASED SERVER BUILDS WITH PROXMOX VE 9
        self.build_specs = {
            "Outside Packages Build (Fastest - 95% Success)": {
                "file": "build_specs/build_spec_outside_packages.yml", 
                "description": "RAM-based server build with prebuilt packages. Full Proxmox VE 9 + ZFS 2.3.3 on Debian Trixie.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "ZFS 2.3.3 + encryption", "Debian Trixie base"]
            },
            "Minimal Proxmox Build (90% Success)": {
                "file": "build_specs/build_spec_minimal_proxmox.yml",
                "description": "RAM-based server build with minimal Proxmox components. Fastest full server deployment.",
                "features": ["RAM workspace (/dev/shm)", "Minimal Proxmox VE 9", "ZFS 2.3.3 + compression", "Optimized performance"]
            },
            "TMPFS High Performance Build (85% Success)": {
                "file": "build_specs/build_spec_tmpfs.yml",
                "description": "Full RAM-based server build for maximum performance. Complete Proxmox VE 9 infrastructure.",
                "features": ["Full RAM filesystem", "Complete Proxmox VE 9", "3-5x build speed", "Enterprise features"]
            },
            "Working Server Build (85% Success)": {
                "file": "build_specs/build_spec_working.yml",
                "description": "Proven RAM-based server configuration. Full Proxmox VE 9 with all ZFS features.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "ZFS encryption + compression", "Hardware optimization"]
            },
            "No /tmp Server Build (80% Success)": {
                "file": "build_specs/build_spec_no_tmp.yml",
                "description": "RAM-based server avoiding /tmp usage. Full Proxmox VE 9 with workspace isolation.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "Workspace isolation", "Permission handling"]
            },
            "Proxmox 9 Server Build (75% Success)": {
                "file": "build_specs/build_spec_proxmox9.yml", 
                "description": "RAM-based specialized Proxmox VE 9 server build. Enterprise clustering and networking.",
                "features": ["RAM workspace (/dev/shm)", "Proxmox VE 9.0 server", "Enterprise clustering", "Advanced networking"]
            },
            "Proxmox Full Server Build (75% Success)": {
                "file": "build_specs/build_spec_proxmox_full.yml",
                "description": "RAM-based complete Proxmox integration. Full enterprise server with all features.",
                "features": ["RAM workspace (/dev/shm)", "Complete Proxmox suite", "High availability server", "Management interfaces"]
            },
            "Full Featured Server Build (70% Success)": {
                "file": "build_specs/build_spec.yml",
                "description": "RAM-based complete server distribution. Full Proxmox VE 9 with all enterprise features.",
                "features": ["RAM workspace (/dev/shm)", "Full Proxmox VE 9 server", "Complete ZFS suite", "All bootloaders"]
            },
            "Trixie Clean Server Build (60% Success)": {
                "file": "build_specs/build_spec_trixie_clean.yml",
                "description": "RAM-based clean Debian Trixie server. Latest packages with full Proxmox VE 9 integration.",
                "features": ["RAM workspace (/dev/shm)", "Debian Trixie server", "Latest kernel 6.14.8", "Full Proxmox VE 9"]
            }
        }
        
        # System info
        self.cpu_count = multiprocessing.cpu_count()
        self.memory_gb = round(psutil.virtual_memory().total / (1024**3))
        self.disk_free_gb = round(psutil.disk_usage('/').free / (1024**3))
        
        # Build process
        self.build_process = None
        self.build_running = False
        
        self.setup_ui()
        self.check_system_status()
        
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
            'accent': '#7C4DFF'        # Accent purple
        }
        
        # Configure root window
        self.root.configure(bg=self.colors['bg'])
        
        # Configure ttk style
        self.style = ttk.Style()
        
        # Configure notebook (tabs)
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
        
        # Configure frames
        self.style.configure('TFrame',
                           background=self.colors['frame_bg'],
                           borderwidth=0)
        
        # Configure labels
        self.style.configure('TLabel',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        
        # Configure buttons
        self.style.configure('TButton',
                           background=self.colors['button_bg'],
                           foreground=self.colors['button_fg'],
                           borderwidth=1,
                           relief='flat',
                           padding=6)
        self.style.map('TButton',
                      background=[('active', self.colors['button_active']),
                                ('pressed', self.colors['select_bg'])])
        
        # Accent button style
        self.style.configure('Accent.TButton',
                           background=self.colors['accent'],
                           foreground='white',
                           borderwidth=0,
                           relief='flat',
                           padding=8)
        self.style.map('Accent.TButton',
                      background=[('active', '#9C6FFF'),
                                ('pressed', '#6C3FFF')])
        
        # Success button style
        self.style.configure('Success.TButton',
                           background=self.colors['success'],
                           foreground='white',
                           borderwidth=0,
                           relief='flat',
                           padding=8)
        
        # Configure entry widgets
        self.style.configure('TEntry',
                           fieldbackground=self.colors['entry_bg'],
                           background=self.colors['entry_bg'],
                           foreground=self.colors['entry_fg'],
                           insertcolor=self.colors['fg'],
                           borderwidth=1)
        
        # Configure radio buttons
        self.style.configure('TRadiobutton',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'],
                           focuscolor='none')
        self.style.map('TRadiobutton',
                      background=[('active', self.colors['frame_bg'])])
        
        # Configure checkbuttons
        self.style.configure('TCheckbutton',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'],
                           focuscolor='none')
        
        # Configure label frames
        self.style.configure('TLabelframe',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'],
                           bordercolor=self.colors['select_bg'],
                           relief='solid',
                           borderwidth=1)
        self.style.configure('TLabelframe.Label',
                           background=self.colors['frame_bg'],
                           foreground=self.colors['fg'])
        
        # Configure scrollbar
        self.style.configure('Vertical.TScrollbar',
                           background=self.colors['button_bg'],
                           bordercolor=self.colors['button_bg'],
                           arrowcolor=self.colors['fg'],
                           troughcolor=self.colors['bg'])
        
        # Configure progressbar
        self.style.configure('TProgressbar',
                           background=self.colors['accent'],
                           troughcolor=self.colors['button_bg'],
                           borderwidth=0,
                           lightcolor=self.colors['accent'],
                           darkcolor=self.colors['accent'])
        
        # Configure scale (slider)
        self.style.configure('TScale',
                           background=self.colors['frame_bg'],
                           troughcolor=self.colors['button_bg'],
                           slidercolor=self.colors['accent'],
                           borderwidth=0)
        self.style.map('TScale',
                      slidercolor=[('active', '#9C6FFF')])
        
        # Configure spinbox
        self.style.configure('TSpinbox',
                           fieldbackground=self.colors['entry_bg'],
                           background=self.colors['entry_bg'],
                           foreground=self.colors['entry_fg'],
                           arrowcolor=self.colors['fg'],
                           borderwidth=1)
        
    def setup_ui(self):
        """Setup the main user interface"""
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Build Selection Tab
        self.build_frame = ttk.Frame(notebook)
        notebook.add(self.build_frame, text="Build Selection")
        self.setup_build_selection()
        
        # Configuration Tab
        self.config_frame = ttk.Frame(notebook)
        notebook.add(self.config_frame, text="Configuration")
        self.setup_configuration()
        
        # System Status Tab
        self.status_frame = ttk.Frame(notebook)
        notebook.add(self.status_frame, text="System Status")
        self.setup_system_status()
        
        # Build Output Tab
        self.output_frame = ttk.Frame(notebook)
        notebook.add(self.output_frame, text="Build Output")
        self.setup_build_output()
        
    def setup_build_selection(self):
        """Setup build selection interface"""
        # Title
        title_label = ttk.Label(self.build_frame, text="Select RAM Server Build Type", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Build type selection
        self.selected_build = tk.StringVar(value="Outside Packages Build (Fastest - 95% Success)")
        
        # Create scrollable frame for build options
        canvas = tk.Canvas(
            self.build_frame,
            bg=self.colors['frame_bg'],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(self.build_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Build option cards
        for build_name, build_info in self.build_specs.items():
            self.create_build_card(scrollable_frame, build_name, build_info)
            
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Build button
        build_button_frame = ttk.Frame(self.build_frame)
        build_button_frame.pack(fill='x', pady=10)
        
        self.build_button = ttk.Button(
            build_button_frame, 
            text="Start Build", 
            command=self.start_build,
            style='Accent.TButton'
        )
        self.build_button.pack(side='right', padx=10)
        
        self.stop_button = ttk.Button(
            build_button_frame,
            text="Stop Build", 
            command=self.stop_build,
            state='disabled'
        )
        self.stop_button.pack(side='right', padx=5)
        
    def create_build_card(self, parent, build_name, build_info):
        """Create a build selection card"""
        # Main card frame
        card_frame = ttk.LabelFrame(parent, text="", padding=10)
        card_frame.pack(fill='x', pady=5, padx=10)
        
        # Radio button and title
        header_frame = ttk.Frame(card_frame)
        header_frame.pack(fill='x', pady=(0, 5))
        
        radio = ttk.Radiobutton(
            header_frame,
            text=build_name,
            variable=self.selected_build,
            value=build_name,
            command=self.on_build_selection_change
        )
        radio.pack(side='left')
        
        # File info
        file_label = ttk.Label(header_frame, text=f"({build_info['file']})", foreground='gray')
        file_label.pack(side='right')
        
        # Description
        desc_label = ttk.Label(card_frame, text=build_info['description'], wraplength=600)
        desc_label.pack(fill='x', pady=(0, 5))
        
        # Features
        features_frame = ttk.Frame(card_frame)
        features_frame.pack(fill='x')
        
        ttk.Label(features_frame, text="Features:", font=('Arial', 9, 'bold')).pack(anchor='w')
        
        for feature in build_info['features']:
            feature_label = ttk.Label(features_frame, text=f"• {feature}", font=('Arial', 8))
            feature_label.pack(anchor='w', padx=(10, 0))
            
    def setup_configuration(self):
        """Setup build configuration interface"""
        # Title
        title_label = ttk.Label(self.config_frame, text="RAM Server Build Configuration", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Configuration notebook
        config_notebook = ttk.Notebook(self.config_frame)
        config_notebook.pack(fill='both', expand=True, padx=10)
        
        # Performance settings
        perf_frame = ttk.Frame(config_notebook)
        config_notebook.add(perf_frame, text="Performance")
        self.setup_performance_config(perf_frame)
        
        # Advanced settings
        advanced_frame = ttk.Frame(config_notebook)
        config_notebook.add(advanced_frame, text="Advanced")
        self.setup_advanced_config(advanced_frame)
        
    def setup_performance_config(self, parent):
        """Setup performance configuration"""
        # CPU Cores/Jobs
        cpu_frame = ttk.LabelFrame(parent, text="CPU Configuration", padding=10)
        cpu_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(cpu_frame, text=f"System has {self.cpu_count} CPU cores").pack(anchor='w')
        
        # Jobs slider
        jobs_frame = ttk.Frame(cpu_frame)
        jobs_frame.pack(fill='x', pady=5)
        
        ttk.Label(jobs_frame, text="Parallel Jobs (-j):").pack(side='left')
        
        self.jobs_var = tk.IntVar(value=min(4, self.cpu_count))
        self.jobs_scale = ttk.Scale(
            jobs_frame,
            from_=1,
            to=self.cpu_count,
            variable=self.jobs_var,
            orient='horizontal',
            command=self.update_jobs_label
        )
        self.jobs_scale.pack(side='left', fill='x', expand=True, padx=10)
        
        self.jobs_label = ttk.Label(jobs_frame, text=str(self.jobs_var.get()))
        self.jobs_label.pack(side='right')
        
        # Memory usage
        mem_frame = ttk.LabelFrame(parent, text="Memory Usage", padding=10)
        mem_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(mem_frame, text=f"System has {self.memory_gb} GB RAM").pack(anchor='w')
        
        self.low_memory = tk.BooleanVar()
        ttk.Checkbutton(
            mem_frame,
            text="Enable low memory mode (reduces parallel operations)",
            variable=self.low_memory
        ).pack(anchor='w', pady=5)
        
        # Storage
        storage_frame = ttk.LabelFrame(parent, text="Storage", padding=10)
        storage_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(storage_frame, text=f"Available disk space: {self.disk_free_gb} GB").pack(anchor='w')
        
        # Workspace selection
        workspace_frame = ttk.Frame(storage_frame)
        workspace_frame.pack(fill='x', pady=5)
        
        ttk.Label(workspace_frame, text="Workspace Directory:").pack(anchor='w')
        
        self.workspace_var = tk.StringVar(value="/dev/shm/zforge-workspace")  # All builds use RAM workspace
        workspace_entry = ttk.Entry(workspace_frame, textvariable=self.workspace_var, width=50)
        workspace_entry.pack(side='left', fill='x', expand=True, pady=2)
        
        ttk.Button(
            workspace_frame,
            text="Browse",
            command=self.browse_workspace
        ).pack(side='right', padx=(5, 0))
        
    def setup_advanced_config(self, parent):
        """Setup advanced configuration"""
        # Debug options
        debug_frame = ttk.LabelFrame(parent, text="Debug Options", padding=10)
        debug_frame.pack(fill='x', pady=10, padx=10)
        
        self.debug_mode = tk.BooleanVar()
        ttk.Checkbutton(
            debug_frame,
            text="Enable debug mode (verbose output)",
            variable=self.debug_mode
        ).pack(anchor='w')
        
        self.keep_temp = tk.BooleanVar()
        ttk.Checkbutton(
            debug_frame,
            text="Keep temporary files after build",
            variable=self.keep_temp
        ).pack(anchor='w')
        
        # Custom options
        custom_frame = ttk.LabelFrame(parent, text="Custom Options", padding=10)
        custom_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(custom_frame, text="Additional build arguments:").pack(anchor='w')
        self.custom_args = tk.StringVar()
        ttk.Entry(custom_frame, textvariable=self.custom_args, width=60).pack(fill='x', pady=2)
        
        # Environment variables
        env_frame = ttk.LabelFrame(parent, text="Environment Variables", padding=10)
        env_frame.pack(fill='both', expand=True, pady=10, padx=10)
        
        ttk.Label(env_frame, text="Custom environment variables (KEY=VALUE, one per line):").pack(anchor='w')
        self.env_text = scrolledtext.ScrolledText(
            env_frame, 
            height=6,
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg'],
            insertbackground=self.colors['fg'],
            selectbackground=self.colors['select_bg'],
            selectforeground=self.colors['select_fg']
        )
        self.env_text.pack(fill='both', expand=True, pady=2)
        
        # Set some useful defaults for RAM builds
        self.env_text.insert('1.0', 'MAKEFLAGS=-j4\nZFORGE_WORKSPACE=/dev/shm/zforge-workspace\nTMPDIR=/dev/shm/tmp\n')
        
    def setup_system_status(self):
        """Setup system status display"""
        # Title
        title_label = ttk.Label(self.status_frame, text="System Status", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 20))
        
        # Status display
        self.status_text = scrolledtext.ScrolledText(
            self.status_frame, 
            height=20, 
            state='disabled',
            bg=self.colors['entry_bg'],
            fg=self.colors['entry_fg'],
            insertbackground=self.colors['fg'],
            selectbackground=self.colors['select_bg'],
            selectforeground=self.colors['select_fg']
        )
        self.status_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Refresh button
        ttk.Button(
            self.status_frame,
            text="Refresh Status",
            command=self.check_system_status
        ).pack(pady=10)
        
    def setup_build_output(self):
        """Setup build output display"""
        # Title
        title_label = ttk.Label(self.output_frame, text="Build Output", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(10, 10))
        
        # Output display
        self.output_text = scrolledtext.ScrolledText(
            self.output_frame, 
            height=25, 
            state='disabled',
            bg='#0c0c0c',  # Even darker for output
            fg='#00ff00',  # Terminal green for output
            insertbackground='#00ff00',
            selectbackground=self.colors['select_bg'],
            selectforeground=self.colors['select_fg'],
            font=('Consolas', 10)  # Monospace font
        )
        self.output_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Configure text tags for colored output
        self.output_text.tag_config('error', foreground=self.colors['error'])
        self.output_text.tag_config('warning', foreground=self.colors['warning'])
        self.output_text.tag_config('success', foreground=self.colors['success'])
        self.output_text.tag_config('info', foreground=self.colors['info'])
        
        # Control buttons
        button_frame = ttk.Frame(self.output_frame)
        button_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(
            button_frame,
            text="Clear Output",
            command=self.clear_output
        ).pack(side='left')
        
        ttk.Button(
            button_frame,
            text="Save Output",
            command=self.save_output
        ).pack(side='left', padx=10)
        
    def update_jobs_label(self, value):
        """Update jobs label when slider changes"""
        self.jobs_label.config(text=str(int(float(value))))
        
    def browse_workspace(self):
        """Browse for workspace directory"""
        directory = filedialog.askdirectory(
            title="Select Workspace Directory",
            initialdir=self.workspace_var.get()
        )
        if directory:
            self.workspace_var.set(directory)
            
    def on_build_selection_change(self):
        """Handle build selection change"""
        selected = self.selected_build.get()
        # Update jobs based on build type
        if "Outside Packages" in selected or "Minimal Proxmox" in selected:
            # RAM builds can use more cores
            self.jobs_var.set(min(8, self.cpu_count))
        else:
            # Complex server builds should be conservative
            self.jobs_var.set(min(4, self.cpu_count))
            
    def check_system_status(self):
        """Check and display system status"""
        def run_status_check():
            try:
                # Run validation
                result = subprocess.run(
                    [sys.executable, 'builder/modules/build_pipeline_validator.py'],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                
                status_info = f"""
Z-FORGE System Status Report
============================

Validation Status:
{result.stdout}

System Information:
- CPU Cores: {self.cpu_count}
- Memory: {self.memory_gb} GB
- Free Disk Space: {self.disk_free_gb} GB
- Python Version: {sys.version.split()[0]}
- Current Directory: {os.getcwd()}

Build Specifications Available:
"""
                for name, info in self.build_specs.items():
                    spec_path = Path(info['file'])
                    exists = "✓" if spec_path.exists() else "✗"
                    status_info += f"{exists} {name} ({info['file']})\\n"
                    
                if result.stderr:
                    status_info += f"\\n\\nValidation Errors:\\n{result.stderr}"
                    
                # Update status display
                self.status_text.config(state='normal')
                self.status_text.delete('1.0', tk.END)
                self.status_text.insert('1.0', status_info)
                self.status_text.config(state='disabled')
                
            except Exception as e:
                error_msg = f"Error checking system status: {str(e)}"
                self.status_text.config(state='normal')
                self.status_text.delete('1.0', tk.END)
                self.status_text.insert('1.0', error_msg)
                self.status_text.config(state='disabled')
                
        # Run in thread to avoid blocking UI
        threading.Thread(target=run_status_check, daemon=True).start()
        
    def start_build(self):
        """Start the build process"""
        if self.build_running:
            messagebox.showwarning("Build Running", "A build is already in progress!")
            return
            
        # Get selected build spec
        selected_build = self.selected_build.get()
        if not selected_build:
            messagebox.showerror("No Selection", "Please select a build type!")
            return
            
        build_file = self.build_specs[selected_build]['file']
        
        # Check if build spec exists
        if not Path(build_file).exists():
            messagebox.showerror("File Not Found", f"Build specification {build_file} not found!")
            return
            
        # Confirm build start
        if not messagebox.askyesno(
            "Confirm Build", 
            f"Start {selected_build}?\\n\\nThis will:\\n"
            f"• Use build specification: {build_file}\\n"
            f"• Use {self.jobs_var.get()} parallel jobs\\n"
            f"• Workspace: {self.workspace_var.get()}\\n\\n"
            f"Continue?"
        ):
            return
            
        # Prepare build command
        cmd = [sys.executable, 'build.py', '--spec', build_file]
        
        # Add workspace if specified
        workspace = self.workspace_var.get().strip()
        if workspace:
            cmd.extend(['--workspace', workspace])
            
        # Add debug flag
        if self.debug_mode.get():
            cmd.append('--debug')
            
        # Add custom arguments
        custom_args = self.custom_args.get().strip()
        if custom_args:
            cmd.extend(custom_args.split())
            
        # Prepare environment
        env = os.environ.copy()
        env['MAKEFLAGS'] = f'-j{self.jobs_var.get()}'
        
        # Add custom environment variables
        env_text = self.env_text.get('1.0', tk.END).strip()
        for line in env_text.split('\\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env[key.strip()] = value.strip()
                
        # Start build in thread
        self.build_running = True
        self.build_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Clear output
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.insert(tk.END, f"Starting build: {' '.join(cmd)}\\n\\n")
        self.output_text.config(state='disabled')
        
        # Start build process
        threading.Thread(target=self.run_build, args=(cmd, env), daemon=True).start()
        
    def run_build(self, cmd, env):
        """Run build process in background thread"""
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
            
            # Read output line by line
            for line in iter(self.build_process.stdout.readline, ''):
                if not self.build_running:
                    break
                    
                # Update output display
                self.root.after(0, self.append_output, line)
                
            # Wait for process to complete
            self.build_process.wait()
            
            # Handle completion
            if self.build_process.returncode == 0:
                self.root.after(0, self.append_output, "\\n\\n=== BUILD COMPLETED SUCCESSFULLY ===\\n")
                self.root.after(0, messagebox.showinfo, "Build Complete", "Build completed successfully!")
            else:
                self.root.after(0, self.append_output, f"\\n\\n=== BUILD FAILED (exit code {self.build_process.returncode}) ===\\n")
                self.root.after(0, messagebox.showerror, "Build Failed", f"Build failed with exit code {self.build_process.returncode}")
                
        except Exception as e:
            self.root.after(0, self.append_output, f"\\n\\nBuild error: {str(e)}\\n")
            self.root.after(0, messagebox.showerror, "Build Error", f"Build error: {str(e)}")
            
        finally:
            # Reset UI state
            self.build_running = False
            self.build_process = None
            self.root.after(0, self.build_button.config, {'state': 'normal'})
            self.root.after(0, self.stop_button.config, {'state': 'disabled'})
            
    def stop_build(self):
        """Stop the running build process"""
        if self.build_process and self.build_running:
            if messagebox.askyesno("Confirm Stop", "Stop the running build?"):
                self.build_running = False
                try:
                    self.build_process.terminate()
                    self.append_output("\\n\\n=== BUILD STOPPED BY USER ===\\n")
                except:
                    pass
                    
    def append_output(self, text, tag=None):
        """Append text to output display with optional color tag"""
        self.output_text.config(state='normal')
        
        # Detect and apply appropriate tags based on content
        if tag:
            self.output_text.insert(tk.END, text, tag)
        elif 'ERROR' in text or 'FAILED' in text or 'Error' in text:
            self.output_text.insert(tk.END, text, 'error')
        elif 'WARNING' in text or 'Warning' in text:
            self.output_text.insert(tk.END, text, 'warning')
        elif 'SUCCESS' in text or 'COMPLETE' in text or '✓' in text or '✅' in text:
            self.output_text.insert(tk.END, text, 'success')
        elif 'INFO' in text or '===' in text:
            self.output_text.insert(tk.END, text, 'info')
        else:
            self.output_text.insert(tk.END, text)
            
        self.output_text.see(tk.END)
        self.output_text.config(state='disabled')
        
    def clear_output(self):
        """Clear the output display"""
        self.output_text.config(state='normal')
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state='disabled')
        
    def save_output(self):
        """Save output to file"""
        filename = filedialog.asksaveasfilename(
            title="Save Build Output",
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.output_text.get('1.0', tk.END))
                messagebox.showinfo("Saved", f"Output saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save output: {str(e)}")

def main():
    """Main function"""
    # Check if we're in the Z-FORGE directory
    if not Path('build.py').exists():
        messagebox.showerror(
            "Wrong Directory", 
            "Please run this GUI from the Z-FORGE root directory\\n"
            "(where build.py is located)"
        )
        return
        
    # Create and run GUI
    root = tk.Tk()
    app = ZForgeGUI(root)
    
    # Handle window close
    def on_closing():
        if app.build_running:
            if messagebox.askyesno("Build Running", "A build is in progress. Stop and exit?"):
                app.stop_build()
                root.after(1000, root.destroy)  # Give time for cleanup
            else:
                return
        else:
            root.destroy()
            
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()