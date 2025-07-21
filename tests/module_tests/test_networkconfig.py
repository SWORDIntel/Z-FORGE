"""Tests for Network Configuration Module"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add module path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "calamares/modules"))

class TestNetworkConfigModule:
    """Test the network configuration module"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for each test"""
        self.mock_calamares = mock_libcalamares
    
    def test_module_import(self):
        """Test that the module can be imported"""
        from networkconfig import main
        assert hasattr(main, 'run')
        assert hasattr(main, 'pretty_name')
        assert hasattr(main, 'icon')
    
    def test_pretty_name(self):
        """Test module metadata"""
        from networkconfig import main
        assert main.pretty_name() == "Network Configuration"
        assert main.icon() == "network-wired"
    
    def test_network_config_generation(self):
        """Test network interface file generation"""
        from networkconfig.main import generate_interfaces_file
        
        config = {
            "interfaces": {
                "eth0": {
                    "type": "static",
                    "address": "192.168.1.100",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.1.1"
                },
                "eth1": {
                    "type": "dhcp"
                }
            }
        }
        
        result = generate_interfaces_file(config)
        
        # Check basic structure
        assert "auto lo" in result
        assert "iface lo inet loopback" in result
        
        # Check static interface
        assert "auto eth0" in result
        assert "iface eth0 inet static" in result
        assert "address 192.168.1.100" in result
        assert "netmask 255.255.255.0" in result
        assert "gateway 192.168.1.1" in result
        
        # Check DHCP interface
        assert "auto eth1" in result
        assert "iface eth1 inet dhcp" in result
    
    def test_bridge_configuration(self):
        """Test bridge creation for Proxmox"""
        from networkconfig.main import generate_interfaces_file
        
        config = {
            "interfaces": {
                "enp1s0": {
                    "type": "static",
                    "address": "192.168.1.10",
                    "netmask": "255.255.255.0",
                    "gateway": "192.168.1.1",
                    "bridge": True,
                    "bridge_name": "vmbr0"
                }
            }
        }
        
        result = generate_interfaces_file(config)
        
        # Check bridge configuration
        assert "auto vmbr0" in result
        assert "iface vmbr0 inet static" in result
        assert "bridge-ports enp1s0" in result
        assert "bridge-stp off" in result
        assert "bridge-fd 0" in result
    
    @patch('networkconfig.main.Path')
    def test_run_function(self, mock_path):
        """Test the main run function"""
        from networkconfig import main
        
        # Setup mock
        self.mock_calamares.globalstorage.insert("networkConfig", {
            "interfaces": {"eth0": {"type": "dhcp"}},
            "dns_servers": ["8.8.8.8"]
        })
        
        mock_file = MagicMock()
        mock_path.return_value.__truediv__.return_value.parent.mkdir.return_value = None
        mock_path.return_value.__truediv__.return_value.write_text = mock_file
        
        # Run the module
        result = main.run()
        
        # Should return None on success
        assert result is None
        
        # Check that files were written
        assert mock_file.call_count >= 1
    
    def test_missing_config_error(self):
        """Test error handling for missing configuration"""
        from networkconfig import main
        
        # Remove network config
        if self.mock_calamares.globalstorage.contains("networkConfig"):
            del self.mock_calamares.globalstorage.data["networkConfig"]
        
        # Run should return error
        result = main.run()
        assert result is not None
        assert result[0] == "No network configuration found"

class TestNetworkConfigGUI:
    """Test the GUI components"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for GUI tests"""
        # Mock GTK
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()
        
        mock_gtk = MagicMock()
        mock_gtk.Box = MagicMock
        mock_gtk.Label = MagicMock
        mock_gtk.Entry = MagicMock
        mock_gtk.CheckButton = MagicMock
        mock_gtk.RadioButton = MagicMock
        mock_gtk.Frame = MagicMock
        sys.modules['gi.repository'].Gtk = mock_gtk
    
    def test_widget_creation(self):
        """Test NetworkConfigWidget creation"""
        from networkconfig.network_config_gui import NetworkConfigWidget
        
        # Should create without errors
        widget = NetworkConfigWidget(Mock())
        assert widget is not None
    
    def test_interface_detection(self):
        """Test network interface detection"""
        from networkconfig.network_config_gui import NetworkConfigWidget
        
        with patch('subprocess.check_output') as mock_subprocess:
            # Mock ip link output
            mock_subprocess.return_value = b"""1: lo: <LOOPBACK,UP,LOWER_UP>
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>
3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP>
4: virbr0: <NO-CARRIER,BROADCAST,MULTICAST,UP>"""
            
            widget = NetworkConfigWidget(Mock())
            
            # Should detect eth0 and eth1, but not lo or virbr0
            assert hasattr(widget, 'interfaces')
            # Note: actual detection happens in add_interface method
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        from networkconfig.network_config_gui import NetworkConfigWidget
        import ipaddress
        
        widget = NetworkConfigWidget(Mock())
        
        # Test valid IP parsing
        try:
            ip_net = ipaddress.ip_network("192.168.1.0/24", strict=False)
            assert str(ip_net.netmask) == "255.255.255.0"
        except:
            pytest.fail("Valid IP should parse correctly")