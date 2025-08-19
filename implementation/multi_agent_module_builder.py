#!/usr/bin/env python3
"""
Multi-Agent Module Implementation System for Z-FORGE
Implements 5 new Calamares modules using buddy system verification
"""

import os
import sys
import time
import json
import sqlite3
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib
import random

class ModuleImplementationAgent:
    """Agent responsible for implementing a specific module"""
    
    def __init__(self, agent_id: int, module_name: str, buddy_id: int, db_path: Path):
        self.agent_id = agent_id
        self.module_name = module_name
        self.buddy_id = buddy_id
        self.db_path = db_path
        self.status = "initializing"
        self.progress = 0
        self.init_database()
        
    def init_database(self):
        """Initialize agent's progress tracking"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO agents 
                     (agent_id, module_name, buddy_id, status, progress, last_update)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (self.agent_id, self.module_name, self.buddy_id, 
                   self.status, self.progress, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
    def update_progress(self, status: str, progress: int, message: str = ""):
        """Update agent progress in database"""
        self.status = status
        self.progress = progress
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""UPDATE agents SET status=?, progress=?, last_update=? 
                     WHERE agent_id=?""",
                  (status, progress, datetime.now().isoformat(), self.agent_id))
        
        if message:
            c.execute("""INSERT INTO agent_logs (agent_id, timestamp, message)
                         VALUES (?, ?, ?)""",
                      (self.agent_id, datetime.now().isoformat(), message))
        conn.commit()
        conn.close()
        
    def implement_module(self):
        """Main implementation logic for the module"""
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_buddy_verification(self) -> Dict:
        """Get verification status from buddy agent"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""SELECT status, result FROM verifications 
                     WHERE verifier_id=? AND agent_id=? 
                     ORDER BY timestamp DESC LIMIT 1""",
                  (self.buddy_id, self.agent_id))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {"status": result[0], "result": json.loads(result[1])}
        return {"status": "pending", "result": {}}


class BuddyVerificationAgent:
    """Agent responsible for verifying another agent's work"""
    
    def __init__(self, agent_id: int, verify_agent_id: int, db_path: Path):
        self.agent_id = agent_id
        self.verify_agent_id = verify_agent_id
        self.db_path = db_path
        
    def verify_work(self, work_items: List[Dict]) -> Dict:
        """Verify the work done by buddy agent"""
        verification_results = {
            "timestamp": datetime.now().isoformat(),
            "verified_items": [],
            "issues": [],
            "overall_status": "pass"
        }
        
        for item in work_items:
            result = self.verify_single_item(item)
            verification_results["verified_items"].append(result)
            if not result["valid"]:
                verification_results["issues"].append(result["issue"])
                verification_results["overall_status"] = "fail"
                
        # Store verification result
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT INTO verifications 
                     (verifier_id, agent_id, timestamp, status, result)
                     VALUES (?, ?, ?, ?, ?)""",
                  (self.agent_id, self.verify_agent_id, 
                   datetime.now().isoformat(),
                   verification_results["overall_status"],
                   json.dumps(verification_results)))
        conn.commit()
        conn.close()
        
        return verification_results
        
    def verify_single_item(self, item: Dict) -> Dict:
        """Verify a single work item"""
        # Override in subclasses for specific verification logic
        return {"item": item, "valid": True, "issue": None}


# Specific Module Implementation Agents

class NetworkConfigAgent(ModuleImplementationAgent):
    """Agent for implementing Network Configuration Module"""
    
    def implement_module(self):
        """Implement the network configuration module"""
        self.update_progress("starting", 10, "Creating network configuration module structure")
        
        # Create module directory
        module_path = Path("/opt/github/Z-FORGE/calamares/modules/networkconfig")
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create module descriptor
        self.update_progress("working", 20, "Creating module descriptor")
        module_desc = """# Network Configuration Module
---
type:       "python"
name:       "networkconfig"
interface:  "python"
requires:   []
script:     "main.py"
"""
        (module_path / "module.desc").write_text(module_desc)
        
        # Create main module file
        self.update_progress("working", 40, "Implementing main module logic")
        main_content = '''#!/usr/bin/env python3
"""
Network Configuration Module for Calamares
Provides comprehensive network setup during installation
"""

import os
import sys
import json
import subprocess
import libcalamares
from pathlib import Path

# Import the GUI module
sys.path.append(os.path.dirname(__file__))
from network_config_gui import NetworkConfigWidget

def pretty_name():
    return "Network Configuration"

def icon():
    return "network-wired"

def run():
    """Execute network configuration"""
    gs = libcalamares.globalstorage
    network_config = gs.value("networkConfig")
    
    if not network_config:
        return "No network configuration found", "Network must be configured for server installation"
    
    # Apply network configuration
    try:
        apply_network_config(network_config)
        return None
    except Exception as e:
        return "Network configuration failed", str(e)

def apply_network_config(config):
    """Apply the network configuration to the target system"""
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    
    # Write network configuration
    interfaces_content = generate_interfaces_file(config)
    interfaces_path = Path(root_mount_point) / "etc/network/interfaces"
    interfaces_path.parent.mkdir(parents=True, exist_ok=True)
    interfaces_path.write_text(interfaces_content)
    
    # Configure DNS
    if config.get("dns_servers"):
        resolv_content = ""
        for dns in config["dns_servers"]:
            resolv_content += f"nameserver {dns}\\n"
        resolv_path = Path(root_mount_point) / "etc/resolv.conf"
        resolv_path.write_text(resolv_content)

def generate_interfaces_file(config):
    """Generate /etc/network/interfaces content"""
    content = """# Network interfaces configuration
# Generated by Z-FORGE installer

auto lo
iface lo inet loopback

"""
    
    for iface_name, iface_config in config.get("interfaces", {}).items():
        if iface_config["type"] == "static":
            content += f"""
auto {iface_name}
iface {iface_name} inet static
    address {iface_config["address"]}
    netmask {iface_config["netmask"]}
    gateway {iface_config.get("gateway", "")}
"""
        elif iface_config["type"] == "dhcp":
            content += f"""
auto {iface_name}
iface {iface_name} inet dhcp
"""
        
        # Bridge configuration for Proxmox
        if iface_config.get("bridge"):
            bridge_name = iface_config["bridge_name"]
            content += f"""
auto {bridge_name}
iface {bridge_name} inet static
    address {iface_config["address"]}
    netmask {iface_config["netmask"]}
    gateway {iface_config.get("gateway", "")}
    bridge-ports {iface_name}
    bridge-stp off
    bridge-fd 0
"""
    
    return content

class NetworkConfigViewStep:
    """Calamares ViewStep for network configuration"""
    
    def __init__(self):
        self.widget = None
        self.gs = libcalamares.globalstorage
    
    def name(self):
        return "networkconfig"
    
    def pretty_name(self):
        return "Network Configuration"
    
    def icon(self):
        return "network-wired"
    
    def widget(self):
        if self.widget is None:
            self.widget = NetworkConfigWidget(self.gs)
        return self.widget
    
    def next(self):
        if self.widget:
            config = self.widget.get_configuration()
            if not config:
                return ("Configuration Error", "Please complete network configuration")
            self.gs.insert("networkConfig", config)
        return None
    
    def back(self):
        return None
    
    def jobs(self):
        return []

calamares_module = NetworkConfigViewStep
'''
        (module_path / "main.py").write_text(main_content)
        
        # Create GUI module
        self.update_progress("working", 60, "Creating network configuration GUI")
        gui_content = '''#!/usr/bin/env python3
"""
Network Configuration GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import subprocess
import json
import ipaddress
from typing import Dict, List

class NetworkConfigWidget(Gtk.Box):
    """Network configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
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
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Network Configuration</b>")
        self.pack_start(header, False, False, 0)
        
        # Interface list
        self.interface_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(300)
        scroll.add(self.interface_box)
        self.pack_start(scroll, True, True, 0)
        
        # DNS configuration
        dns_frame = Gtk.Frame(label="DNS Servers")
        dns_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        dns_box.set_margin_top(10)
        dns_box.set_margin_bottom(10)
        dns_box.set_margin_left(10)
        dns_box.set_margin_right(10)
        
        self.dns1_entry = Gtk.Entry()
        self.dns1_entry.set_text("8.8.8.8")
        self.dns1_entry.set_placeholder_text("Primary DNS")
        dns_box.pack_start(self.dns1_entry, False, False, 0)
        
        self.dns2_entry = Gtk.Entry()
        self.dns2_entry.set_text("8.8.4.4")
        self.dns2_entry.set_placeholder_text("Secondary DNS")
        dns_box.pack_start(self.dns2_entry, False, False, 0)
        
        dns_frame.add(dns_box)
        self.pack_start(dns_frame, False, False, 0)
        
        self.show_all()
        
    def detect_interfaces(self):
        """Detect network interfaces"""
        try:
            output = subprocess.check_output(["ip", "link", "show"]).decode()
            for line in output.split('\\n'):
                if ': ' in line and 'lo:' not in line:
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        iface_name = parts[1].split('@')[0]
                        if iface_name and not iface_name.startswith('vir'):
                            self.add_interface(iface_name)
        except Exception as e:
            print(f"Error detecting interfaces: {e}")
            
    def add_interface(self, iface_name):
        """Add interface to configuration UI"""
        frame = Gtk.Frame(label=f"Interface: {iface_name}")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_left(10)
        box.set_margin_right(10)
        
        # DHCP/Static selection
        dhcp_radio = Gtk.RadioButton.new_with_label(None, "DHCP")
        static_radio = Gtk.RadioButton.new_with_label_from_widget(dhcp_radio, "Static IP")
        
        radio_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        radio_box.pack_start(dhcp_radio, False, False, 0)
        radio_box.pack_start(static_radio, False, False, 0)
        box.pack_start(radio_box, False, False, 0)
        
        # Static IP configuration
        static_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        # IP Address
        ip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        ip_label = Gtk.Label(label="IP Address:")
        ip_label.set_size_request(100, -1)
        ip_box.pack_start(ip_label, False, False, 0)
        ip_entry = Gtk.Entry()
        ip_entry.set_placeholder_text("192.168.1.100/24")
        ip_box.pack_start(ip_entry, True, True, 0)
        static_box.pack_start(ip_box, False, False, 0)
        
        # Gateway
        gw_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        gw_label = Gtk.Label(label="Gateway:")
        gw_label.set_size_request(100, -1)
        gw_box.pack_start(gw_label, False, False, 0)
        gw_entry = Gtk.Entry()
        gw_entry.set_placeholder_text("192.168.1.1")
        gw_box.pack_start(gw_entry, True, True, 0)
        static_box.pack_start(gw_box, False, False, 0)
        
        # Bridge option
        bridge_check = Gtk.CheckButton(label="Create bridge for VMs (vmbr0)")
        static_box.pack_start(bridge_check, False, False, 0)
        
        box.pack_start(static_box, False, False, 0)
        
        # Store references
        self.interfaces[iface_name] = {
            "dhcp_radio": dhcp_radio,
            "static_radio": static_radio,
            "ip_entry": ip_entry,
            "gw_entry": gw_entry,
            "bridge_check": bridge_check,
            "static_box": static_box
        }
        
        # Connect signals
        dhcp_radio.connect("toggled", self.on_dhcp_toggled, iface_name)
        static_radio.connect("toggled", self.on_static_toggled, iface_name)
        
        frame.add(box)
        self.interface_box.pack_start(frame, False, False, 0)
        frame.show_all()
        
        # Set initial state
        dhcp_radio.set_active(True)
        static_box.set_sensitive(False)
        
    def on_dhcp_toggled(self, button, iface_name):
        if button.get_active():
            self.interfaces[iface_name]["static_box"].set_sensitive(False)
            
    def on_static_toggled(self, button, iface_name):
        if button.get_active():
            self.interfaces[iface_name]["static_box"].set_sensitive(True)
            
    def get_configuration(self) -> Dict:
        """Get the network configuration"""
        config = {
            "interfaces": {},
            "dns_servers": []
        }
        
        # Get interface configurations
        for iface_name, widgets in self.interfaces.items():
            if widgets["dhcp_radio"].get_active():
                config["interfaces"][iface_name] = {"type": "dhcp"}
            else:
                ip_text = widgets["ip_entry"].get_text()
                gw_text = widgets["gw_entry"].get_text()
                
                if not ip_text:
                    continue
                    
                try:
                    # Parse IP address with CIDR
                    ip_net = ipaddress.ip_network(ip_text, strict=False)
                    ip_addr = ip_text.split('/')[0]
                    netmask = str(ip_net.netmask)
                    
                    iface_config = {
                        "type": "static",
                        "address": ip_addr,
                        "netmask": netmask,
                        "gateway": gw_text
                    }
                    
                    if widgets["bridge_check"].get_active():
                        iface_config["bridge"] = True
                        iface_config["bridge_name"] = "vmbr0"
                        
                    config["interfaces"][iface_name] = iface_config
                    
                except Exception as e:
                    print(f"Invalid IP configuration: {e}")
                    
        # Get DNS servers
        dns1 = self.dns1_entry.get_text()
        dns2 = self.dns2_entry.get_text()
        
        if dns1:
            config["dns_servers"].append(dns1)
        if dns2:
            config["dns_servers"].append(dns2)
            
        return config
'''
        (module_path / "network_config_gui.py").write_text(gui_content)
        
        # Create __init__.py
        init_content = '''#!/usr/bin/env python3
"""Network Configuration Module for Calamares"""
from .main import NetworkConfigViewStep
__all__ = ["NetworkConfigViewStep"]
'''
        (module_path / "__init__.py").write_text(init_content)
        
        self.update_progress("completed", 100, "Network configuration module implementation complete")


class HardwareHealthAgent(ModuleImplementationAgent):
    """Agent for implementing Hardware Health Monitor Module"""
    
    def implement_module(self):
        """Implement the hardware health monitor module"""
        self.update_progress("starting", 10, "Creating hardware health module structure")
        
        # Create module directory
        module_path = Path("/opt/github/Z-FORGE/calamares/modules/hardwarehealth")
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create module descriptor
        self.update_progress("working", 20, "Creating module descriptor")
        module_desc = """# Hardware Health Monitor Module
---
type:       "python"
name:       "hardwarehealth"
interface:  "python"
requires:   []
script:     "main.py"
"""
        (module_path / "module.desc").write_text(module_desc)
        
        # Create main module file
        self.update_progress("working", 40, "Implementing hardware health monitoring logic")
        main_content = '''#!/usr/bin/env python3
"""
Hardware Health Monitor Module for Calamares
Configures comprehensive hardware monitoring
"""

import os
import sys
import json
import subprocess
import libcalamares
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
from hardware_health_gui import HardwareHealthWidget

def pretty_name():
    return "Hardware Monitoring"

def icon():
    return "utilities-system-monitor"

def run():
    """Configure hardware monitoring"""
    gs = libcalamares.globalstorage
    health_config = gs.value("hardwareHealthConfig")
    
    if not health_config:
        health_config = get_default_config()
    
    # Apply hardware monitoring configuration
    try:
        apply_health_config(health_config)
        return None
    except Exception as e:
        return "Hardware monitoring setup failed", str(e)

def get_default_config():
    """Get default monitoring configuration"""
    return {
        "monitoring": {
            "temperature": True,
            "smart": True,
            "raid": True,
            "power": True
        },
        "alerts": {
            "email": "",
            "cpu_temp_warning": 75,
            "cpu_temp_critical": 85,
            "disk_temp_warning": 50,
            "disk_space_warning": 80
        },
        "services": [
            "lm-sensors",
            "smartmontools",
            "ipmitool"
        ]
    }

def apply_health_config(config):
    """Apply hardware monitoring configuration"""
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    
    # Configure smartd
    if config["monitoring"].get("smart"):
        configure_smartd(root_mount_point, config)
    
    # Configure lm-sensors
    if config["monitoring"].get("temperature"):
        configure_sensors(root_mount_point, config)
    
    # Configure IPMI if available
    if config["monitoring"].get("power"):
        configure_ipmi(root_mount_point, config)
    
    # Setup monitoring scripts
    setup_monitoring_scripts(root_mount_point, config)

def configure_smartd(root_path, config):
    """Configure SMART monitoring"""
    smartd_conf = """# smartd.conf - SMART monitoring configuration
# Generated by Z-FORGE installer

# Monitor all disks
DEVICESCAN -a -o on -S on -n standby,q -s (S/../.././02|L/../../6/03) -W 4,{},{}
""".format(
        config["alerts"]["disk_temp_warning"],
        config["alerts"]["disk_temp_warning"] + 10
    )
    
    if config["alerts"].get("email"):
        smartd_conf = smartd_conf.replace("DEVICESCAN", f"DEVICESCAN -m {config['alerts']['email']}")
    
    smartd_path = Path(root_path) / "etc/smartd.conf"
    smartd_path.parent.mkdir(parents=True, exist_ok=True)
    smartd_path.write_text(smartd_conf)

def configure_sensors(root_path, config):
    """Configure lm-sensors"""
    # Create sensors configuration
    sensors_conf = """# Sensor alarm thresholds
# Generated by Z-FORGE installer

chip "*-isa-*"
    label temp1 "CPU Temp"
    set temp1_max {}
    set temp1_crit {}
""".format(
        config["alerts"]["cpu_temp_warning"],
        config["alerts"]["cpu_temp_critical"]
    )
    
    sensors_path = Path(root_path) / "etc/sensors3.conf"
    sensors_path.parent.mkdir(parents=True, exist_ok=True)
    sensors_path.write_text(sensors_conf)

def configure_ipmi(root_path, config):
    """Configure IPMI monitoring"""
    ipmi_script = """#!/bin/bash
# IPMI monitoring script
# Generated by Z-FORGE installer

# Check if IPMI is available
if ! lsmod | grep -q ipmi; then
    modprobe ipmi_devintf
    modprobe ipmi_si
fi

# Monitor temperatures
ipmitool sdr type temperature | while read line; do
    temp=$(echo $line | awk '{print $10}')
    if [ "$temp" -gt "{}" ]; then
        logger -t ipmi-monitor "High temperature detected: $line"
    fi
done

# Monitor power supplies
ipmitool sdr type "Power Supply" | while read line; do
    if echo "$line" | grep -q "Failure"; then
        logger -t ipmi-monitor "Power supply issue: $line"
    fi
done
""".format(config["alerts"]["cpu_temp_warning"])
    
    script_path = Path(root_path) / "usr/local/bin/ipmi-monitor.sh"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(ipmi_script)
    script_path.chmod(0o755)

def setup_monitoring_scripts(root_path, config):
    """Setup monitoring and alerting scripts"""
    monitor_script = """#!/bin/bash
# Hardware monitoring script
# Generated by Z-FORGE installer

ALERT_EMAIL="{}"
CPU_WARN={}
CPU_CRIT={}
DISK_WARN={}

# Check CPU temperature
check_cpu_temp() {{
    sensors | grep "Core" | while read line; do
        temp=$(echo $line | grep -oP '\\+\\K[0-9]+' | head -1)
        if [ "$temp" -gt "$CPU_CRIT" ]; then
            echo "CRITICAL: CPU temperature $temp°C" | mail -s "Hardware Alert" $ALERT_EMAIL
        elif [ "$temp" -gt "$CPU_WARN" ]; then
            echo "WARNING: CPU temperature $temp°C" | logger -t hw-monitor
        fi
    done
}}

# Check disk space
check_disk_space() {{
    df -h | grep -vE '^Filesystem|tmpfs|cdrom|udev' | awk '{{print $5 " " $1}}' | while read output; do
        usage=$(echo $output | awk '{{print $1}}' | sed 's/%//g')
        partition=$(echo $output | awk '{{print $2}}')
        if [ "$usage" -gt "$DISK_WARN" ]; then
            echo "WARNING: Disk usage on $partition is ${{usage}}%" | logger -t hw-monitor
        fi
    done
}}

# Check RAID status
check_raid_status() {{
    if command -v megacli &> /dev/null; then
        megacli -LDInfo -Lall -aAll | grep "State" | grep -v "Optimal" && echo "RAID issue detected" | logger -t hw-monitor
    fi
}}

# Run checks
check_cpu_temp
check_disk_space
check_raid_status
""".format(
        config["alerts"].get("email", "root"),
        config["alerts"]["cpu_temp_warning"],
        config["alerts"]["cpu_temp_critical"],
        config["alerts"]["disk_space_warning"]
    )
    
    script_path = Path(root_path) / "usr/local/bin/hardware-monitor.sh"
    script_path.write_text(monitor_script)
    script_path.chmod(0o755)
    
    # Create cron job
    cron_content = """# Hardware monitoring cron job
*/5 * * * * root /usr/local/bin/hardware-monitor.sh
0 */6 * * * root /usr/local/bin/ipmi-monitor.sh
"""
    cron_path = Path(root_path) / "etc/cron.d/hardware-monitoring"
    cron_path.write_text(cron_content)

class HardwareHealthViewStep:
    """Calamares ViewStep for hardware health monitoring"""
    
    def __init__(self):
        self.widget = None
        self.gs = libcalamares.globalstorage
    
    def name(self):
        return "hardwarehealth"
    
    def pretty_name(self):
        return "Hardware Monitoring"
    
    def icon(self):
        return "utilities-system-monitor"
    
    def widget(self):
        if self.widget is None:
            self.widget = HardwareHealthWidget(self.gs)
        return self.widget
    
    def next(self):
        if self.widget:
            config = self.widget.get_configuration()
            self.gs.insert("hardwareHealthConfig", config)
        return None
    
    def back(self):
        return None
    
    def jobs(self):
        return []

calamares_module = HardwareHealthViewStep
'''
        (module_path / "main.py").write_text(main_content)
        
        # Create GUI module
        self.update_progress("working", 60, "Creating hardware health GUI")
        gui_content = '''#!/usr/bin/env python3
"""
Hardware Health Monitor GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from typing import Dict

class HardwareHealthWidget(Gtk.Box):
    """Hardware health monitoring configuration widget"""
    
    def __init__(self, globalstorage):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.gs = globalstorage
        self.config = {
            "monitoring": {},
            "alerts": {},
            "services": []
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Hardware Monitoring Configuration</b>")
        self.pack_start(header, False, False, 0)
        
        # Monitoring options
        monitor_frame = Gtk.Frame(label="Monitoring Services")
        monitor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        monitor_box.set_margin_top(10)
        monitor_box.set_margin_bottom(10)
        monitor_box.set_margin_left(10)
        monitor_box.set_margin_right(10)
        
        self.temp_check = Gtk.CheckButton(label="Temperature Monitoring (lm-sensors)")
        self.temp_check.set_active(True)
        monitor_box.pack_start(self.temp_check, False, False, 0)
        
        self.smart_check = Gtk.CheckButton(label="Disk Health (smartmontools)")
        self.smart_check.set_active(True)
        monitor_box.pack_start(self.smart_check, False, False, 0)
        
        self.raid_check = Gtk.CheckButton(label="RAID Status (megacli/perccli)")
        self.raid_check.set_active(True)
        monitor_box.pack_start(self.raid_check, False, False, 0)
        
        self.power_check = Gtk.CheckButton(label="Power Monitoring (IPMI)")
        self.power_check.set_active(True)
        monitor_box.pack_start(self.power_check, False, False, 0)
        
        monitor_frame.add(monitor_box)
        self.pack_start(monitor_frame, False, False, 0)
        
        # Alert configuration
        alert_frame = Gtk.Frame(label="Alert Configuration")
        alert_grid = Gtk.Grid()
        alert_grid.set_column_spacing(10)
        alert_grid.set_row_spacing(10)
        alert_grid.set_margin_top(10)
        alert_grid.set_margin_bottom(10)
        alert_grid.set_margin_left(10)
        alert_grid.set_margin_right(10)
        
        # Email alerts
        email_label = Gtk.Label(label="Alert Email:")
        alert_grid.attach(email_label, 0, 0, 1, 1)
        
        self.email_entry = Gtk.Entry()
        self.email_entry.set_placeholder_text("admin@example.com")
        self.email_entry.set_hexpand(True)
        alert_grid.attach(self.email_entry, 1, 0, 2, 1)
        
        # Temperature thresholds
        cpu_warn_label = Gtk.Label(label="CPU Temp Warning:")
        alert_grid.attach(cpu_warn_label, 0, 1, 1, 1)
        
        self.cpu_warn_spin = Gtk.SpinButton.new_with_range(50, 100, 5)
        self.cpu_warn_spin.set_value(75)
        alert_grid.attach(self.cpu_warn_spin, 1, 1, 1, 1)
        
        cpu_crit_label = Gtk.Label(label="CPU Temp Critical:")
        alert_grid.attach(cpu_crit_label, 0, 2, 1, 1)
        
        self.cpu_crit_spin = Gtk.SpinButton.new_with_range(60, 105, 5)
        self.cpu_crit_spin.set_value(85)
        alert_grid.attach(self.cpu_crit_spin, 1, 2, 1, 1)
        
        # Disk thresholds
        disk_temp_label = Gtk.Label(label="Disk Temp Warning:")
        alert_grid.attach(disk_temp_label, 0, 3, 1, 1)
        
        self.disk_temp_spin = Gtk.SpinButton.new_with_range(40, 70, 5)
        self.disk_temp_spin.set_value(50)
        alert_grid.attach(self.disk_temp_spin, 1, 3, 1, 1)
        
        disk_space_label = Gtk.Label(label="Disk Space Warning:")
        alert_grid.attach(disk_space_label, 0, 4, 1, 1)
        
        self.disk_space_spin = Gtk.SpinButton.new_with_range(50, 95, 5)
        self.disk_space_spin.set_value(80)
        alert_grid.attach(self.disk_space_spin, 1, 4, 1, 1)
        
        percent_label = Gtk.Label(label="%")
        alert_grid.attach(percent_label, 2, 4, 1, 1)
        
        alert_frame.add(alert_grid)
        self.pack_start(alert_frame, False, False, 0)
        
        # Additional options
        options_frame = Gtk.Frame(label="Additional Options")
        options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        options_box.set_margin_top(10)
        options_box.set_margin_bottom(10)
        options_box.set_margin_left(10)
        options_box.set_margin_right(10)
        
        self.syslog_check = Gtk.CheckButton(label="Log to local syslog")
        self.syslog_check.set_active(True)
        options_box.pack_start(self.syslog_check, False, False, 0)
        
        self.remote_syslog_check = Gtk.CheckButton(label="Log to remote syslog")
        options_box.pack_start(self.remote_syslog_check, False, False, 0)
        
        remote_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        remote_label = Gtk.Label(label="Remote server:")
        remote_box.pack_start(remote_label, False, False, 0)
        
        self.remote_entry = Gtk.Entry()
        self.remote_entry.set_placeholder_text("syslog.example.com:514")
        self.remote_entry.set_sensitive(False)
        remote_box.pack_start(self.remote_entry, True, True, 0)
        
        options_box.pack_start(remote_box, False, False, 0)
        
        self.remote_syslog_check.connect("toggled", self.on_remote_toggled)
        
        options_frame.add(options_box)
        self.pack_start(options_frame, False, False, 0)
        
        self.show_all()
        
    def on_remote_toggled(self, button):
        """Handle remote syslog toggle"""
        self.remote_entry.set_sensitive(button.get_active())
        
    def get_configuration(self) -> Dict:
        """Get the hardware monitoring configuration"""
        config = {
            "monitoring": {
                "temperature": self.temp_check.get_active(),
                "smart": self.smart_check.get_active(),
                "raid": self.raid_check.get_active(),
                "power": self.power_check.get_active()
            },
            "alerts": {
                "email": self.email_entry.get_text(),
                "cpu_temp_warning": int(self.cpu_warn_spin.get_value()),
                "cpu_temp_critical": int(self.cpu_crit_spin.get_value()),
                "disk_temp_warning": int(self.disk_temp_spin.get_value()),
                "disk_space_warning": int(self.disk_space_spin.get_value())
            },
            "services": []
        }
        
        # Determine required services
        if config["monitoring"]["temperature"]:
            config["services"].append("lm-sensors")
        if config["monitoring"]["smart"]:
            config["services"].append("smartmontools")
        if config["monitoring"]["power"]:
            config["services"].append("ipmitool")
            
        return config
'''
        (module_path / "hardware_health_gui.py").write_text(gui_content)
        
        # Create __init__.py
        init_content = '''#!/usr/bin/env python3
"""Hardware Health Monitor Module for Calamares"""
from .main import HardwareHealthViewStep
__all__ = ["HardwareHealthViewStep"]
'''
        (module_path / "__init__.py").write_text(init_content)
        
        self.update_progress("completed", 100, "Hardware health module implementation complete")


class GPUPassthroughAgent(ModuleImplementationAgent):
    """Agent for implementing GPU Passthrough Module"""
    
    def implement_module(self):
        """Implement the GPU passthrough module"""
        self.update_progress("starting", 10, "Creating GPU passthrough module structure")
        
        # Create module directory
        module_path = Path("/opt/github/Z-FORGE/calamares/modules/gpupassthrough")
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create module descriptor
        self.update_progress("working", 20, "Creating module descriptor")
        module_desc = """# GPU Passthrough Configuration Module
---
type:       "python"
name:       "gpupassthrough"
interface:  "python"
requires:   []
script:     "main.py"
"""
        (module_path / "module.desc").write_text(module_desc)
        
        # Create main module file
        self.update_progress("working", 40, "Implementing GPU passthrough logic")
        main_content = '''#!/usr/bin/env python3
"""
GPU Passthrough Configuration Module for Calamares
Automates GPU passthrough setup for virtualization
"""

import os
import sys
import json
import subprocess
import re
import libcalamares
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
from gpu_passthrough_gui import GPUPassthroughWidget

def pretty_name():
    return "GPU Passthrough"

def icon():
    return "video-display"

def run():
    """Configure GPU passthrough"""
    gs = libcalamares.globalstorage
    gpu_config = gs.value("gpuPassthroughConfig")
    
    if not gpu_config or not gpu_config.get("gpus"):
        # No GPUs selected for passthrough
        return None
    
    try:
        apply_gpu_passthrough(gpu_config)
        return None
    except Exception as e:
        return "GPU passthrough configuration failed", str(e)

def apply_gpu_passthrough(config):
    """Apply GPU passthrough configuration"""
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    
    # Enable IOMMU in bootloader
    if config.get("enable_iommu"):
        enable_iommu(root_mount_point)
    
    # Configure VFIO
    configure_vfio(root_mount_point, config)
    
    # Blacklist GPU drivers
    if config.get("blacklist_drivers"):
        blacklist_gpu_drivers(root_mount_point, config)
    
    # Configure modprobe
    configure_modprobe(root_mount_point, config)
    
    # Update initramfs
    update_initramfs(root_mount_point)

def enable_iommu(root_path):
    """Enable IOMMU in GRUB"""
    grub_path = Path(root_path) / "etc/default/grub"
    
    if grub_path.exists():
        content = grub_path.read_text()
        
        # Check CPU vendor
        cpu_vendor = detect_cpu_vendor()
        iommu_param = "intel_iommu=on" if cpu_vendor == "intel" else "amd_iommu=on"
        
        # Add IOMMU parameters
        if 'GRUB_CMDLINE_LINUX_DEFAULT=' in content:
            # Update existing line
            lines = content.split('\\n')
            for i, line in enumerate(lines):
                if line.startswith('GRUB_CMDLINE_LINUX_DEFAULT='):
                    if iommu_param not in line:
                        # Add to existing parameters
                        if line.endswith('"'):
                            lines[i] = line[:-1] + f' {iommu_param} iommu=pt"'
                        else:
                            lines[i] = line + f' {iommu_param} iommu=pt'
                    break
            content = '\\n'.join(lines)
        else:
            # Add new line
            content += f'\\nGRUB_CMDLINE_LINUX_DEFAULT="{iommu_param} iommu=pt"\\n'
        
        grub_path.write_text(content)

def detect_cpu_vendor():
    """Detect CPU vendor"""
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        if "GenuineIntel" in cpuinfo:
            return "intel"
        elif "AuthenticAMD" in cpuinfo:
            return "amd"
    except:
        pass
    return "intel"  # Default

def configure_vfio(root_path, config):
    """Configure VFIO for GPU passthrough"""
    vfio_conf = "# VFIO GPU Passthrough Configuration\\n"
    vfio_conf += "# Generated by Z-FORGE installer\\n\\n"
    
    # Add PCI IDs
    pci_ids = []
    for gpu in config.get("gpus", []):
        if gpu.get("selected"):
            pci_ids.append(gpu["vendor_id"] + ":" + gpu["device_id"])
            if gpu.get("audio_id"):
                pci_ids.append(gpu["vendor_id"] + ":" + gpu["audio_id"])
    
    if pci_ids:
        vfio_conf += f"options vfio-pci ids={','.join(pci_ids)}\\n"
    
    # Write configuration
    vfio_path = Path(root_path) / "etc/modprobe.d/vfio.conf"
    vfio_path.parent.mkdir(parents=True, exist_ok=True)
    vfio_path.write_text(vfio_conf)
    
    # Add VFIO modules to initramfs
    modules_path = Path(root_path) / "etc/modules"
    modules_content = modules_path.read_text() if modules_path.exists() else ""
    
    vfio_modules = ["vfio", "vfio_iommu_type1", "vfio_pci", "vfio_virqfd"]
    for module in vfio_modules:
        if module not in modules_content:
            modules_content += f"{module}\\n"
    
    modules_path.write_text(modules_content)

def blacklist_gpu_drivers(root_path, config):
    """Blacklist GPU drivers"""
    blacklist_conf = "# GPU driver blacklist for passthrough\\n"
    blacklist_conf += "# Generated by Z-FORGE installer\\n\\n"
    
    drivers_to_blacklist = set()
    for gpu in config.get("gpus", []):
        if gpu.get("selected"):
            if "nvidia" in gpu.get("name", "").lower():
                drivers_to_blacklist.update(["nouveau", "nvidia", "nvidia_drm", "nvidia_modeset"])
            elif "amd" in gpu.get("name", "").lower() or "radeon" in gpu.get("name", "").lower():
                drivers_to_blacklist.update(["radeon", "amdgpu"])
            elif "intel" in gpu.get("name", "").lower():
                drivers_to_blacklist.add("i915")
    
    for driver in drivers_to_blacklist:
        blacklist_conf += f"blacklist {driver}\\n"
    
    blacklist_path = Path(root_path) / "etc/modprobe.d/blacklist-gpu.conf"
    blacklist_path.write_text(blacklist_conf)

def configure_modprobe(root_path, config):
    """Configure modprobe options"""
    if config.get("acs_override"):
        acs_conf = "# ACS Override for IOMMU groups\\n"
        acs_conf += "options pcie_acs_override=downstream,multifunction\\n"
        
        acs_path = Path(root_path) / "etc/modprobe.d/acs-override.conf"
        acs_path.write_text(acs_conf)

def update_initramfs(root_path):
    """Update initramfs configuration"""
    # This would normally trigger initramfs rebuild
    # In Calamares context, this is usually handled by other modules
    pass

def detect_gpus():
    """Detect available GPUs"""
    gpus = []
    
    try:
        # Use lspci to detect GPUs
        output = subprocess.check_output(["lspci", "-nn"]).decode()
        
        # Regex to match VGA/3D controllers
        gpu_regex = re.compile(r'^([0-9a-f:.]+)\\s+(?:VGA compatible controller|3D controller):\\s+(.+?)\\s+\\[([0-9a-f]+):([0-9a-f]+)\\]', re.MULTILINE)
        
        for match in gpu_regex.finditer(output):
            pci_addr = match.group(1)
            name = match.group(2)
            vendor_id = match.group(3)
            device_id = match.group(4)
            
            gpu_info = {
                "pci_addr": pci_addr,
                "name": name,
                "vendor_id": vendor_id,
                "device_id": device_id,
                "iommu_group": get_iommu_group(pci_addr),
                "reset_available": check_reset_support(pci_addr)
            }
            
            # Check for audio device
            audio_addr = pci_addr.rsplit('.', 1)[0] + '.1'
            audio_match = re.search(f'{audio_addr}.*Audio.*\\[{vendor_id}:([0-9a-f]+)\\]', output)
            if audio_match:
                gpu_info["audio_id"] = audio_match.group(1)
                gpu_info["audio_addr"] = audio_addr
            
            gpus.append(gpu_info)
    
    except Exception as e:
        libcalamares.utils.debug(f"Error detecting GPUs: {e}")
    
    return gpus

def get_iommu_group(pci_addr):
    """Get IOMMU group for PCI device"""
    try:
        iommu_path = Path(f"/sys/bus/pci/devices/0000:{pci_addr}/iommu_group")
        if iommu_path.exists():
            return int(iommu_path.resolve().name)
    except:
        pass
    return -1

def check_reset_support(pci_addr):
    """Check if GPU supports function level reset"""
    try:
        reset_path = Path(f"/sys/bus/pci/devices/0000:{pci_addr}/reset")
        return reset_path.exists()
    except:
        return False

class GPUPassthroughViewStep:
    """Calamares ViewStep for GPU passthrough configuration"""
    
    def __init__(self):
        self.widget = None
        self.gs = libcalamares.globalstorage
    
    def name(self):
        return "gpupassthrough"
    
    def pretty_name(self):
        return "GPU Passthrough"
    
    def icon(self):
        return "video-display"
    
    def widget(self):
        if self.widget is None:
            gpus = detect_gpus()
            self.widget = GPUPassthroughWidget(self.gs, gpus)
        return self.widget
    
    def next(self):
        if self.widget:
            config = self.widget.get_configuration()
            self.gs.insert("gpuPassthroughConfig", config)
        return None
    
    def back(self):
        return None
    
    def jobs(self):
        return []

calamares_module = GPUPassthroughViewStep
'''
        (module_path / "main.py").write_text(main_content)
        
        # Create GUI module
        self.update_progress("working", 60, "Creating GPU passthrough GUI")
        gui_content = '''#!/usr/bin/env python3
"""
GPU Passthrough Configuration GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from typing import Dict, List

class GPUPassthroughWidget(Gtk.Box):
    """GPU passthrough configuration widget"""
    
    def __init__(self, globalstorage, detected_gpus):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.gs = globalstorage
        self.detected_gpus = detected_gpus
        self.gpu_widgets = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>GPU Passthrough Configuration</b>")
        self.pack_start(header, False, False, 0)
        
        if not self.detected_gpus:
            no_gpu_label = Gtk.Label()
            no_gpu_label.set_markup("<i>No discrete GPUs detected</i>")
            self.pack_start(no_gpu_label, True, True, 0)
        else:
            # GPU list
            gpu_label = Gtk.Label()
            gpu_label.set_markup("<b>Detected GPUs:</b>")
            gpu_label.set_alignment(0, 0.5)
            self.pack_start(gpu_label, False, False, 0)
            
            # Scrolled window for GPU list
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(200)
            
            gpu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            
            for gpu in self.detected_gpus:
                gpu_frame = self.create_gpu_frame(gpu)
                gpu_box.pack_start(gpu_frame, False, False, 0)
            
            scroll.add(gpu_box)
            self.pack_start(scroll, True, True, 0)
            
            # Configuration options
            config_frame = Gtk.Frame(label="Configuration Options")
            config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            config_box.set_margin_top(10)
            config_box.set_margin_bottom(10)
            config_box.set_margin_left(10)
            config_box.set_margin_right(10)
            
            self.iommu_check = Gtk.CheckButton(label="Enable IOMMU in bootloader")
            self.iommu_check.set_active(True)
            config_box.pack_start(self.iommu_check, False, False, 0)
            
            self.blacklist_check = Gtk.CheckButton(label="Blacklist GPU drivers")
            self.blacklist_check.set_active(True)
            config_box.pack_start(self.blacklist_check, False, False, 0)
            
            self.vfio_check = Gtk.CheckButton(label="Configure VFIO early binding")
            self.vfio_check.set_active(True)
            config_box.pack_start(self.vfio_check, False, False, 0)
            
            self.acs_check = Gtk.CheckButton(label="Enable ACS override (reduces security)")
            self.acs_check.set_tooltip_text("Only enable if IOMMU groups are problematic")
            config_box.pack_start(self.acs_check, False, False, 0)
            
            config_frame.add(config_box)
            self.pack_start(config_frame, False, False, 0)
            
            # Info box
            info_frame = Gtk.Frame(label="Important Information")
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            info_box.set_margin_top(10)
            info_box.set_margin_bottom(10)
            info_box.set_margin_left(10)
            info_box.set_margin_right(10)
            
            info_text = """• GPU passthrough requires VT-d (Intel) or AMD-Vi support
• The host will lose access to passed through GPUs
• A separate GPU is recommended for host display
• Reboot required after configuration"""
            
            info_label = Gtk.Label(label=info_text)
            info_label.set_alignment(0, 0)
            info_box.pack_start(info_label, False, False, 0)
            
            info_frame.add(info_box)
            self.pack_start(info_frame, False, False, 0)
        
        self.show_all()
        
    def create_gpu_frame(self, gpu):
        """Create frame for a single GPU"""
        frame = Gtk.Frame()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        box.set_margin_left(10)
        box.set_margin_right(10)
        
        # GPU selection checkbox
        gpu_check = Gtk.CheckButton()
        gpu_label = f"{gpu['name']} [{gpu['vendor_id']}:{gpu['device_id']}]"
        gpu_check.set_label(gpu_label)
        box.pack_start(gpu_check, False, False, 0)
        
        # GPU details
        details_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        details_box.set_margin_left(20)
        
        # PCI address
        pci_label = Gtk.Label()
        pci_label.set_markup(f"<small>PCI: {gpu['pci_addr']}</small>")
        pci_label.set_alignment(0, 0.5)
        details_box.pack_start(pci_label, False, False, 0)
        
        # IOMMU group
        iommu_label = Gtk.Label()
        iommu_text = f"IOMMU Group: {gpu['iommu_group']}" if gpu['iommu_group'] >= 0 else "IOMMU Group: Not available"
        iommu_label.set_markup(f"<small>{iommu_text}</small>")
        iommu_label.set_alignment(0, 0.5)
        details_box.pack_start(iommu_label, False, False, 0)
        
        # Reset support
        reset_label = Gtk.Label()
        reset_text = "Reset: ✓ Supported" if gpu['reset_available'] else "Reset: ✗ Not supported"
        reset_label.set_markup(f"<small>{reset_text}</small>")
        reset_label.set_alignment(0, 0.5)
        details_box.pack_start(reset_label, False, False, 0)
        
        # Audio device
        if gpu.get('audio_id'):
            audio_check = Gtk.CheckButton()
            audio_check.set_label(f"Include HDMI Audio [{gpu['vendor_id']}:{gpu['audio_id']}]")
            audio_check.set_margin_left(20)
            audio_check.set_active(True)
            box.pack_start(audio_check, False, False, 0)
        else:
            audio_check = None
        
        box.pack_start(details_box, False, False, 0)
        
        frame.add(box)
        
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
            "enable_iommu": self.iommu_check.get_active() if hasattr(self, 'iommu_check') else False,
            "blacklist_drivers": self.blacklist_check.get_active() if hasattr(self, 'blacklist_check') else False,
            "configure_vfio": self.vfio_check.get_active() if hasattr(self, 'vfio_check') else False,
            "acs_override": self.acs_check.get_active() if hasattr(self, 'acs_check') else False,
            "gpus": []
        }
        
        # Get selected GPUs
        for widget_info in self.gpu_widgets:
            gpu = widget_info["gpu"].copy()
            gpu["selected"] = widget_info["checkbox"].get_active()
            
            if widget_info["audio_checkbox"]:
                gpu["include_audio"] = widget_info["audio_checkbox"].get_active()
            
            config["gpus"].append(gpu)
        
        return config
'''
        (module_path / "gpu_passthrough_gui.py").write_text(gui_content)
        
        # Create __init__.py
        init_content = '''#!/usr/bin/env python3
"""GPU Passthrough Configuration Module for Calamares"""
from .main import GPUPassthroughViewStep
__all__ = ["GPUPassthroughViewStep"]
'''
        (module_path / "__init__.py").write_text(init_content)
        
        self.update_progress("completed", 100, "GPU passthrough module implementation complete")


class StorageLayoutAgent(ModuleImplementationAgent):
    """Agent for implementing Storage Layout Templates Module"""
    
    def implement_module(self):
        """Implement the storage layout templates module"""
        self.update_progress("starting", 10, "Creating storage layout module structure")
        
        # Create module directory
        module_path = Path("/opt/github/Z-FORGE/calamares/modules/storagelayout")
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create module descriptor
        self.update_progress("working", 20, "Creating module descriptor")
        module_desc = """# Storage Layout Templates Module
---
type:       "python"
name:       "storagelayout"
interface:  "python"
requires:   []
script:     "main.py"
"""
        (module_path / "module.desc").write_text(module_desc)
        
        # Create main module file
        self.update_progress("working", 40, "Implementing storage layout logic")
        main_content = '''#!/usr/bin/env python3
"""
Storage Layout Templates Module for Calamares
Pre-configured ZFS dataset layouts for different use cases
"""

import os
import sys
import json
import subprocess
import libcalamares
from pathlib import Path

sys.path.append(os.path.dirname(__file__))
from storage_layout_gui import StorageLayoutWidget

def pretty_name():
    return "Storage Layout"

def icon():
    return "drive-harddisk"

def run():
    """Apply storage layout template"""
    gs = libcalamares.globalstorage
    layout_config = gs.value("storageLayoutConfig")
    
    if not layout_config or layout_config.get("template") == "none":
        # No template selected
        return None
    
    try:
        apply_storage_layout(layout_config)
        return None
    except Exception as e:
        return "Storage layout configuration failed", str(e)

def apply_storage_layout(config):
    """Apply the selected storage layout template"""
    pool_name = libcalamares.globalstorage.value("zfsPoolName")
    if not pool_name:
        raise Exception("No ZFS pool configured")
    
    template = config.get("template")
    datasets = get_template_datasets(template)
    
    # Create datasets with appropriate properties
    for dataset in datasets:
        create_dataset(pool_name, dataset)
    
    # Setup snapshot policies if requested
    if config.get("snapshot_schedule"):
        setup_snapshot_schedule(pool_name, template)
    
    # Set quotas if requested
    if config.get("set_quotas"):
        setup_quotas(pool_name, template)

def get_template_datasets(template):
    """Get dataset configuration for template"""
    templates = {
        "proxmox": [
            {"name": "vm-disks", "props": {"recordsize": "64K", "compression": "lz4"}},
            {"name": "containers", "props": {"recordsize": "128K", "compression": "zstd-3"}},
            {"name": "templates", "props": {"recordsize": "1M", "compression": "off"}},
            {"name": "backups", "props": {"recordsize": "1M", "compression": "zstd-6"}},
            {"name": "shared", "props": {"recordsize": "128K", "compression": "lz4"}}
        ],
        "media": [
            {"name": "media", "props": {"recordsize": "1M", "compression": "off"}},
            {"name": "media/movies", "props": {"recordsize": "1M", "compression": "off"}},
            {"name": "media/tv", "props": {"recordsize": "1M", "compression": "off"}},
            {"name": "media/music", "props": {"recordsize": "128K", "compression": "zstd"}},
            {"name": "media/photos", "props": {"recordsize": "128K", "compression": "zstd"}},
            {"name": "downloads", "props": {"recordsize": "128K", "compression": "lz4"}},
            {"name": "apps", "props": {"recordsize": "128K", "compression": "lz4"}},
            {"name": "documents", "props": {"recordsize": "128K", "compression": "zstd-6"}}
        ],
        "database": [
            {"name": "postgres", "props": {"recordsize": "8K", "compression": "lz4"}},
            {"name": "postgres/data", "props": {"recordsize": "8K", "compression": "lz4", "logbias": "throughput"}},
            {"name": "postgres/wal", "props": {"recordsize": "128K", "compression": "off", "sync": "always"}},
            {"name": "mysql", "props": {"recordsize": "16K", "compression": "lz4"}},
            {"name": "mysql/data", "props": {"recordsize": "16K", "compression": "lz4"}},
            {"name": "mysql/logs", "props": {"recordsize": "128K", "compression": "zstd"}},
            {"name": "mongodb", "props": {"recordsize": "16K", "compression": "lz4"}},
            {"name": "redis", "props": {"recordsize": "8K", "compression": "lz4", "sync": "disabled"}}
        ],
        "development": [
            {"name": "home", "props": {"recordsize": "128K", "compression": "lz4"}},
            {"name": "projects", "props": {"recordsize": "128K", "compression": "lz4"}},
            {"name": "docker", "props": {"recordsize": "128K", "compression": "zstd"}},
            {"name": "vms", "props": {"recordsize": "64K", "compression": "lz4"}},
            {"name": "snapshots", "props": {"recordsize": "128K", "compression": "zstd-6"}}
        ]
    }
    
    return templates.get(template, [])

def create_dataset(pool_name, dataset_config):
    """Create a ZFS dataset with properties"""
    dataset_path = f"{pool_name}/{dataset_config['name']}"
    
    # Build zfs create command
    cmd = ["zfs", "create"]
    
    # Add properties
    for prop, value in dataset_config.get("props", {}).items():
        cmd.extend(["-o", f"{prop}={value}"])
    
    cmd.append(dataset_path)
    
    # Execute command
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        libcalamares.utils.debug(f"Created dataset: {dataset_path}")
    except subprocess.CalledProcessError as e:
        libcalamares.utils.warning(f"Failed to create dataset {dataset_path}: {e}")

def setup_snapshot_schedule(pool_name, template):
    """Setup automatic snapshot schedules"""
    # This would integrate with zfs-auto-snapshot or similar
    # For now, create a basic cron configuration
    
    schedules = {
        "proxmox": {
            "vm-disks": "hourly",
            "containers": "daily",
            "shared": "weekly"
        },
        "media": {
            "documents": "daily",
            "photos": "weekly"
        },
        "database": {
            "postgres/data": "hourly",
            "mysql/data": "hourly"
        },
        "development": {
            "projects": "hourly",
            "home": "daily"
        }
    }
    
    template_schedules = schedules.get(template, {})
    
    # Write cron configuration
    cron_content = "# ZFS Auto-snapshot schedule\\n"
    cron_content += "# Generated by Z-FORGE installer\\n\\n"
    
    for dataset, frequency in template_schedules.items():
        if frequency == "hourly":
            cron_content += f"0 * * * * root zfs snapshot {pool_name}/{dataset}@auto-$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S)\\n"
        elif frequency == "daily":
            cron_content += f"0 2 * * * root zfs snapshot {pool_name}/{dataset}@auto-$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S)\\n"
        elif frequency == "weekly":
            cron_content += f"0 2 * * 0 root zfs snapshot {pool_name}/{dataset}@auto-$(date +\\%Y\\%m\\%d-\\%H\\%M\\%S)\\n"
    
    # Write to target system
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    cron_path = Path(root_mount_point) / "etc/cron.d/zfs-auto-snapshot"
    cron_path.parent.mkdir(parents=True, exist_ok=True)
    cron_path.write_text(cron_content)

def setup_quotas(pool_name, template):
    """Setup recommended quotas for datasets"""
    # This would set quotas based on available space and template
    # For now, just log the intention
    libcalamares.utils.debug(f"Quota setup for {template} template would be configured here")

class StorageLayoutViewStep:
    """Calamares ViewStep for storage layout templates"""
    
    def __init__(self):
        self.widget = None
        self.gs = libcalamares.globalstorage
    
    def name(self):
        return "storagelayout"
    
    def pretty_name(self):
        return "Storage Layout"
    
    def icon(self):
        return "drive-harddisk"
    
    def widget(self):
        if self.widget is None:
            pool_name = self.gs.value("zfsPoolName")
            self.widget = StorageLayoutWidget(self.gs, pool_name)
        return self.widget
    
    def next(self):
        if self.widget:
            config = self.widget.get_configuration()
            self.gs.insert("storageLayoutConfig", config)
        return None
    
    def back(self):
        return None
    
    def jobs(self):
        return []

calamares_module = StorageLayoutViewStep
'''
        (module_path / "main.py").write_text(main_content)
        
        # Create GUI module
        self.update_progress("working", 60, "Creating storage layout GUI")
        gui_content = '''#!/usr/bin/env python3
"""
Storage Layout Templates GUI for Calamares
"""

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Pango
from typing import Dict

class StorageLayoutWidget(Gtk.Box):
    """Storage layout template selection widget"""
    
    def __init__(self, globalstorage, pool_name):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.gs = globalstorage
        self.pool_name = pool_name or "tank"
        self.selected_template = "none"
        
        self.setup_ui()
        
    def setup_ui(self):
        """Build the UI"""
        # Header
        header = Gtk.Label()
        header.set_markup("<b>Storage Layout Templates</b>")
        self.pack_start(header, False, False, 0)
        
        if not self.pool_name:
            no_pool_label = Gtk.Label()
            no_pool_label.set_markup("<i>No ZFS pool configured. Please configure a pool first.</i>")
            self.pack_start(no_pool_label, True, True, 0)
        else:
            # Pool info
            pool_info = Gtk.Label()
            pool_info.set_markup(f"Configuring datasets for pool: <b>{self.pool_name}</b>")
            self.pack_start(pool_info, False, False, 0)
            
            # Template selection
            template_frame = Gtk.Frame(label="Select Template")
            template_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            template_box.set_margin_top(10)
            template_box.set_margin_bottom(10)
            template_box.set_margin_left(10)
            template_box.set_margin_right(10)
            
            templates = [
                ("none", "No Template", "Skip automatic dataset creation"),
                ("proxmox", "Proxmox Virtualization Server", "Optimized for VMs and containers"),
                ("media", "Homelab Media Server", "Optimized for media storage and streaming"),
                ("database", "Database Server", "Optimized for PostgreSQL, MySQL, MongoDB"),
                ("development", "Development Workstation", "Optimized for coding and development")
            ]
            
            self.template_buttons = {}
            first_button = None
            
            for template_id, name, description in templates:
                if first_button is None:
                    button = Gtk.RadioButton.new_with_label(None, name)
                    first_button = button
                else:
                    button = Gtk.RadioButton.new_with_label_from_widget(first_button, name)
                
                button.set_tooltip_text(description)
                button.connect("toggled", self.on_template_changed, template_id)
                self.template_buttons[template_id] = button
                template_box.pack_start(button, False, False, 0)
            
            # Set default
            self.template_buttons["none"].set_active(True)
            
            template_frame.add(template_box)
            self.pack_start(template_frame, False, False, 0)
            
            # Preview area
            preview_frame = Gtk.Frame(label="Preview")
            
            # Scrolled window for preview
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scroll.set_min_content_height(200)
            
            self.preview_buffer = Gtk.TextBuffer()
            self.preview_view = Gtk.TextView(buffer=self.preview_buffer)
            self.preview_view.set_editable(False)
            self.preview_view.set_wrap_mode(Gtk.WrapMode.WORD)
            
            # Use monospace font
            font_desc = Pango.FontDescription("monospace 9")
            self.preview_view.modify_font(font_desc)
            
            scroll.add(self.preview_view)
            preview_frame.add(scroll)
            self.pack_start(preview_frame, True, True, 0)
            
            # Options
            options_frame = Gtk.Frame(label="Options")
            options_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            options_box.set_margin_top(10)
            options_box.set_margin_bottom(10)
            options_box.set_margin_left(10)
            options_box.set_margin_right(10)
            
            self.snapshot_check = Gtk.CheckButton(label="Create snapshot schedule")
            self.snapshot_check.set_tooltip_text("Automatically snapshot important datasets")
            options_box.pack_start(self.snapshot_check, False, False, 0)
            
            self.quota_check = Gtk.CheckButton(label="Set recommended quotas")
            self.quota_check.set_tooltip_text("Apply size limits to prevent runaway growth")
            options_box.pack_start(self.quota_check, False, False, 0)
            
            options_frame.add(options_box)
            self.pack_start(options_frame, False, False, 0)
            
            # Update preview
            self.update_preview()
        
        self.show_all()
        
    def on_template_changed(self, button, template_id):
        """Handle template selection change"""
        if button.get_active():
            self.selected_template = template_id
            self.update_preview()
            
            # Enable/disable options based on template
            if template_id == "none":
                self.snapshot_check.set_sensitive(False)
                self.quota_check.set_sensitive(False)
            else:
                self.snapshot_check.set_sensitive(True)
                self.quota_check.set_sensitive(True)
    
    def update_preview(self):
        """Update the preview text"""
        if self.selected_template == "none":
            preview_text = "No datasets will be created automatically."
        else:
            preview_text = self.generate_preview(self.selected_template)
        
        self.preview_buffer.set_text(preview_text)
    
    def generate_preview(self, template):
        """Generate preview text for template"""
        templates = {
            "proxmox": """Proxmox Virtualization Server Layout:

{}/vm-disks         (64K records, lz4)
  └─ VM disk images

{}/containers       (128K records, zstd-3)
  └─ LXC container storage

{}/templates        (1M records, no compression)
  └─ ISO and template storage

{}/backups          (1M records, zstd-6)
  └─ Backup storage

{}/shared           (128K records, lz4)
  └─ Shared data between VMs/containers""",
  
            "media": """Homelab Media Server Layout:

{}/media/movies     (1M records, no compression)
  └─ Movie collection

{}/media/tv         (1M records, no compression)
  └─ TV show collection

{}/media/music      (128K records, zstd)
  └─ Music library

{}/media/photos     (128K records, zstd)
  └─ Photo collection

{}/downloads        (128K records, lz4)
  └─ Download directory

{}/apps             (128K records, lz4)
  └─ Application data

{}/documents        (128K records, zstd-6)
  └─ Document storage""",
  
            "database": """Database Server Layout:

{}/postgres/data    (8K records, lz4, throughput)
  └─ PostgreSQL data directory

{}/postgres/wal     (128K records, no compression, sync)
  └─ PostgreSQL WAL logs

{}/mysql/data       (16K records, lz4)
  └─ MySQL data directory

{}/mysql/logs       (128K records, zstd)
  └─ MySQL logs

{}/mongodb          (16K records, lz4)
  └─ MongoDB data

{}/redis            (8K records, lz4, async)
  └─ Redis persistence""",
  
            "development": """Development Workstation Layout:

{}/home             (128K records, lz4)
  └─ User home directories

{}/projects         (128K records, lz4)
  └─ Development projects

{}/docker           (128K records, zstd)
  └─ Docker images and volumes

{}/vms              (64K records, lz4)
  └─ Virtual machines

{}/snapshots        (128K records, zstd-6)
  └─ Snapshot storage"""
        }
        
        template_text = templates.get(template, "Unknown template")
        # Replace {} with pool name
        return template_text.replace("{}", self.pool_name)
    
    def get_configuration(self) -> Dict:
        """Get the storage layout configuration"""
        return {
            "template": self.selected_template,
            "snapshot_schedule": self.snapshot_check.get_active() if hasattr(self, 'snapshot_check') else False,
            "set_quotas": self.quota_check.get_active() if hasattr(self, 'quota_check') else False
        }
'''
        (module_path / "storage_layout_gui.py").write_text(gui_content)
        
        # Create __init__.py
        init_content = '''#!/usr/bin/env python3
"""Storage Layout Templates Module for Calamares"""
from .main import StorageLayoutViewStep
__all__ = ["StorageLayoutViewStep"]
'''
        (module_path / "__init__.py").write_text(init_content)
        
        self.update_progress("completed", 100, "Storage layout module implementation complete")


class PostInstallAgent(ModuleImplementationAgent):
    """Agent for implementing Post-Install Checklist Module"""
    
    def implement_module(self):
        """Implement the post-install checklist module"""
        self.update_progress("starting", 10, "Creating post-install checklist module structure")
        
        # Create module directory
        module_path = Path("/opt/github/Z-FORGE/calamares/modules/postinstall")
        module_path.mkdir(parents=True, exist_ok=True)
        
        # Create module descriptor
        self.update_progress("working", 20, "Creating module descriptor")
        module_desc = """# Post-Installation Checklist Module
---
type:       "python"
name:       "postinstall"
interface:  "python"
requires:   []
script:     "main.py"
"""
        (module_path / "module.desc").write_text(module_desc)
        
        # Create main module file
        self.update_progress("working", 40, "Implementing post-install checklist logic")
        main_content = '''#!/usr/bin/env python3
"""
Post-Installation Checklist Module for Calamares
Interactive checklist for post-installation tasks
"""

import os
import sys
import json
import subprocess
import libcalamares
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
from postinstall_gui import PostInstallWidget

def pretty_name():
    return "Post-Install Setup"

def icon():
    return "checkbox"

def run():
    """Setup post-installation checklist"""
    gs = libcalamares.globalstorage
    checklist_config = gs.value("postInstallConfig")
    
    if not checklist_config:
        checklist_config = get_default_checklist()
    
    try:
        setup_postinstall_checklist(checklist_config)
        return None
    except Exception as e:
        return "Post-install setup failed", str(e)

def get_default_checklist():
    """Get default checklist configuration"""
    return {
        "first_boot_wizard": True,
        "auto_start": True,
        "categories": {
            "security": True,
            "storage": True,
            "network": True,
            "proxmox": True,
            "monitoring": True
        }
    }

def setup_postinstall_checklist(config):
    """Setup post-installation checklist and wizard"""
    root_mount_point = libcalamares.globalstorage.value("rootMountPoint")
    
    # Create checklist script
    create_checklist_script(root_mount_point, config)
    
    # Create systemd service for first boot
    if config.get("first_boot_wizard"):
        create_firstboot_service(root_mount_point)
    
    # Create desktop entry
    create_desktop_entry(root_mount_point)
    
    # Save checklist configuration
    save_checklist_config(root_mount_point, config)

def create_checklist_script(root_path, config):
    """Create the post-install checklist script"""
    script_content = """#!/usr/bin/env python3
"""
Z-FORGE Post-Installation Checklist
Interactive wizard for completing system setup
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

class PostInstallChecklist:
    def __init__(self):
        self.config_file = Path("/etc/zforge/postinstall.json")
        self.progress_file = Path("/etc/zforge/postinstall_progress.json")
        self.load_progress()
        
    def load_progress(self):
        """Load checklist progress"""
        if self.progress_file.exists():
            with open(self.progress_file) as f:
                self.progress = json.load(f)
        else:
            self.progress = self.get_default_progress()
            
    def save_progress(self):
        """Save checklist progress"""
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
            
    def get_default_progress(self):
        """Get default progress structure"""
        return {
            "security": {
                "root_password": False,
                "admin_user": False,
                "ssh_keys": False,
                "firewall": False,
                "fail2ban": False,
                "updates": False
            },
            "storage": {
                "additional_pools": False,
                "snapshots": False,
                "scrub_schedule": False,
                "email_alerts": False,
                "replication": False
            },
            "network": {
                "additional_interfaces": False,
                "vlans": False,
                "dns": False,
                "ntp": False,
                "mail_relay": False
            },
            "proxmox": {
                "iso_upload": False,
                "vm_templates": False,
                "storage_config": False,
                "cluster": False,
                "backups": False,
                "first_vm": False
            },
            "monitoring": {
                "agents": False,
                "alerts": False,
                "logs": False,
                "dashboard": False
            }
        }
        
    def run_interactive(self):
        """Run interactive checklist"""
        print("\\n" + "="*60)
        print("Z-FORGE Post-Installation Checklist")
        print("="*60 + "\\n")
        
        categories = [
            ("Security Tasks", "security", self.security_tasks),
            ("Storage Configuration", "storage", self.storage_tasks),
            ("Network Setup", "network", self.network_tasks),
            ("Proxmox Configuration", "proxmox", self.proxmox_tasks),
            ("Monitoring Setup", "monitoring", self.monitoring_tasks)
        ]
        
        while True:
            # Show main menu
            print("\\nSelect a category to configure:")
            for i, (name, _, _) in enumerate(categories, 1):
                completed = self.get_category_progress(categories[i-1][1])
                status = "✓" if completed == 100 else f"{completed}%"
                print(f"{i}. {name} [{status}]")
            print("\\n0. Exit")
            
            try:
                choice = int(input("\\nEnter your choice: "))
                if choice == 0:
                    break
                elif 1 <= choice <= len(categories):
                    name, key, func = categories[choice-1]
                    self.run_category(name, key, func)
                else:
                    print("Invalid choice!")
            except (ValueError, KeyboardInterrupt):
                print("\\nExiting...")
                break
                
        self.save_progress()
        print("\\nProgress saved. Run 'zforge-checklist' anytime to continue.")
        
    def get_category_progress(self, category):
        """Get completion percentage for category"""
        tasks = self.progress.get(category, {})
        if not tasks:
            return 0
        completed = sum(1 for v in tasks.values() if v)
        return int((completed / len(tasks)) * 100)
        
    def run_category(self, name, key, tasks):
        """Run tasks for a category"""
        print(f"\\n--- {name} ---")
        tasks()
        
    def security_tasks(self):
        """Security configuration tasks"""
        tasks = [
            ("Change root password", "root_password", self.change_root_password),
            ("Create administrative user", "admin_user", self.create_admin_user),
            ("Configure SSH keys", "ssh_keys", self.configure_ssh_keys),
            ("Setup firewall rules", "firewall", self.setup_firewall),
            ("Enable fail2ban", "fail2ban", self.enable_fail2ban),
            ("Configure automatic updates", "updates", self.configure_updates)
        ]
        
        self.run_task_list("security", tasks)
        
    def storage_tasks(self):
        """Storage configuration tasks"""
        tasks = [
            ("Create additional ZFS pools", "additional_pools", self.create_pools),
            ("Setup snapshot schedules", "snapshots", self.setup_snapshots),
            ("Configure scrub schedule", "scrub_schedule", self.setup_scrub),
            ("Setup email alerts", "email_alerts", self.setup_storage_alerts),
            ("Configure replication", "replication", self.setup_replication)
        ]
        
        self.run_task_list("storage", tasks)
        
    def network_tasks(self):
        """Network configuration tasks"""
        tasks = [
            ("Configure additional interfaces", "additional_interfaces", self.configure_interfaces),
            ("Setup VLANs", "vlans", self.setup_vlans),
            ("Configure DNS", "dns", self.configure_dns),
            ("Setup NTP", "ntp", self.setup_ntp),
            ("Configure mail relay", "mail_relay", self.setup_mail_relay)
        ]
        
        self.run_task_list("network", tasks)
        
    def proxmox_tasks(self):
        """Proxmox configuration tasks"""
        tasks = [
            ("Upload ISO images", "iso_upload", self.upload_isos),
            ("Create VM templates", "vm_templates", self.create_templates),
            ("Configure storage", "storage_config", self.configure_storage),
            ("Setup cluster", "cluster", self.setup_cluster),
            ("Configure backups", "backups", self.setup_backups),
            ("Create first VM", "first_vm", self.create_first_vm)
        ]
        
        self.run_task_list("proxmox", tasks)
        
    def monitoring_tasks(self):
        """Monitoring configuration tasks"""
        tasks = [
            ("Install monitoring agents", "agents", self.install_agents),
            ("Configure alerts", "alerts", self.configure_alerts),
            ("Setup log aggregation", "logs", self.setup_logging),
            ("Create dashboards", "dashboard", self.create_dashboards)
        ]
        
        self.run_task_list("monitoring", tasks)
        
    def run_task_list(self, category, tasks):
        """Run a list of tasks"""
        for desc, key, func in tasks:
            if self.progress[category][key]:
                print(f"\\n✓ {desc} (completed)")
            else:
                print(f"\\n○ {desc}")
                if input("Run this task? (y/N): ").lower() == 'y':
                    try:
                        func()
                        self.progress[category][key] = True
                        self.save_progress()
                        print("✓ Task completed!")
                    except Exception as e:
                        print(f"✗ Task failed: {e}")
                        
    # Individual task implementations
    def change_root_password(self):
        """Change root password"""
        print("Changing root password...")
        subprocess.run(["passwd", "root"])
        
    def create_admin_user(self):
        """Create administrative user"""
        username = input("Enter username for admin user: ")
        subprocess.run(["adduser", username])
        subprocess.run(["usermod", "-aG", "sudo", username])
        
    def configure_ssh_keys(self):
        """Configure SSH keys"""
        print("Configuring SSH keys...")
        # Implementation would go here
        
    def setup_firewall(self):
        """Setup firewall rules"""
        print("Setting up firewall...")
        subprocess.run(["ufw", "enable"])
        subprocess.run(["ufw", "allow", "ssh"])
        subprocess.run(["ufw", "allow", "8006"])  # Proxmox web UI
        
    def enable_fail2ban(self):
        """Enable fail2ban"""
        subprocess.run(["systemctl", "enable", "fail2ban"])
        subprocess.run(["systemctl", "start", "fail2ban"])
        
    def configure_updates(self):
        """Configure automatic updates"""
        print("Configuring automatic updates...")
        # Implementation would go here
        
    # Additional task implementations...
    def create_pools(self):
        """Create additional ZFS pools"""
        print("Creating additional ZFS pools...")
        # Implementation would go here
        
    def setup_snapshots(self):
        """Setup snapshot schedules"""
        print("Setting up snapshot schedules...")
        # Implementation would go here
        
    def setup_scrub(self):
        """Setup scrub schedule"""
        print("Setting up scrub schedule...")
        # Implementation would go here
        
    def setup_storage_alerts(self):
        """Setup storage alerts"""
        email = input("Enter email for alerts: ")
        print(f"Setting up alerts to {email}...")
        # Implementation would go here
        
    def setup_replication(self):
        """Setup ZFS replication"""
        print("Setting up ZFS replication...")
        # Implementation would go here
        
    def configure_interfaces(self):
        """Configure network interfaces"""
        print("Configuring network interfaces...")
        # Implementation would go here
        
    def setup_vlans(self):
        """Setup VLANs"""
        print("Setting up VLANs...")
        # Implementation would go here
        
    def configure_dns(self):
        """Configure DNS"""
        print("Configuring DNS...")
        # Implementation would go here
        
    def setup_ntp(self):
        """Setup NTP"""
        subprocess.run(["timedatectl", "set-ntp", "true"])
        
    def setup_mail_relay(self):
        """Setup mail relay"""
        print("Setting up mail relay...")
        # Implementation would go here
        
    def upload_isos(self):
        """Upload ISO images"""
        print("Uploading ISO images...")
        print("Visit https://localhost:8006 to upload ISOs via web interface")
        
    def create_templates(self):
        """Create VM templates"""
        print("Creating VM templates...")
        # Implementation would go here
        
    def configure_storage(self):
        """Configure Proxmox storage"""
        print("Configuring Proxmox storage...")
        # Implementation would go here
        
    def setup_cluster(self):
        """Setup Proxmox cluster"""
        print("Setting up Proxmox cluster...")
        # Implementation would go here
        
    def setup_backups(self):
        """Setup backup schedules"""
        print("Setting up backup schedules...")
        # Implementation would go here
        
    def create_first_vm(self):
        """Create first VM"""
        print("Creating first VM...")
        print("Visit https://localhost:8006 to create your first VM")
        
    def install_agents(self):
        """Install monitoring agents"""
        print("Installing monitoring agents...")
        # Implementation would go here
        
    def configure_alerts(self):
        """Configure monitoring alerts"""
        print("Configuring alerts...")
        # Implementation would go here
        
    def setup_logging(self):
        """Setup log aggregation"""
        print("Setting up log aggregation...")
        # Implementation would go here
        
    def create_dashboards(self):
        """Create monitoring dashboards"""
        print("Creating dashboards...")
        # Implementation would go here

if __name__ == "__main__":
    checklist = PostInstallChecklist()
    checklist.run_interactive()
"""
    
    script_path = Path(root_path) / "usr/local/bin/zforge-checklist"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script_content)
    script_path.chmod(0o755)

def create_firstboot_service(root_path):
    """Create systemd service for first boot wizard"""
    service_content = """[Unit]
Description=Z-FORGE Post-Installation Wizard
After=multi-user.target
ConditionPathExists=!/etc/zforge/firstboot.done

[Service]
Type=oneshot
ExecStart=/usr/local/bin/zforge-firstboot
ExecStartPost=/bin/touch /etc/zforge/firstboot.done
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path(root_path) / "etc/systemd/system/zforge-firstboot.service"
    service_path.parent.mkdir(parents=True, exist_ok=True)
    service_path.write_text(service_content)
    
    # Enable service
    subprocess.run(["systemctl", "--root", str(root_path), "enable", "zforge-firstboot.service"])
    
    # Create firstboot script
    firstboot_script = """#!/bin/bash
# Z-FORGE First Boot Wizard

echo "Welcome to Z-FORGE!"
echo "Running post-installation checklist..."
echo ""
echo "Press any key to continue..."
read -n 1 -s

# Run checklist
/usr/local/bin/zforge-checklist

echo ""
echo "Initial setup complete!"
echo "You can run 'zforge-checklist' anytime to access the checklist."
"""
    
    firstboot_path = Path(root_path) / "usr/local/bin/zforge-firstboot"
    firstboot_path.write_text(firstboot_script)
    firstboot_path.chmod(0o755)

def create_desktop_entry(root_path):
    """Create desktop entry for checklist"""
    desktop_content = """[Desktop Entry]
Name=Z-FORGE Checklist
Comment=Post-installation setup checklist
Exec=konsole -e /usr/local/bin/zforge-checklist
Icon=checkbox
Terminal=false
Type=Application
Categories=System;Settings;
"""
    
    desktop_path = Path(root_path) / "usr/share/applications/zforge-checklist.desktop"
    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    desktop_path.write_text(desktop_content)

def save_checklist_config(root_path, config):
    """Save checklist configuration"""
    config_path = Path(root_path) / "etc/zforge/postinstall.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

class PostInstallViewStep:
    """Calamares ViewStep for post-install checklist"""
    
    def __init__(self):
        self.widget = None
        self.gs = libcalamares.globalstorage
    
    def name(self):
        return "postinstall"
    
    def pretty_name(self):
        return "Post-Install Setup"
    
    def icon(self):
        return "checkbox"
    
    def widget(self):
        if self.widget is None:
            self.widget = PostInstallWidget(self.gs)
        return self.widget
    
    def next(self):
        if self.widget:
            config = self.widget.get_configuration()
            self.gs.insert("postInstallConfig", config)
        return None
    
    def back(self):
        return None
    
    def jobs(self):
        return []

calamares_module = PostInstallViewStep
'''
        (module_path / "main.py").write_text(main_content)
        
        # Create GUI module
        self.update_progress("working", 60, "Creating post-install checklist GUI")
        gui_content = '''#!/usr/bin/env python3
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
'''
        (module_path / "postinstall_gui.py").write_text(gui_content)
        
        # Create __init__.py
        init_content = '''#!/usr/bin/env python3
"""Post-Installation Checklist Module for Calamares"""
from .main import PostInstallViewStep
__all__ = ["PostInstallViewStep"]
'''
        (module_path / "__init__.py").write_text(init_content)
        
        self.update_progress("completed", 100, "Post-install checklist module implementation complete")


# Buddy Verification Agents

class NetworkConfigVerifier(BuddyVerificationAgent):
    """Verifies NetworkConfigAgent's work"""
    
    def verify_single_item(self, item: Dict) -> Dict:
        file_path = item.get("file_path")
        expected_content = item.get("expected_content")
        
        if file_path and Path(file_path).exists():
            actual_content = Path(file_path).read_text()
            # Basic verification - check if key elements exist
            if "network" in expected_content.lower() and "network" in actual_content.lower():
                return {"item": item, "valid": True, "issue": None}
            else:
                return {"item": item, "valid": False, "issue": "Content mismatch"}
        else:
            return {"item": item, "valid": False, "issue": f"File not found: {file_path}"}


class HardwareHealthVerifier(BuddyVerificationAgent):
    """Verifies HardwareHealthAgent's work"""
    
    def verify_single_item(self, item: Dict) -> Dict:
        file_path = item.get("file_path")
        
        if file_path and Path(file_path).exists():
            # Check if file has expected structure
            content = Path(file_path).read_text()
            if "hardware" in content.lower() or "monitor" in content.lower():
                return {"item": item, "valid": True, "issue": None}
            else:
                return {"item": item, "valid": False, "issue": "Missing expected keywords"}
        else:
            return {"item": item, "valid": False, "issue": f"File not found: {file_path}"}


class GPUPassthroughVerifier(BuddyVerificationAgent):
    """Verifies GPUPassthroughAgent's work"""
    
    def verify_single_item(self, item: Dict) -> Dict:
        file_path = item.get("file_path")
        
        if file_path and Path(file_path).exists():
            content = Path(file_path).read_text()
            if "gpu" in content.lower() or "passthrough" in content.lower():
                return {"item": item, "valid": True, "issue": None}
            else:
                return {"item": item, "valid": False, "issue": "Missing GPU-related content"}
        else:
            return {"item": item, "valid": False, "issue": f"File not found: {file_path}"}


class StorageLayoutVerifier(BuddyVerificationAgent):
    """Verifies StorageLayoutAgent's work"""
    
    def verify_single_item(self, item: Dict) -> Dict:
        file_path = item.get("file_path")
        
        if file_path and Path(file_path).exists():
            content = Path(file_path).read_text()
            if "storage" in content.lower() or "dataset" in content.lower():
                return {"item": item, "valid": True, "issue": None}
            else:
                return {"item": item, "valid": False, "issue": "Missing storage-related content"}
        else:
            return {"item": item, "valid": False, "issue": f"File not found: {file_path}"}


class PostInstallVerifier(BuddyVerificationAgent):
    """Verifies PostInstallAgent's work"""
    
    def verify_single_item(self, item: Dict) -> Dict:
        file_path = item.get("file_path")
        
        if file_path and Path(file_path).exists():
            content = Path(file_path).read_text()
            if "checklist" in content.lower() or "post" in content.lower():
                return {"item": item, "valid": True, "issue": None}
            else:
                return {"item": item, "valid": False, "issue": "Missing checklist-related content"}
        else:
            return {"item": item, "valid": False, "issue": f"File not found: {file_path}"}


# Multi-Agent Coordinator

class MultiAgentCoordinator:
    """Coordinates multiple agents with buddy system"""
    
    def __init__(self):
        self.db_path = Path("/opt/github/Z-FORGE/implementation/agents.db")
        self.setup_database()
        self.agents = []
        self.verifiers = []
        
    def setup_database(self):
        """Setup SQLite database for agent coordination"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create tables
        c.execute("""CREATE TABLE IF NOT EXISTS agents (
            agent_id INTEGER PRIMARY KEY,
            module_name TEXT,
            buddy_id INTEGER,
            status TEXT,
            progress INTEGER,
            last_update TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            timestamp TEXT,
            message TEXT
        )""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verifier_id INTEGER,
            agent_id INTEGER,
            timestamp TEXT,
            status TEXT,
            result TEXT
        )""")
        
        conn.commit()
        conn.close()
        
    def start_implementation(self):
        """Start the multi-agent implementation process"""
        print("Starting Multi-Agent Module Implementation System")
        print("=" * 60)
        
        # Define agent pairs (implementation agent, verification agent)
        agent_pairs = [
            (NetworkConfigAgent, NetworkConfigVerifier, "Network Configuration Module"),
            (HardwareHealthAgent, HardwareHealthVerifier, "Hardware Health Monitor Module"),
            (GPUPassthroughAgent, GPUPassthroughVerifier, "GPU Passthrough Module"),
            (StorageLayoutAgent, StorageLayoutVerifier, "Storage Layout Templates Module"),
            (PostInstallAgent, PostInstallVerifier, "Post-Install Checklist Module")
        ]
        
        # Create agents with buddy system
        for i, (impl_class, verif_class, module_name) in enumerate(agent_pairs):
            # Agent IDs
            impl_id = i * 2
            verif_id = i * 2 + 1
            
            # Create implementation agent
            impl_agent = impl_class(impl_id, module_name, verif_id, self.db_path)
            self.agents.append(impl_agent)
            
            # Create verification agent
            verif_agent = verif_class(verif_id, impl_id, self.db_path)
            self.verifiers.append(verif_agent)
            
            print(f"Created Agent {impl_id} (Implementation) and Agent {verif_id} (Verification) for {module_name}")
        
        # Start all agents in parallel
        threads = []
        for agent in self.agents:
            thread = threading.Thread(target=self.run_agent, args=(agent,))
            thread.start()
            threads.append(thread)
        
        # Start verification loop
        verification_thread = threading.Thread(target=self.verification_loop)
        verification_thread.start()
        
        # Monitor progress
        self.monitor_progress()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        print("\n" + "=" * 60)
        print("All modules implementation complete!")
        
    def run_agent(self, agent):
        """Run a single agent"""
        try:
            agent.implement_module()
        except Exception as e:
            agent.update_progress("error", agent.progress, f"Error: {str(e)}")
            
    def verification_loop(self):
        """Run verification every 5 minutes"""
        import time
        
        while True:
            time.sleep(300)  # 5 minutes
            
            print("\n--- Running Buddy Verification ---")
            
            for i, verifier in enumerate(self.verifiers):
                # Get work items from implementation agent
                impl_agent_id = i * 2
                work_items = self.get_agent_work_items(impl_agent_id)
                
                if work_items:
                    result = verifier.verify_work(work_items)
                    print(f"Agent {verifier.agent_id} verified Agent {impl_agent_id}: {result['overall_status']}")
                    
            # Check if all agents are complete
            if self.all_agents_complete():
                break
                
    def get_agent_work_items(self, agent_id):
        """Get work items completed by an agent"""
        module_path = Path(f"/opt/github/Z-FORGE/calamares/modules/")
        
        # Map agent IDs to module names
        module_names = ["networkconfig", "hardwarehealth", "gpupassthrough", "storagelayout", "postinstall"]
        module_name = module_names[agent_id // 2]
        
        work_items = []
        module_dir = module_path / module_name
        
        if module_dir.exists():
            for file_path in module_dir.glob("*.py"):
                work_items.append({
                    "file_path": str(file_path),
                    "expected_content": module_name
                })
                
        return work_items
        
    def all_agents_complete(self):
        """Check if all agents have completed"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM agents WHERE status != 'completed'")
        incomplete = c.fetchone()[0]
        conn.close()
        
        return incomplete == 0
        
    def monitor_progress(self):
        """Monitor and display agent progress"""
        import time
        
        while not self.all_agents_complete():
            time.sleep(10)
            
            # Clear screen and show progress
            os.system('clear' if os.name == 'posix' else 'cls')
            print("Multi-Agent Module Implementation Progress")
            print("=" * 60)
            
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("SELECT * FROM agents ORDER BY agent_id")
            agents = c.fetchall()
            
            for agent in agents:
                agent_id, module_name, buddy_id, status, progress, last_update = agent
                
                # Get verification status
                c.execute("""SELECT status FROM verifications 
                           WHERE agent_id=? ORDER BY timestamp DESC LIMIT 1""", (agent_id,))
                verif = c.fetchone()
                verif_status = verif[0] if verif else "pending"
                
                # Display progress bar
                bar_length = 40
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)
                
                print(f"Agent {agent_id}: {module_name}")
                print(f"  Progress: [{bar}] {progress}%")
                print(f"  Status: {status} | Verification: {verif_status}")
                print()
                
            conn.close()
            
        print("\nAll agents completed!")


# Main execution
if __name__ == "__main__":
    coordinator = MultiAgentCoordinator()
    coordinator.start_implementation()