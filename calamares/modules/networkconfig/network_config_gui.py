#!/usr/bin/env python3
"""
Network Configuration GUI for Calamares
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QCheckBox, QLineEdit, 
                             QTextEdit, QGroupBox, QRadioButton, QScrollArea)
from PyQt5.QtCore import Qt, pyqtSignal
import subprocess
import json
import ipaddress
from typing import Dict, List

class NetworkConfigGui(QGroupBox):
    """Network configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__("Network Configuration")
        self.gs = globalstorage
        self.interfaces = {}
        self.network_config = {
            "interfaces": {},
            "dns_servers": ["8.8.8.8", "8.8.4.4"]
        }
        
        self.setup_ui()
        self.detect_interfaces()
        
    def setup_ui(self):
        """Build the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("<b>Network Configuration</b>")
        layout.addWidget(header)
        
        # Interface list in scroll area
        scroll = QScrollArea()
        scroll.setMinimumHeight(300)
        
        self.interface_widget = QWidget()
        self.interface_layout = QVBoxLayout()
        self.interface_widget.setLayout(self.interface_layout)
        
        scroll.setWidget(self.interface_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)
        
        # DNS configuration
        dns_frame = QGroupBox("DNS Servers")
        dns_layout = QVBoxLayout()
        dns_frame.setLayout(dns_layout)
        
        dns1_layout = QHBoxLayout()
        dns1_layout.addWidget(QLabel("Primary DNS:"))
        self.dns1_entry = QLineEdit("8.8.8.8")
        self.dns1_entry.setPlaceholderText("Primary DNS")
        dns1_layout.addWidget(self.dns1_entry)
        dns_layout.addLayout(dns1_layout)
        
        dns2_layout = QHBoxLayout()
        dns2_layout.addWidget(QLabel("Secondary DNS:"))
        self.dns2_entry = QLineEdit("8.8.4.4")
        self.dns2_entry.setPlaceholderText("Secondary DNS")
        dns2_layout.addWidget(self.dns2_entry)
        dns_layout.addLayout(dns2_layout)
        
        layout.addWidget(dns_frame)
        
        self.show()
        
    def detect_interfaces(self):
        """Detect network interfaces"""
        try:
            output = subprocess.check_output(["ip", "link", "show"]).decode()
            for line in output.split('\n'):
                if ': ' in line and 'lo:' not in line:
                    # Parse interface name
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        # Format: "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP>"
                        iface_parts = parts[1].split(':')
                        if iface_parts:
                            iface_name = iface_parts[0].strip()
                            
                            # Skip virtual interfaces
                            if iface_name and not iface_name.startswith('vir'):
                                self.add_interface(iface_name)
        except Exception as e:
            print(f"Error detecting interfaces: {e}")
            
    def add_interface(self, iface_name):
        """Add interface to configuration UI"""
        frame = QGroupBox(f"Interface: {iface_name}")
        layout = QVBoxLayout()
        frame.setLayout(layout)
        
        # DHCP/Static selection
        dhcp_radio = QRadioButton("DHCP")
        dhcp_radio.setChecked(True)
        static_radio = QRadioButton("Static IP")
        
        radio_layout = QHBoxLayout()
        radio_layout.addWidget(dhcp_radio)
        radio_layout.addWidget(static_radio)
        layout.addLayout(radio_layout)
        
        # Static IP configuration
        static_widget = QWidget()
        static_layout = QVBoxLayout()
        static_widget.setLayout(static_layout)
        
        # IP Address
        ip_layout = QHBoxLayout()
        ip_label = QLabel("IP Address:")
        ip_label.setMinimumWidth(100)
        ip_layout.addWidget(ip_label)
        
        ip_entry = QLineEdit()
        ip_entry.setPlaceholderText("192.168.1.100/24")
        ip_layout.addWidget(ip_entry)
        static_layout.addLayout(ip_layout)
        
        # Gateway
        gw_layout = QHBoxLayout()
        gw_label = QLabel("Gateway:")
        gw_label.setMinimumWidth(100)
        gw_layout.addWidget(gw_label)
        
        gw_entry = QLineEdit()
        gw_entry.setPlaceholderText("192.168.1.1")
        gw_layout.addWidget(gw_entry)
        static_layout.addLayout(gw_layout)
        
        # Bridge option
        bridge_check = QCheckBox("Create bridge for VMs (vmbr0)")
        static_layout.addWidget(bridge_check)
        
        layout.addWidget(static_widget)
        
        # Store references
        self.interfaces[iface_name] = {
            "dhcp_radio": dhcp_radio,
            "static_radio": static_radio,
            "ip_entry": ip_entry,
            "gw_entry": gw_entry,
            "bridge_check": bridge_check,
            "static_widget": static_widget
        }
        
        # Connect signals
        dhcp_radio.toggled.connect(lambda checked: self.on_dhcp_toggled(checked, iface_name))
        static_radio.toggled.connect(lambda checked: self.on_static_toggled(checked, iface_name))
        
        self.interface_layout.addWidget(frame)
        
        # Set initial state
        dhcp_radio.setChecked(True)
        static_widget.setEnabled(False)
        
    def on_dhcp_toggled(self, checked, iface_name):
        """Handle DHCP radio toggle"""
        if checked and iface_name in self.interfaces:
            self.interfaces[iface_name]["static_widget"].setEnabled(False)
            
    def on_static_toggled(self, checked, iface_name):
        """Handle static IP radio toggle"""
        if checked and iface_name in self.interfaces:
            self.interfaces[iface_name]["static_widget"].setEnabled(True)
            
    def get_configuration(self) -> Dict:
        """Get the network configuration"""
        config = {
            "interfaces": {},
            "dns_servers": [
                self.dns1_entry.text(),
                self.dns2_entry.text()
            ]
        }
        
        for iface_name, widgets in self.interfaces.items():
            iface_config = {
                "dhcp": widgets["dhcp_radio"].isChecked(),
                "static": widgets["static_radio"].isChecked(),
                "ip_address": widgets["ip_entry"].text() if widgets["static_radio"].isChecked() else "",
                "gateway": widgets["gw_entry"].text() if widgets["static_radio"].isChecked() else "",
                "bridge": widgets["bridge_check"].isChecked()
            }
            config["interfaces"][iface_name] = iface_config
            
        return config