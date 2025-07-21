#!/usr/bin/env python3
"""
Module Configuration Preset Loader
Loads and applies configuration presets for Z-FORGE modules
"""
import yaml
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class PresetLoader:
    """Load and manage configuration presets"""
    
    def __init__(self, preset_dir: Path = None):
        self.preset_dir = preset_dir or Path(__file__).parent.parent.parent / "config/module_presets"
        self.presets = {}
        self.variables = {}
        self._load_all_presets()
    
    def _load_all_presets(self):
        """Load all available presets"""
        if not self.preset_dir.exists():
            logger.warning(f"Preset directory not found: {self.preset_dir}")
            return
        
        for preset_file in self.preset_dir.glob("*.yaml"):
            try:
                with open(preset_file) as f:
                    preset_data = yaml.safe_load(f)
                    preset_name = preset_file.stem
                    self.presets[preset_name] = preset_data
                    logger.info(f"Loaded preset: {preset_name}")
            except Exception as e:
                logger.error(f"Failed to load preset {preset_file}: {e}")
    
    def list_presets(self) -> List[Dict[str, str]]:
        """List all available presets"""
        return [
            {
                "name": name,
                "display_name": data.get("name", name),
                "description": data.get("description", "")
            }
            for name, data in self.presets.items()
        ]
    
    def get_preset(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific preset by name"""
        return self.presets.get(name)
    
    def apply_preset(self, preset_name: str, variables: Dict[str, str] = None) -> Dict[str, Any]:
        """Apply a preset and resolve variables"""
        preset = self.get_preset(preset_name)
        if not preset:
            raise ValueError(f"Preset not found: {preset_name}")
        
        # Merge provided variables with environment
        self.variables = {
            **os.environ,
            **(variables or {})
        }
        
        # Deep copy and resolve variables
        resolved = self._resolve_variables(preset)
        
        return resolved
    
    def _resolve_variables(self, data: Any) -> Any:
        """Recursively resolve ${VARIABLE} references"""
        if isinstance(data, str):
            # Replace ${VAR} with actual values
            import re
            def replacer(match):
                var_name = match.group(1)
                return self.variables.get(var_name, match.group(0))
            
            return re.sub(r'\$\{([^}]+)\}', replacer, data)
        
        elif isinstance(data, dict):
            return {k: self._resolve_variables(v) for k, v in data.items()}
        
        elif isinstance(data, list):
            return [self._resolve_variables(item) for item in data]
        
        return data
    
    def generate_module_configs(self, preset_name: str, 
                              variables: Dict[str, str] = None) -> Dict[str, Any]:
        """Generate individual module configurations from preset"""
        preset = self.apply_preset(preset_name, variables)
        
        module_configs = {}
        
        # Extract module-specific configurations
        if "modules" in preset:
            for module_name, module_config in preset["modules"].items():
                module_configs[module_name] = self._process_module_config(
                    module_name, module_config
                )
        
        return module_configs
    
    def _process_module_config(self, module_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate module configuration"""
        processed = {}
        
        # Handle preset references within modules
        if "preset" in config:
            # Could load module-specific presets here
            processed["preset_name"] = config["preset"]
        
        # Copy all configuration
        processed.update(config)
        
        # Module-specific processing
        if module_name == "networkconfig":
            processed = self._process_network_config(processed)
        elif module_name == "storagelayout":
            processed = self._process_storage_config(processed)
        elif module_name == "gpupassthrough":
            processed = self._process_gpu_config(processed)
        
        return processed
    
    def _process_network_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process network configuration"""
        # Convert high-level config to module format
        if "interfaces" in config:
            processed_interfaces = {}
            
            for iface_name, iface_config in config["interfaces"].items():
                if iface_name in ["primary", "secondary"]:
                    # These are logical names, need to map to actual interfaces
                    # In real implementation, would detect actual interface names
                    actual_name = "eth0" if iface_name == "primary" else "eth1"
                    processed_interfaces[actual_name] = iface_config
                else:
                    processed_interfaces[iface_name] = iface_config
            
            config["interfaces"] = processed_interfaces
        
        return config
    
    def _process_storage_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process storage configuration"""
        # Ensure pools have all required fields
        if "pools" in config:
            for pool in config["pools"]:
                # Set defaults
                pool.setdefault("encryption", False)
                pool.setdefault("mount_options", ["noatime"])
                
                # Process datasets
                if "datasets" in pool:
                    for dataset in pool["datasets"]:
                        dataset.setdefault("compression", "lz4")
                        dataset.setdefault("sync", "standard")
        
        return config
    
    def _process_gpu_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process GPU passthrough configuration"""
        # Ensure required fields
        config.setdefault("settings", {})
        config["settings"].setdefault("enable_iommu", True)
        
        return config
    
    def save_to_calamares_config(self, preset_name: str, output_path: Path,
                                variables: Dict[str, str] = None):
        """Save preset as Calamares configuration files"""
        module_configs = self.generate_module_configs(preset_name, variables)
        
        for module_name, config in module_configs.items():
            module_config_path = output_path / f"{module_name}.conf"
            
            # Convert to Calamares YAML format
            calamares_config = {
                "module": module_name,
                "config": config
            }
            
            with open(module_config_path, 'w') as f:
                yaml.dump(calamares_config, f, default_flow_style=False)
            
            logger.info(f"Saved {module_name} config to {module_config_path}")
    
    def validate_preset(self, preset_name: str) -> List[str]:
        """Validate a preset configuration"""
        errors = []
        
        preset = self.get_preset(preset_name)
        if not preset:
            return [f"Preset not found: {preset_name}"]
        
        # Check required fields
        if "name" not in preset:
            errors.append("Missing 'name' field")
        
        if "modules" not in preset:
            errors.append("Missing 'modules' section")
        else:
            # Validate each module config
            for module_name, config in preset["modules"].items():
                module_errors = self._validate_module_config(module_name, config)
                errors.extend(module_errors)
        
        return errors
    
    def _validate_module_config(self, module_name: str, config: Dict[str, Any]) -> List[str]:
        """Validate module-specific configuration"""
        errors = []
        
        # Module-specific validation
        if module_name == "networkconfig":
            if "interfaces" not in config:
                errors.append(f"{module_name}: Missing 'interfaces' configuration")
        
        elif module_name == "storagelayout":
            if "pools" not in config:
                errors.append(f"{module_name}: Missing 'pools' configuration")
            else:
                for i, pool in enumerate(config["pools"]):
                    if "name" not in pool:
                        errors.append(f"{module_name}: Pool {i} missing 'name'")
                    if "type" not in pool:
                        errors.append(f"{module_name}: Pool {i} missing 'type'")
        
        return errors


class PresetCLI:
    """Command-line interface for preset management"""
    
    def __init__(self):
        self.loader = PresetLoader()
    
    def list_command(self):
        """List available presets"""
        presets = self.loader.list_presets()
        
        print("Available Z-FORGE Configuration Presets:")
        print("-" * 50)
        
        for preset in presets:
            print(f"\n{preset['name']}:")
            print(f"  Name: {preset['display_name']}")
            print(f"  Description: {preset['description']}")
    
    def show_command(self, preset_name: str):
        """Show preset details"""
        preset = self.loader.get_preset(preset_name)
        
        if not preset:
            print(f"Error: Preset '{preset_name}' not found")
            return
        
        print(f"Preset: {preset.get('name', preset_name)}")
        print(f"Description: {preset.get('description', 'N/A')}")
        print("\nConfiguration:")
        print(yaml.dump(preset, default_flow_style=False))
    
    def validate_command(self, preset_name: str):
        """Validate preset"""
        errors = self.loader.validate_preset(preset_name)
        
        if errors:
            print(f"Validation errors for preset '{preset_name}':")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Preset '{preset_name}' is valid!")
    
    def apply_command(self, preset_name: str, output_dir: str, variables: List[str]):
        """Apply preset and generate configs"""
        # Parse variables
        var_dict = {}
        for var in variables:
            if '=' in var:
                key, value = var.split('=', 1)
                var_dict[key] = value
        
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            self.loader.save_to_calamares_config(preset_name, output_path, var_dict)
            print(f"Applied preset '{preset_name}' to {output_path}")
            
        except Exception as e:
            print(f"Error applying preset: {e}")


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Z-FORGE Configuration Preset Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # List command
    subparsers.add_parser("list", help="List available presets")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show preset details")
    show_parser.add_argument("preset", help="Preset name")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate preset")
    validate_parser.add_argument("preset", help="Preset name")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply preset")
    apply_parser.add_argument("preset", help="Preset name")
    apply_parser.add_argument("-o", "--output", required=True, help="Output directory")
    apply_parser.add_argument("-v", "--var", action="append", default=[],
                            help="Variables (KEY=VALUE)")
    
    args = parser.parse_args()
    
    cli = PresetCLI()
    
    if args.command == "list":
        cli.list_command()
    elif args.command == "show":
        cli.show_command(args.preset)
    elif args.command == "validate":
        cli.validate_command(args.preset)
    elif args.command == "apply":
        cli.apply_command(args.preset, args.output, args.var)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()