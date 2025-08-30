#!/usr/bin/env python3
"""
Z-FORGE HPC Build Integration Module
Integrates HPC build specifications and workflows into the main Z-FORGE build system
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

class HPCBuildIntegration:
    """
    Integrates HPC capabilities into the Z-FORGE build system
    
    Provides:
    - HPC build specification detection
    - Hardware-aware build path selection
    - HPC compilation orchestration
    - Performance validation integration
    """
    
    def __init__(self, project_root: Path, logger: Optional[logging.Logger] = None):
        self.project_root = project_root
        self.logger = logger or self._setup_logger()
        self.hpc_specs_dir = project_root / "build_specs"
        self.hpc_scripts_dir = project_root / "scripts" / "hpc"
        
        # HPC build specification patterns
        self.hpc_spec_patterns = [
            "build_spec_hpc_*.yml",
            "*_hpc.yml", 
            "*_tesla.yml",
            "*_phi.yml",
            "*_xeon_phi*.yml"
        ]
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for HPC integration"""
        logging.basicConfig(
            level=logging.INFO,
            format='[HPC] %(levelname)s: %(message)s'
        )
        return logging.getLogger(__name__)
        
    def is_hpc_build_spec(self, spec_file: Path) -> bool:
        """
        Determine if a build specification is HPC-oriented
        
        Args:
            spec_file: Path to build specification file
            
        Returns:
            True if spec is HPC-oriented, False otherwise
        """
        try:
            # Check filename patterns
            spec_name = spec_file.name.lower()
            hpc_keywords = ['hpc', 'tesla', 'phi', 'xeon_phi', 'cuda', 'scientific']
            
            if any(keyword in spec_name for keyword in hpc_keywords):
                return True
                
            # Check spec content
            if spec_file.suffix.lower() in ['.yml', '.yaml']:
                with open(spec_file, 'r') as f:
                    spec_content = yaml.safe_load(f)
                    
                # Check for HPC-specific configuration
                hpc_indicators = [
                    'hpc' in spec_content,
                    'cuda_version' in str(spec_content).lower(),
                    'xeon_phi' in str(spec_content).lower(),
                    'tesla' in str(spec_content).lower(),
                    any('hpc_' in module_name for module_name in self._extract_module_names(spec_content))
                ]
                
                return any(hpc_indicators)
                
        except Exception as e:
            self.logger.warning(f"Error checking HPC spec {spec_file}: {e}")
            
        return False
        
    def _extract_module_names(self, spec_content: Dict[str, Any]) -> List[str]:
        """Extract module names from build specification"""
        module_names = []
        
        if 'modules' in spec_content:
            for module in spec_content['modules']:
                if isinstance(module, dict) and 'name' in module:
                    module_names.append(module['name'])
                elif isinstance(module, str):
                    module_names.append(module)
                    
        return module_names
        
    def detect_hpc_hardware(self) -> Dict[str, Any]:
        """
        Detect HPC hardware on the system
        
        Returns:
            Dictionary containing hardware detection results
        """
        hardware_info = {
            'tesla_gpus': [],
            'xeon_phi_devices': [], 
            'hpc_capable': False,
            'recommended_specs': []
        }
        
        try:
            # Check for NVIDIA Tesla GPUs
            try:
                nvidia_result = subprocess.run(['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'], 
                                             capture_output=True, text=True, check=True)
                for line in nvidia_result.stdout.strip().split('\n'):
                    if 'Tesla' in line:
                        hardware_info['tesla_gpus'].append(line.strip())
                        
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
                
            # Check for Intel Xeon Phi
            try:
                lspci_result = subprocess.run(['lspci'], capture_output=True, text=True, check=True)
                for line in lspci_result.stdout.split('\n'):
                    if 'Xeon Phi' in line:
                        hardware_info['xeon_phi_devices'].append(line.strip())
                        
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
                
            # Determine HPC capability and recommended specs
            if hardware_info['tesla_gpus']:
                hardware_info['hpc_capable'] = True
                if any('K40' in gpu or 'K80' in gpu for gpu in hardware_info['tesla_gpus']):
                    hardware_info['recommended_specs'].append('build_spec_hpc_tesla.yml')
                    
            if hardware_info['xeon_phi_devices']:
                hardware_info['hpc_capable'] = True
                hardware_info['recommended_specs'].append('build_spec_hpc_phi.yml')
                
            # Check for Dell T30
            try:
                dmidecode_result = subprocess.run(['dmidecode', '-s', 'system-product-name'],
                                                capture_output=True, text=True, check=True)
                if 'PowerEdge T30' in dmidecode_result.stdout:
                    hardware_info['recommended_specs'].append('build_spec_hpc_dell_t30.yml')
                    
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
                
            # If no specific hardware detected but system is capable
            cpu_info = Path('/proc/cpuinfo').read_text()
            if 'Xeon' in cpu_info or hardware_info['tesla_gpus'] or hardware_info['xeon_phi_devices']:
                if not hardware_info['recommended_specs']:
                    hardware_info['recommended_specs'].append('build_spec_hpc_combined.yml')
                    
        except Exception as e:
            self.logger.error(f"Hardware detection failed: {e}")
            
        self.logger.info(f"HPC Hardware Detection Results:")
        self.logger.info(f"  Tesla GPUs: {len(hardware_info['tesla_gpus'])}")
        self.logger.info(f"  Xeon Phi Devices: {len(hardware_info['xeon_phi_devices'])}")
        self.logger.info(f"  HPC Capable: {hardware_info['hpc_capable']}")
        self.logger.info(f"  Recommended Specs: {hardware_info['recommended_specs']}")
            
        return hardware_info
        
    def get_hpc_build_specs(self) -> List[Path]:
        """
        Get all available HPC build specifications
        
        Returns:
            List of HPC build specification files
        """
        hpc_specs = []
        
        if self.hpc_specs_dir.exists():
            for pattern in self.hpc_spec_patterns:
                hpc_specs.extend(list(self.hpc_specs_dir.glob(pattern)))
                
        # Remove duplicates and sort
        hpc_specs = sorted(list(set(hpc_specs)))
        
        self.logger.info(f"Found {len(hpc_specs)} HPC build specifications")
        for spec in hpc_specs:
            self.logger.info(f"  - {spec.name}")
            
        return hpc_specs
        
    def recommend_hpc_spec(self, hardware_info: Optional[Dict[str, Any]] = None) -> Optional[Path]:
        """
        Recommend best HPC build specification based on detected hardware
        
        Args:
            hardware_info: Hardware detection results (optional, will detect if not provided)
            
        Returns:
            Path to recommended HPC build specification or None
        """
        if hardware_info is None:
            hardware_info = self.detect_hpc_hardware()
            
        if not hardware_info['hpc_capable']:
            self.logger.info("No HPC hardware detected, no HPC specification recommended")
            return None
            
        # Find best matching specification
        for recommended_spec in hardware_info['recommended_specs']:
            spec_path = self.hpc_specs_dir / recommended_spec
            if spec_path.exists():
                self.logger.info(f"Recommended HPC specification: {recommended_spec}")
                return spec_path
                
        # Fallback to first available HPC spec
        hpc_specs = self.get_hpc_build_specs()
        if hpc_specs:
            self.logger.info(f"Fallback HPC specification: {hpc_specs[0].name}")
            return hpc_specs[0]
            
        return None
        
    def prepare_hpc_environment(self, spec_file: Path) -> Dict[str, str]:
        """
        Prepare environment variables for HPC build
        
        Args:
            spec_file: HPC build specification file
            
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        try:
            with open(spec_file, 'r') as f:
                spec_content = yaml.safe_load(f)
                
            # HPC workspace
            hpc_workspace = os.environ.get('HPC_WORKSPACE', '/tmp/zforge-hpc-workspace')
            env_vars['HPC_WORKSPACE'] = hpc_workspace
            env_vars['WORKSPACE'] = hpc_workspace
            
            # HPC configuration from spec
            if 'hpc' in spec_content:
                hpc_config = spec_content['hpc']
                
                if 'cuda_version' in hpc_config:
                    env_vars['CUDA_VERSION'] = str(hpc_config['cuda_version'])
                    env_vars['CUDA_AVAILABLE'] = 'true'
                    
                if 'target_hardware' in hpc_config:
                    env_vars['HPC_TARGET_HARDWARE'] = hpc_config['target_hardware']
                    
                if 'xeon_phi' in str(hpc_config).lower():
                    env_vars['XEON_PHI_AVAILABLE'] = 'true'
                    
            # Compiler preferences
            if Path('/opt/intel/bin/icc').exists():
                env_vars['CC'] = '/opt/intel/bin/icc'
                env_vars['CXX'] = '/opt/intel/bin/icpc'
                env_vars['FC'] = '/opt/intel/bin/ifort'
                
            # HPC library paths
            hpc_prefix = '/opt/hpc'
            if Path(hpc_prefix).exists():
                env_vars['HPC_PREFIX'] = hpc_prefix
                env_vars['PATH'] = f"{hpc_prefix}/bin:{os.environ.get('PATH', '')}"
                env_vars['LD_LIBRARY_PATH'] = f"{hpc_prefix}/lib:{os.environ.get('LD_LIBRARY_PATH', '')}"
                env_vars['PKG_CONFIG_PATH'] = f"{hpc_prefix}/lib/pkgconfig:{os.environ.get('PKG_CONFIG_PATH', '')}"
                
        except Exception as e:
            self.logger.error(f"Error preparing HPC environment: {e}")
            
        return env_vars
        
    def run_hpc_preparation(self, spec_file: Path) -> bool:
        """
        Run HPC preparation script before build
        
        Args:
            spec_file: HPC build specification file
            
        Returns:
            True if preparation successful, False otherwise
        """
        preparation_script = self.project_root / "prepare-hpc-compilation.sh"
        
        if not preparation_script.exists():
            self.logger.warning("HPC preparation script not found, skipping preparation")
            return True
            
        try:
            self.logger.info("Running HPC preparation script...")
            
            env = os.environ.copy()
            env.update(self.prepare_hpc_environment(spec_file))
            
            result = subprocess.run([str(preparation_script)], 
                                  cwd=self.project_root,
                                  env=env,
                                  check=True,
                                  capture_output=True,
                                  text=True)
                                  
            self.logger.info("HPC preparation completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"HPC preparation failed: {e}")
            self.logger.error(f"stdout: {e.stdout}")
            self.logger.error(f"stderr: {e.stderr}")
            return False
            
    def run_hpc_validation(self) -> Dict[str, Any]:
        """
        Run HPC performance validation after build
        
        Returns:
            Validation results dictionary
        """
        validation_script = self.hpc_scripts_dir / "validate_hpc_performance.sh"
        
        if not validation_script.exists():
            self.logger.warning("HPC validation script not found")
            return {"status": "skipped", "reason": "validation script not found"}
            
        try:
            self.logger.info("Running HPC performance validation...")
            
            result = subprocess.run([str(validation_script)],
                                  cwd=self.project_root,
                                  capture_output=True,
                                  text=True,
                                  timeout=3600)  # 1 hour timeout
                                  
            validation_results = {
                "status": "completed" if result.returncode == 0 else "failed",
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            # Try to parse JSON results if available
            results_dir = Path(os.environ.get('HPC_WORKSPACE', '/tmp/zforge-hpc-workspace')) / "results"
            if results_dir.exists():
                latest_result = max(results_dir.glob("hpc_performance_*.json"), 
                                  key=lambda p: p.stat().st_mtime, default=None)
                if latest_result:
                    try:
                        with open(latest_result, 'r') as f:
                            validation_results.update(json.load(f))
                    except Exception as e:
                        self.logger.warning(f"Could not parse validation results: {e}")
                        
            if validation_results["status"] == "completed":
                self.logger.info("HPC validation completed successfully")
            else:
                self.logger.error("HPC validation failed")
                
            return validation_results
            
        except subprocess.TimeoutExpired:
            self.logger.error("HPC validation timed out")
            return {"status": "timeout", "reason": "validation took too long"}
        except Exception as e:
            self.logger.error(f"HPC validation error: {e}")
            return {"status": "error", "reason": str(e)}
            
    def create_hpc_build_wrapper(self, original_build_script: Path, spec_file: Path) -> Path:
        """
        Create HPC build wrapper that integrates HPC preparation and validation
        
        Args:
            original_build_script: Original build script path
            spec_file: HPC build specification file
            
        Returns:
            Path to HPC build wrapper script
        """
        wrapper_script = self.project_root / "build_hpc_wrapper.py"
        
        wrapper_code = f'''#!/usr/bin/env python3
"""
Z-FORGE HPC Build Wrapper
Automatically generated HPC build integration
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "scripts" / "hpc"))

from hpc_build_integration import HPCBuildIntegration

def main():
    # Initialize HPC integration
    hpc_integration = HPCBuildIntegration(project_root)
    
    # Run HPC preparation
    spec_file = Path("{spec_file}")
    if not hpc_integration.run_hpc_preparation(spec_file):
        print("HPC preparation failed, aborting build")
        sys.exit(1)
    
    # Set HPC environment
    hpc_env = hpc_integration.prepare_hpc_environment(spec_file)
    for key, value in hpc_env.items():
        os.environ[key] = value
    
    # Run original build
    import subprocess
    try:
        result = subprocess.run([sys.executable, "{original_build_script}", "--spec", str(spec_file)],
                              cwd=project_root,
                              check=True)
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {{e}}")
        sys.exit(e.returncode)
    
    # Run HPC validation
    print("\\n=== Running HPC Performance Validation ===")
    validation_results = hpc_integration.run_hpc_validation()
    
    # Save validation results
    results_file = project_root / "hpc_build_results.json"
    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    
    print(f"\\nHPC build completed successfully!")
    print(f"Validation results: {{results_file}}")
    
    if validation_results.get("status") == "failed":
        print("Warning: HPC validation detected performance issues")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        
        with open(wrapper_script, 'w') as f:
            f.write(wrapper_code)
            
        wrapper_script.chmod(0o755)
        
        self.logger.info(f"Created HPC build wrapper: {wrapper_script}")
        return wrapper_script
        
    def integrate_hpc_modules(self) -> bool:
        """
        Ensure HPC modules are available in the builder modules directory
        
        Returns:
            True if integration successful, False otherwise
        """
        builder_modules_dir = self.project_root / "builder" / "modules"
        
        if not builder_modules_dir.exists():
            self.logger.error("Builder modules directory not found")
            return False
            
        # Check for required HPC modules
        required_hpc_modules = [
            "hpc_hardware_detector.py",
            "hpc_compilation_orchestrator.py", 
            "hpc_memory_optimizer.py",
            "hpc_driver_bundle_orchestrator.py",
            "hpc_system_integrator.py",
            "hpc_performance_projector.py"
        ]
        
        missing_modules = []
        for module_name in required_hpc_modules:
            module_path = builder_modules_dir / module_name
            if not module_path.exists():
                missing_modules.append(module_name)
                
        if missing_modules:
            self.logger.error(f"Missing HPC modules: {missing_modules}")
            return False
            
        self.logger.info("All required HPC modules are available")
        return True
        
    def get_hpc_build_summary(self) -> Dict[str, Any]:
        """
        Get summary of HPC build capabilities and status
        
        Returns:
            Dictionary containing HPC build summary
        """
        hardware_info = self.detect_hpc_hardware()
        hpc_specs = self.get_hpc_build_specs()
        recommended_spec = self.recommend_hpc_spec(hardware_info)
        modules_available = self.integrate_hpc_modules()
        
        summary = {
            "hpc_capable": hardware_info['hpc_capable'],
            "tesla_gpus": len(hardware_info['tesla_gpus']),
            "xeon_phi_devices": len(hardware_info['xeon_phi_devices']),
            "available_specs": [spec.name for spec in hpc_specs],
            "recommended_spec": recommended_spec.name if recommended_spec else None,
            "hpc_modules_available": modules_available,
            "preparation_script_available": (self.project_root / "prepare-hpc-compilation.sh").exists(),
            "validation_script_available": (self.hpc_scripts_dir / "validate_hpc_performance.sh").exists()
        }
        
        return summary

def main():
    """Command line interface for HPC build integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-FORGE HPC Build Integration")
    parser.add_argument("--detect", action="store_true", help="Detect HPC hardware")
    parser.add_argument("--list-specs", action="store_true", help="List HPC build specifications")
    parser.add_argument("--recommend", action="store_true", help="Recommend HPC build specification")
    parser.add_argument("--summary", action="store_true", help="Show HPC build summary")
    parser.add_argument("--prepare", metavar="SPEC_FILE", help="Run HPC preparation for specification")
    parser.add_argument("--validate", action="store_true", help="Run HPC performance validation")
    
    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent.parent
    hpc_integration = HPCBuildIntegration(project_root)
    
    if args.detect:
        hardware_info = hpc_integration.detect_hpc_hardware()
        print(json.dumps(hardware_info, indent=2))
        
    elif args.list_specs:
        specs = hpc_integration.get_hpc_build_specs()
        print("Available HPC build specifications:")
        for spec in specs:
            print(f"  - {spec.name}")
            
    elif args.recommend:
        recommended = hpc_integration.recommend_hpc_spec()
        if recommended:
            print(f"Recommended HPC specification: {recommended.name}")
        else:
            print("No HPC specification recommended (no HPC hardware detected)")
            
    elif args.summary:
        summary = hpc_integration.get_hpc_build_summary()
        print("HPC Build Summary:")
        print(json.dumps(summary, indent=2))
        
    elif args.prepare:
        spec_file = Path(args.prepare)
        if not spec_file.exists():
            spec_file = project_root / "build_specs" / args.prepare
        if spec_file.exists():
            success = hpc_integration.run_hpc_preparation(spec_file)
            sys.exit(0 if success else 1)
        else:
            print(f"HPC specification not found: {args.prepare}")
            sys.exit(1)
            
    elif args.validate:
        results = hpc_integration.run_hpc_validation()
        print(json.dumps(results, indent=2))
        sys.exit(0 if results.get("status") == "completed" else 1)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()