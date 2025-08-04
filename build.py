#!/usr/bin/env python3
"""
Z-FORGE Build Launcher
Modular launcher for the automated build process with enhanced configuration management
"""
import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class BuildConfig:
    """Build configuration settings"""
    config_file: Path
    workspace: str
    debug_mode: bool
    python_path: List[str]
    environment: Dict[str, str]


class ConfigurationManager:
    """Manages build configuration discovery and selection"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup basic logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='[%(levelname)s] %(message)s'
        )
        return logging.getLogger(__name__)
    
    def find_build_specs(self) -> List[Path]:
        """Find available build spec YAML files"""
        yaml_files = list(self.project_root.glob("*.yml")) + list(self.project_root.glob("*.yaml"))
        
        # Filter to build spec files
        build_specs = []
        for yaml_file in yaml_files:
            if 'build_spec' in yaml_file.name.lower() or yaml_file.name == 'build_specs/build_spec.yml':
                build_specs.append(yaml_file)
        
        return sorted(build_specs)
    
    def select_build_spec(self, build_specs: List[Path], override: Optional[str] = None) -> Optional[Path]:
        """Select a build spec from available options"""
        if override:
            config_file = Path(override)
            if config_file.is_absolute():
                return config_file if config_file.exists() else None
            else:
                # Try relative to project root
                config_file = self.project_root / override
                return config_file if config_file.exists() else None
        
        if len(build_specs) == 0:
            return None
        elif len(build_specs) == 1:
            return build_specs[0]
        else:
            # Multiple specs found, check for default
            for spec in build_specs:
                if spec.name == 'build_specs/build_spec.yml':
                    return spec
            # No default, use first one
            return build_specs[0]
    
    def get_default_workspace(self) -> str:
        """Get default workspace path"""
        return os.environ.get('ZFORGE_WORKSPACE', f"{os.path.expanduser('~')}/zforge_workspace")


class ArgumentParser:
    """Parses command line arguments"""
    
    def __init__(self, args: List[str]):
        self.args = args
    
    def parse(self) -> Dict[str, Any]:
        """Parse command line arguments"""
        result = {
            'debug_mode': '--debug' in self.args,
            'config_override': None,
            'workspace_override': None,
            'help': '--help' in self.args or '-h' in self.args
        }
        
        # Parse config override
        for i, arg in enumerate(self.args):
            if arg.startswith('--config='):
                result['config_override'] = arg.split('=', 1)[1]
            elif arg == '--config' and i + 1 < len(self.args):
                result['config_override'] = self.args[i + 1]
            elif arg.startswith('--workspace='):
                result['workspace_override'] = arg.split('=', 1)[1]
            elif arg == '--workspace' and i + 1 < len(self.args):
                result['workspace_override'] = self.args[i + 1]
        
        return result


class EnvironmentManager:
    """Manages build environment setup"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def setup_environment(self, config: BuildConfig) -> Dict[str, str]:
        """Setup build environment variables"""
        env = os.environ.copy()
        
        # Set Z-FORGE specific variables
        env['ZFORGE_CONFIG'] = str(config.config_file)
        env['ZFORGE_WORKSPACE'] = config.workspace
        env['ZFORGE_ROOT'] = str(self.project_root)
        
        # Setup Python path
        python_path_parts = [str(self.project_root)]
        python_path_parts.extend(config.python_path)
        if 'PYTHONPATH' in env:
            python_path_parts.append(env['PYTHONPATH'])
        env['PYTHONPATH'] = ':'.join(python_path_parts)
        
        # Add any custom environment variables
        env.update(config.environment)
        
        return env


class BuildLauncher:
    """Main build launcher orchestrator"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.config_manager = ConfigurationManager(project_root)
        self.env_manager = EnvironmentManager(project_root)
        self.logger = self.config_manager.logger
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        # Check if running as root
        if os.geteuid() != 0:
            self.logger.error("This script must be run as root")
            self.logger.info("Relaunching with sudo...")
            return False
        
        # Check if build script exists
        build_script = self.project_root / "scripts/build/build-auto.py"
        if not build_script.exists():
            self.logger.error(f"Build script not found: {build_script}")
            return False
        
        return True
    
    def create_build_config(self, args: Dict[str, Any]) -> Optional[BuildConfig]:
        """Create build configuration from arguments"""
        # Find build specs
        build_specs = self.config_manager.find_build_specs()
        config_file = self.config_manager.select_build_spec(build_specs, args['config_override'])
        
        if not config_file:
            self.logger.error("No build configuration found")
            self.logger.info("Please create a build_specs/build_spec.yml file first")
            self.logger.info("Example: build_specs/build_spec.yml, build_specs/build_spec_proxmox_full.yml")
            return None
        
        # Determine workspace
        workspace = args['workspace_override'] or self.config_manager.get_default_workspace()
        
        return BuildConfig(
            config_file=config_file,
            workspace=workspace,
            debug_mode=args['debug_mode'],
            python_path=[],
            environment={}
        )
    
    def display_build_info(self, config: BuildConfig, all_specs: List[Path]):
        """Display build information"""
        print("════════════════════════════════════════════════════════════════")
        print("                Z-FORGE BUILD LAUNCHER")
        print("════════════════════════════════════════════════════════════════")
        print()
        print(f"[*] Config: {config.config_file.name}")
        print(f"[*] Workspace: {config.workspace}")
        print(f"[*] Debug mode: {'ON' if config.debug_mode else 'OFF'}")
        print()
        
        if len(all_specs) > 1:
            print(f"[*] Found {len(all_specs)} build configs:")
            for spec in all_specs:
                prefix = "  → " if spec == config.config_file else "    "
                print(f"{prefix}{spec.name}")
            print()
    
    def execute_build(self, config: BuildConfig) -> int:
        """Execute the build process"""
        build_script = self.project_root / "scripts/build/build-auto.py"
        
        # Setup environment
        env = self.env_manager.setup_environment(config)
        
        # Build command
        cmd = [sys.executable, str(build_script)]
        if config.debug_mode:
            cmd.append('--debug')
        
        try:
            # Run the build
            result = subprocess.run(cmd, env=env)
            return result.returncode
        except KeyboardInterrupt:
            self.logger.warning("Build interrupted by user")
            return 130
        except Exception as e:
            self.logger.error(f"Error launching build: {e}")
            return 1
    
    def relaunch_with_sudo(self):
        """Relaunch script with sudo privileges"""
        args = ['sudo', sys.executable] + sys.argv
        os.execvp('sudo', args)
    
    def show_help(self):
        """Display help information"""
        print("Z-FORGE Build Launcher")
        print()
        print("Usage:")
        print("  sudo python3 build.py [options]")
        print()
        print("Options:")
        print("  --config=FILE       Use specific build configuration")
        print("  --workspace=PATH    Use specific workspace directory")
        print("  --debug             Enable debug mode")
        print("  --help, -h          Show this help message")
        print()
        print("Examples:")
        print("  sudo python3 build.py")
        print("  sudo python3 build.py --config=build_specs/build_spec_proxmox_full.yml")
        print("  sudo python3 build.py --workspace=/home/user/custom_workspace --debug")
    
    def run(self) -> int:
        """Main entry point"""
        # Parse arguments
        arg_parser = ArgumentParser(sys.argv[1:])
        args = arg_parser.parse()
        
        # Show help if requested
        if args['help']:
            self.show_help()
            return 0
        
        # Change to project directory
        os.chdir(self.project_root)
        
        # Fix Python path for imports
        sys.path.insert(0, str(self.project_root))
        
        # Check prerequisites
        if not self.check_prerequisites():
            if os.geteuid() != 0:
                self.relaunch_with_sudo()
                return 0  # This won't be reached
            return 1
        
        # Create build configuration
        config = self.create_build_config(args)
        if not config:
            return 1
        
        # Display build information
        all_specs = self.config_manager.find_build_specs()
        self.display_build_info(config, all_specs)
        
        # Execute build
        return self.execute_build(config)


def main():
    """Main entry point"""
    project_root = Path(__file__).parent
    launcher = BuildLauncher(project_root)
    return launcher.run()


if __name__ == "__main__":
    sys.exit(main())