#!/usr/bin/env python3
"""
Z-FORGE HPC Compilation UI Handler for Calamares
Manages the display and interaction during extended compilation sessions
"""

import os
import sys
import time
import threading
import subprocess
import queue
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Try Qt5 for Calamares GUI, fallback to curses for TUI
try:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                 QTextEdit, QProgressBar, QLabel,
                                 QPushButton, QTabWidget, QGroupBox,
                                 QComboBox, QCheckBox, QSplitter)
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

import curses
import curses.panel

class CompilationPhase(Enum):
    """Compilation phases for HPC drivers"""
    PREPARING = "Preparing compilation environment"
    DETECTING = "Detecting hardware"
    CUDA = "Compiling CUDA for Tesla GPUs"
    INTEL_PHI = "Compiling Intel Xeon Phi drivers"
    MELLANOX = "Compiling Mellanox OFED"
    SCIENTIFIC = "Compiling scientific libraries"
    PYTHON = "Building Python HPC stack"
    OPTIMIZING = "Applying hardware optimizations"
    VALIDATING = "Validating compilation"
    COMPLETE = "Compilation complete"
    FAILED = "Compilation failed"

@dataclass
class CompilationStatus:
    """Status of current compilation"""
    phase: CompilationPhase
    component: str
    progress: float  # 0.0 to 100.0
    elapsed_time: int  # seconds
    estimated_remaining: int  # seconds
    current_file: str
    warnings: int
    errors: int
    cpu_usage: float
    memory_usage: float
    temperature: float
    compilation_speed: float  # files per minute
    log_tail: List[str]  # last 20 lines of output

class CompilationProgressParser:
    """Parse compilation output to extract progress"""
    
    def __init__(self):
        self.patterns = {
            # GCC/G++ compilation
            r'\[(\d+)/(\d+)\]': self._parse_make_progress,
            r'(\d+)%\s+\[': self._parse_percentage,
            r'Compiling\s+(\S+)': self._parse_current_file,
            r'Building CXX object\s+(\S+)': self._parse_cmake_file,
            
            # CUDA compilation
            r'nvcc.*?(\S+\.cu)': self._parse_cuda_file,
            r'ptxas info\s+:\s+Compiling entry function': self._parse_cuda_kernel,
            
            # Intel compiler
            r'icpc.*?(\S+\.cpp)': self._parse_intel_file,
            r'ifort.*?(\S+\.f90)': self._parse_fortran_file,
            
            # Errors and warnings
            r'error:': self._count_error,
            r'warning:': self._count_warning,
            r'fatal error:': self._count_fatal,
            
            # Configure/cmake progress
            r'-- Checking for.*?(\S+)': self._parse_configure,
            r'-- Found\s+(\S+)': self._parse_found_lib,
        }
        
        self.current_file = ""
        self.total_files = 0
        self.completed_files = 0
        self.warnings = 0
        self.errors = 0
        
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a compilation output line"""
        for pattern, handler in self.patterns.items():
            match = re.search(pattern, line)
            if match:
                return handler(match)
        return None
    
    def _parse_make_progress(self, match) -> Dict:
        self.completed_files = int(match.group(1))
        self.total_files = int(match.group(2))
        progress = (self.completed_files / self.total_files * 100) if self.total_files > 0 else 0
        return {'progress': progress, 'files': f"{self.completed_files}/{self.total_files}"}
    
    def _parse_percentage(self, match) -> Dict:
        return {'progress': float(match.group(1))}
    
    def _parse_current_file(self, match) -> Dict:
        self.current_file = match.group(1)
        return {'current_file': self.current_file}
    
    def _parse_cmake_file(self, match) -> Dict:
        self.current_file = match.group(1)
        return {'current_file': self.current_file, 'type': 'cmake'}
    
    def _parse_cuda_file(self, match) -> Dict:
        self.current_file = match.group(1)
        return {'current_file': self.current_file, 'type': 'cuda'}
    
    def _parse_cuda_kernel(self, match) -> Dict:
        return {'status': 'Compiling CUDA kernel'}
    
    def _parse_intel_file(self, match) -> Dict:
        self.current_file = match.group(1)
        return {'current_file': self.current_file, 'type': 'intel'}
    
    def _parse_fortran_file(self, match) -> Dict:
        self.current_file = match.group(1)
        return {'current_file': self.current_file, 'type': 'fortran'}
    
    def _count_error(self, match) -> Dict:
        self.errors += 1
        return {'errors': self.errors, 'type': 'error'}
    
    def _count_warning(self, match) -> Dict:
        self.warnings += 1
        return {'warnings': self.warnings, 'type': 'warning'}
    
    def _count_fatal(self, match) -> Dict:
        self.errors += 1
        return {'errors': self.errors, 'type': 'fatal', 'fatal': True}
    
    def _parse_configure(self, match) -> Dict:
        return {'status': f"Checking {match.group(1)}"}
    
    def _parse_found_lib(self, match) -> Dict:
        return {'status': f"Found {match.group(1)}", 'library': match.group(1)}

class CompilationUIHandler:
    """Main handler for compilation UI during installation"""
    
    def __init__(self, use_gui=True):
        self.use_gui = use_gui and GUI_AVAILABLE
        self.status = CompilationStatus(
            phase=CompilationPhase.PREPARING,
            component="Initialization",
            progress=0.0,
            elapsed_time=0,
            estimated_remaining=0,
            current_file="",
            warnings=0,
            errors=0,
            cpu_usage=0.0,
            memory_usage=0.0,
            temperature=0.0,
            compilation_speed=0.0,
            log_tail=[]
        )
        
        self.parser = CompilationProgressParser()
        self.compilation_process = None
        self.monitoring_thread = None
        self.output_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.start_time = time.time()
        
        # Compilation zones with time estimates (minutes)
        self.compilation_zones = [
            ("cuda", "NVIDIA Tesla CUDA", 45),
            ("intel_phi", "Intel Xeon Phi", 60),
            ("mellanox", "Mellanox OFED", 30),
            ("scientific", "Scientific Libraries", 40),
            ("python", "Python HPC Stack", 35),
            ("optimization", "Hardware Optimization", 20),
        ]
        
        self.current_zone_index = 0
        self.zone_start_time = None
        
    def start_compilation(self, hardware_profile: Dict) -> bool:
        """Start the compilation process based on detected hardware"""
        self.status.phase = CompilationPhase.DETECTING
        self.hardware_profile = hardware_profile
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self._monitor_system)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        # Start compilation in background
        compilation_thread = threading.Thread(
            target=self._run_compilation,
            args=(hardware_profile,)
        )
        compilation_thread.daemon = True
        compilation_thread.start()
        
        return True
    
    def _run_compilation(self, hardware_profile: Dict):
        """Run the actual compilation process"""
        try:
            # Determine which zones to compile based on hardware
            zones_to_compile = self._select_compilation_zones(hardware_profile)
            
            for zone_id, zone_name, estimated_time in zones_to_compile:
                if self.stop_event.is_set():
                    break
                    
                self.current_zone_index += 1
                self.zone_start_time = time.time()
                self.status.component = zone_name
                
                # Update phase based on zone
                if zone_id == "cuda":
                    self.status.phase = CompilationPhase.CUDA
                elif zone_id == "intel_phi":
                    self.status.phase = CompilationPhase.INTEL_PHI
                elif zone_id == "mellanox":
                    self.status.phase = CompilationPhase.MELLANOX
                elif zone_id == "scientific":
                    self.status.phase = CompilationPhase.SCIENTIFIC
                elif zone_id == "python":
                    self.status.phase = CompilationPhase.PYTHON
                elif zone_id == "optimization":
                    self.status.phase = CompilationPhase.OPTIMIZING
                
                # Run compilation for this zone
                success = self._compile_zone(zone_id, zone_name, hardware_profile)
                
                if not success and zone_id in ["cuda", "intel_phi", "mellanox"]:
                    # Critical zone failed
                    self.status.phase = CompilationPhase.FAILED
                    self._handle_compilation_failure(zone_id, zone_name)
                    break
            
            if not self.stop_event.is_set() and self.status.phase != CompilationPhase.FAILED:
                self.status.phase = CompilationPhase.VALIDATING
                self._validate_compilation()
                self.status.phase = CompilationPhase.COMPLETE
                
        except Exception as e:
            self.status.phase = CompilationPhase.FAILED
            self.status.log_tail.append(f"Fatal error: {str(e)}")
    
    def _select_compilation_zones(self, hardware_profile: Dict) -> List[Tuple]:
        """Select which zones to compile based on hardware"""
        zones = []
        
        if hardware_profile.get('tesla_k40') or hardware_profile.get('tesla_k80'):
            zones.append(("cuda", "NVIDIA Tesla CUDA", 45))
        
        if hardware_profile.get('xeon_phi'):
            zones.append(("intel_phi", "Intel Xeon Phi", 60))
        
        if hardware_profile.get('mellanox'):
            zones.append(("mellanox", "Mellanox OFED", 30))
        
        # Always compile scientific libraries for HPC
        zones.append(("scientific", "Scientific Libraries", 40))
        zones.append(("python", "Python HPC Stack", 35))
        zones.append(("optimization", "Hardware Optimization", 20))
        
        return zones
    
    def _compile_zone(self, zone_id: str, zone_name: str, hardware_profile: Dict) -> bool:
        """Compile a specific zone"""
        script_path = f"/tmp/zforge_compile_{zone_id}.sh"
        
        # Create compilation script
        self._create_compilation_script(script_path, zone_id, hardware_profile)
        
        # Run compilation with output capture
        try:
            process = subprocess.Popen(
                ['bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.compilation_process = process
            
            # Process output line by line
            for line in iter(process.stdout.readline, ''):
                if self.stop_event.is_set():
                    process.terminate()
                    break
                
                while self.pause_event.is_set():
                    time.sleep(0.1)
                
                # Parse line for progress
                parsed = self.parser.parse_line(line.strip())
                if parsed:
                    self._update_status_from_parse(parsed)
                
                # Update log tail
                self.status.log_tail.append(line.strip())
                if len(self.status.log_tail) > 20:
                    self.status.log_tail.pop(0)
                
                # Put in queue for UI update
                self.output_queue.put(line.strip())
            
            process.wait()
            return process.returncode == 0
            
        except Exception as e:
            self.status.log_tail.append(f"Compilation error: {str(e)}")
            return False
    
    def _create_compilation_script(self, script_path: str, zone_id: str, hardware_profile: Dict):
        """Create a compilation script for a specific zone"""
        script_content = f"""#!/bin/bash
set -euo pipefail

# Z-FORGE HPC Compilation - Zone: {zone_id}
export MAKEFLAGS="-j$(nproc)"
export CCACHE_DIR=/tmp/ccache

echo "[1/100] Starting {zone_id} compilation..."

"""
        
        if zone_id == "cuda":
            script_content += self._get_cuda_compilation_script(hardware_profile)
        elif zone_id == "intel_phi":
            script_content += self._get_intel_phi_compilation_script(hardware_profile)
        elif zone_id == "mellanox":
            script_content += self._get_mellanox_compilation_script(hardware_profile)
        elif zone_id == "scientific":
            script_content += self._get_scientific_compilation_script()
        elif zone_id == "python":
            script_content += self._get_python_compilation_script()
        elif zone_id == "optimization":
            script_content += self._get_optimization_script(hardware_profile)
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
    
    def _get_cuda_compilation_script(self, hardware_profile: Dict) -> str:
        """Get CUDA compilation script for Tesla GPUs"""
        compute_cap = "3.5" if hardware_profile.get('tesla_k40') else "3.7"
        return f"""
# CUDA compilation for Tesla
cd /tmp/zforge_sources/cuda
export CUDA_ARCH="-gencode arch=compute_{compute_cap.replace('.', '')},code=sm_{compute_cap.replace('.', '')}"

echo "[10/100] Extracting CUDA toolkit..."
sh cuda_11.8.0_linux.run --extract=/tmp/cuda_extract

echo "[20/100] Installing CUDA toolkit..."
cd /tmp/cuda_extract
./cuda-installer --silent --toolkit --installpath=/opt/cuda-11.8

echo "[40/100] Installing NVIDIA driver..."
./NVIDIA-Linux-x86_64-470.223.02.run --silent --no-opengl-files

echo "[60/100] Building CUDA samples..."
cd /opt/cuda-11.8/samples
make -j$(nproc)

echo "[80/100] Configuring CUDA environment..."
echo 'export PATH=/opt/cuda-11.8/bin:$PATH' >> /etc/profile.d/cuda.sh
echo 'export LD_LIBRARY_PATH=/opt/cuda-11.8/lib64:$LD_LIBRARY_PATH' >> /etc/profile.d/cuda.sh

echo "[100/100] CUDA compilation complete"
"""
    
    def _get_intel_phi_compilation_script(self, hardware_profile: Dict) -> str:
        """Get Intel Xeon Phi compilation script"""
        return """
# Intel Xeon Phi compilation
cd /tmp/zforge_sources/intel

echo "[10/100] Extracting Intel Parallel Studio..."
tar -xzf parallel_studio_xe_2020.4.912.tar.gz

echo "[30/100] Installing Intel compilers..."
cd parallel_studio_xe_2020.4.912
./install.sh --silent --accept-eula

echo "[50/100] Installing MPSS..."
tar -xf mpss-4.7.1.tar
cd mpss-4.7.1
./install.sh --silent

echo "[70/100] Configuring Xeon Phi environment..."
source /opt/intel/bin/compilervars.sh intel64

echo "[90/100] Building MIC libraries..."
icc -mmic -O3 -o test_mic test.c

echo "[100/100] Intel Xeon Phi compilation complete"
"""
    
    def _get_mellanox_compilation_script(self, hardware_profile: Dict) -> str:
        """Get Mellanox OFED compilation script"""
        return """
# Mellanox OFED compilation
cd /tmp/zforge_sources/mellanox

echo "[10/100] Extracting Mellanox OFED..."
tar -xzf MLNX_OFED_LINUX-5.8.tar.gz

echo "[30/100] Installing OFED..."
cd MLNX_OFED_LINUX-5.8
./mlnxofedinstall --force --without-fw-update

echo "[60/100] Configuring RoCE..."
mlxconfig -d /dev/mst/mt*_pciconf0 set ROCE_ENABLE=1

echo "[80/100] Starting OpeniB..."
/etc/init.d/openibd start

echo "[100/100] Mellanox OFED compilation complete"
"""
    
    def _get_scientific_compilation_script(self) -> str:
        """Get scientific libraries compilation script"""
        return """
# Scientific libraries compilation
cd /tmp/zforge_sources/scientific

echo "[10/100] Building OpenMPI..."
tar -xzf openmpi-4.1.5.tar.gz
cd openmpi-4.1.5
./configure --prefix=/opt/openmpi --enable-mpi-cxx --with-cuda=/opt/cuda-11.8
make -j$(nproc) && make install

echo "[30/100] Building FFTW..."
cd ../
tar -xzf fftw-3.3.10.tar.gz
cd fftw-3.3.10
./configure --prefix=/opt/fftw --enable-openmp --enable-threads --enable-avx2
make -j$(nproc) && make install

echo "[50/100] Building OpenBLAS..."
cd ../
tar -xzf OpenBLAS-0.3.24.tar.gz
cd OpenBLAS-0.3.24
make -j$(nproc) TARGET=HASWELL USE_OPENMP=1
make install PREFIX=/opt/openblas

echo "[70/100] Building ScaLAPACK..."
cd ../
tar -xzf scalapack-2.2.0.tgz
cd scalapack-2.2.0
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/opt/scalapack
make -j$(nproc) && make install

echo "[100/100] Scientific libraries compilation complete"
"""
    
    def _get_python_compilation_script(self) -> str:
        """Get Python HPC stack compilation script"""
        return """
# Python HPC stack compilation
cd /tmp/zforge_sources/python

echo "[10/100] Installing Anaconda..."
bash Anaconda3-2023.09-0-Linux-x86_64.sh -b -p /opt/anaconda3

echo "[30/100] Creating HPC environment..."
/opt/anaconda3/bin/conda create -n hpc python=3.11 -y

echo "[50/100] Installing HPC packages..."
/opt/anaconda3/bin/conda activate hpc
pip install --no-index --find-links ./python_packages/ -r requirements_hpc.txt

echo "[80/100] Installing CuPy for CUDA..."
pip install cupy-cuda11x --no-index --find-links ./python_packages/

echo "[100/100] Python HPC stack compilation complete"
"""
    
    def _get_optimization_script(self, hardware_profile: Dict) -> str:
        """Get hardware optimization script"""
        cpu_flags = "-march=native"
        if hardware_profile.get('avx512'):
            cpu_flags += " -mavx512f"
        elif hardware_profile.get('avx2'):
            cpu_flags += " -mavx2"
        
        return f"""
# Hardware optimization
echo "[10/100] Detecting CPU features..."
export CFLAGS="{cpu_flags} -O3 -pipe"
export CXXFLAGS="$CFLAGS"

echo "[30/100] Optimizing system libraries..."
ldconfig /opt/cuda-11.8/lib64
ldconfig /opt/openmpi/lib
ldconfig /opt/fftw/lib
ldconfig /opt/openblas/lib

echo "[50/100] Setting up environment modules..."
cat > /etc/profile.d/hpc_env.sh << 'EOF'
export PATH=/opt/openmpi/bin:/opt/cuda-11.8/bin:$PATH
export LD_LIBRARY_PATH=/opt/openmpi/lib:/opt/cuda-11.8/lib64:/opt/fftw/lib:/opt/openblas/lib:$LD_LIBRARY_PATH
export CFLAGS="{cpu_flags} -O3"
export CXXFLAGS="$CFLAGS"
EOF

echo "[70/100] Configuring NUMA optimization..."
numactl --hardware > /etc/numa.conf

echo "[90/100] Setting up GPU persistence..."
nvidia-smi -pm 1

echo "[100/100] Hardware optimization complete"
"""
    
    def _monitor_system(self):
        """Monitor system resources during compilation"""
        while not self.stop_event.is_set():
            try:
                # Update elapsed time
                self.status.elapsed_time = int(time.time() - self.start_time)
                
                # Get CPU usage
                with open('/proc/stat', 'r') as f:
                    cpu_line = f.readline()
                    cpu_vals = [int(x) for x in cpu_line.split()[1:8]]
                    idle = cpu_vals[3]
                    total = sum(cpu_vals)
                    self.status.cpu_usage = 100.0 * (1.0 - idle/total) if total > 0 else 0
                
                # Get memory usage
                with open('/proc/meminfo', 'r') as f:
                    lines = f.readlines()
                    total_mem = int(lines[0].split()[1])
                    free_mem = int(lines[1].split()[1])
                    self.status.memory_usage = 100.0 * (1.0 - free_mem/total_mem) if total_mem > 0 else 0
                
                # Get temperature (if available)
                try:
                    with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                        self.status.temperature = float(f.read().strip()) / 1000.0
                except:
                    self.status.temperature = 0.0
                
                # Calculate compilation speed
                if self.parser.completed_files > 0 and self.status.elapsed_time > 0:
                    self.status.compilation_speed = (self.parser.completed_files / self.status.elapsed_time) * 60
                
                # Estimate remaining time
                if self.status.progress > 0:
                    total_estimated = self.status.elapsed_time / (self.status.progress / 100.0)
                    self.status.estimated_remaining = int(total_estimated - self.status.elapsed_time)
                
            except Exception as e:
                pass  # Silently ignore monitoring errors
            
            time.sleep(1)
    
    def _update_status_from_parse(self, parsed: Dict):
        """Update status from parsed compilation output"""
        if 'progress' in parsed:
            self.status.progress = parsed['progress']
        if 'current_file' in parsed:
            self.status.current_file = parsed['current_file']
        if 'warnings' in parsed:
            self.status.warnings = parsed['warnings']
        if 'errors' in parsed:
            self.status.errors = parsed['errors']
        if 'fatal' in parsed and parsed['fatal']:
            self.status.phase = CompilationPhase.FAILED
    
    def _handle_compilation_failure(self, zone_id: str, zone_name: str):
        """Handle compilation failure for a zone"""
        error_msg = f"Failed to compile {zone_name}"
        self.status.log_tail.append(error_msg)
        
        # Try to determine failure reason
        if self.status.errors > 0:
            if "out of memory" in " ".join(self.status.log_tail).lower():
                error_msg += " - Out of memory. Try reducing parallel jobs."
            elif "permission denied" in " ".join(self.status.log_tail).lower():
                error_msg += " - Permission issue. Check installation privileges."
            elif "not found" in " ".join(self.status.log_tail).lower():
                error_msg += " - Missing dependencies. Check source files."
        
        self.status.log_tail.append(error_msg)
    
    def _validate_compilation(self):
        """Validate the compilation results"""
        validation_script = """#!/bin/bash
# Validate HPC compilation
errors=0

# Check CUDA
if [ -d /opt/cuda-11.8 ]; then
    echo "CUDA installation verified"
else
    echo "ERROR: CUDA not found"
    ((errors++))
fi

# Check OpenMPI
if [ -f /opt/openmpi/bin/mpirun ]; then
    echo "OpenMPI installation verified"
else
    echo "ERROR: OpenMPI not found"
    ((errors++))
fi

# Check Python HPC
if /opt/anaconda3/bin/conda list -n hpc | grep -q numpy; then
    echo "Python HPC stack verified"
else
    echo "ERROR: Python HPC stack not found"
    ((errors++))
fi

exit $errors
"""
        
        with open('/tmp/validate_hpc.sh', 'w') as f:
            f.write(validation_script)
        os.chmod('/tmp/validate_hpc.sh', 0o755)
        
        result = subprocess.run(['/tmp/validate_hpc.sh'], capture_output=True, text=True)
        self.status.log_tail.extend(result.stdout.strip().split('\n'))
        
        if result.returncode != 0:
            self.status.phase = CompilationPhase.FAILED
            self.status.log_tail.append(f"Validation failed with {result.returncode} errors")
    
    def pause_compilation(self):
        """Pause the compilation process"""
        self.pause_event.set()
        if self.compilation_process:
            os.kill(self.compilation_process.pid, signal.SIGSTOP)
    
    def resume_compilation(self):
        """Resume the compilation process"""
        self.pause_event.clear()
        if self.compilation_process:
            os.kill(self.compilation_process.pid, signal.SIGCONT)
    
    def stop_compilation(self):
        """Stop the compilation process"""
        self.stop_event.set()
        if self.compilation_process:
            self.compilation_process.terminate()
            time.sleep(2)
            if self.compilation_process.poll() is None:
                self.compilation_process.kill()
    
    def get_status(self) -> CompilationStatus:
        """Get current compilation status"""
        return self.status
    
    def get_log_tail(self) -> List[str]:
        """Get the last lines of compilation output"""
        return self.status.log_tail

# Main execution for testing
if __name__ == "__main__":
    print("Z-FORGE HPC Compilation UI Handler")
    print("This module is designed to be used by Calamares installer")
    print("Testing compilation progress parser...")
    
    parser = CompilationProgressParser()
    test_lines = [
        "[10/100] Compiling test.cpp",
        "Building CXX object src/CMakeFiles/test.dir/main.cpp.o",
        "nvcc -O3 kernel.cu",
        "error: undefined reference to 'cuda_init'",
        "warning: unused variable 'x'",
        "50% [=============>      ]"
    ]
    
    for line in test_lines:
        result = parser.parse_line(line)
        if result:
            print(f"Parsed: {line} -> {result}")