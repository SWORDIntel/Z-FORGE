"""Tests for Hardware Health Monitor Module"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "calamares/modules"))

class TestHardwareHealthModule:
    """Test the hardware health monitoring module"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for each test"""
        self.mock_calamares = mock_libcalamares
    
    def test_module_import(self):
        """Test that the module can be imported"""
        from hardwarehealth import main
        assert hasattr(main, 'run')
        assert hasattr(main, 'configure_smartd')
        assert hasattr(main, 'configure_sensors')
    
    def test_default_config(self):
        """Test default configuration generation"""
        from hardwarehealth.main import get_default_config
        
        config = get_default_config()
        
        # Check structure
        assert "monitoring" in config
        assert "alerts" in config
        assert "services" in config
        
        # Check defaults
        assert config["monitoring"]["temperature"] == True
        assert config["monitoring"]["smart"] == True
        assert config["alerts"]["cpu_temp_warning"] == 75
        assert config["alerts"]["cpu_temp_critical"] == 85
    
    def test_smartd_configuration(self, temp_dir):
        """Test SMART monitoring configuration"""
        from hardwarehealth.main import configure_smartd
        
        config = {
            "alerts": {
                "disk_temp_warning": 45,
                "email": "admin@example.com"
            }
        }
        
        configure_smartd(str(temp_dir), config)
        
        smartd_conf = temp_dir / "etc/smartd.conf"
        assert smartd_conf.exists()
        
        content = smartd_conf.read_text()
        assert "DEVICESCAN" in content
        assert "-W 4,45,55" in content  # Temperature thresholds
        assert "-m admin@example.com" in content
    
    def test_sensors_configuration(self, temp_dir):
        """Test lm-sensors configuration"""
        from hardwarehealth.main import configure_sensors
        
        config = {
            "alerts": {
                "cpu_temp_warning": 70,
                "cpu_temp_critical": 80
            }
        }
        
        configure_sensors(str(temp_dir), config)
        
        sensors_conf = temp_dir / "etc/sensors3.conf"
        assert sensors_conf.exists()
        
        content = sensors_conf.read_text()
        assert "set temp1_max 70" in content
        assert "set temp1_crit 80" in content
    
    def test_ipmi_script_creation(self, temp_dir):
        """Test IPMI monitoring script creation"""
        from hardwarehealth.main import configure_ipmi
        
        config = {
            "alerts": {
                "cpu_temp_warning": 75
            }
        }
        
        configure_ipmi(str(temp_dir), config)
        
        script_path = temp_dir / "usr/local/bin/ipmi-monitor.sh"
        assert script_path.exists()
        assert script_path.stat().st_mode & 0o111  # Check executable
        
        content = script_path.read_text()
        assert "ipmitool sdr type temperature" in content
        assert '"$temp" -gt "75"' in content
    
    def test_monitoring_scripts(self, temp_dir):
        """Test monitoring script generation"""
        from hardwarehealth.main import setup_monitoring_scripts
        
        config = {
            "alerts": {
                "email": "ops@company.com",
                "cpu_temp_warning": 72,
                "cpu_temp_critical": 82,
                "disk_space_warning": 85
            }
        }
        
        setup_monitoring_scripts(str(temp_dir), config)
        
        # Check main monitoring script
        monitor_script = temp_dir / "usr/local/bin/hardware-monitor.sh"
        assert monitor_script.exists()
        assert monitor_script.stat().st_mode & 0o111
        
        content = monitor_script.read_text()
        assert 'ALERT_EMAIL="ops@company.com"' in content
        assert "CPU_WARN=72" in content
        assert "CPU_CRIT=82" in content
        assert "DISK_WARN=85" in content
        
        # Check cron job
        cron_file = temp_dir / "etc/cron.d/hardware-monitoring"
        assert cron_file.exists()
        assert "*/5 * * * *" in cron_file.read_text()
    
    @patch('hardwarehealth.main.Path')
    def test_run_function(self, mock_path):
        """Test the main run function"""
        from hardwarehealth import main
        
        # Setup config
        self.mock_calamares.globalstorage.insert("hardwareHealthConfig", {
            "monitoring": {
                "temperature": True,
                "smart": True
            },
            "alerts": {
                "email": "test@example.com"
            }
        })
        
        # Mock file operations
        mock_path.return_value.parent.mkdir.return_value = None
        mock_path.return_value.write_text = MagicMock()
        mock_path.return_value.chmod = MagicMock()
        
        # Run the module
        result = main.run()
        
        # Should succeed
        assert result is None
    
    def test_raid_monitoring(self):
        """Test RAID monitoring configuration"""
        from hardwarehealth.main import setup_monitoring_scripts
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "monitoring": {"raid": True},
                "alerts": {
                    "email": "raid@example.com",
                    "cpu_temp_warning": 75,
                    "cpu_temp_critical": 85,
                    "disk_space_warning": 80
                }
            }
            
            setup_monitoring_scripts(temp_dir, config)
            
            script = Path(temp_dir) / "usr/local/bin/hardware-monitor.sh"
            content = script.read_text()
            
            # Should include RAID monitoring
            assert "check_raid_status" in content
            assert "megacli" in content

class TestHardwareHealthGUI:
    """Test the GUI components"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for GUI tests"""
        # Mock GTK
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()
        
        mock_gtk = MagicMock()
        sys.modules['gi.repository'].Gtk = mock_gtk
    
    def test_widget_creation(self):
        """Test HardwareHealthWidget creation"""
        from hardwarehealth.hardware_health_gui import HardwareHealthWidget
        
        widget = HardwareHealthWidget(Mock())
        assert widget is not None
        assert hasattr(widget, 'config')
    
    def test_configuration_structure(self):
        """Test configuration data structure"""
        from hardwarehealth.hardware_health_gui import HardwareHealthWidget
        
        widget = HardwareHealthWidget(Mock())
        
        # Check initial config structure
        assert "monitoring" in widget.config
        assert "alerts" in widget.config
        assert "services" in widget.config