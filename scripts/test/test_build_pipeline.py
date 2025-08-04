#!/usr/bin/env python3
"""
Test Build Pipeline with Validation
Tests the enhanced build system with complete validation
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import our enhanced modules
from builder.modules.build_pipeline_validator import BuildPipelineValidator
from builder.modules.calamares_integration_enhanced import EnhancedCalamaresIntegration
from builder.modules.integrated_build_orchestrator import IntegratedBuildOrchestrator


def setup_logging():
    """Setup logging for test"""
    log_dir = project_root / "logs" / "tests"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f"test_build_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def test_pipeline_validation(workspace: Path, config: dict, logger):
    """Test the build pipeline validator"""
    logger.info("=" * 60)
    logger.info("📋 Testing Build Pipeline Validator")
    logger.info("=" * 60)
    
    validator = BuildPipelineValidator(project_root, workspace, config)
    
    # Run complete validation
    logger.info("Running complete pipeline validation...")
    report = validator.validate_complete_pipeline()
    
    # Save reports
    reports_dir = workspace / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    json_report = reports_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    md_report = reports_dir / f"validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    validator.save_validation_report(report, json_report)
    validator.generate_markdown_report(report, md_report)
    
    # Display results
    logger.info(f"\n📊 Validation Results:")
    logger.info(f"Overall Status: {report.overall_status}")
    logger.info(f"Total Checks: {report.total_checks}")
    logger.info(f"Passed: {report.passed_checks}")
    logger.info(f"Failed: {report.failed_checks}")
    logger.info(f"Critical Failures: {report.critical_failures}")
    logger.info(f"Errors: {report.error_failures}")
    logger.info(f"Warnings: {report.warning_count}")
    
    logger.info(f"\n📄 Reports saved:")
    logger.info(f"JSON: {json_report}")
    logger.info(f"Markdown: {md_report}")
    
    return report


def test_calamares_integration(workspace: Path, config: dict, logger):
    """Test the enhanced Calamares integration"""
    logger.info("\n" + "=" * 60)
    logger.info("🖥️ Testing Enhanced Calamares Integration")
    logger.info("=" * 60)
    
    # Create minimal chroot structure for testing
    chroot_path = workspace / "chroot"
    chroot_path.mkdir(exist_ok=True)
    
    # Create required directories
    (chroot_path / "etc").mkdir(exist_ok=True)
    (chroot_path / "usr/lib/calamares/modules").mkdir(parents=True, exist_ok=True)
    (chroot_path / "home/user/Desktop").mkdir(parents=True, exist_ok=True)
    
    integration = EnhancedCalamaresIntegration(workspace, config)
    
    # Display available modules
    logger.info(f"\n📦 Available Calamares Modules:")
    zfs_modules = []
    hardware_modules = []
    other_modules = []
    
    for name, module in integration.available_modules.items():
        if module.zfs_specific:
            zfs_modules.append(name)
        elif any(keyword in name for keyword in ['hardware', 'gpu', 'network', 'storage']):
            hardware_modules.append(name)
        else:
            other_modules.append(name)
    
    logger.info(f"\n🔧 ZFS-Specific Modules ({len(zfs_modules)}):")
    for module in zfs_modules:
        logger.info(f"  - {module}")
        
    logger.info(f"\n🖥️ Hardware/System Modules ({len(hardware_modules)}):")
    for module in hardware_modules:
        logger.info(f"  - {module}")
        
    logger.info(f"\n📋 Other Modules ({len(other_modules)}):")
    for module in other_modules:
        logger.info(f"  - {module}")
    
    # Test validation
    logger.info("\n🔍 Running integration validation...")
    validation = integration._validate_current_integration()
    
    logger.info(f"\nValidation Results:")
    logger.info(f"Valid: {validation.valid}")
    logger.info(f"Errors: {len(validation.errors)}")
    logger.info(f"Warnings: {len(validation.warnings)}")
    logger.info(f"Missing Components: {len(validation.missing_components)}")
    
    if validation.errors:
        logger.warning("\n❌ Validation Errors:")
        for error in validation.errors:
            logger.warning(f"  - {error}")
            
    if validation.warnings:
        logger.info("\n⚠️ Validation Warnings:")
        for warning in validation.warnings:
            logger.info(f"  - {warning}")
    
    return validation


def test_build_orchestration(workspace: Path, config: dict, logger):
    """Test the integrated build orchestrator"""
    logger.info("\n" + "=" * 60)
    logger.info("🚀 Testing Integrated Build Orchestrator")
    logger.info("=" * 60)
    
    orchestrator = IntegratedBuildOrchestrator(workspace, config)
    
    # Display orchestrator state
    logger.info("\n📊 Orchestrator Initial State:")
    logger.info(f"Phase: {orchestrator.build_state['phase']}")
    logger.info(f"Components: {', '.join(orchestrator.build_state['components_completed'])}")
    
    # Test individual components
    logger.info("\n🔧 Testing GUI Connectivity...")
    gui_connectivity = orchestrator._verify_gui_connectivity()
    
    logger.info(f"\nGUI Connectivity Results:")
    logger.info(f"Complete Chain Connected: {gui_connectivity['complete_chain_connected']}")
    logger.info(f"Connectivity Score: {gui_connectivity['connectivity_score']:.2%}")
    
    for check, result in gui_connectivity['individual_connections'].items():
        status = "✅" if result else "❌"
        logger.info(f"  {status} {check}: {result}")
    
    # Test integration matrix
    logger.info("\n🔗 Integration Matrix:")
    matrix = orchestrator._get_integration_matrix()
    
    for component, connections in matrix.items():
        logger.info(f"\n{component}:")
        if isinstance(connections, dict):
            for key, value in connections.items():
                if isinstance(value, list):
                    logger.info(f"  {key}: {', '.join(value)}")
                else:
                    logger.info(f"  {key}: {value}")
    
    return gui_connectivity


def test_modular_build_launcher(logger):
    """Test the modular build launcher"""
    logger.info("\n" + "=" * 60)
    logger.info("⚙️ Testing Modular Build Launcher")
    logger.info("=" * 60)
    
    build_py = project_root / "build.py"
    
    if not build_py.exists():
        logger.error("❌ build.py not found!")
        return False
        
    # Check for modular classes
    content = build_py.read_text()
    required_classes = [
        "ConfigurationManager",
        "ArgumentParser", 
        "EnvironmentManager",
        "BuildLauncher"
    ]
    
    logger.info("\n🔍 Checking modular classes:")
    all_found = True
    
    for cls in required_classes:
        if cls in content:
            logger.info(f"✅ {cls}: Found")
        else:
            logger.error(f"❌ {cls}: Missing")
            all_found = False
            
    # Check build specifications
    logger.info("\n📄 Available build specifications:")
    build_specs = list(project_root.glob("build_spec*.yml"))
    
    for spec in build_specs:
        logger.info(f"  - {spec.name}")
        
    if not build_specs:
        logger.warning("⚠️ No build specifications found!")
        
    return all_found


def main():
    """Main test runner"""
    # Setup
    logger = setup_logging()
    
    logger.info("🧪 Z-FORGE Enhanced Build System Test Suite")
    logger.info("=" * 60)
    logger.info(f"Project Root: {project_root}")
    logger.info(f"Test Started: {datetime.now().isoformat()}")
    
    # Create test workspace
    test_workspace = project_root / "test_workspace" / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_workspace.mkdir(parents=True, exist_ok=True)
    
    # Test configuration
    test_config = {
        'name': 'Z-FORGE',
        'version': '3.0',
        'zfs': {
            'enabled': True,
            'compression': 'lz4',
            'encryption': True
        },
        'calamares': {
            'enabled': True
        },
        'branding': {
            'component_name': 'zforge'
        }
    }
    
    logger.info(f"\n📁 Test Workspace: {test_workspace}")
    logger.info(f"⚙️ Test Configuration: {test_config['name']} v{test_config['version']}")
    
    # Run tests
    test_results = {}
    
    try:
        # Test 1: Modular Build Launcher
        logger.info("\n" + "="*20 + " TEST 1 " + "="*20)
        test_results['modular_launcher'] = test_modular_build_launcher(logger)
        
        # Test 2: Pipeline Validation
        logger.info("\n" + "="*20 + " TEST 2 " + "="*20)
        validation_report = test_pipeline_validation(test_workspace, test_config, logger)
        test_results['pipeline_validation'] = validation_report.overall_status
        
        # Test 3: Calamares Integration
        logger.info("\n" + "="*20 + " TEST 3 " + "="*20)
        calamares_validation = test_calamares_integration(test_workspace, test_config, logger)
        test_results['calamares_integration'] = calamares_validation.valid
        
        # Test 4: Build Orchestration
        logger.info("\n" + "="*20 + " TEST 4 " + "="*20)
        gui_connectivity = test_build_orchestration(test_workspace, test_config, logger)
        test_results['build_orchestration'] = gui_connectivity['complete_chain_connected']
        
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, result in test_results.items():
        if isinstance(result, bool):
            status = "✅ PASSED" if result else "❌ FAILED"
            if not result:
                all_passed = False
        else:
            status = f"📋 {result}"
            if "FAIL" in str(result).upper() or "ERROR" in str(result).upper():
                all_passed = False
                
        logger.info(f"{test_name}: {status}")
    
    logger.info("\n" + "=" * 60)
    
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED - System Ready!")
        logger.info("\n📋 Next Steps:")
        logger.info("1. Run: sudo python3 build.py")
        logger.info("2. Build a test ISO")
        logger.info("3. Verify Calamares GUI in live environment")
    else:
        logger.warning("⚠️ Some tests indicated issues - review results")
        
    logger.info("\n📄 Test logs saved to: logs/tests/")
    logger.info("📊 Test reports saved to: {}/test_reports/".format(test_workspace))
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())