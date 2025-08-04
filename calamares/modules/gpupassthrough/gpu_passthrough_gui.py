#!/usr/bin/env python3
"""
GPU Passthrough Configuration GUI for Calamares
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox, QScrollArea
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict, List

class GpuPassthroughGui(QGroupBox):
    """GPU passthrough configuration widget"""
    
    def __init__(self, globalstorage, detected_gpus):
        super().__init__("GPU Passthrough Configuration")
        self.gs = globalstorage
        self.detected_gpus = detected_gpus
        self.gpu_widgets = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<b>GPU Passthrough Configuration</b>")
        layout.addWidget(header)
        
        if not self.detected_gpus:
            no_gpu_label = QLabel("<i>No discrete GPUs detected</i>")
            layout.addWidget(no_gpu_label)
        else:
            # GPU list
            gpu_label = QLabel("<b>Detected GPUs:</b>")
            gpu_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            layout.addWidget(gpu_label)
            
            # Scrolled area for GPU list
            scroll = QScrollArea()
            scroll.setMinimumHeight(200)
            
            gpu_widget = QWidget()
            gpu_layout = QVBoxLayout()
            gpu_widget.setLayout(gpu_layout)
            
            for gpu in self.detected_gpus:
                gpu_frame = self.create_gpu_frame(gpu)
                gpu_layout.addWidget(gpu_frame)
            
            scroll.setWidget(gpu_widget)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)
            
            # Configuration options
            config_frame = QGroupBox("Configuration Options")
            config_layout = QVBoxLayout()
            config_frame.setLayout(config_layout)
            
            self.iommu_check = QCheckBox("Enable IOMMU in bootloader")
            self.iommu_check.setChecked(True)
            config_layout.addWidget(self.iommu_check)
            
            self.blacklist_check = QCheckBox("Blacklist GPU drivers")
            self.blacklist_check.setChecked(True)
            config_layout.addWidget(self.blacklist_check)
            
            self.vfio_check = QCheckBox("Configure VFIO early binding")
            self.vfio_check.setChecked(True)
            config_layout.addWidget(self.vfio_check)
            
            self.acs_check = QCheckBox("Enable ACS override (reduces security)")
            self.acs_check.setToolTip("Only enable if IOMMU groups are problematic")
            config_layout.addWidget(self.acs_check)
            
            layout.addWidget(config_frame)
            
            # Info box
            info_frame = QGroupBox("Important Information")
            info_layout = QVBoxLayout()
            info_frame.setLayout(info_layout)
            
            info_text = """• GPU passthrough requires VT-d (Intel) or AMD-Vi support
• The host will lose access to passed through GPUs
• A separate GPU is recommended for host display
• Reboot required after configuration"""
            
            info_label = QLabel(info_text)
            info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            info_layout.addWidget(info_label)
            
            layout.addWidget(info_frame)
        
        self.show()
        
    def create_gpu_frame(self, gpu):
        """Create frame for a single GPU"""
        frame = QGroupBox()
        layout = QVBoxLayout()
        frame.setLayout(layout)
        
        # GPU selection checkbox
        gpu_check = QCheckBox()
        gpu_label = f"{gpu['name']} [{gpu['vendor_id']}:{gpu['device_id']}]"
        gpu_check.setText(gpu_label)
        layout.addWidget(gpu_check)
        
        # GPU details
        details_widget = QWidget()
        details_layout = QVBoxLayout()
        details_widget.setLayout(details_layout)
        details_layout.setContentsMargins(20, 0, 0, 0)
        
        # PCI address
        pci_label = QLabel(f"<small>PCI: {gpu['pci_addr']}</small>")
        pci_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        details_layout.addWidget(pci_label)
        
        # IOMMU group
        iommu_text = f"IOMMU Group: {gpu['iommu_group']}" if gpu['iommu_group'] >= 0 else "IOMMU Group: Not available"
        iommu_label = QLabel(f"<small>{iommu_text}</small>")
        iommu_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        details_layout.addWidget(iommu_label)
        
        # Reset support
        reset_text = "Reset: ✓ Supported" if gpu['reset_available'] else "Reset: ✗ Not supported"
        reset_label = QLabel(f"<small>{reset_text}</small>")
        reset_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        details_layout.addWidget(reset_label)
        
        layout.addWidget(details_widget)
        
        # Audio device
        audio_check = None
        if gpu.get('audio_id'):
            audio_check = QCheckBox(f"Include HDMI Audio [{gpu['vendor_id']}:{gpu['audio_id']}]")
            audio_check.setChecked(True)
            audio_check.setContentsMargins(20, 0, 0, 0)
            layout.addWidget(audio_check)
        
        # Store widget references
        self.gpu_widgets.append({
            "gpu": gpu,
            "checkbox": gpu_check,
            "audio_checkbox": audio_check
        })
        
        return frame
        
    def get_configuration(self) -> Dict:
        """Get the GPU passthrough configuration"""
        config = {
            "enabled_gpus": [],
            "iommu_enabled": self.iommu_check.isChecked() if hasattr(self, 'iommu_check') else False,
            "blacklist_drivers": self.blacklist_check.isChecked() if hasattr(self, 'blacklist_check') else False,
            "vfio_binding": self.vfio_check.isChecked() if hasattr(self, 'vfio_check') else False,
            "acs_override": self.acs_check.isChecked() if hasattr(self, 'acs_check') else False
        }
        
        for widget_info in self.gpu_widgets:
            if widget_info["checkbox"].isChecked():
                gpu_config = {
                    "gpu": widget_info["gpu"],
                    "include_audio": widget_info["audio_checkbox"].isChecked() if widget_info["audio_checkbox"] else False
                }
                config["enabled_gpus"].append(gpu_config)
        
        return config