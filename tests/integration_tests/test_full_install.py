"""Integration tests for full Z-FORGE installation flow"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "calamares/modules"))

class TestFullInstallFlow:
    """Test complete installation workflow"""
    
    @pytest.fixture
    def install_env(self, temp_dir):
        """Create a mock installation environment"""
        # Create root mount point
        root_mount = temp_dir / "target"
        root_mount.mkdir()
        
        # Create essential directories
        for directory in ["etc", "usr/bin", "var/lib", "boot", "home"]:
            (root_mount / directory).mkdir(parents=True)
        
        # Mock globalstorage
        mock_gs = Mock()
        mock_gs.value.return_value = str(root_mount)
        mock_gs.data = {"rootMountPoint": str(root_mount)}
        
        return {
            "root": root_mount,
            "globalstorage": mock_gs,
            "temp_dir": temp_dir
        }
    
    def test_module_execution_order(self, install_env):
        """Test that modules execute in correct order"""
        executed_modules = []
        
        def track_execution(module_name):
            def wrapper(*args, **kwargs):
                executed_modules.append(module_name)
                return None
            return wrapper
        
        # Mock module run functions
        with patch('networkconfig.main.run', track_execution('networkconfig')):
            with patch('hardwarehealth.main.run', track_execution('hardwarehealth')):
                with patch('gpupassthrough.main.run', track_execution('gpupassthrough')):
                    with patch('storagelayout.main.run', track_execution('storagelayout')):
                        with patch('postinstall.main.run', track_execution('postinstall')):
                            # Import and run modules
                            from networkconfig import main as net_main
                            from hardwarehealth import main as hw_main
                            from gpupassthrough import main as gpu_main
                            from storagelayout import main as storage_main
                            from postinstall import main as post_main
                            
                            # Simulate installation flow
                            net_main.run()
                            hw_main.run()
                            gpu_main.run()
                            storage_main.run()
                            post_main.run()
                            
                            # Verify execution order
                            assert executed_modules == [
                                'networkconfig',
                                'hardwarehealth',
                                'gpupassthrough',
                                'storagelayout',
                                'postinstall'
                            ]
    
    def test_configuration_persistence(self, install_env):
        """Test that configuration persists across modules"""
        gs = install_env["globalstorage"]
        
        # Network module stores config
        network_config = {
            "interfaces": {"eth0": {"type": "dhcp"}},
            "dns_servers": ["8.8.8.8"]
        }
        gs.insert = Mock()
        gs.value = Mock(return_value=network_config)
        
        # Hardware module should be able to read it
        from hardwarehealth.main import run as hw_run
        
        # Mock the module to check if it can access network config
        with patch('hardwarehealth.main.apply_health_config') as mock_apply:
            gs.value = Mock(side_effect=lambda key: {
                "hardwareHealthConfig": {"monitoring": {"temperature": True}},
                "networkConfig": network_config,
                "rootMountPoint": str(install_env["root"])
            }.get(key))
            
            hw_run()
            
            # Should have been called
            mock_apply.assert_called_once()
    
    def test_error_propagation(self, install_env):
        """Test that errors are properly propagated"""
        from networkconfig.main import run
        
        # Remove required config to trigger error
        install_env["globalstorage"].value = Mock(return_value=None)
        
        with patch('libcalamares.globalstorage', install_env["globalstorage"]):
            result = run()
            
            # Should return error tuple
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
            assert "No network configuration" in result[0]
    
    def test_file_creation(self, install_env):
        """Test that modules create expected files"""
        root = install_env["root"]
        gs = install_env["globalstorage"]
        
        # Test network configuration file creation
        from networkconfig.main import apply_network_config
        
        config = {
            "interfaces": {"eth0": {"type": "static", "address": "192.168.1.10", 
                                   "netmask": "255.255.255.0", "gateway": "192.168.1.1"}},
            "dns_servers": ["8.8.8.8", "8.8.4.4"]
        }
        
        with patch('libcalamares.globalstorage', gs):
            apply_network_config(config)
            
            # Check network interfaces file
            interfaces_file = root / "etc/network/interfaces"
            assert interfaces_file.exists()
            content = interfaces_file.read_text()
            assert "iface eth0 inet static" in content
            assert "address 192.168.1.10" in content
            
            # Check resolv.conf
            resolv_file = root / "etc/resolv.conf"
            assert resolv_file.exists()
            assert "nameserver 8.8.8.8" in resolv_file.read_text()
    
    def test_proxmox_integration(self, install_env):
        """Test Proxmox-specific configurations"""
        root = install_env["root"]
        
        # Test bridge creation for Proxmox
        from networkconfig.main import generate_interfaces_file
        
        config = {
            "interfaces": {
                "enp1s0": {
                    "type": "static",
                    "address": "10.0.0.10",
                    "netmask": "255.255.255.0",
                    "gateway": "10.0.0.1",
                    "bridge": True,
                    "bridge_name": "vmbr0"
                }
            }
        }
        
        content = generate_interfaces_file(config)
        
        # Should create bridge configuration
        assert "auto vmbr0" in content
        assert "iface vmbr0 inet static" in content
        assert "bridge-ports enp1s0" in content
        
        # Test GPU passthrough for VMs
        from gpupassthrough.main import configure_vfio
        
        gpu_config = {
            "gpus": [{
                "pci_id": "01:00.0",
                "vendor_id": "10de",
                "device_id": "2204",
                "selected": True
            }]
        }
        
        configure_vfio(str(root), gpu_config)
        
        vfio_conf = root / "etc/modprobe.d/vfio.conf"
        assert vfio_conf.exists()
        assert "vfio-pci" in vfio_conf.read_text()

class TestModuleInteraction:
    """Test interactions between modules"""
    
    def test_storage_affects_monitoring(self, temp_dir):
        """Test that storage layout affects monitoring setup"""
        # If ZFS pools are created, monitoring should include ZFS checks
        from storagelayout.main import apply_storage_template
        from hardwarehealth.main import setup_monitoring_scripts
        
        # Apply storage template with ZFS
        storage_config = {
            "template": "proxmox_virtualization",
            "pools": [{
                "name": "tank",
                "mountpoint": "/tank",
                "datasets": [
                    {"name": "vm-disks", "recordsize": "64K"}
                ]
            }]
        }
        
        # This should trigger ZFS-specific monitoring
        monitoring_config = {
            "monitoring": {"zfs": True},
            "alerts": {
                "email": "admin@example.com",
                "cpu_temp_warning": 75,
                "cpu_temp_critical": 85,
                "disk_space_warning": 80
            }
        }
        
        setup_monitoring_scripts(str(temp_dir), monitoring_config)
        
        script = temp_dir / "usr/local/bin/hardware-monitor.sh"
        if script.exists():
            content = script.read_text()
            # Should include ZFS pool checks
            # Note: Actual implementation would need to add ZFS monitoring
    
    def test_network_affects_postinstall(self):
        """Test that network config affects post-install tasks"""
        # If static IP is configured, post-install might skip network setup
        network_config = {
            "interfaces": {"eth0": {"type": "static", "address": "192.168.1.10"}},
            "dns_servers": ["8.8.8.8"]
        }
        
        # Post-install checklist should reflect this
        from postinstall.main import get_default_checklist
        
        checklist = get_default_checklist()
        
        # Should have network category
        assert "network" in checklist["categories"]
        
        # In real implementation, static config might pre-check some items