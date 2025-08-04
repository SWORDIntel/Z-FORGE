import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

#!/usr/bin/env python3
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
from postinstall_gui import PostinstallGui as PostInstallWidget

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
    script_content = '''#!/usr/bin/env python3
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
        print("\n" + "="*60)
        print("Z-FORGE Post-Installation Checklist")
        print("="*60 + "\n")
        
        categories = [
            ("Security Tasks", "security", self.security_tasks),
            ("Storage Configuration", "storage", self.storage_tasks),
            ("Network Setup", "network", self.network_tasks),
            ("Proxmox Configuration", "proxmox", self.proxmox_tasks),
            ("Monitoring Setup", "monitoring", self.monitoring_tasks)
        ]
        
        while True:
            # Show main menu
            print("\nSelect a category to configure:")
            for i, (name, _, _) in enumerate(categories, 1):
                completed = self.get_category_progress(categories[i-1][1])
                status = "✓" if completed == 100 else f"{completed}%"
                print(f"{i}. {name} [{status}]")
            print("\n0. Exit")
            
            try:
                choice = int(input("\nEnter your choice: "))
                if choice == 0:
                    break
                elif 1 <= choice <= len(categories):
                    name, key, func = categories[choice-1]
                    self.run_category(name, key, func)
                else:
                    print("Invalid choice!")
            except (ValueError, KeyboardInterrupt):
                print("\nExiting...")
                break
                
        self.save_progress()
        print("\nProgress saved. Run 'zforge-checklist' anytime to continue.")
        
    def get_category_progress(self, category):
        """Get completion percentage for category"""
        tasks = self.progress.get(category, {})
        if not tasks:
            return 0
        completed = sum(1 for v in tasks.values() if v)
        return int((completed / len(tasks)) * 100)
        
    def run_category(self, name, key, tasks):
        """Run tasks for a category"""
        print(f"\n--- {name} ---")
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
                print(f"\n✓ {desc} (completed)")
            else:
                print(f"\n○ {desc}")
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
'''
    
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

class PostinstallJob:
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

calamares_module = PostinstallJob
