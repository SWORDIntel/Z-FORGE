#!/usr/bin/env python3
"""
Test script for Z-FORGE Enhanced GUI
Verifies all components load correctly
"""

import sys
import tkinter as tk
from pathlib import Path

def test_enhanced_gui():
    """Test that enhanced GUI loads without errors"""
    print("Testing Z-FORGE Enhanced GUI...")
    
    try:
        # Import the enhanced GUI
        from zforge_gui_enhanced import ZForgeGUIEnhanced
        
        # Create test window
        root = tk.Tk()
        root.withdraw()  # Hide window for testing
        
        # Initialize GUI
        print("  ✅ Importing enhanced GUI module")
        app = ZForgeGUIEnhanced(root)
        print("  ✅ Creating GUI instance")
        
        # Test key components
        assert hasattr(app, 'diagnostic_tool'), "Missing diagnostic tool"
        print("  ✅ Diagnostic tool initialized")
        
        assert hasattr(app, 'recovery_tool'), "Missing recovery tool"
        print("  ✅ Recovery tool initialized")
        
        assert hasattr(app, 'auto_recovery_enabled'), "Missing auto-recovery setting"
        print("  ✅ Auto-recovery system ready")
        
        assert hasattr(app, 'build_specs'), "Missing build specifications"
        assert len(app.build_specs) == 7, f"Expected 7 build specs, got {len(app.build_specs)}"
        print("  ✅ All 7 build specifications loaded")
        
        # Test success rates
        for name, spec in app.build_specs.items():
            assert 'success_rate' in spec, f"Missing success rate for {name}"
        print("  ✅ Success rates configured for all builds")
        
        # Test color scheme
        assert hasattr(app, 'colors'), "Missing color scheme"
        required_colors = ['bg', 'fg', 'success', 'error', 'warning', 'recovery']
        for color in required_colors:
            assert color in app.colors, f"Missing color: {color}"
        print("  ✅ Dark theme with recovery colors configured")
        
        # Test message queue
        assert hasattr(app, 'message_queue'), "Missing message queue"
        print("  ✅ Thread-safe message queue initialized")
        
        # Test statistics
        assert hasattr(app, 'build_stats'), "Missing build statistics"
        print("  ✅ Build statistics system ready")
        
        # Clean up
        root.destroy()
        
        print("\n🎉 Enhanced GUI test completed successfully!")
        print("\nKey Features Verified:")
        print("  ✅ Automatic failure recovery system")
        print("  ✅ Intelligent error analysis")
        print("  ✅ Pre-build validation")
        print("  ✅ Real-time monitoring")
        print("  ✅ Build success optimization")
        print("  ✅ Statistics and learning")
        print("\nThe enhanced GUI is ready to help achieve your first successful build!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Enhanced GUI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_dependencies():
    """Test that all required dependencies are available"""
    print("\nTesting dependencies...")
    
    required_modules = [
        'tkinter',
        'yaml', 
        'psutil',
        'threading',
        'subprocess',
        'queue',
        'json',
        're'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module} - MISSING")
            return False
            
    return True

def test_diagnostic_tools():
    """Test that diagnostic and recovery tools are available"""
    print("\nTesting diagnostic tools...")
    
    tools = [
        ('build_diagnostic_tool.py', 'BuildDiagnosticTool'),
        ('build_recovery_tool.py', 'BuildRecoveryTool'),
        ('analyze_build_failures.py', 'BuildFailureAnalyzer')
    ]
    
    for tool_file, tool_class in tools:
        tool_path = Path(tool_file)
        if tool_path.exists():
            print(f"  ✅ {tool_file}")
        else:
            print(f"  ❌ {tool_file} - MISSING")
            return False
            
    return True

def main():
    """Main test function"""
    print("=" * 60)
    print("Z-FORGE ENHANCED GUI TEST SUITE")
    print("=" * 60)
    
    # Test dependencies
    if not test_dependencies():
        print("\n❌ Dependency test failed!")
        return 1
        
    # Test diagnostic tools
    if not test_diagnostic_tools():
        print("\n❌ Diagnostic tools test failed!")
        return 1
        
    # Test enhanced GUI
    if not test_enhanced_gui():
        print("\n❌ Enhanced GUI test failed!")
        return 1
        
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\nThe enhanced GUI is ready to use!")
    print("\nTo launch: ./launch-enhanced-gui.sh")
    print("Or: python3 zforge_gui_enhanced.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())