#!/usr/bin/env python3
"""
Hardware Health Monitoring Configuration GUI for Calamares
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QTextEdit, QGroupBox, QSpinBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Dict

class HardwareHealthGui(QGroupBox):
    """Hardware health monitoring configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__("Hardware Monitoring Configuration")
        self.gs = globalstorage
        self.config = {
            "monitoring": {},
            "alerts": {},
            "services": []
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<b>Hardware Monitoring Configuration</b>")
        layout.addWidget(header)
        
        # Monitoring options
        monitor_frame = QGroupBox("Monitoring Services")
        monitor_layout = QVBoxLayout()
        monitor_frame.setLayout(monitor_layout)
        
        self.temp_check = QCheckBox("Temperature Monitoring (lm-sensors)")
        self.temp_check.setChecked(True)
        monitor_layout.addWidget(self.temp_check)
        
        self.smart_check = QCheckBox("Disk Health (smartmontools)")
        self.smart_check.setChecked(True)
        monitor_layout.addWidget(self.smart_check)
        
        self.raid_check = QCheckBox("RAID Status (megacli/perccli)")
        self.raid_check.setChecked(True)
        monitor_layout.addWidget(self.raid_check)
        
        self.power_check = QCheckBox("Power Monitoring (IPMI)")
        self.power_check.setChecked(True)
        monitor_layout.addWidget(self.power_check)
        
        layout.addWidget(monitor_frame)
        
        # Alert configuration
        alert_frame = QGroupBox("Alert Configuration")
        alert_layout = QGridLayout()
        alert_frame.setLayout(alert_layout)
        
        # Email alerts
        email_label = QLabel("Alert Email:")
        alert_layout.addWidget(email_label, 0, 0)
        
        self.email_entry = QLineEdit()
        self.email_entry.setPlaceholderText("admin@example.com")
        alert_layout.addWidget(self.email_entry, 0, 1, 1, 2)
        
        # Temperature threshold
        temp_label = QLabel("Temperature Alert:")
        alert_layout.addWidget(temp_label, 1, 0)
        
        self.temp_spin = QSpinBox()
        self.temp_spin.setMinimum(40)
        self.temp_spin.setMaximum(100)
        self.temp_spin.setValue(75)
        alert_layout.addWidget(self.temp_spin, 1, 1)
        
        temp_unit_label = QLabel("°C")
        alert_layout.addWidget(temp_unit_label, 1, 2)
        
        # CPU usage threshold
        cpu_label = QLabel("CPU Alert:")
        alert_layout.addWidget(cpu_label, 2, 0)
        
        self.cpu_spin = QSpinBox()
        self.cpu_spin.setMinimum(50)
        self.cpu_spin.setMaximum(100)
        self.cpu_spin.setValue(90)
        alert_layout.addWidget(self.cpu_spin, 2, 1)
        
        cpu_unit_label = QLabel("%")
        alert_layout.addWidget(cpu_unit_label, 2, 2)
        
        # Memory threshold
        mem_label = QLabel("Memory Alert:")
        alert_layout.addWidget(mem_label, 3, 0)
        
        self.mem_spin = QSpinBox()
        self.mem_spin.setMinimum(50)
        self.mem_spin.setMaximum(100)
        self.mem_spin.setValue(85)
        alert_layout.addWidget(self.mem_spin, 3, 1)
        
        mem_unit_label = QLabel("%")
        alert_layout.addWidget(mem_unit_label, 3, 2)
        
        # Disk space threshold
        disk_label = QLabel("Disk Space Alert:")
        alert_layout.addWidget(disk_label, 4, 0)
        
        self.disk_space_spin = QSpinBox()
        self.disk_space_spin.setMinimum(50)
        self.disk_space_spin.setMaximum(95)
        self.disk_space_spin.setValue(80)
        alert_layout.addWidget(self.disk_space_spin, 4, 1)
        
        disk_unit_label = QLabel("%")
        alert_layout.addWidget(disk_unit_label, 4, 2)
        
        layout.addWidget(alert_frame)
        
        # Additional options
        options_frame = QGroupBox("Additional Options")
        options_layout = QVBoxLayout()
        options_frame.setLayout(options_layout)
        
        self.syslog_check = QCheckBox("Log to local syslog")
        self.syslog_check.setChecked(True)
        options_layout.addWidget(self.syslog_check)
        
        self.remote_syslog_check = QCheckBox("Log to remote syslog")
        self.remote_syslog_check.toggled.connect(self.on_remote_toggled)
        options_layout.addWidget(self.remote_syslog_check)
        
        remote_layout = QHBoxLayout()
        remote_label = QLabel("Remote server:")
        remote_layout.addWidget(remote_label)
        
        self.remote_entry = QLineEdit()
        self.remote_entry.setPlaceholderText("syslog.example.com:514")
        self.remote_entry.setEnabled(False)
        remote_layout.addWidget(self.remote_entry)
        
        options_layout.addLayout(remote_layout)
        
        layout.addWidget(options_frame)
        
        self.show()
        
    def on_remote_toggled(self, checked):
        """Handle remote syslog toggle"""
        self.remote_entry.setEnabled(checked)
        
    def get_configuration(self) -> Dict:
        """Get the hardware monitoring configuration"""
        config = {
            "monitoring": {
                "temperature": self.temp_check.isChecked(),
                "smart": self.smart_check.isChecked(),
                "raid": self.raid_check.isChecked(),
                "power": self.power_check.isChecked()
            },
            "alerts": {
                "email": self.email_entry.text(),
                "thresholds": {
                    "temperature": self.temp_spin.value(),
                    "cpu": self.cpu_spin.value(),
                    "memory": self.mem_spin.value(),
                    "disk_space": self.disk_space_spin.value()
                }
            },
            "logging": {
                "local_syslog": self.syslog_check.isChecked(),
                "remote_syslog": self.remote_syslog_check.isChecked(),
                "remote_server": self.remote_entry.text() if self.remote_syslog_check.isChecked() else ""
            }
        }
        
        return config