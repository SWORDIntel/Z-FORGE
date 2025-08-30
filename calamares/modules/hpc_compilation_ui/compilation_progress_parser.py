#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HPC Compilation Progress Parser and Error Handler
Intelligent parsing of compiler output with progress tracking and error detection
"""

import re
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Pattern
from dataclasses import dataclass, field
from enum import Enum
import subprocess

class CompilationPhase(Enum):
    """Compilation phases for progress tracking"""
    CONFIGURE = "configure"
    GENERATE = "generate" 
    COMPILE = "compile"
    LINK = "link"
    INSTALL = "install"
    TEST = "test"
    PACKAGE = "package"

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"

@dataclass
class CompilationError:
    """Compilation error information"""
    severity: ErrorSeverity
    phase: CompilationPhase
    component: str
    file_path: str
    line_number: int
    error_code: str
    message: str
    suggestion: str = ""
    timestamp: float = field(default_factory=time.time)

@dataclass
class ProgressInfo:
    """Compilation progress information"""
    component: str
    phase: CompilationPhase
    current_step: int
    total_steps: int
    percent_complete: float
    current_file: str = ""
    files_processed: int = 0
    total_files: int = 0
    estimated_remaining_seconds: float = 0.0

class CompilationProgressParser:
    """
    Intelligent parser for HPC compilation output
    
    Features:
    - Real-time progress extraction from build tools
    - Error detection and classification
    - Performance analysis and time estimation
    - Compiler-specific output parsing
    - Recovery suggestions for common issues
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Progress tracking patterns
        self.progress_patterns = self._init_progress_patterns()
        
        # Error detection patterns
        self.error_patterns = self._init_error_patterns()
        
        # Performance tracking
        self.start_times: Dict[str, float] = {}
        self.file_counts: Dict[str, Tuple[int, int]] = {}  # (processed, total)
        
        # Component-specific parsers
        self.component_parsers = {
            'cuda': self._parse_cuda_output,
            'intel': self._parse_intel_output,
            'openmpi': self._parse_mpi_output,
            'fftw': self._parse_fftw_output,
            'openblas': self._parse_openblas_output,
            'hdf5': self._parse_hdf5_output,
            'python': self._parse_python_output,
            'cmake': self._parse_cmake_output,
            'make': self._parse_make_output,
            'gcc': self._parse_gcc_output,
            'nvcc': self._parse_nvcc_output
        }
        
        # Error recovery suggestions
        self.error_solutions = self._init_error_solutions()
    
    def _init_progress_patterns(self) -> Dict[str, List[Pattern]]:
        """Initialize progress detection patterns"""
        patterns = {
            # Make progress patterns
            'make': [
                re.compile(r'\[\s*(\d+)%\]'),  # CMake progress
                re.compile(r'(\d+)/(\d+)'),     # Make file count
                re.compile(r'\[\s*(\d+)\s*/\s*(\d+)\]'),  # Progress fraction
            ],
            
            # CMake configure patterns
            'cmake': [
                re.compile(r'-- (\d+)% complete'),
                re.compile(r'Configuring (.+)'),
                re.compile(r'-- Found (.+)'),
            ],
            
            # GCC compilation patterns
            'gcc': [
                re.compile(r'Compiling (.+\.c)'),
                re.compile(r'Building (.+\.o)'),
                re.compile(r'\[\s*CC\s*\]\s*(.+)'),
            ],
            
            # NVCC CUDA patterns
            'nvcc': [
                re.compile(r'Compiling CUDA (.+\.cu)'),
                re.compile(r'\[\s*NVCC\s*\]\s*(.+)'),
                re.compile(r'Building shared library (.+)'),
            ],
            
            # Intel compiler patterns
            'intel': [
                re.compile(r'icc: Compiling (.+)'),
                re.compile(r'Building (.+) with Intel compiler'),
                re.compile(r'Intel\(R\) MKL .+ Building'),
            ],
            
            # Python package installation
            'python': [
                re.compile(r'Processing (.+)'),
                re.compile(r'Building wheel for (.+)'),
                re.compile(r'Installing (.+)'),
                re.compile(r'Successfully installed (.+)'),
            ],
            
            # Configure script patterns
            'configure': [
                re.compile(r'checking (.+)\.\.\.'),
                re.compile(r'configure: (.+)'),
                re.compile(r'Configuring (.+)'),
            ],
            
            # Package manager patterns
            'apt': [
                re.compile(r'Processing (\d+)/(\d+) (.+)'),
                re.compile(r'Unpacking (.+)'),
                re.compile(r'Setting up (.+)'),
            ]
        }
        
        return patterns
    
    def _init_error_patterns(self) -> Dict[ErrorSeverity, List[Pattern]]:
        """Initialize error detection patterns"""
        patterns = {
            ErrorSeverity.FATAL: [
                re.compile(r'fatal error: (.+)', re.IGNORECASE),
                re.compile(r'FATAL: (.+)', re.IGNORECASE),
                re.compile(r'Error: (.+) failed with exit code (\d+)'),
                re.compile(r'make\[\d+\]: \*\*\* (.+) Error (\d+)'),
                re.compile(r'CMake Error: (.+)'),
                re.compile(r'configure: error: (.+)'),
            ],
            
            ErrorSeverity.ERROR: [
                re.compile(r'error: (.+)', re.IGNORECASE),
                re.compile(r'ERROR: (.+)', re.IGNORECASE),
                re.compile(r'(.+):(\d+):(\d+): error: (.+)'),
                re.compile(r'nvcc fatal\s*: (.+)'),
                re.compile(r'(.+\.cu)\((\d+)\): error (.+): (.+)'),
                re.compile(r'Intel\(R\) Compiler: Error: (.+)'),
            ],
            
            ErrorSeverity.WARNING: [
                re.compile(r'warning: (.+)', re.IGNORECASE),
                re.compile(r'WARNING: (.+)', re.IGNORECASE),
                re.compile(r'(.+):(\d+):(\d+): warning: (.+)'),
                re.compile(r'(.+\.cu)\((\d+)\): warning (.+): (.+)'),
                re.compile(r'Intel\(R\) Compiler: Warning: (.+)'),
            ],
            
            ErrorSeverity.INFO: [
                re.compile(r'note: (.+)', re.IGNORECASE),
                re.compile(r'info: (.+)', re.IGNORECASE),
                re.compile(r'INFO: (.+)', re.IGNORECASE),
            ]
        }
        
        return patterns
    
    def _init_error_solutions(self) -> Dict[str, str]:
        """Initialize error recovery suggestions"""
        return {
            'permission denied': "Check file permissions and ensure running with appropriate privileges",
            'no such file or directory': "Verify all required files and dependencies are installed",
            'command not found': "Install missing build tools or add to PATH",
            'out of memory': "Reduce parallel jobs (-j parameter) or increase system RAM",
            'disk full': "Free up disk space or use tmpfs for builds",
            'cuda.*not found': "Install NVIDIA CUDA toolkit and ensure PATH/LD_LIBRARY_PATH are set",
            'nvcc.*not found': "Install NVIDIA CUDA development tools",
            'intel.*not found': "Install Intel Parallel Studio XE and source environment",
            'mpi.*not found': "Install MPI development libraries (libopenmpi-dev)",
            'blas.*not found': "Install BLAS library (libopenblas-dev or libatlas-base-dev)",
            'missing.*header': "Install development packages for missing headers",
            'undefined reference': "Link required libraries or install development packages",
            'cannot find -l': "Install library development packages or fix library paths",
            'version.*mismatch': "Update dependencies or use compatible versions",
            'thermal throttling': "Reduce parallel jobs or improve system cooling",
            'compilation.*timeout': "Increase timeout limit or reduce optimization level",
        }
    
    def parse_output_line(self, line: str, component: str = "") -> Tuple[Optional[ProgressInfo], List[CompilationError]]:
        """
        Parse a single line of compilation output
        
        Args:
            line: Output line to parse
            component: Current component being compiled
            
        Returns:
            Tuple of (progress_info, list_of_errors)
        """
        progress_info = None
        errors = []
        
        # Clean the line
        clean_line = self._clean_output_line(line)
        
        # Check for errors first
        detected_errors = self._detect_errors(clean_line)
        errors.extend(detected_errors)
        
        # Parse progress if no fatal errors
        if not any(e.severity == ErrorSeverity.FATAL for e in detected_errors):
            progress_info = self._extract_progress(clean_line, component)
        
        return progress_info, errors
    
    def parse_output_stream(self, process: subprocess.Popen, component: str = "") -> Dict[str, Any]:
        """
        Parse continuous output stream from compilation process
        
        Args:
            process: Running subprocess
            component: Component being compiled
            
        Returns:
            Dictionary with progress and error information
        """
        results = {
            'progress_history': [],
            'errors': [],
            'warnings': [],
            'current_progress': None,
            'estimated_completion': None,
            'performance_metrics': {}
        }
        
        start_time = time.time()
        last_progress_time = start_time
        
        try:
            while True:
                # Read line with timeout
                try:
                    line = process.stdout.readline().decode('utf-8', errors='ignore')
                    if not line:
                        # Check if process is still running
                        if process.poll() is not None:
                            break
                        time.sleep(0.1)
                        continue
                        
                except Exception as e:
                    self.logger.warning(f"Error reading process output: {e}")
                    break
                
                # Parse the line
                progress_info, line_errors = self.parse_output_line(line.strip(), component)
                
                # Update progress
                if progress_info:
                    results['current_progress'] = progress_info
                    results['progress_history'].append(progress_info)
                    last_progress_time = time.time()
                    
                    # Estimate completion time
                    if progress_info.percent_complete > 5:  # Only after 5% for accuracy
                        elapsed = time.time() - start_time
                        estimated_total = elapsed / (progress_info.percent_complete / 100)
                        estimated_remaining = estimated_total - elapsed
                        results['estimated_completion'] = estimated_remaining
                
                # Handle errors
                for error in line_errors:
                    if error.severity in [ErrorSeverity.ERROR, ErrorSeverity.FATAL]:
                        results['errors'].append(error)
                    elif error.severity == ErrorSeverity.WARNING:
                        results['warnings'].append(error)
                
                # Performance metrics
                current_time = time.time()
                if current_time - last_progress_time > 30:  # No progress for 30 seconds
                    results['performance_metrics']['stalled'] = True
                    results['performance_metrics']['stall_duration'] = current_time - last_progress_time
                
        except Exception as e:
            self.logger.error(f"Error parsing output stream: {e}")
            results['errors'].append(
                CompilationError(
                    severity=ErrorSeverity.ERROR,
                    phase=CompilationPhase.COMPILE,
                    component=component,
                    file_path="",
                    line_number=0,
                    error_code="PARSER_ERROR",
                    message=f"Output parsing failed: {e}"
                )
            )
        
        return results
    
    def _clean_output_line(self, line: str) -> str:
        """Clean and normalize output line"""
        # Remove ANSI color codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_line = ansi_escape.sub('', line)
        
        # Remove extra whitespace
        clean_line = clean_line.strip()
        
        # Remove timestamps if present
        timestamp_pattern = re.compile(r'^\[\d{2}:\d{2}:\d{2}\]\s*')
        clean_line = timestamp_pattern.sub('', clean_line)
        
        return clean_line
    
    def _detect_errors(self, line: str) -> List[CompilationError]:
        """Detect errors in output line"""
        errors = []
        
        for severity, patterns in self.error_patterns.items():
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    error = self._create_error_from_match(match, line, severity)
                    if error:
                        errors.append(error)
        
        return errors
    
    def _create_error_from_match(self, match: re.Match, line: str, severity: ErrorSeverity) -> Optional[CompilationError]:
        """Create CompilationError from regex match"""
        try:
            # Extract common information
            groups = match.groups()
            
            # Determine file path and line number
            file_path = ""
            line_number = 0
            error_code = ""
            message = line
            
            # Parse different error formats
            if len(groups) >= 4 and ':' in groups[0]:  # Format: file:line:col: error: message
                file_path = groups[0]
                line_number = int(groups[1]) if groups[1].isdigit() else 0
                message = groups[3] if len(groups) > 3 else groups[-1]
            elif len(groups) >= 2:
                if groups[1].isdigit():  # Format: file(line): error: message
                    file_path = groups[0] if len(groups) > 0 else ""
                    line_number = int(groups[1])
                    message = groups[2] if len(groups) > 2 else line
                else:
                    message = groups[0] if groups else line
            elif len(groups) == 1:
                message = groups[0]
            
            # Determine phase from context
            phase = self._determine_compilation_phase(line, file_path)
            
            # Get component from file path or context
            component = self._extract_component_from_path(file_path) or "unknown"
            
            # Generate suggestion
            suggestion = self._generate_error_suggestion(message, error_code)
            
            return CompilationError(
                severity=severity,
                phase=phase,
                component=component,
                file_path=file_path,
                line_number=line_number,
                error_code=error_code,
                message=message,
                suggestion=suggestion
            )
            
        except Exception as e:
            self.logger.warning(f"Error creating CompilationError: {e}")
            return None
    
    def _extract_progress(self, line: str, component: str) -> Optional[ProgressInfo]:
        """Extract progress information from output line"""
        # Try component-specific parser first
        for comp_name, parser in self.component_parsers.items():
            if comp_name in component.lower() or comp_name in line.lower():
                progress = parser(line)
                if progress:
                    return progress
        
        # Try general progress patterns
        for tool, patterns in self.progress_patterns.items():
            for pattern in patterns:
                match = pattern.search(line)
                if match:
                    progress = self._create_progress_from_match(match, line, component)
                    if progress:
                        return progress
        
        return None
    
    def _create_progress_from_match(self, match: re.Match, line: str, component: str) -> Optional[ProgressInfo]:
        """Create ProgressInfo from regex match"""
        try:
            groups = match.groups()
            
            if len(groups) == 1:  # Single percentage
                percent = float(groups[0])
                return ProgressInfo(
                    component=component,
                    phase=self._determine_compilation_phase(line),
                    current_step=int(percent),
                    total_steps=100,
                    percent_complete=percent
                )
            elif len(groups) == 2:  # Fraction format
                current = int(groups[0])
                total = int(groups[1])
                percent = (current / total) * 100 if total > 0 else 0
                
                return ProgressInfo(
                    component=component,
                    phase=self._determine_compilation_phase(line),
                    current_step=current,
                    total_steps=total,
                    percent_complete=percent,
                    files_processed=current,
                    total_files=total
                )
            
        except Exception as e:
            self.logger.warning(f"Error creating ProgressInfo: {e}")
        
        return None
    
    def _determine_compilation_phase(self, line: str, file_path: str = "") -> CompilationPhase:
        """Determine compilation phase from context"""
        line_lower = line.lower()
        
        if any(word in line_lower for word in ['configure', 'checking', 'config']):
            return CompilationPhase.CONFIGURE
        elif any(word in line_lower for word in ['generate', 'generating', 'cmake']):
            return CompilationPhase.GENERATE
        elif any(word in line_lower for word in ['compile', 'compiling', 'gcc', 'nvcc', 'icc']):
            return CompilationPhase.COMPILE
        elif any(word in line_lower for word in ['link', 'linking', 'ld']):
            return CompilationPhase.LINK
        elif any(word in line_lower for word in ['install', 'installing', 'make install']):
            return CompilationPhase.INSTALL
        elif any(word in line_lower for word in ['test', 'testing', 'check']):
            return CompilationPhase.TEST
        elif any(word in line_lower for word in ['package', 'packaging', 'cpack']):
            return CompilationPhase.PACKAGE
        else:
            return CompilationPhase.COMPILE  # Default
    
    def _extract_component_from_path(self, file_path: str) -> Optional[str]:
        """Extract component name from file path"""
        if not file_path:
            return None
        
        # Component patterns in paths
        component_patterns = {
            'cuda': r'cuda|nvcc',
            'intel': r'intel|mkl|tbb|mpi',
            'openmpi': r'openmpi|mpi',
            'fftw': r'fftw',
            'openblas': r'openblas|blas',
            'hdf5': r'hdf5',
            'python': r'python|numpy|scipy',
            'zfs': r'zfs|zpool',
            'kernel': r'linux|kernel'
        }
        
        path_lower = file_path.lower()
        for component, pattern in component_patterns.items():
            if re.search(pattern, path_lower):
                return component
        
        return None
    
    def _generate_error_suggestion(self, message: str, error_code: str) -> str:
        """Generate helpful suggestion for error"""
        message_lower = message.lower()
        
        for pattern, suggestion in self.error_solutions.items():
            if re.search(pattern, message_lower):
                return suggestion
        
        # Generic suggestions based on error type
        if any(word in message_lower for word in ['not found', 'no such file']):
            return "Check if all required packages and dependencies are installed"
        elif any(word in message_lower for word in ['permission', 'denied']):
            return "Check file permissions or run with appropriate privileges"
        elif any(word in message_lower for word in ['memory', 'ram']):
            return "Reduce parallel compilation jobs or increase available memory"
        elif any(word in message_lower for word in ['disk', 'space']):
            return "Free up disk space or use tmpfs for temporary files"
        else:
            return "Check compilation logs and ensure all dependencies are properly installed"
    
    # Component-specific parsers
    def _parse_cuda_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse CUDA compilation output"""
        # NVCC progress patterns
        patterns = [
            re.compile(r'ptxas info    : Compiling entry function \'(.+)\''),
            re.compile(r'nvcc.*: Compiling (.+\.cu)'),
            re.compile(r'Building shared library (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="cuda",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_intel_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse Intel compiler output"""
        patterns = [
            re.compile(r'icc.*: Compiling (.+)'),
            re.compile(r'Building (.+) with Intel compiler'),
            re.compile(r'Intel\(R\) MKL .+ Building (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="intel",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_mpi_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse MPI compilation output"""
        patterns = [
            re.compile(r'mpicc.*: Compiling (.+)'),
            re.compile(r'Building MPI (.+)'),
            re.compile(r'OpenMPI.*Building (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="openmpi",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_fftw_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse FFTW compilation output"""
        patterns = [
            re.compile(r'Building FFTW (.+)'),
            re.compile(r'fftw.*: Compiling (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="fftw",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_openblas_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse OpenBLAS compilation output"""
        patterns = [
            re.compile(r'Building OpenBLAS (.+)'),
            re.compile(r'BLAS.*: Compiling (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="openblas",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_hdf5_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse HDF5 compilation output"""
        patterns = [
            re.compile(r'Building HDF5 (.+)'),
            re.compile(r'hdf5.*: Compiling (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="hdf5",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_python_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse Python package compilation output"""
        patterns = [
            re.compile(r'Building wheel for (.+)'),
            re.compile(r'Processing (.+)'),
            re.compile(r'Installing (.+)'),
            re.compile(r'Successfully (.+) (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="python",
                    phase=CompilationPhase.INSTALL,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_cmake_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse CMake output"""
        patterns = [
            re.compile(r'-- (\d+)% complete'),
            re.compile(r'\[\s*(\d+)%\]'),
            re.compile(r'Configuring (.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                if match.group(1).isdigit():
                    percent = float(match.group(1))
                    return ProgressInfo(
                        component="cmake",
                        phase=CompilationPhase.GENERATE,
                        current_step=int(percent),
                        total_steps=100,
                        percent_complete=percent
                    )
        
        return None
    
    def _parse_make_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse Make output"""
        patterns = [
            re.compile(r'\[\s*(\d+)/(\d+)\]'),
            re.compile(r'(\d+)/(\d+)'),
            re.compile(r'\[\s*(\d+)%\]')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    current = int(groups[0])
                    total = int(groups[1])
                    percent = (current / total) * 100 if total > 0 else 0
                    
                    return ProgressInfo(
                        component="make",
                        phase=CompilationPhase.COMPILE,
                        current_step=current,
                        total_steps=total,
                        percent_complete=percent
                    )
                elif len(groups) == 1 and groups[0].isdigit():
                    percent = float(groups[0])
                    return ProgressInfo(
                        component="make",
                        phase=CompilationPhase.COMPILE,
                        current_step=int(percent),
                        total_steps=100,
                        percent_complete=percent
                    )
        
        return None
    
    def _parse_gcc_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse GCC compiler output"""
        patterns = [
            re.compile(r'gcc.*-c (.+\.c)'),
            re.compile(r'Compiling (.+)'),
            re.compile(r'\[\s*CC\s*\]\s*(.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="gcc",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None
    
    def _parse_nvcc_output(self, line: str) -> Optional[ProgressInfo]:
        """Parse NVCC compiler output"""
        patterns = [
            re.compile(r'nvcc.*-c (.+\.cu)'),
            re.compile(r'Compiling CUDA (.+)'),
            re.compile(r'\[\s*NVCC\s*\]\s*(.+)')
        ]
        
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                return ProgressInfo(
                    component="nvcc",
                    phase=CompilationPhase.COMPILE,
                    current_step=0,
                    total_steps=100,
                    percent_complete=0,
                    current_file=match.group(1) if match.groups() else ""
                )
        
        return None


# Test the parser
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create parser
    parser = CompilationProgressParser()
    
    # Test with sample output lines
    test_lines = [
        "[ 25%] Building CXX object CMakeFiles/test.dir/main.cpp.o",
        "gcc -c -O3 -march=native src/main.c -o main.o",
        "nvcc -arch=sm_35 -c kernel.cu -o kernel.o",
        "error: 'undefined_function' was not declared in this scope",
        "warning: unused variable 'temp' [-Wunused-variable]",
        "fatal error: cuda_runtime.h: No such file or directory",
        "make[2]: *** [CMakeFiles/test.dir/build.make:76: main.o] Error 1",
        "Installing collected packages: numpy, scipy, pandas",
        "Successfully installed numpy-1.21.6 scipy-1.7.3",
        "Intel(R) MKL 2020.4: Building optimized libraries",
        "ptxas info    : Compiling entry function '_Z6kernelPf'",
        "OpenMPI 4.1.4: Building MPI libraries",
        "[100%] Built target hpc_application"
    ]
    
    print("=== HPC Compilation Progress Parser Test ===\n")
    
    for line in test_lines:
        print(f"Input:  {line}")
        
        progress, errors = parser.parse_output_line(line, "test_component")
        
        if progress:
            print(f"Progress: {progress.component} - {progress.phase.value} - {progress.percent_complete:.1f}%")
            if progress.current_file:
                print(f"         File: {progress.current_file}")
        
        if errors:
            for error in errors:
                print(f"Error:   [{error.severity.value.upper()}] {error.message}")
                if error.suggestion:
                    print(f"         Suggestion: {error.suggestion}")
        
        if not progress and not errors:
            print("No progress or errors detected")
        
        print()