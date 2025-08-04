#!/usr/bin/env python3
"""
Test GUI Connectivity Chain
Verifies the complete chain from build system to Calamares GUI
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from builder.modules.integrated_build_orchestrator import IntegratedBuildOrchestrator
import logging

logging.basicConfig(level=logging.INFO)

def test_connectivity():
    """Test the GUI connectivity chain"""
    print("🔗 Testing GUI Connectivity Chain")
    print("=" * 60)
    
    # Create orchestrator
    workspace = Path.home() / "zforge_workspace"
    config = {
        'builder_config': {
            'workspace_path': str(workspace)
        }
    }
    orchestrator = IntegratedBuildOrchestrator(workspace, config)
    
    # Test connectivity
    result = orchestrator._verify_gui_connectivity()
    
    # Display results
    print("\n📊 Connectivity Test Results:")
    print(f"Complete Chain Connected: {'✅' if result['complete_chain_connected'] else '❌'}")
    print(f"Connectivity Score: {result['connectivity_score']*100:.2f}%")
    
    print("\n🔗 Connection Status:")
    for key, value in result['individual_connections'].items():
        status = '✅' if value else '❌'
        print(f"  {status} {key}: {value}")
    
    print("\n📋 Integration Matrix:")
    matrix = orchestrator._get_integration_matrix()
    
    for component, details in matrix.items():
        print(f"\n{component}:")
        for key, value in details.items():
            if isinstance(value, list):
                print(f"  {key}: {', '.join(map(str, value[:3]))}...")
            else:
                print(f"  {key}: {value}")
    
    # Check what's missing for full connectivity
    if not result['complete_chain_connected']:
        print("\n⚠️ Missing Components for Full Connectivity:")
        
        if not result['individual_connections']['modules_to_calamares']:
            print("  - Calamares modules not deployed")
            print("    Fix: Run calamares_integration module")
        
        if not result['individual_connections']['calamares_to_gui']:
            print("  - Calamares GUI not configured")
            print("    Fix: Install Calamares and configure settings.conf")
        
        if not result['individual_connections']['live_environment_gui']:
            print("  - Live environment missing desktop")
            print("    Fix: Run desktop_environment module")
            print("    Fix: Install display manager (lightdm/gdm)")
    
    return result

def suggest_next_steps(result):
    """Suggest next steps based on connectivity test"""
    print("\n📝 Next Steps:")
    
    if result['complete_chain_connected']:
        print("✅ GUI connectivity chain is complete!")
        print("   You can now build a live ISO with full Calamares GUI support")
        print("   Run: sudo ./scripts/build/build_live_environment.sh")
    else:
        print("To complete the GUI connectivity chain:")
        print("1. Ensure all modules are properly configured in build_spec.yml")
        print("2. Run a test build to create the chroot environment")
        print("3. Execute the live environment builder:")
        print("   sudo ./scripts/build/build_live_environment.sh")
        print("4. The script will:")
        print("   - Install desktop environment")
        print("   - Configure Calamares GUI")
        print("   - Create bootable ISO")
        print("   - Test connectivity")

if __name__ == "__main__":
    result = test_connectivity()
    suggest_next_steps(result)
    
    # Exit with appropriate code
    sys.exit(0 if result['complete_chain_connected'] else 1)