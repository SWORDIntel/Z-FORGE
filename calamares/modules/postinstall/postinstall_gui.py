#!/usr/bin/env python3
"""
Post-Install Checklist GUI for Calamares
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit, QGroupBox
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict

class PostinstallGui(QGroupBox):
    """Post-install checklist configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__("Post-Installation Setup")
        self.gs = globalstorage
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<b>Post-Installation Setup</b>")
        layout.addWidget(header)
        
        # Description
        desc = QLabel("Configure what happens after installation completes.")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # First boot options
        boot_frame = QGroupBox("First Boot")
        boot_layout = QVBoxLayout()
        boot_frame.setLayout(boot_layout)
        
        self.wizard_check = QCheckBox("Run setup wizard on first boot")
        self.wizard_check.setChecked(True)
        self.wizard_check.setToolTip("Automatically start the checklist when system boots")
        boot_layout.addWidget(self.wizard_check)
        
        self.auto_check = QCheckBox("Auto-start checklist for root login")
        self.auto_check.setChecked(True)
        self.auto_check.setToolTip("Show checklist when logging in as root")
        boot_layout.addWidget(self.auto_check)
        
        layout.addWidget(boot_frame)
        
        # Categories to include
        cat_frame = QGroupBox("Checklist Categories")
        cat_layout = QVBoxLayout()
        cat_frame.setLayout(cat_layout)
        
        self.category_checks = {}
        
        categories = [
            ("security", "Security Tasks", "Password, SSH, firewall configuration"),
            ("storage", "Storage Configuration", "ZFS pools, snapshots, alerts"),
            ("network", "Network Setup", "Interfaces, VLANs, DNS"),
            ("proxmox", "Proxmox Configuration", "VMs, backups, clustering"),
            ("monitoring", "Monitoring Setup", "Agents, alerts, dashboards")
        ]
        
        for cat_id, name, tooltip in categories:
            check = QCheckBox(name)
            check.setChecked(True)
            check.setToolTip(tooltip)
            self.category_checks[cat_id] = check
            cat_layout.addWidget(check)
        
        layout.addWidget(cat_frame)
        
        # Info box
        info_frame = QGroupBox("Information")
        info_layout = QVBoxLayout()
        info_frame.setLayout(info_layout)
        
        info_text = """The post-installation checklist helps you:
• Complete essential security configuration
• Setup storage and network properly
• Configure Proxmox services
• Enable monitoring and alerts

You can run 'zforge-checklist' at any time to access it."""
        
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_frame)
        
        self.show()
        
    def get_configuration(self) -> Dict:
        """Get the post-install configuration"""
        config = {
            "first_boot_wizard": self.wizard_check.isChecked(),
            "auto_start": self.auto_check.isChecked(),
            "categories": {}
        }
        
        for cat_id, check in self.category_checks.items():
            config["categories"][cat_id] = check.isChecked()
        
        return config