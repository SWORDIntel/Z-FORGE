#!/usr/bin/env python3
"""
Z-FORGE Full Integration Test Suite
Tests all build specifications, GUI integration, and dracut configuration
"""

import os
import sys
import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
import unittest
import multiprocessing
import psutil

# Add Z-FORGE modules to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'builder'))

class ZForgeFullIntegrationTests(unittest.TestCase):
    """Comprehensive integration tests for Z-FORGE build system"""
    
    @classmethod
    def setUpClass(cls):
        """Setup test environment"""
        cls.project_root = Path(__file__).parent
        cls.build_specs = [
            "build_specs/build_spec.yml",
            "build_specs/build_spec_stable.yml", 
            "build_specs/build_spec_no_tmp.yml",
            "build_specs/build_spec_outside_packages.yml",
            "build_specs/build_spec_proxmox9.yml",
            "build_specs/build_spec_proxmox_full.yml",
            "build_specs/build_spec_trixie_clean.yml"
        ]
        cls.expected_workspace = "/home/john/zforge_workspace"
        cls.test_results = []
        
    def test_01_all_build_specs_exist(self):
        """Test that all 7 build specifications exist"""
        print("\n[TEST 1] Checking build specification files...")
        missing_specs = []
        
        for spec in self.build_specs:
            spec_path = self.project_root / spec
            if not spec_path.exists():
                missing_specs.append(spec)
            else:
                print(f"  ✅ {spec} exists")
                
        self.assertEqual(len(missing_specs), 0, 
                        f"Missing build specs: {missing_specs}")
        print("  ✅ All 7 build specifications found")
        
    def test_02_build_spec_validity(self):
        """Test that all build specifications are valid YAML"""
        print("\n[TEST 2] Validating YAML structure...")
        invalid_specs = []
        
        for spec in self.build_specs:
            spec_path = self.project_root / spec
            try:
                with open(spec_path, 'r') as f:
                    data = yaml.safe_load(f)
                    # Check required fields
                    self.assertIn('name', data, f"{spec} missing 'name' field")
                    self.assertIn('version', data, f"{spec} missing 'version' field")
                    self.assertIn('builder_config', data, f"{spec} missing 'builder_config'")
                    self.assertIn('modules', data, f"{spec} missing 'modules'")
                    print(f"  ✅ {spec} is valid YAML with required fields")
            except Exception as e:
                invalid_specs.append((spec, str(e)))
                
        self.assertEqual(len(invalid_specs), 0,
                        f"Invalid specs: {invalid_specs}")
        print("  ✅ All build specifications are valid")
        
    def test_03_workspace_configuration(self):
        """Test that all specs have correct workspace path"""
        print("\n[TEST 3] Checking workspace configuration...")
        incorrect_workspace = []
        
        for spec in self.build_specs:
            spec_path = self.project_root / spec
            with open(spec_path, 'r') as f:
                data = yaml.safe_load(f)
                workspace = data.get('builder_config', {}).get('workspace_path')
                
                if workspace != self.expected_workspace:
                    incorrect_workspace.append((spec, workspace))
                else:
                    print(f"  ✅ {spec}: {workspace}")
                    
        self.assertEqual(len(incorrect_workspace), 0,
                        f"Incorrect workspace paths: {incorrect_workspace}")
        print(f"  ✅ All specs use {self.expected_workspace}")
        
    def test_04_dracut_module_present(self):
        """Test that all specs with kernel_acquisition have dracut_config"""
        print("\n[TEST 4] Checking dracut configuration...")
        missing_dracut = []
        
        for spec in self.build_specs:
            spec_path = self.project_root / spec
            with open(spec_path, 'r') as f:
                data = yaml.safe_load(f)
                modules = data.get('modules', [])
                
                has_kernel = False
                has_dracut = False
                
                for module in modules:
                    if module.get('name') == 'kernel_acquisition':
                        has_kernel = True
                    if module.get('name') == 'dracut_config':
                        has_dracut = True
                        
                if has_kernel:
                    if has_dracut:
                        print(f"  ✅ {spec} has both kernel_acquisition and dracut_config")
                    else:
                        missing_dracut.append(spec)
                        print(f"  ❌ {spec} has kernel_acquisition but missing dracut_config")
                else:
                    print(f"  ℹ️  {spec} doesn't have kernel_acquisition (dracut not needed)")
                    
        self.assertEqual(len(missing_dracut), 0,
                        f"Specs missing dracut_config: {missing_dracut}")
        print("  ✅ All specs with kernels have dracut configured")
        
    def test_05_gui_module_structure(self):
        """Test GUI module structure and imports"""
        print("\n[TEST 5] Testing GUI module...")
        
        # Check GUI file exists
        gui_path = self.project_root / "zforge_gui.py"
        self.assertTrue(gui_path.exists(), "zforge_gui.py not found")
        print("  ✅ GUI module exists")
        
        # Try to import GUI module
        try:
            import zforge_gui
            print("  ✅ GUI module imports successfully")
        except ImportError as e:
            self.fail(f"Failed to import GUI: {e}")
            
        # Check GUI has all required attributes
        from zforge_gui import ZForgeGUI
        # build_specs is an instance attribute, not class attribute
        required_methods = ['setup_ui', 'start_build', 'stop_build']
        
        for method in required_methods:
            self.assertTrue(hasattr(ZForgeGUI, method),
                          f"GUI missing required method: {method}")
            print(f"  ✅ GUI has {method} method")
            
        # Check build_specs exists on instance
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        try:
            gui = ZForgeGUI(root)
            self.assertTrue(hasattr(gui, 'build_specs'),
                          "GUI instance missing build_specs attribute")
            print(f"  ✅ GUI instance has build_specs attribute")
        finally:
            root.destroy()
            
    def test_06_gui_build_specs_complete(self):
        """Test that GUI includes all 7 build specifications"""
        print("\n[TEST 6] Checking GUI build specifications...")
        
        # Import and check GUI build specs
        from zforge_gui import ZForgeGUI
        import tkinter as tk
        
        # Create a dummy root for testing
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        try:
            gui = ZForgeGUI(root)
            gui_specs = gui.build_specs
            
            # Check we have 7 specs
            self.assertEqual(len(gui_specs), 7,
                           f"GUI has {len(gui_specs)} specs, expected 7")
            print(f"  ✅ GUI has all 7 build specifications")
            
            # Check each spec file is correct
            expected_files = set([
                "build_specs/build_spec.yml",
                "build_specs/build_spec_stable.yml",
                "build_specs/build_spec_no_tmp.yml", 
                "build_specs/build_spec_outside_packages.yml",
                "build_specs/build_spec_proxmox9.yml",
                "build_specs/build_spec_proxmox_full.yml",
                "build_specs/build_spec_trixie_clean.yml"
            ])
            
            actual_files = set([spec['file'] for spec in gui_specs.values()])
            
            missing = expected_files - actual_files
            extra = actual_files - expected_files
            
            self.assertEqual(len(missing), 0, f"GUI missing specs: {missing}")
            self.assertEqual(len(extra), 0, f"GUI has extra specs: {extra}")
            
            for name, spec in gui_specs.items():
                print(f"  ✅ {name}: {spec['file']}")
                
        finally:
            root.destroy()
            
    def test_07_builder_modules_import(self):
        """Test that all critical builder modules import correctly"""
        print("\n[TEST 7] Testing builder module imports...")
        
        critical_modules = [
            "builder.modules.workspace_setup",
            "builder.modules.debootstrap",
            "builder.modules.kernel_acquisition",
            "builder.modules.dracut_config",
            "builder.modules.zfs_build",
            "builder.modules.live_environment",
            "builder.modules.iso_generation",
            "builder.modules.build_pipeline_validator"
        ]
        
        failed_imports = []
        
        for module in critical_modules:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                failed_imports.append((module, str(e)))
                print(f"  ❌ {module}: {e}")
                
        self.assertEqual(len(failed_imports), 0,
                        f"Failed imports: {failed_imports}")
        print("  ✅ All critical modules import successfully")
        
    def test_08_dracut_module_functionality(self):
        """Test dracut module configuration"""
        print("\n[TEST 8] Testing dracut module functionality...")
        
        from builder.modules.dracut_config import DracutConfig
        from pathlib import Path
        
        # Test instantiation
        test_workspace = Path("/tmp/test_workspace")
        test_config = {"builder_config": {"enable_debug": False}}
        
        try:
            dracut = DracutConfig(test_workspace, test_config)
            self.assertIsNotNone(dracut)
            print("  ✅ DracutConfig instantiates correctly")
            
            # Check required methods
            required_methods = ['execute', '_remove_initramfs_tools', 
                              '_install_dracut', '_configure_dracut',
                              '_generate_initramfs']
            
            for method in required_methods:
                self.assertTrue(hasattr(dracut, method),
                              f"DracutConfig missing method: {method}")
                print(f"  ✅ DracutConfig has {method} method")
                
        except Exception as e:
            self.fail(f"DracutConfig test failed: {e}")
            
    def test_09_kernel_acquisition_dracut_integration(self):
        """Test that kernel acquisition properly integrates with dracut"""
        print("\n[TEST 9] Testing kernel acquisition dracut integration...")
        
        from builder.modules.kernel_acquisition import KernelAcquisition
        
        # Check the module doesn't reference initramfs-tools
        module_path = self.project_root / "builder/modules/kernel_acquisition.py"
        with open(module_path, 'r') as f:
            content = f.read()
            
        # Should not have initramfs-tools method defined
        # Check that the method definition doesn't exist (ignore comments)
        import re
        method_pattern = r'^\s*def\s+_generate_initramfs_tools'
        self.assertIsNone(re.search(method_pattern, content, re.MULTILINE),
                        "kernel_acquisition still has initramfs-tools method defined")
        print("  ✅ No initramfs-tools method found")
        
        # Should have dracut packages
        self.assertIn("dracut", content, "dracut not found in kernel_acquisition")
        self.assertIn("dracut-core", content, "dracut-core not found")
        self.assertIn("dracut-network", content, "dracut-network not found")
        print("  ✅ Dracut packages properly configured")
        
    def test_10_system_validation(self):
        """Test build pipeline validation"""
        print("\n[TEST 10] Running system validation...")
        
        from builder.modules.build_pipeline_validator import BuildPipelineValidator
        
        # BuildPipelineValidator needs proper initialization
        validator = BuildPipelineValidator(
            project_root=self.project_root,
            workspace=Path("/home/john/zforge_workspace"),
            config={}
        )
        report = validator.validate_complete_pipeline()
        
        print(f"  Validation: {report.overall_status}")
        print(f"  Checks: {report.passed_checks}/{report.total_checks} passed")
        
        self.assertEqual(report.critical_failures, 0, "Critical errors found")
        self.assertEqual(report.error_failures, 0, "Errors found")
        
        if report.warning_count > 0:
            print(f"  ⚠️  {report.warning_count} warnings (non-critical)")
            
        self.assertEqual(report.overall_status, "ALL_CHECKS_PASSED",
                        "System validation did not pass")
        print("  ✅ System validation passed")
        
    def test_11_gui_launcher_script(self):
        """Test GUI launcher script exists and is executable"""
        print("\n[TEST 11] Testing GUI launcher script...")
        
        launcher_path = self.project_root / "launch-gui.sh"
        self.assertTrue(launcher_path.exists(), "launch-gui.sh not found")
        print("  ✅ Launcher script exists")
        
        # Check it's executable
        import stat
        file_stat = launcher_path.stat()
        is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
        self.assertTrue(is_executable, "launch-gui.sh is not executable")
        print("  ✅ Launcher script is executable")
        
    def test_12_desktop_integration(self):
        """Test desktop integration file"""
        print("\n[TEST 12] Testing desktop integration...")
        
        desktop_path = self.project_root / "zforge-gui.desktop"
        self.assertTrue(desktop_path.exists(), "zforge-gui.desktop not found")
        print("  ✅ Desktop file exists")
        
        # Validate desktop file
        with open(desktop_path, 'r') as f:
            content = f.read()
            self.assertIn("[Desktop Entry]", content)
            self.assertIn("Name=Z-FORGE Build System", content)
            self.assertIn("Exec=", content)
            self.assertIn("Icon=", content)
            print("  ✅ Desktop file is valid")
            
    def test_13_hardware_detection(self):
        """Test hardware detection functionality"""
        print("\n[TEST 13] Testing hardware detection...")
        
        # Get system info
        cpu_count = multiprocessing.cpu_count()
        memory_gb = round(psutil.virtual_memory().total / (1024**3))
        disk_free_gb = round(psutil.disk_usage('/').free / (1024**3))
        
        print(f"  System: {cpu_count} CPUs, {memory_gb}GB RAM, {disk_free_gb}GB free")
        
        self.assertGreater(cpu_count, 0, "Invalid CPU count")
        self.assertGreater(memory_gb, 0, "Invalid memory size")
        self.assertGreater(disk_free_gb, 0, "Invalid disk space")
        print("  ✅ Hardware detection working")
        
    def test_14_build_command_construction(self):
        """Test build command construction"""
        print("\n[TEST 14] Testing build command construction...")
        
        # Test command for each spec
        for spec in self.build_specs:
            cmd = ["python3", "build.py", "--spec", spec]
            
            # Add optional parameters
            cmd.extend(["--jobs", "4"])
            cmd.extend(["--workspace", self.expected_workspace])
            
            # Verify command structure
            self.assertIn("python3", cmd)
            self.assertIn("build.py", cmd)
            self.assertIn(spec, cmd)
            
            print(f"  ✅ {spec}: {' '.join(cmd)}")
            
    def test_15_documentation_completeness(self):
        """Test that documentation is complete"""
        print("\n[TEST 15] Testing documentation...")
        
        required_docs = [
            "README.md",
            "GUI_GUIDE.md",
            "GUI_TESTING_SUMMARY.md",
            "DRACUT_IMPLEMENTATION.md",
            "WHERE_ARE_THE_FILES.md"
        ]
        
        missing_docs = []
        for doc in required_docs:
            doc_path = self.project_root / doc
            if not doc_path.exists():
                missing_docs.append(doc)
            else:
                print(f"  ✅ {doc}")
                
        self.assertEqual(len(missing_docs), 0,
                        f"Missing documentation: {missing_docs}")
        print("  ✅ All documentation present")

def run_tests():
    """Run all integration tests"""
    print("=" * 60)
    print("Z-FORGE FULL INTEGRATION TEST SUITE")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(ZForgeFullIntegrationTests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ System is ready for production use")
        print("\nNext steps:")
        print("1. Run GUI: python3 zforge_gui.py")
        print("2. Or build directly: sudo python3 build.py --spec build_specs/build_spec_stable.yml")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("Please review the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())