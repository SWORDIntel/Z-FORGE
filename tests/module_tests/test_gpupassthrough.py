"""Tests for GPU Passthrough Module"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "calamares/modules"))

class TestGPUPassthroughModule:
    """Test the GPU passthrough configuration module"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for each test"""
        self.mock_calamares = mock_libcalamares
    
    def test_module_import(self):
        """Test that the module can be imported"""
        from gpupassthrough import main
        assert hasattr(main, 'run')
        assert hasattr(main, 'detect_gpus')
        assert hasattr(main, 'configure_grub')
    
    def test_gpu_detection(self):
        """Test GPU detection from lspci"""
        from gpupassthrough.main import detect_gpus
        
        mock_lspci_output = """01:00.0 VGA compatible controller: NVIDIA Corporation GA102 [GeForce RTX 3090] (rev a1)
01:00.1 Audio device: NVIDIA Corporation GA102 High Definition Audio Controller (rev a1)
00:02.0 VGA compatible controller: Intel Corporation UHD Graphics 770 (rev 04)"""
        
        with patch('subprocess.check_output', return_value=mock_lspci_output.encode()):
            gpus = detect_gpus()
            
            assert len(gpus) == 2
            # Check NVIDIA GPU
            nvidia_gpu = next(g for g in gpus if "NVIDIA" in g["name"])
            assert nvidia_gpu["pci_id"] == "01:00.0"
            assert "RTX 3090" in nvidia_gpu["name"]
            assert nvidia_gpu["vendor"] == "nvidia"
            
            # Check Intel GPU
            intel_gpu = next(g for g in gpus if "Intel" in g["name"])
            assert intel_gpu["pci_id"] == "00:02.0"
            assert intel_gpu["vendor"] == "intel"
    
    def test_iommu_group_detection(self):
        """Test IOMMU group detection"""
        from gpupassthrough.main import get_iommu_groups
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.iterdir') as mock_iterdir:
                # Mock IOMMU group structure
                mock_group1 = MagicMock()
                mock_group1.name = "1"
                mock_group1.is_dir.return_value = True
                
                mock_iterdir.return_value = [mock_group1]
                
                with patch('pathlib.Path.glob') as mock_glob:
                    mock_device = MagicMock()
                    mock_device.name = "0000:01:00.0"
                    mock_glob.return_value = [mock_device]
                    
                    groups = get_iommu_groups()
                    
                    assert "1" in groups
                    assert "0000:01:00.0" in groups["1"]
    
    def test_grub_configuration(self, temp_dir):
        """Test GRUB configuration for IOMMU"""
        from gpupassthrough.main import configure_grub
        
        config = {
            "enable_iommu": True,
            "cpu_vendor": "intel"
        }
        
        # Create mock GRUB file
        grub_file = temp_dir / "etc/default/grub"
        grub_file.parent.mkdir(parents=True)
        grub_file.write_text('GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"\n')
        
        configure_grub(str(temp_dir), config)
        
        content = grub_file.read_text()
        assert "intel_iommu=on" in content
        assert "iommu=pt" in content
    
    def test_vfio_configuration(self, temp_dir):
        """Test VFIO driver configuration"""
        from gpupassthrough.main import configure_vfio
        
        config = {
            "gpus": [
                {
                    "pci_id": "01:00.0",
                    "vendor_id": "10de",
                    "device_id": "2204",
                    "selected": True
                }
            ]
        }
        
        configure_vfio(str(temp_dir), config)
        
        # Check modprobe config
        vfio_conf = temp_dir / "etc/modprobe.d/vfio.conf"
        assert vfio_conf.exists()
        assert "options vfio-pci ids=10de:2204" in vfio_conf.read_text()
        
        # Check blacklist
        blacklist = temp_dir / "etc/modprobe.d/blacklist-nvidia.conf"
        assert blacklist.exists()
        assert "blacklist nouveau" in blacklist.read_text()
    
    def test_pci_stub_configuration(self, temp_dir):
        """Test PCI stub configuration"""
        from gpupassthrough.main import setup_pci_stub
        
        gpu_ids = ["10de:2204", "10de:1aef"]
        
        setup_pci_stub(str(temp_dir), gpu_ids)
        
        # Check initramfs modules
        modules_file = temp_dir / "etc/modules"
        content = modules_file.read_text()
        assert "vfio" in content
        assert "vfio_iommu_type1" in content
        assert "vfio_pci" in content
    
    def test_acs_override(self, temp_dir):
        """Test ACS override configuration"""
        from gpupassthrough.main import configure_grub
        
        config = {
            "enable_iommu": True,
            "cpu_vendor": "intel",
            "acs_override": True
        }
        
        grub_file = temp_dir / "etc/default/grub"
        grub_file.parent.mkdir(parents=True)
        grub_file.write_text('GRUB_CMDLINE_LINUX_DEFAULT="quiet"\n')
        
        configure_grub(str(temp_dir), config)
        
        content = grub_file.read_text()
        assert "pcie_acs_override=downstream,multifunction" in content
    
    @patch('gpupassthrough.main.detect_gpus')
    @patch('gpupassthrough.main.get_iommu_groups')
    def test_run_function(self, mock_iommu, mock_detect):
        """Test the main run function"""
        from gpupassthrough import main
        
        # Mock GPU detection
        mock_detect.return_value = [
            {
                "pci_id": "01:00.0",
                "name": "NVIDIA RTX 3090",
                "vendor": "nvidia",
                "vendor_id": "10de",
                "device_id": "2204"
            }
        ]
        
        mock_iommu.return_value = {"1": ["0000:01:00.0"]}
        
        # Setup config
        self.mock_calamares.globalstorage.insert("gpuPassthroughConfig", {
            "enable_iommu": True,
            "gpus": [{"pci_id": "01:00.0", "selected": True}]
        })
        
        with patch('gpupassthrough.main.Path'):
            result = main.run()
            assert result is None

class TestGPUPassthroughGUI:
    """Test the GUI components"""
    
    @pytest.fixture(autouse=True)
    def setup(self, mock_libcalamares):
        """Setup for GUI tests"""
        sys.modules['gi'] = MagicMock()
        sys.modules['gi.repository'] = MagicMock()
        
        mock_gtk = MagicMock()
        sys.modules['gi.repository'].Gtk = mock_gtk
    
    def test_widget_creation(self):
        """Test GPUPassthroughWidget creation"""
        from gpupassthrough.gpu_passthrough_gui import GPUPassthroughWidget
        
        widget = GPUPassthroughWidget(Mock())
        assert widget is not None
    
    @patch('subprocess.check_output')
    def test_gpu_list_population(self, mock_subprocess):
        """Test GPU list population in GUI"""
        from gpupassthrough.gpu_passthrough_gui import GPUPassthroughWidget
        
        # Mock lspci output
        mock_subprocess.return_value = b"01:00.0 VGA compatible controller: NVIDIA Corporation Device 2204"
        
        widget = GPUPassthroughWidget(Mock())
        
        # Widget should attempt to detect GPUs
        mock_subprocess.assert_called()