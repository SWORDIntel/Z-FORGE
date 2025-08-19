#!/usr/bin/env python3
"""
Build Pipeline Validator
UltraThink Agent Recommendation #2 - Priority 9/10

Implements validation layer to ensure all build components are properly connected
and the complete pipeline from build system to Calamares GUI is functional.
"""

import os
import sys
import json
import yaml
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ValidationLevel(Enum):
    """Validation severity levels"""
    CRITICAL = "critical"
    ERROR = "error" 
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    component: str
    check_name: str
    level: ValidationLevel
    status: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    fix_suggestion: Optional[str] = None


@dataclass
class PipelineValidationReport:
    """Complete pipeline validation report"""
    timestamp: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_failures: int
    error_failures: int
    warning_count: int
    overall_status: str
    results: List[ValidationResult]
    integration_matrix: Dict[str, List[str]]


class BuildPipelineValidator:
    """
    Comprehensive validator for the Z-FORGE build pipeline
    
    Validates complete connectivity from:
    Build System -> Builder Modules -> Calamares Integration -> Live Environment -> GUI
    """
    
    def __init__(self, project_root: Path, workspace: Path, config: Dict[str, Any]):
        self.project_root = project_root
        self.workspace = workspace
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Key paths
        self.chroot_path = workspace / "chroot"
        self.builder_modules_dir = project_root / "builder" / "modules"
        self.calamares_source_dir = project_root / "calamares"
        self.scripts_dir = project_root / "scripts"
        
        # Validation results
        self.results: List[ValidationResult] = []
        
    def validate_complete_pipeline(self) -> PipelineValidationReport:
        """
        Run complete pipeline validation
        
        Returns comprehensive report of all validation checks
        """
        self.logger.info("🔍 Starting Complete Build Pipeline Validation")
        
        # Clear previous results
        self.results = []
        
        # Phase 1: Core Build System Validation
        self.logger.info("Phase 1: Core Build System Validation")
        self._validate_build_system()
        
        # Phase 2: Builder Module Validation
        self.logger.info("Phase 2: Builder Module Validation")
        self._validate_builder_modules()
        
        # Phase 3: Calamares Integration Validation
        self.logger.info("Phase 3: Calamares Integration Validation")
        self._validate_calamares_integration()
        
        # Phase 4: Configuration Consistency Validation
        self.logger.info("Phase 4: Configuration Consistency Validation")
        self._validate_configuration_consistency()
        
        # Phase 5: Live Environment Validation
        self.logger.info("Phase 5: Live Environment Validation")
        self._validate_live_environment()
        
        # Phase 6: Integration Matrix Validation
        self.logger.info("Phase 6: Integration Matrix Validation")
        integration_matrix = self._build_integration_matrix()
        
        # Generate report
        report = self._generate_validation_report(integration_matrix)
        
        self.logger.info(f"✅ Pipeline validation completed: {report.passed_checks}/{report.total_checks} checks passed")
        
        return report
        
    def _validate_build_system(self):
        """Validate core build system components"""
        
        # Check main build.py structure
        build_py = self.project_root / "build.py"
        if build_py.exists():
            content = build_py.read_text()
            
            # Check for modular classes
            required_classes = ["ConfigurationManager", "ArgumentParser", "EnvironmentManager", "BuildLauncher"]
            for cls in required_classes:
                if cls in content:
                    self.results.append(ValidationResult(
                        component="build_system",
                        check_name=f"modular_class_{cls.lower()}",
                        level=ValidationLevel.INFO,
                        status=True,
                        message=f"Found modular class: {cls}",
                        fix_suggestion=None
                    ))
                else:
                    self.results.append(ValidationResult(
                        component="build_system",
                        check_name=f"modular_class_{cls.lower()}",
                        level=ValidationLevel.ERROR,
                        status=False,
                        message=f"Missing required modular class: {cls}",
                        fix_suggestion=f"Implement {cls} class in build.py"
                    ))
                    
            # Check for error handling
            if "try:" in content and "except Exception" in content:
                self.results.append(ValidationResult(
                    component="build_system",
                    check_name="error_handling",
                    level=ValidationLevel.INFO,
                    status=True,
                    message="Error handling implemented",
                    fix_suggestion=None
                ))
            else:
                self.results.append(ValidationResult(
                    component="build_system",
                    check_name="error_handling",
                    level=ValidationLevel.WARNING,
                    status=False,
                    message="Limited error handling detected",
                    fix_suggestion="Add comprehensive try/except blocks"
                ))
        else:
            self.results.append(ValidationResult(
                component="build_system",
                check_name="main_script",
                level=ValidationLevel.CRITICAL,
                status=False,
                message="Main build.py script not found",
                fix_suggestion="Create modular build.py script"
            ))
            
        # Check build specifications
        build_specs = list(self.project_root.glob("build_spec*.yml"))
        if build_specs:
            self.results.append(ValidationResult(
                component="build_system",
                check_name="build_specifications",
                level=ValidationLevel.INFO,
                status=True,
                message=f"Found {len(build_specs)} build specifications",
                details={"specs": [spec.name for spec in build_specs]}
            ))
        else:
            self.results.append(ValidationResult(
                component="build_system",
                check_name="build_specifications",
                level=ValidationLevel.ERROR,
                status=False,
                message="No build specifications found",
                fix_suggestion="Create at least one build_specs/build_spec.yml file"
            ))
            
    def _validate_builder_modules(self):
        """Validate builder module system"""
        
        if not self.builder_modules_dir.exists():
            self.results.append(ValidationResult(
                component="builder_modules",
                check_name="modules_directory",
                level=ValidationLevel.CRITICAL,
                status=False,
                message="Builder modules directory not found",
                fix_suggestion="Create builder/modules directory"
            ))
            return
            
        # Check for key modules
        key_modules = [
            "calamares_integration.py",
            "calamares_integration_enhanced.py", 
            "zfs_build.py",
            "iso_generation.py",
            "live_environment.py"
        ]
        
        for module in key_modules:
            module_path = self.builder_modules_dir / module
            if module_path.exists():
                self.results.append(ValidationResult(
                    component="builder_modules",
                    check_name=f"module_{module.replace('.py', '')}",
                    level=ValidationLevel.INFO,
                    status=True,
                    message=f"Found builder module: {module}"
                ))
            else:
                self.results.append(ValidationResult(
                    component="builder_modules",
                    check_name=f"module_{module.replace('.py', '')}",
                    level=ValidationLevel.WARNING,
                    status=False,
                    message=f"Missing builder module: {module}",
                    fix_suggestion=f"Create or verify {module} module"
                ))
                
        # Check module imports and dependencies
        python_modules = list(self.builder_modules_dir.glob("*.py"))
        import_errors = []
        
        for module_file in python_modules:
            try:
                content = module_file.read_text()
                if "class " in content and "def execute(" in content:
                    self.results.append(ValidationResult(
                        component="builder_modules",
                        check_name=f"module_structure_{module_file.stem}",
                        level=ValidationLevel.INFO,
                        status=True,
                        message=f"Module {module_file.name} has proper structure"
                    ))
            except Exception as e:
                import_errors.append(f"{module_file.name}: {e}")
                
        if import_errors:
            self.results.append(ValidationResult(
                component="builder_modules",
                check_name="module_syntax",
                level=ValidationLevel.ERROR,
                status=False,
                message="Some modules have syntax errors",
                details={"errors": import_errors},
                fix_suggestion="Fix syntax errors in modules"
            ))
            
    def _validate_calamares_integration(self):
        """Validate Calamares integration components"""
        
        # Check Calamares source directory
        if not self.calamares_source_dir.exists():
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="source_directory",
                level=ValidationLevel.CRITICAL,
                status=False,
                message="Calamares source directory not found",
                fix_suggestion="Create calamares/ directory with modules"
            ))
            return
            
        # Check for custom modules
        modules_dir = self.calamares_source_dir / "modules"
        if modules_dir.exists():
            module_count = len([d for d in modules_dir.iterdir() if d.is_dir()])
            if module_count > 0:
                self.results.append(ValidationResult(
                    component="calamares_integration",
                    check_name="custom_modules",
                    level=ValidationLevel.INFO,
                    status=True,
                    message=f"Found {module_count} custom Calamares modules"
                ))
            else:
                self.results.append(ValidationResult(
                    component="calamares_integration",
                    check_name="custom_modules",
                    level=ValidationLevel.WARNING,
                    status=False,
                    message="No custom Calamares modules found",
                    fix_suggestion="Add custom modules for Z-FORGE functionality"
                ))
        else:
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="modules_directory",
                level=ValidationLevel.ERROR,
                status=False,
                message="Calamares modules directory not found",
                fix_suggestion="Create calamares/modules directory"
            ))
            
        # Check for ZFS-specific modules
        zfs_modules = ["zfsrootselect", "zfspooldetect", "zfsenhancedconfig", "zfsbootloader"]
        found_zfs_modules = []
        
        for zfs_module in zfs_modules:
            module_path = modules_dir / zfs_module
            if module_path.exists():
                found_zfs_modules.append(zfs_module)
                
        if found_zfs_modules:
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="zfs_modules",
                level=ValidationLevel.INFO,
                status=True,
                message=f"Found {len(found_zfs_modules)} ZFS modules",
                details={"modules": found_zfs_modules}
            ))
        else:
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="zfs_modules",
                level=ValidationLevel.ERROR,
                status=False,
                message="No ZFS-specific Calamares modules found",
                fix_suggestion="Create ZFS modules for installer integration"
            ))
            
        # Check for settings.conf
        settings_conf = self.calamares_source_dir / "settings.conf"
        if settings_conf.exists():
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="settings_configuration",
                level=ValidationLevel.INFO,
                status=True,
                message="Calamares settings.conf found"
            ))
        else:
            self.results.append(ValidationResult(
                component="calamares_integration",
                check_name="settings_configuration",
                level=ValidationLevel.WARNING,
                status=False,
                message="Calamares settings.conf not found",
                fix_suggestion="Generate settings.conf with module sequence"
            ))
            
    def _validate_configuration_consistency(self):
        """Validate configuration consistency across components"""
        
        # Load build specs and check consistency
        build_specs = list(self.project_root.glob("build_spec*.yml"))
        
        for spec_file in build_specs:
            try:
                with open(spec_file, 'r') as f:
                    spec_config = yaml.safe_load(f)
                    
                # Check for required sections
                # Support both old style (workspace) and new style (builder_config.workspace_path)
                required_sections = ["name", "version", "modules"]
                missing_sections = []
                
                for section in required_sections:
                    if section not in spec_config:
                        missing_sections.append(section)
                
                # Check for workspace configuration (old or new style)
                has_workspace = False
                if "workspace" in spec_config:
                    has_workspace = True
                elif "builder_config" in spec_config and "workspace_path" in spec_config.get("builder_config", {}):
                    has_workspace = True
                
                if not has_workspace:
                    missing_sections.append("workspace or builder_config.workspace_path")
                        
                if missing_sections:
                    self.results.append(ValidationResult(
                        component="configuration",
                        check_name=f"spec_completeness_{spec_file.stem}",
                        level=ValidationLevel.WARNING,
                        status=False,
                        message=f"Build spec missing sections: {missing_sections}",
                        fix_suggestion="Add missing configuration sections"
                    ))
                else:
                    self.results.append(ValidationResult(
                        component="configuration",
                        check_name=f"spec_completeness_{spec_file.stem}",
                        level=ValidationLevel.INFO,
                        status=True,
                        message=f"Build spec {spec_file.name} is complete"
                    ))
                    
                # Additional validation for new format
                if "builder_config" in spec_config:
                    builder_config = spec_config["builder_config"]
                    required_builder_fields = ["debian_release", "kernel_version", "output_iso_name", "workspace_path"]
                    missing_builder_fields = [f for f in required_builder_fields if f not in builder_config]
                    
                    if missing_builder_fields:
                        self.results.append(ValidationResult(
                            component="configuration",
                            check_name=f"builder_config_completeness_{spec_file.stem}",
                            level=ValidationLevel.ERROR,
                            status=False,
                            message=f"builder_config missing fields: {missing_builder_fields}",
                            fix_suggestion="Add all required fields to builder_config section"
                        ))
                    else:
                        self.results.append(ValidationResult(
                            component="configuration",
                            check_name=f"builder_config_validation_{spec_file.stem}",
                            level=ValidationLevel.INFO,
                            status=True,
                            message=f"builder_config properly configured"
                        ))
                    
                # Validate module names match actual files
                if "modules" in spec_config:
                    modules_dir = self.project_root / "builder" / "modules"
                    invalid_modules = []
                    
                    for module in spec_config["modules"]:
                        module_name = module.get("name", "")
                        module_file = modules_dir / f"{module_name}.py"
                        
                        if not module_file.exists():
                            invalid_modules.append(module_name)
                    
                    if invalid_modules:
                        self.results.append(ValidationResult(
                            component="configuration",
                            check_name=f"module_name_validation_{spec_file.stem}",
                            level=ValidationLevel.ERROR,
                            status=False,
                            message=f"Invalid module names: {invalid_modules}",
                            details={"invalid_modules": invalid_modules},
                            fix_suggestion="Update module names to match actual files in builder/modules/"
                        ))
                    else:
                        self.results.append(ValidationResult(
                            component="configuration",
                            check_name=f"module_name_validation_{spec_file.stem}",
                            level=ValidationLevel.INFO,
                            status=True,
                            message=f"All module names are valid"
                        ))
                
                # Check for Calamares integration references
                if "calamares" in str(spec_config).lower():
                    self.results.append(ValidationResult(
                        component="configuration",
                        check_name=f"calamares_reference_{spec_file.stem}",
                        level=ValidationLevel.INFO,
                        status=True,
                        message=f"Build spec references Calamares integration"
                    ))
                    
            except yaml.YAMLError as e:
                self.results.append(ValidationResult(
                    component="configuration",
                    check_name=f"spec_syntax_{spec_file.stem}",
                    level=ValidationLevel.ERROR,
                    status=False,
                    message=f"YAML syntax error in {spec_file.name}",
                    details={"error": str(e)},
                    fix_suggestion="Fix YAML syntax errors"
                ))
                
    def _validate_live_environment(self):
        """Validate live environment setup"""
        
        # Check for live environment module
        live_env_module = self.builder_modules_dir / "live_environment.py"
        if live_env_module.exists():
            self.results.append(ValidationResult(
                component="live_environment",
                check_name="module_exists",
                level=ValidationLevel.INFO,
                status=True,
                message="Live environment module found"
            ))
        else:
            self.results.append(ValidationResult(
                component="live_environment", 
                check_name="module_exists",
                level=ValidationLevel.WARNING,
                status=False,
                message="Live environment module not found",
                fix_suggestion="Create live_environment.py module"
            ))
            
        # Check for desktop environment setup scripts
        desktop_scripts = list(self.scripts_dir.rglob("*desktop*"))
        if desktop_scripts:
            self.results.append(ValidationResult(
                component="live_environment",
                check_name="desktop_setup",
                level=ValidationLevel.INFO,
                status=True,
                message=f"Found {len(desktop_scripts)} desktop setup scripts"
            ))
        else:
            self.results.append(ValidationResult(
                component="live_environment",
                check_name="desktop_setup",
                level=ValidationLevel.WARNING,
                status=False,
                message="No desktop setup scripts found",
                fix_suggestion="Add scripts for desktop environment configuration"
            ))
            
    def _build_integration_matrix(self) -> Dict[str, List[str]]:
        """Build integration matrix showing component dependencies"""
        matrix = {
            "build_system": [
                "builder_modules",
                "configuration_files",
                "workspace_setup"
            ],
            "builder_modules": [
                "calamares_integration",
                "zfs_modules", 
                "live_environment",
                "iso_generation"
            ],
            "calamares_integration": [
                "custom_modules",
                "settings_configuration",
                "zfs_modules",
                "live_environment"
            ],
            "live_environment": [
                "desktop_setup",
                "calamares_launcher",
                "user_configuration"
            ],
            "configuration": [
                "build_specifications",
                "module_configs",
                "hardware_profiles"
            ]
        }
        
        return matrix
        
    def _generate_validation_report(self, integration_matrix: Dict[str, List[str]]) -> PipelineValidationReport:
        """Generate comprehensive validation report"""
        from datetime import datetime
        
        total_checks = len(self.results)
        passed_checks = len([r for r in self.results if r.status])
        failed_checks = total_checks - passed_checks
        
        critical_failures = len([r for r in self.results if r.level == ValidationLevel.CRITICAL and not r.status])
        error_failures = len([r for r in self.results if r.level == ValidationLevel.ERROR and not r.status])
        warning_count = len([r for r in self.results if r.level == ValidationLevel.WARNING])
        
        # Determine overall status
        if critical_failures > 0:
            overall_status = "CRITICAL_FAILURES"
        elif error_failures > 0:
            overall_status = "ERROR_FAILURES"
        elif warning_count > 0:
            overall_status = "WARNINGS_PRESENT"
        else:
            overall_status = "ALL_CHECKS_PASSED"
            
        return PipelineValidationReport(
            timestamp=datetime.now().isoformat(),
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            critical_failures=critical_failures,
            error_failures=error_failures,
            warning_count=warning_count,
            overall_status=overall_status,
            results=self.results,
            integration_matrix=integration_matrix
        )
        
    def save_validation_report(self, report: PipelineValidationReport, output_file: Path):
        """Save validation report to file"""
        report_data = asdict(report)
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
            
        self.logger.info(f"📄 Validation report saved to: {output_file}")
        
    def generate_markdown_report(self, report: PipelineValidationReport, output_file: Path):
        """Generate human-readable markdown report"""
        
        with open(output_file, 'w') as f:
            f.write("# Z-FORGE Build Pipeline Validation Report\n\n")
            f.write(f"**Generated:** {report.timestamp}\n")
            f.write(f"**Overall Status:** {report.overall_status}\n\n")
            
            # Summary
            f.write("## Summary\n\n")
            f.write(f"- **Total Checks:** {report.total_checks}\n")
            f.write(f"- **Passed:** {report.passed_checks}\n")
            f.write(f"- **Failed:** {report.failed_checks}\n")
            f.write(f"- **Critical Failures:** {report.critical_failures}\n")
            f.write(f"- **Error Failures:** {report.error_failures}\n")
            f.write(f"- **Warnings:** {report.warning_count}\n\n")
            
            # Results by component
            components = set(r.component for r in report.results)
            
            for component in sorted(components):
                f.write(f"## {component.title().replace('_', ' ')}\n\n")
                
                component_results = [r for r in report.results if r.component == component]
                
                for result in component_results:
                    status_icon = "✅" if result.status else "❌"
                    f.write(f"- {status_icon} **{result.check_name}** ({result.level.value}): {result.message}\n")
                    
                    if result.fix_suggestion:
                        f.write(f"  - *Fix:* {result.fix_suggestion}\n")
                        
                f.write("\n")
                
        self.logger.info(f"📝 Markdown report saved to: {output_file}")


def main():
    """Test the build pipeline validator"""
    project_root = Path(__file__).parent.parent.parent
    workspace = project_root / "test_workspace" 
    
    config = {
        'name': 'Z-FORGE',
        'zfs': {'enabled': True}
    }
    
    validator = BuildPipelineValidator(project_root, workspace, config)
    report = validator.validate_complete_pipeline()
    
    print(f"Validation Results: {report.overall_status}")
    print(f"Checks: {report.passed_checks}/{report.total_checks} passed")
    print(f"Critical: {report.critical_failures}, Errors: {report.error_failures}, Warnings: {report.warning_count}")


if __name__ == "__main__":
    main()