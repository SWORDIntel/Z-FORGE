#!/usr/bin/env python3
"""
Post-Install Checklist GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from typing import Dict

class PostInstallWidget(Gtk.Box):
    """Post-install checklist configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.gs = globalstorage
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Post-Installation Setup</b>")
        self.pack_start(header, False, False, 0)
        
        # Description
        desc = Gtk.Label()
        desc.set_text("Configure what happens after installation completes.")
        desc.set_line_wrap(True)
        desc.set_margin_bottom(10)
        self.pack_start(desc, False, False, 0)
        
        # First boot options
        boot_frame = Gtk.Frame(label="First Boot")
        boot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        boot_box.set_margin_top(10)
        boot_box.set_margin_bottom(10)
        boot_box.set_margin_left(10)
        boot_box.set_margin_right(10)
        
        self.wizard_check = Gtk.CheckButton(label="Run setup wizard on first boot")
        self.wizard_check.set_active(True)
        self.wizard_check.set_tooltip_text("Automatically start the checklist when system boots")
        boot_box.pack_start(self.wizard_check, False, False, 0)
        
        self.auto_check = Gtk.CheckButton(label="Auto-start checklist for root login")
        self.auto_check.set_active(True)
        self.auto_check.set_tooltip_text("Show checklist when logging in as root")
        boot_box.pack_start(self.auto_check, False, False, 0)
        
        boot_frame.add(boot_box)
        self.pack_start(boot_frame, False, False, 0)
        
        # Categories to include
        cat_frame = Gtk.Frame(label="Checklist Categories")
        cat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        cat_box.set_margin_top(10)
        cat_box.set_margin_bottom(10)
        cat_box.set_margin_left(10)
        cat_box.set_margin_right(10)
        
        self.category_checks = {}
        
        categories = [
            ("security", "Security Tasks", "Password, SSH, firewall configuration"),
            ("storage", "Storage Configuration", "ZFS pools, snapshots, alerts"),
            ("network", "Network Setup", "Interfaces, VLANs, DNS"),
            ("proxmox", "Proxmox Configuration", "VMs, backups, clustering"),
            ("monitoring", "Monitoring Setup", "Agents, alerts, dashboards")
        ]
        
        for cat_id, name, tooltip in categories:
            check = Gtk.CheckButton(label=name)
            check.set_active(True)
            check.set_tooltip_text(tooltip)
            self.category_checks[cat_id] = check
            cat_box.pack_start(check, False, False, 0)
        
        cat_frame.add(cat_box)
        self.pack_start(cat_frame, False, False, 0)
        
        # Info box
        info_frame = Gtk.Frame(label="Information")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        info_box.set_margin_top(10)
        info_box.set_margin_bottom(10)
        info_box.set_margin_left(10)
        info_box.set_margin_right(10)
        
        info_text = """The post-installation checklist helps you:
• Complete essential security configuration
• Setup storage and network properly
• Configure Proxmox services
• Enable monitoring and alerts

You can run 'zforge-checklist' at any time to access it."""
        
        info_label = Gtk.Label(label=info_text)
        info_label.set_alignment(0, 0)
        info_box.pack_start(info_label, False, False, 0)
        
        info_frame.add(info_box)
        self.pack_start(info_frame, False, False, 0)
        
        self.show_all()
        
    def get_configuration(self) -> Dict:
        """Get the post-install configuration"""
        config = {
            "first_boot_wizard": self.wizard_check.get_active(),
            "auto_start": self.auto_check.get_active(),
            "categories": {}
        }
        
        for cat_id, check in self.category_checks.items():
            config["categories"][cat_id] = check.get_active()
        
        return config
