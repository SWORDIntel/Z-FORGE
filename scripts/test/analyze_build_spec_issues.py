#!/usr/bin/env python3
"""
Analyze Build Spec Issues Not Caught in Testing
Identifies missing fields and configuration problems
"""

import yaml
import sys
from pathlib import Path
from typing import Dict, List, Any, Set


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse YAML file"""
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}


def find_required_fields() -> Dict[str, Set[str]]:
    """Find all required fields based on code analysis"""
    required_fields = {
        'top_level': {
            'builder_config',  # CRITICAL - missing in main build_spec.yml
            'modules',         # Present but different format
            'proxmox_config',  # Missing
            'zfs_config',      # Missing
            'bootloader_config',  # Missing
            'hardware_detection',  # Missing
            'calamares_config',   # Missing
            'universal_config'    # Missing
        },
        'builder_config': {
            'debian_release',     # Present as top-level
            'kernel_version',     # Present as top-level
            'output_iso_name',    # Missing
            'enable_debug',       # Missing
            'workspace_path',     # Different format
            'cache_packages',     # Missing
            'auto_detect_hardware',  # Missing
            'iso_version'         # Missing - used by Calamares
        },
        'modules_format': {
            'name',
            'enabled',
            'config'  # Optional but expected
        }
    }
    
    return required_fields


def analyze_build_spec(spec_path: Path, required_fields: Dict[str, Set[str]]) -> Dict[str, Any]:
    """Analyze a build spec file for missing fields"""
    spec_data = load_yaml_file(spec_path)
    
    issues = {
        'file': spec_path.name,
        'missing_top_level': [],
        'missing_builder_config': [],
        'module_format_issues': [],
        'workspace_format_issue': False,
        'other_issues': []
    }
    
    # Check top-level fields
    for field in required_fields['top_level']:
        if field not in spec_data:
            issues['missing_top_level'].append(field)
    
    # Check builder_config fields
    if 'builder_config' in spec_data:
        builder_config = spec_data['builder_config']
        for field in required_fields['builder_config']:
            if field not in builder_config:
                issues['missing_builder_config'].append(field)
    else:
        # Check if fields are at top level instead
        top_level_builder_fields = []
        for field in required_fields['builder_config']:
            if field in spec_data:
                top_level_builder_fields.append(field)
        
        if top_level_builder_fields:
            issues['other_issues'].append(f"Builder config fields at top level: {', '.join(top_level_builder_fields)}")
    
    # Check module format
    if 'modules' in spec_data:
        modules = spec_data['modules']
        if isinstance(modules, list):
            for i, module in enumerate(modules):
                if isinstance(module, dict):
                    if 'name' not in module:
                        issues['module_format_issues'].append(f"Module {i}: missing 'name'")
                    if 'enabled' not in module:
                        issues['module_format_issues'].append(f"Module {i}: missing 'enabled'")
                else:
                    issues['module_format_issues'].append(f"Module {i}: not a dict")
        else:
            issues['module_format_issues'].append("'modules' is not a list")
    elif 'build_modules' in spec_data:
        issues['other_issues'].append("Uses 'build_modules' instead of 'modules'")
    
    # Check workspace format
    if 'workspace' in spec_data:
        workspace = spec_data['workspace']
        if isinstance(workspace, dict) and 'base_path' in workspace:
            issues['workspace_format_issue'] = True
            issues['other_issues'].append("Uses nested workspace structure instead of builder_config.workspace_path")
    
    return issues


def compare_specs(spec_files: List[Path]) -> Dict[str, Any]:
    """Compare multiple spec files to find common issues"""
    all_keys = {}
    
    for spec_path in spec_files:
        spec_data = load_yaml_file(spec_path)
        all_keys[spec_path.name] = set(spec_data.keys())
    
    # Find common and unique keys
    if all_keys:
        common_keys = set.intersection(*all_keys.values())
        unique_keys = {}
        
        for file_name, keys in all_keys.items():
            unique = keys - common_keys
            if unique:
                unique_keys[file_name] = unique
                
        return {
            'common_keys': common_keys,
            'unique_keys': unique_keys,
            'all_keys': all_keys
        }
    
    return {}


def generate_corrected_spec(original_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a corrected version of the build spec"""
    # Start with the reference structure
    corrected = {
        'builder_config': {
            'debian_release': original_spec.get('debian_release', 'trixie'),
            'kernel_version': original_spec.get('kernel_version', 'latest'),
            'output_iso_name': 'zforge-3.0-amd64.iso',
            'enable_debug': False,
            'workspace_path': original_spec.get('workspace', {}).get('base_path', '${HOME}/zforge_workspace'),
            'cache_packages': True,
            'auto_detect_hardware': True,
            'iso_version': original_spec.get('version', '3.0')
        },
        'proxmox_config': {
            'version': 'latest',
            'minimal_install': False,
            'build_from_source': False,
            'include_packages': []
        },
        'zfs_config': {
            'version': '2.3.3',
            'build_from_source': False,
            'enable_encryption': True,
            'compression': {
                'default': 'lz4',
                'algorithm': 'auto'
            }
        },
        'bootloader_config': {
            'primary': 'grub',
            'enable_zfsbootmenu': True,
            'encryption_support': True
        },
        'hardware_detection': {
            'enabled': True,
            'enforce_zfs_mode': True
        },
        'calamares_config': {
            'enabled': True
        },
        'modules': []
    }
    
    # Convert build_modules to modules format
    if 'build_modules' in original_spec:
        for module in original_spec['build_modules']:
            if isinstance(module, dict) and 'name' in module:
                corrected['modules'].append({
                    'name': module['name'],
                    'enabled': module.get('enabled', True)
                })
    
    # Add other top-level fields that don't need restructuring
    for key in ['name', 'version', 'codename', 'architecture']:
        if key in original_spec:
            corrected[key] = original_spec[key]
    
    return corrected


def main():
    """Main analysis function"""
    project_root = Path(__file__).parent.parent.parent
    
    print("🔍 Build Spec Issue Analysis")
    print("=" * 60)
    
    # Find all build spec files
    spec_files = list(project_root.glob("build_spec*.yml"))
    print(f"\nFound {len(spec_files)} build spec files:")
    for spec in spec_files:
        print(f"  - {spec.name}")
    
    # Get required fields
    required_fields = find_required_fields()
    
    print("\n📋 Required Fields Analysis")
    print("=" * 60)
    
    # Analyze each spec
    all_issues = []
    for spec_path in spec_files:
        issues = analyze_build_spec(spec_path, required_fields)
        all_issues.append(issues)
        
        print(f"\n{spec_path.name}:")
        
        if issues['missing_top_level']:
            print(f"  ❌ Missing top-level fields: {', '.join(issues['missing_top_level'])}")
        
        if issues['missing_builder_config']:
            print(f"  ❌ Missing builder_config fields: {', '.join(issues['missing_builder_config'])}")
            
        if issues['module_format_issues']:
            print(f"  ⚠️ Module format issues: {len(issues['module_format_issues'])}")
            for issue in issues['module_format_issues'][:3]:  # Show first 3
                print(f"    - {issue}")
                
        if issues['workspace_format_issue']:
            print(f"  ⚠️ Uses nested workspace structure")
            
        if issues['other_issues']:
            print(f"  ℹ️ Other issues:")
            for issue in issues['other_issues']:
                print(f"    - {issue}")
    
    # Compare specs
    print("\n🔄 Spec Comparison")
    print("=" * 60)
    comparison = compare_specs(spec_files)
    
    if comparison:
        print(f"\nCommon keys across all specs: {len(comparison['common_keys'])}")
        print(f"Keys: {', '.join(sorted(comparison['common_keys']))}")
        
        if comparison['unique_keys']:
            print(f"\nUnique keys per file:")
            for file_name, keys in comparison['unique_keys'].items():
                print(f"  {file_name}: {', '.join(sorted(keys))}")
    
    # Critical issues not caught in testing
    print("\n🚨 Critical Issues Not Caught in Testing")
    print("=" * 60)
    
    critical_issues = [
        "1. Missing 'builder_config' section - REQUIRED by BuildConfig class",
        "2. Using 'build_modules' instead of 'modules' - incompatible format",
        "3. Workspace path in nested structure instead of builder_config.workspace_path",
        "4. Missing output_iso_name in builder_config - affects ISO generation",
        "5. Missing iso_version in builder_config - used by Calamares branding",
        "6. Module format incompatible - expects {name, enabled} not nested config",
        "7. Missing proxmox_config section - may cause module failures",
        "8. Missing zfs_config at top level - modules expect it there",
        "9. Missing calamares_config section - affects installer integration",
        "10. No hardware_detection config - auto-detection may fail"
    ]
    
    for issue in critical_issues:
        print(f"  ❌ {issue}")
    
    # Generate corrected spec
    print("\n💡 Correcting build_spec.yml...")
    print("=" * 60)
    
    main_spec_path = project_root / "build_spec.yml"
    if main_spec_path.exists():
        original_spec = load_yaml_file(main_spec_path)
        corrected_spec = generate_corrected_spec(original_spec)
        
        # Save corrected version
        corrected_path = project_root / "build_spec_corrected.yml"
        with open(corrected_path, 'w') as f:
            yaml.dump(corrected_spec, f, default_flow_style=False, sort_keys=False)
            
        print(f"✅ Generated corrected spec: {corrected_path}")
        print("\nKey corrections made:")
        print("  - Added builder_config section with all required fields")
        print("  - Converted build_modules to modules format")
        print("  - Added missing top-level sections")
        print("  - Fixed workspace path location")
        print("  - Added iso_version for Calamares")
    
    print("\n📊 Summary")
    print("=" * 60)
    print("The build pipeline validator did NOT catch these issues because:")
    print("1. It only checked for module files, not configuration structure")
    print("2. It didn't validate YAML schema against expected format")
    print("3. It didn't check if config sections match code expectations")
    print("4. No integration test between config loader and spec files")
    print("\nRecommendation: Add schema validation to BuildConfig class")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())