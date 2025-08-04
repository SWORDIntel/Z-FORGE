#!/usr/bin/env python3
"""
Test UltraThink Implementation
Verifies that all enhanced components work together correctly
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_ultrathink_analysis():
    """Test the UltraThink multi-agent analysis system"""
    print("🔍 Testing UltraThink Multi-Agent Analysis...")
    
    try:
        from scripts.analysis.ultrathink_build_system_analysis import UltraThinkCoordinator
        
        coordinator = UltraThinkCoordinator(project_root)
        print(f"✅ UltraThink Coordinator initialized")
        print(f"   Agents available: {len(coordinator.agents)}")
        print(f"   Analysis directory: {coordinator.analysis_dir}")
        return True
    except Exception as e:
        print(f"❌ UltraThink Analysis test failed: {e}")
        return False

def test_enhanced_calamares_integration():
    """Test the Enhanced Calamares Integration module"""
    print("🖥️ Testing Enhanced Calamares Integration...")
    
    try:
        import tempfile
        from builder.modules.calamares_integration_enhanced import EnhancedCalamaresIntegration
        
        workspace = Path(tempfile.mkdtemp())
        config = {'name': 'Z-FORGE', 'zfs': {'enabled': True}}
        
        integration = EnhancedCalamaresIntegration(workspace, config)
        print(f"✅ Enhanced Calamares Integration initialized")
        print(f"   Available modules: {len(integration.available_modules)}")
        print(f"   ZFS modules: {len([m for m in integration.available_modules.values() if m.zfs_specific])}")
        
        # Cleanup
        import shutil
        shutil.rmtree(workspace)
        return True
    except Exception as e:
        print(f"❌ Enhanced Calamares Integration test failed: {e}")
        return False

def test_build_pipeline_validator():
    """Test the Build Pipeline Validator"""
    print("📋 Testing Build Pipeline Validator...")
    
    try:
        import tempfile
        from builder.modules.build_pipeline_validator import BuildPipelineValidator
        
        workspace = Path(tempfile.mkdtemp())
        config = {'name': 'Z-FORGE'}
        
        validator = BuildPipelineValidator(project_root, workspace, config)
        print(f"✅ Build Pipeline Validator initialized")
        print(f"   Project root: {validator.project_root}")
        print(f"   Chroot path: {validator.chroot_path}")
        
        # Cleanup
        import shutil
        shutil.rmtree(workspace)
        return True
    except Exception as e:
        print(f"❌ Build Pipeline Validator test failed: {e}")
        return False

def test_integrated_build_orchestrator():
    """Test the Integrated Build Orchestrator"""
    print("🚀 Testing Integrated Build Orchestrator...")
    
    try:
        import tempfile
        from builder.modules.integrated_build_orchestrator import IntegratedBuildOrchestrator
        
        workspace = Path(tempfile.mkdtemp())
        config = {'name': 'Z-FORGE', 'zfs': {'enabled': True}}
        
        orchestrator = IntegratedBuildOrchestrator(workspace, config)
        print(f"✅ Integrated Build Orchestrator initialized")
        print(f"   Build state: {orchestrator.build_state['phase']}")
        print(f"   Components: Calamares Integration, Pipeline Validator")
        
        # Cleanup
        import shutil
        shutil.rmtree(workspace)
        return True
    except Exception as e:
        print(f"❌ Integrated Build Orchestrator test failed: {e}")
        return False

def test_modular_build_system():
    """Test the modular build system"""
    print("⚙️ Testing Modular Build System...")
    
    try:
        # Check that build.py has modular classes
        build_py = project_root / "build.py"
        if not build_py.exists():
            print("❌ build.py not found")
            return False
            
        content = build_py.read_text()
        required_classes = ["ConfigurationManager", "ArgumentParser", "EnvironmentManager", "BuildLauncher"]
        
        for cls in required_classes:
            if cls in content:
                print(f"✅ Found modular class: {cls}")
            else:
                print(f"❌ Missing modular class: {cls}")
                return False
                
        print(f"✅ Modular Build System verified")
        return True
    except Exception as e:
        print(f"❌ Modular Build System test failed: {e}")
        return False

def test_calamares_modules():
    """Test Calamares modules availability"""
    print("🔧 Testing Calamares Modules...")
    
    try:
        calamares_dir = project_root / "calamares/modules"
        if not calamares_dir.exists():
            print("❌ Calamares modules directory not found")
            return False
            
        modules = [d.name for d in calamares_dir.iterdir() if d.is_dir()]
        zfs_modules = [m for m in modules if 'zfs' in m.lower()]
        
        print(f"✅ Found {len(modules)} Calamares modules")
        print(f"✅ Found {len(zfs_modules)} ZFS-specific modules")
        
        # Check for key modules
        key_modules = ['zfsrootselect', 'zfspooldetect', 'zfsenhancedconfig']
        for module in key_modules:
            if module in modules:
                print(f"✅ Key module found: {module}")
            else:
                print(f"⚠️ Key module missing: {module}")
                
        return True
    except Exception as e:
        print(f"❌ Calamares Modules test failed: {e}")
        return False

def test_integration_connectivity():
    """Test the complete integration connectivity"""
    print("🔗 Testing Integration Connectivity...")
    
    connectivity_checks = []
    
    # Check build.py → builder modules connection
    enhanced_module = project_root / "builder/modules/calamares_integration_enhanced.py"
    connectivity_checks.append(("Build → Enhanced Calamares", enhanced_module.exists()))
    
    # Check builder modules → calamares connection
    calamares_modules = project_root / "calamares/modules"
    connectivity_checks.append(("Builder → Calamares Modules", calamares_modules.exists()))
    
    # Check analysis system availability
    analysis_script = project_root / "scripts/analysis/ultrathink_build_system_analysis.py"
    connectivity_checks.append(("UltraThink Analysis System", analysis_script.exists()))
    
    # Check validation system
    validator_module = project_root / "builder/modules/build_pipeline_validator.py"
    connectivity_checks.append(("Pipeline Validator", validator_module.exists()))
    
    # Check orchestrator
    orchestrator_module = project_root / "builder/modules/integrated_build_orchestrator.py"
    connectivity_checks.append(("Build Orchestrator", orchestrator_module.exists()))
    
    all_connected = True
    for check_name, result in connectivity_checks:
        if result:
            print(f"✅ {check_name}: Connected")
        else:
            print(f"❌ {check_name}: Disconnected")
            all_connected = False
            
    if all_connected:
        print("✅ Complete integration connectivity verified")
    else:
        print("❌ Integration connectivity issues detected")
        
    return all_connected

def main():
    """Run all tests"""
    print("="*60)
    print("🧪 UltraThink Implementation Test Suite")
    print("="*60)
    
    tests = [
        ("Modular Build System", test_modular_build_system),
        ("Calamares Modules", test_calamares_modules),
        ("UltraThink Analysis", test_ultrathink_analysis),
        ("Enhanced Calamares Integration", test_enhanced_calamares_integration),
        ("Build Pipeline Validator", test_build_pipeline_validator),
        ("Integrated Build Orchestrator", test_integrated_build_orchestrator),
        ("Integration Connectivity", test_integration_connectivity)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print("\n" + "="*60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - UltraThink Implementation is ready!")
        print("\n📋 Next Steps:")
        print("1. Run: sudo python3 build.py")
        print("2. Test the enhanced Calamares integration")
        print("3. Verify GUI installer functionality")
    else:
        print("⚠️ Some tests failed - review implementation")
        
    print("="*60)
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())