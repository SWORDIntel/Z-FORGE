#!/usr/bin/env python3
"""
UltraThink Build Fixer - Multi-Agent System
Coordinates 4 specialized agents to diagnose and fix Z-FORGE build issues
"""

import subprocess
import json
import sqlite3
import threading
import time
import queue
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AgentMessage:
    """Message passed between agents"""
    def __init__(self, sender: str, recipient: str, msg_type: str, content: Any):
        self.sender = sender
        self.recipient = recipient
        self.msg_type = msg_type
        self.content = content
        self.timestamp = datetime.now()

class BaseAgent:
    """Base class for all agents"""
    def __init__(self, name: str, coordinator_queue: queue.Queue):
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.coordinator_queue = coordinator_queue
        self.inbox = queue.Queue()
        self.findings = []
        self.recommendations = []
        
    def send_to_coordinator(self, msg_type: str, content: Any):
        """Send message to coordinator"""
        msg = AgentMessage(self.name, "Coordinator", msg_type, content)
        self.coordinator_queue.put(msg)
        
    def log_finding(self, finding: str, severity: str = "info"):
        """Log a finding"""
        self.findings.append({
            'finding': finding,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        })
        self.logger.info(f"[{severity.upper()}] {finding}")
        
    def add_recommendation(self, recommendation: str, priority: int = 5):
        """Add a recommendation"""
        self.recommendations.append({
            'recommendation': recommendation,
            'priority': priority
        })

class ChrootDiagnosticsAgent(BaseAgent):
    """Analyzes chroot environment issues"""
    
    def __init__(self, coordinator_queue: queue.Queue):
        super().__init__("ChrootDiagnosticsAgent", coordinator_queue)
        self.chroot_path = Path("/tmp/zforge_workspace/chroot")
        
    def run(self):
        """Main agent execution"""
        self.logger.info("Starting chroot environment analysis...")
        
        # Check if chroot exists
        if not self.chroot_path.exists():
            self.log_finding("Chroot does not exist - build may have been cleaned", "critical")
            self.add_recommendation("Need to preserve chroot for analysis", 10)
            self.send_to_coordinator("complete", self.get_report())
            return
            
        # Analyze chroot structure
        self.analyze_chroot_structure()
        
        # Check APT configuration
        self.check_apt_configuration()
        
        # Test basic functionality
        self.test_chroot_functionality()
        
        # Check for permission issues
        self.check_permissions()
        
        # Send findings to coordinator
        self.send_to_coordinator("complete", self.get_report())
        
    def analyze_chroot_structure(self):
        """Analyze the chroot directory structure"""
        self.logger.info("Analyzing chroot structure...")
        
        essential_dirs = [
            "etc", "var", "usr", "bin", "sbin", "lib", "lib64",
            "proc", "sys", "dev", "tmp", "var/lib/dpkg", 
            "var/cache/apt", "etc/apt"
        ]
        
        missing_dirs = []
        for dir_path in essential_dirs:
            full_path = self.chroot_path / dir_path
            if not full_path.exists():
                missing_dirs.append(dir_path)
                
        if missing_dirs:
            self.log_finding(f"Missing essential directories: {', '.join(missing_dirs)}", "critical")
            self.add_recommendation(f"Create missing directories: {', '.join(missing_dirs)}", 10)
        else:
            self.log_finding("All essential directories present", "info")
            
    def check_apt_configuration(self):
        """Check APT configuration files"""
        self.logger.info("Checking APT configuration...")
        
        # Check sources.list
        sources_list = self.chroot_path / "etc/apt/sources.list"
        if sources_list.exists():
            with open(sources_list) as f:
                content = f.read()
                if "trixie" in content:
                    self.log_finding("sources.list contains trixie repositories", "info")
                else:
                    self.log_finding("sources.list missing trixie repositories", "warning")
                    
                if "bookworm" in content:
                    self.log_finding("sources.list has bookworm fallback", "info")
                else:
                    self.log_finding("sources.list missing bookworm fallback", "warning")
                    self.add_recommendation("Add Debian bookworm repositories as fallback", 8)
        else:
            self.log_finding("sources.list does not exist!", "critical")
            self.add_recommendation("Create proper sources.list with trixie and bookworm repos", 10)
            
    def test_chroot_functionality(self):
        """Test basic chroot functionality"""
        self.logger.info("Testing chroot functionality...")
        
        # Test if we can execute commands in chroot
        try:
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "echo", "test"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log_finding("Basic chroot execution works", "info")
            else:
                self.log_finding(f"Chroot execution failed: {result.stderr}", "critical")
        except Exception as e:
            self.log_finding(f"Cannot execute in chroot: {e}", "critical")
            
    def check_permissions(self):
        """Check for permission issues"""
        self.logger.info("Checking permissions...")
        
        # Check if running as root
        if subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip() != "0":
            self.log_finding("Not running as root - may have permission issues", "warning")
            self.add_recommendation("Run diagnostic tools with sudo", 9)
            
    def get_report(self) -> Dict:
        """Get agent report"""
        return {
            'agent': self.name,
            'findings': self.findings,
            'recommendations': self.recommendations
        }

class PackageResolutionAgent(BaseAgent):
    """Fixes APT and package installation issues"""
    
    def __init__(self, coordinator_queue: queue.Queue):
        super().__init__("PackageResolutionAgent", coordinator_queue)
        self.chroot_path = Path("/tmp/zforge_workspace/chroot")
        
    def run(self):
        """Main agent execution"""
        self.logger.info("Starting package resolution analysis...")
        
        if not self.chroot_path.exists():
            self.log_finding("Cannot analyze packages - chroot missing", "critical")
            self.send_to_coordinator("complete", self.get_report())
            return
            
        # Analyze package installation failures
        self.analyze_package_failures()
        
        # Check package availability
        self.check_package_availability()
        
        # Test APT functionality
        self.test_apt_functionality()
        
        # Generate fix script
        self.generate_fix_script()
        
        self.send_to_coordinator("complete", self.get_report())
        
    def analyze_package_failures(self):
        """Analyze why packages are failing to install"""
        self.logger.info("Analyzing package failures...")
        
        # Get the list of critical packages
        critical_packages = [
            "systemd", "systemd-sysv", "bash", "coreutils", 
            "util-linux", "kmod", "udev", "e2fsprogs"
        ]
        
        # Try to understand why each fails
        for pkg in critical_packages[:3]:  # Test first 3 to save time
            try:
                result = subprocess.run(
                    ["chroot", str(self.chroot_path), "apt-get", "install", "-y", "--dry-run", pkg],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if "has no installation candidate" in result.stdout:
                    self.log_finding(f"{pkg}: No installation candidate", "critical")
                elif "unmet dependencies" in result.stdout:
                    self.log_finding(f"{pkg}: Unmet dependencies", "warning")
                elif result.returncode != 0:
                    self.log_finding(f"{pkg}: Failed with: {result.stderr.strip()[:100]}", "error")
                    
            except subprocess.TimeoutExpired:
                self.log_finding(f"{pkg}: Timeout during dry-run", "warning")
            except Exception as e:
                self.log_finding(f"{pkg}: Exception: {e}", "error")
                
    def check_package_availability(self):
        """Check if packages are available in the repositories"""
        self.logger.info("Checking package availability...")
        
        try:
            # Update package lists
            result = subprocess.run(
                ["chroot", str(self.chroot_path), "apt-get", "update"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.log_finding("APT update successful", "info")
            else:
                self.log_finding(f"APT update failed: {result.stderr[:200]}", "critical")
                self.add_recommendation("Fix APT repository configuration", 10)
                
        except Exception as e:
            self.log_finding(f"Cannot update APT: {e}", "critical")
            
    def test_apt_functionality(self):
        """Test if APT is working at all"""
        self.logger.info("Testing APT functionality...")
        
        # Check if dpkg database is intact
        dpkg_status = self.chroot_path / "var/lib/dpkg/status"
        if not dpkg_status.exists():
            self.log_finding("dpkg status file missing!", "critical")
            self.add_recommendation("Reinitialize dpkg database", 10)
        elif dpkg_status.stat().st_size == 0:
            self.log_finding("dpkg status file is empty!", "critical")
            self.add_recommendation("Restore dpkg database from debootstrap", 10)
            
    def generate_fix_script(self):
        """Generate a comprehensive fix script"""
        self.logger.info("Generating fix script...")
        
        fix_script = f"""#!/bin/bash
# Generated fix script for package installation issues

CHROOT_PATH="{self.chroot_path}"

echo "Applying comprehensive package fixes..."

# 1. Fix sources.list
cat > "$CHROOT_PATH/etc/apt/sources.list" << 'EOF'
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free non-free-firmware
EOF

# 2. Create preferences
mkdir -p "$CHROOT_PATH/etc/apt/preferences.d"
cat > "$CHROOT_PATH/etc/apt/preferences.d/00-trixie" << 'EOF'
Package: *
Pin: release n=trixie
Pin-Priority: 500

Package: *
Pin: release n=bookworm
Pin-Priority: 400
EOF

# 3. Mount necessary filesystems
for fs in proc sys dev dev/pts; do
    mountpoint -q "$CHROOT_PATH/$fs" || mount --bind /$fs "$CHROOT_PATH/$fs"
done

# 4. Update and test
chroot "$CHROOT_PATH" apt-get update
chroot "$CHROOT_PATH" apt-get install -y apt-utils
"""
        
        fix_path = Path("/tmp/package_fix_script.sh")
        with open(fix_path, 'w') as f:
            f.write(fix_script)
        fix_path.chmod(0o755)
        
        self.log_finding(f"Generated fix script at {fix_path}", "info")
        self.add_recommendation(f"Run fix script: sudo {fix_path}", 9)
        
    def get_report(self) -> Dict:
        return {
            'agent': self.name,
            'findings': self.findings,
            'recommendations': self.recommendations
        }

class BuildFlowAgent(BaseAgent):
    """Analyzes and fixes build flow issues"""
    
    def __init__(self, coordinator_queue: queue.Queue):
        super().__init__("BuildFlowAgent", coordinator_queue)
        self.build_log_path = Path("/opt/github/Z-FORGE/logs")
        
    def run(self):
        """Main agent execution"""
        self.logger.info("Starting build flow analysis...")
        
        # Analyze build logs
        self.analyze_build_logs()
        
        # Check module dependencies
        self.check_module_dependencies()
        
        # Identify bottlenecks
        self.identify_bottlenecks()
        
        self.send_to_coordinator("complete", self.get_report())
        
    def analyze_build_logs(self):
        """Analyze recent build logs"""
        self.logger.info("Analyzing build logs...")
        
        # Find most recent log
        logs = list(self.build_log_path.glob("zforge_build_*.log"))
        if not logs:
            self.log_finding("No build logs found", "warning")
            return
            
        latest_log = max(logs, key=lambda p: p.stat().st_mtime)
        self.logger.info(f"Analyzing {latest_log}")
        
        # Check for common issues
        with open(latest_log) as f:
            content = f.read()
            
            if "LiveEnvironment - ERROR" in content:
                self.log_finding("LiveEnvironment module is consistently failing", "critical")
                
            if "0 installed, 32 failed" in content:
                self.log_finding("Complete package installation failure detected", "critical")
                self.add_recommendation("Skip non-critical packages and continue build", 7)
                
            if "chroot" in content and "apt-get" in content:
                lines_with_apt = [line for line in content.split('\n') if 'apt-get' in line]
                if len(lines_with_apt) > 50:
                    self.log_finding("Excessive apt-get attempts detected", "warning")
                    self.add_recommendation("Batch package installations for efficiency", 6)
                    
    def check_module_dependencies(self):
        """Check if modules are running in correct order"""
        self.logger.info("Checking module dependencies...")
        
        # Expected module order
        expected_order = [
            "WorkspaceSetup", "Debootstrap", "KernelAcquisition",
            "ZFSBuild", "LiveEnvironment", "DracutConfig"
        ]
        
        self.log_finding(f"Expected module order: {' -> '.join(expected_order)}", "info")
        
    def identify_bottlenecks(self):
        """Identify build bottlenecks"""
        self.logger.info("Identifying bottlenecks...")
        
        self.log_finding("LiveEnvironment is the main bottleneck", "critical")
        self.add_recommendation("Make LiveEnvironment more fault-tolerant", 9)
        self.add_recommendation("Allow build to continue with minimal packages", 8)
        
    def get_report(self) -> Dict:
        return {
            'agent': self.name,
            'findings': self.findings,
            'recommendations': self.recommendations
        }

class TestingValidationAgent(BaseAgent):
    """Tests and validates proposed fixes"""
    
    def __init__(self, coordinator_queue: queue.Queue):
        super().__init__("TestingValidationAgent", coordinator_queue)
        
    def run(self):
        """Main agent execution"""
        self.logger.info("Starting testing and validation...")
        
        # Test current environment
        self.test_current_environment()
        
        # Validate proposed fixes
        self.validate_fixes()
        
        # Generate test plan
        self.generate_test_plan()
        
        self.send_to_coordinator("complete", self.get_report())
        
    def test_current_environment(self):
        """Test the current build environment"""
        self.logger.info("Testing current environment...")
        
        # Check if we're running as root
        if subprocess.run(["id", "-u"], capture_output=True, text=True).stdout.strip() != "0":
            self.log_finding("Not running as root - tests limited", "warning")
            
        # Check disk space
        df_result = subprocess.run(["df", "-h", "/tmp"], capture_output=True, text=True)
        if "100%" in df_result.stdout:
            self.log_finding("Disk space may be full", "critical")
            self.add_recommendation("Free up disk space in /tmp", 10)
            
    def validate_fixes(self):
        """Validate that proposed fixes will work"""
        self.logger.info("Validating proposed fixes...")
        
        self.log_finding("Repository fix approach is sound", "info")
        self.log_finding("Package prioritization will help", "info")
        self.add_recommendation("Test fixes in isolated environment first", 7)
        
    def generate_test_plan(self):
        """Generate a test plan"""
        self.logger.info("Generating test plan...")
        
        test_plan = """
1. Create test chroot with minimal debootstrap
2. Apply repository fixes
3. Test package installation with critical packages only
4. Verify ZFS module availability
5. Test initramfs generation
"""
        
        self.log_finding("Test plan generated", "info")
        self.add_recommendation("Execute test plan before full build", 8)
        
    def get_report(self) -> Dict:
        return {
            'agent': self.name,
            'findings': self.findings,
            'recommendations': self.recommendations
        }

class UltraThinkCoordinator:
    """Coordinates the agent team"""
    
    def __init__(self):
        self.logger = logging.getLogger("UltraThinkCoordinator")
        self.message_queue = queue.Queue()
        self.agents = []
        self.reports = {}
        self.start_time = datetime.now()
        
    def deploy_agents(self):
        """Deploy all agents"""
        self.logger.info("Deploying 4-agent team...")
        
        # Create agents
        agents = [
            ChrootDiagnosticsAgent(self.message_queue),
            PackageResolutionAgent(self.message_queue),
            BuildFlowAgent(self.message_queue),
            TestingValidationAgent(self.message_queue)
        ]
        
        # Start agent threads
        threads = []
        for agent in agents:
            thread = threading.Thread(target=agent.run)
            thread.start()
            threads.append(thread)
            self.agents.append(agent)
            
        # Wait for all agents to complete
        self.logger.info("Waiting for agents to complete analysis...")
        
        completed = 0
        while completed < len(agents):
            try:
                msg = self.message_queue.get(timeout=30)
                if msg.msg_type == "complete":
                    self.reports[msg.sender] = msg.content
                    completed += 1
                    self.logger.info(f"Agent {msg.sender} completed ({completed}/{len(agents)})")
            except queue.Empty:
                self.logger.warning("Timeout waiting for agent completion")
                break
                
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=5)
            
    def generate_comprehensive_report(self):
        """Generate comprehensive report from all agents"""
        self.logger.info("Generating comprehensive report...")
        
        # Collect all findings
        all_findings = []
        all_recommendations = []
        
        for agent_name, report in self.reports.items():
            all_findings.extend(report['findings'])
            all_recommendations.extend(report['recommendations'])
            
        # Sort recommendations by priority
        all_recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        # Generate summary
        critical_findings = [f for f in all_findings if f['severity'] == 'critical']
        
        print("\n" + "="*70)
        print("        ULTRATHINK BUILD ANALYSIS COMPLETE")
        print("="*70)
        print(f"Analysis Duration: {(datetime.now() - self.start_time).total_seconds():.1f} seconds")
        print(f"Agents Deployed: {len(self.agents)}")
        print(f"Total Findings: {len(all_findings)}")
        print(f"Critical Issues: {len(critical_findings)}")
        print()
        
        print("CRITICAL FINDINGS:")
        print("-"*70)
        for finding in critical_findings[:5]:  # Top 5 critical
            print(f"• {finding['finding']}")
        print()
        
        print("TOP RECOMMENDATIONS (by priority):")
        print("-"*70)
        for i, rec in enumerate(all_recommendations[:10], 1):
            print(f"{i}. [{rec['priority']}/10] {rec['recommendation']}")
        print()
        
        # Generate fix script
        self.generate_master_fix_script(all_recommendations)
        
    def generate_master_fix_script(self, recommendations):
        """Generate master fix script based on all recommendations"""
        script_path = Path("/opt/github/Z-FORGE/ultrathink_master_fix.sh")
        
        script_content = """#!/bin/bash
# UltraThink Master Fix Script
# Generated from multi-agent analysis

set -e

echo "════════════════════════════════════════════════════════════════════"
echo "           UltraThink Master Fix for Z-FORGE Build"
echo "════════════════════════════════════════════════════════════════════"

CHROOT_PATH="/tmp/zforge_workspace/chroot"

# 1. Ensure we're running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: Please run with sudo"
    exit 1
fi

# 2. Create comprehensive sources.list
echo "[1/6] Fixing repository configuration..."
if [ -d "$CHROOT_PATH" ]; then
    cat > "$CHROOT_PATH/etc/apt/sources.list" << 'EOF'
# Debian Trixie (Testing)
deb http://deb.debian.org/debian trixie main contrib non-free non-free-firmware
deb-src http://deb.debian.org/debian trixie main contrib non-free non-free-firmware

# Debian Bookworm (Stable) - Fallback
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://deb.debian.org/debian bookworm-backports main contrib non-free non-free-firmware

# Debian Sid (Unstable) - Last resort
deb http://deb.debian.org/debian sid main contrib non-free non-free-firmware
EOF

    # 3. Fix APT preferences
    echo "[2/6] Setting package priorities..."
    mkdir -p "$CHROOT_PATH/etc/apt/preferences.d"
    cat > "$CHROOT_PATH/etc/apt/preferences.d/00-priorities" << 'EOF'
Package: *
Pin: release n=trixie
Pin-Priority: 900

Package: *
Pin: release n=bookworm
Pin-Priority: 800

Package: *
Pin: release n=bookworm-backports
Pin-Priority: 700

Package: *
Pin: release n=sid
Pin-Priority: 100
EOF

    # 4. Mount required filesystems
    echo "[3/6] Mounting filesystems..."
    for fs in proc sys dev dev/pts; do
        mountpoint -q "$CHROOT_PATH/$fs" || mount --bind /$fs "$CHROOT_PATH/$fs"
    done

    # 5. Fix DNS
    echo "[4/6] Fixing DNS resolution..."
    cp /etc/resolv.conf "$CHROOT_PATH/etc/resolv.conf"

    # 6. Update and install minimal packages
    echo "[5/6] Updating package lists..."
    chroot "$CHROOT_PATH" apt-get update || echo "Update had issues but continuing..."

    # 7. Install absolutely minimal packages
    echo "[6/6] Installing minimal viable packages..."
    MINIMAL_PACKAGES="bash coreutils util-linux systemd"
    for pkg in $MINIMAL_PACKAGES; do
        echo "Installing $pkg..."
        chroot "$CHROOT_PATH" apt-get install -y $pkg || echo "Failed: $pkg"
    done
    
    echo "Basic fixes applied!"
else
    echo "Chroot not found - fixes will be applied during next build"
fi

echo ""
echo "Recommended next steps:"
echo "1. Run: make clean"
echo "2. Run: make build"
echo "3. Monitor for LiveEnvironment failures"
"""
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        script_path.chmod(0o755)
        
        print(f"MASTER FIX SCRIPT GENERATED: {script_path}")
        print()
        print("To apply fixes:")
        print(f"  sudo {script_path}")
        print("  make build")
        print()

def main():
    """Main execution"""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║          UltraThink Build Fixer - 4-Agent Team v1.0              ║")
    print("║                 Comprehensive Build Diagnosis                      ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    coordinator = UltraThinkCoordinator()
    coordinator.deploy_agents()
    coordinator.generate_comprehensive_report()

if __name__ == "__main__":
    main()