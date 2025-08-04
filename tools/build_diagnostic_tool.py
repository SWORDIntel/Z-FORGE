#!/usr/bin/env python3
"""
Z-FORGE Build Diagnostic and Pre-Build Validation Tool
Comprehensive checks to ensure successful builds
"""

import os
import sys
import subprocess
import shutil
import json
import psutil
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class BuildDiagnosticTool:
    """Comprehensive build diagnostics and validation"""
    
    def __init__(self):
        self.project_root = Path("/opt/github/Z-FORGE")
        self.workspace = Path("/home/john/zforge_workspace")
        self.checks_passed = 0
        self.checks_failed = 0
        self.critical_issues = []
        self.warnings = []
        self.fixes_applied = []
        
    def run_all_checks(self) -> Dict:
        """Run all diagnostic checks"""
        print("=" * 80)
        print("Z-FORGE BUILD DIAGNOSTIC TOOL")
        print("=" * 80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "system": self.check_system_requirements(),
            "dependencies": self.check_dependencies(),
            "workspace": self.check_workspace(),
            "network": self.check_network(),
            "apt": self.check_apt_system(),
            "kernel": self.check_kernel_compatibility(),
            "zfs": self.check_zfs_readiness(),
            "dracut": self.check_dracut_setup(),
            "permissions": self.check_permissions(),
            "build_specs": self.check_build_specifications()
        }
        
        # Generate summary
        results["summary"] = self.generate_summary()
        
        return results
    
    def check_system_requirements(self) -> Dict:
        """Check system requirements"""
        print("\n[1/10] Checking System Requirements...")
        requirements = {
            "cpu_cores": 2,
            "memory_gb": 4,
            "disk_gb": 50
        }
        
        actual = {
            "cpu_cores": psutil.cpu_count(),
            "memory_gb": round(psutil.virtual_memory().total / (1024**3)),
            "disk_gb": round(psutil.disk_usage('/').free / (1024**3))
        }
        
        results = {
            "actual": actual,
            "requirements": requirements,
            "status": "PASS"
        }
        
        # Check each requirement
        issues = []
        if actual["cpu_cores"] < requirements["cpu_cores"]:
            issues.append(f"Insufficient CPU cores: {actual['cpu_cores']} < {requirements['cpu_cores']}")
        if actual["memory_gb"] < requirements["memory_gb"]:
            issues.append(f"Insufficient memory: {actual['memory_gb']}GB < {requirements['memory_gb']}GB")
        if actual["disk_gb"] < requirements["disk_gb"]:
            issues.append(f"Insufficient disk space: {actual['disk_gb']}GB < {requirements['disk_gb']}GB")
            
        if issues:
            results["status"] = "FAIL"
            results["issues"] = issues
            self.critical_issues.extend(issues)
            self.checks_failed += 1
            print(f"  ❌ FAILED: {', '.join(issues)}")
        else:
            self.checks_passed += 1
            print(f"  ✅ PASS: {actual['cpu_cores']} CPUs, {actual['memory_gb']}GB RAM, {actual['disk_gb']}GB free")
            
        return results
    
    def check_dependencies(self) -> Dict:
        """Check required dependencies"""
        print("\n[2/10] Checking Dependencies...")
        
        required_commands = [
            ("python3", "--version"),
            ("debootstrap", "--version"),
            ("mksquashfs", "-version"),
            ("xorriso", "--version"),
            ("git", "--version")
        ]
        
        required_python = [
            "yaml",
            "psutil",
            "jinja2"
        ]
        
        results = {
            "commands": {},
            "python_modules": {},
            "status": "PASS"
        }
        
        # Check commands
        for cmd, arg in required_commands:
            try:
                result = subprocess.run([cmd, arg], capture_output=True, text=True, timeout=5)
                results["commands"][cmd] = "installed"
                print(f"  ✅ {cmd}: installed")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                results["commands"][cmd] = "missing"
                results["status"] = "FAIL"
                self.critical_issues.append(f"Missing command: {cmd}")
                print(f"  ❌ {cmd}: missing")
        
        # Check Python modules
        for module in required_python:
            try:
                __import__(module)
                results["python_modules"][module] = "installed"
                print(f"  ✅ Python module {module}: installed")
            except ImportError:
                results["python_modules"][module] = "missing"
                results["status"] = "FAIL"
                self.warnings.append(f"Missing Python module: {module}")
                print(f"  ⚠️  Python module {module}: missing")
        
        if results["status"] == "PASS":
            self.checks_passed += 1
        else:
            self.checks_failed += 1
            
        return results
    
    def check_workspace(self) -> Dict:
        """Check workspace configuration"""
        print("\n[3/10] Checking Workspace...")
        
        results = {
            "path": str(self.workspace),
            "exists": self.workspace.exists(),
            "writable": False,
            "space_gb": 0,
            "status": "PASS"
        }
        
        if results["exists"]:
            # Check if writable
            test_file = self.workspace / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
                results["writable"] = True
                print(f"  ✅ Workspace exists and is writable")
            except:
                results["writable"] = False
                results["status"] = "FAIL"
                self.critical_issues.append(f"Workspace not writable: {self.workspace}")
                print(f"  ❌ Workspace not writable")
            
            # Check space
            try:
                stat = os.statvfs(self.workspace)
                results["space_gb"] = round((stat.f_bavail * stat.f_frsize) / (1024**3))
                if results["space_gb"] < 30:
                    self.warnings.append(f"Low workspace space: {results['space_gb']}GB")
                    print(f"  ⚠️  Low space: {results['space_gb']}GB (recommend 50GB+)")
                else:
                    print(f"  ✅ Workspace has {results['space_gb']}GB free")
            except:
                pass
        else:
            # Try to create workspace
            try:
                self.workspace.mkdir(parents=True, exist_ok=True)
                results["exists"] = True
                results["writable"] = True
                self.fixes_applied.append(f"Created workspace: {self.workspace}")
                print(f"  ✅ Created workspace directory")
            except:
                results["status"] = "FAIL"
                self.critical_issues.append(f"Cannot create workspace: {self.workspace}")
                print(f"  ❌ Cannot create workspace")
        
        if results["status"] == "PASS":
            self.checks_passed += 1
        else:
            self.checks_failed += 1
            
        return results
    
    def check_network(self) -> Dict:
        """Check network connectivity"""
        print("\n[4/10] Checking Network...")
        
        results = {
            "dns": False,
            "debian_repo": False,
            "internet": False,
            "status": "PASS"
        }
        
        # Check DNS
        try:
            result = subprocess.run(["nslookup", "debian.org"], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                results["dns"] = True
                print(f"  ✅ DNS resolution working")
            else:
                print(f"  ⚠️  DNS resolution issues")
        except:
            print(f"  ⚠️  Cannot check DNS")
        
        # Check Debian repo
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "5", "deb.debian.org"],
                                  capture_output=True, timeout=6)
            if result.returncode == 0:
                results["debian_repo"] = True
                print(f"  ✅ Debian repository accessible")
            else:
                print(f"  ⚠️  Cannot reach Debian repository")
        except:
            print(f"  ⚠️  Cannot check repository")
        
        # Check general internet
        try:
            result = subprocess.run(["ping", "-c", "1", "-W", "5", "8.8.8.8"],
                                  capture_output=True, timeout=6)
            if result.returncode == 0:
                results["internet"] = True
                print(f"  ✅ Internet connectivity working")
            else:
                print(f"  ⚠️  No internet connectivity")
        except:
            print(f"  ⚠️  Cannot check internet")
        
        if not (results["dns"] and results["debian_repo"]):
            results["status"] = "WARN"
            self.warnings.append("Network connectivity issues detected")
        
        self.checks_passed += 1
        return results
    
    def check_apt_system(self) -> Dict:
        """Check APT system health"""
        print("\n[5/10] Checking APT System...")
        
        results = {
            "lock_files": [],
            "broken_packages": False,
            "sources_list": False,
            "status": "PASS"
        }
        
        # Check for lock files
        lock_files = [
            "/var/lib/dpkg/lock",
            "/var/lib/dpkg/lock-frontend",
            "/var/lib/apt/lists/lock",
            "/var/cache/apt/archives/lock"
        ]
        
        for lock_file in lock_files:
            if Path(lock_file).exists():
                try:
                    # Check if file is actually locked
                    subprocess.run(["lsof", lock_file], 
                                 capture_output=True, timeout=2)
                    results["lock_files"].append(lock_file)
                    self.warnings.append(f"APT lock file exists: {lock_file}")
                    print(f"  ⚠️  Lock file: {lock_file}")
                except:
                    pass
        
        if not results["lock_files"]:
            print(f"  ✅ No APT lock files")
        
        # Check for broken packages
        try:
            result = subprocess.run(["dpkg", "--audit"], 
                                  capture_output=True, text=True, timeout=10)
            if result.stdout.strip():
                results["broken_packages"] = True
                self.warnings.append("Broken packages detected")
                print(f"  ⚠️  Broken packages detected")
            else:
                print(f"  ✅ No broken packages")
        except:
            print(f"  ⚠️  Cannot check package status")
        
        # Check sources.list
        sources_file = Path("/etc/apt/sources.list")
        if sources_file.exists():
            results["sources_list"] = True
            print(f"  ✅ APT sources configured")
        else:
            results["status"] = "FAIL"
            self.critical_issues.append("Missing /etc/apt/sources.list")
            print(f"  ❌ Missing APT sources")
        
        if results["status"] == "PASS":
            self.checks_passed += 1
        else:
            self.checks_failed += 1
            
        return results
    
    def check_kernel_compatibility(self) -> Dict:
        """Check kernel compatibility"""
        print("\n[6/10] Checking Kernel Compatibility...")
        
        results = {
            "current_kernel": platform.release(),
            "architecture": platform.machine(),
            "headers_installed": False,
            "status": "PASS"
        }
        
        # Check architecture
        if results["architecture"] != "x86_64":
            results["status"] = "FAIL"
            self.critical_issues.append(f"Unsupported architecture: {results['architecture']}")
            print(f"  ❌ Unsupported architecture: {results['architecture']}")
        else:
            print(f"  ✅ Architecture: {results['architecture']}")
        
        # Check kernel headers
        headers_path = Path(f"/usr/src/linux-headers-{results['current_kernel']}")
        if headers_path.exists():
            results["headers_installed"] = True
            print(f"  ✅ Kernel headers installed")
        else:
            self.warnings.append(f"Kernel headers not installed for {results['current_kernel']}")
            print(f"  ⚠️  Kernel headers not installed")
        
        print(f"  ℹ️  Current kernel: {results['current_kernel']}")
        
        if results["status"] == "PASS":
            self.checks_passed += 1
        else:
            self.checks_failed += 1
            
        return results
    
    def check_zfs_readiness(self) -> Dict:
        """Check ZFS build readiness"""
        print("\n[7/10] Checking ZFS Readiness...")
        
        results = {
            "zfs_installed": False,
            "dkms_installed": False,
            "build_deps": [],
            "status": "PASS"
        }
        
        # Check if ZFS already installed
        try:
            result = subprocess.run(["which", "zfs"], capture_output=True)
            if result.returncode == 0:
                results["zfs_installed"] = True
                print(f"  ℹ️  ZFS already installed")
        except:
            pass
        
        # Check DKMS
        try:
            result = subprocess.run(["which", "dkms"], capture_output=True)
            if result.returncode == 0:
                results["dkms_installed"] = True
                print(f"  ✅ DKMS installed")
            else:
                self.warnings.append("DKMS not installed - required for ZFS")
                print(f"  ⚠️  DKMS not installed")
        except:
            pass
        
        # Check build dependencies
        build_deps = ["build-essential", "autoconf", "automake", "libtool", "gawk"]
        for dep in build_deps:
            try:
                result = subprocess.run(["dpkg", "-l", dep], capture_output=True)
                if result.returncode == 0:
                    results["build_deps"].append(dep)
            except:
                pass
        
        if len(results["build_deps"]) < len(build_deps):
            missing = set(build_deps) - set(results["build_deps"])
            self.warnings.append(f"Missing ZFS build deps: {missing}")
            print(f"  ⚠️  Missing build dependencies: {missing}")
        else:
            print(f"  ✅ All ZFS build dependencies present")
        
        self.checks_passed += 1
        return results
    
    def check_dracut_setup(self) -> Dict:
        """Check dracut configuration"""
        print("\n[8/10] Checking Dracut Setup...")
        
        results = {
            "dracut_installed": False,
            "initramfs_tools": False,
            "config_exists": False,
            "status": "PASS"
        }
        
        # Check dracut installation
        try:
            result = subprocess.run(["which", "dracut"], capture_output=True)
            if result.returncode == 0:
                results["dracut_installed"] = True
                print(f"  ✅ Dracut installed")
            else:
                print(f"  ℹ️  Dracut not installed (will be installed during build)")
        except:
            pass
        
        # Check for initramfs-tools conflict
        try:
            result = subprocess.run(["dpkg", "-l", "initramfs-tools"], 
                                  capture_output=True, text=True)
            if "ii  initramfs-tools" in result.stdout:
                results["initramfs_tools"] = True
                self.warnings.append("initramfs-tools installed - may conflict with dracut")
                print(f"  ⚠️  initramfs-tools present (will be removed)")
        except:
            pass
        
        # Check dracut config
        dracut_conf = Path("/etc/dracut.conf.d")
        if dracut_conf.exists():
            results["config_exists"] = True
            print(f"  ✅ Dracut config directory exists")
        else:
            print(f"  ℹ️  Dracut config will be created during build")
        
        self.checks_passed += 1
        return results
    
    def check_permissions(self) -> Dict:
        """Check file permissions"""
        print("\n[9/10] Checking Permissions...")
        
        results = {
            "user": os.environ.get("USER", "unknown"),
            "sudo_access": False,
            "build_py_executable": False,
            "modules_readable": True,
            "status": "PASS"
        }
        
        # Check sudo access
        try:
            result = subprocess.run(["sudo", "-n", "true"], 
                                  capture_output=True, timeout=2)
            if result.returncode == 0:
                results["sudo_access"] = True
                print(f"  ✅ Sudo access available")
            else:
                print(f"  ℹ️  Sudo will require password")
        except:
            pass
        
        # Check build.py
        build_py = self.project_root / "build.py"
        if build_py.exists():
            if os.access(build_py, os.X_OK):
                results["build_py_executable"] = True
                print(f"  ✅ build.py is executable")
            else:
                # Try to fix
                try:
                    build_py.chmod(0o755)
                    results["build_py_executable"] = True
                    self.fixes_applied.append("Made build.py executable")
                    print(f"  ✅ Fixed: made build.py executable")
                except:
                    self.warnings.append("build.py not executable")
                    print(f"  ⚠️  build.py not executable")
        
        # Check modules directory
        modules_dir = self.project_root / "builder/modules"
        if modules_dir.exists():
            for module_file in modules_dir.glob("*.py"):
                if not os.access(module_file, os.R_OK):
                    results["modules_readable"] = False
                    self.warnings.append(f"Module not readable: {module_file.name}")
                    
        if results["modules_readable"]:
            print(f"  ✅ All modules readable")
        else:
            print(f"  ⚠️  Some modules not readable")
        
        self.checks_passed += 1
        return results
    
    def check_build_specifications(self) -> Dict:
        """Check build specification files"""
        print("\n[10/10] Checking Build Specifications...")
        
        build_specs = [
            "build_specs/build_spec.yml",
            "build_specs/build_spec_stable.yml",
            "build_specs/build_spec_no_tmp.yml",
            "build_specs/build_spec_outside_packages.yml",
            "build_specs/build_spec_proxmox9.yml",
            "build_specs/build_spec_proxmox_full.yml",
            "build_specs/build_spec_trixie_clean.yml"
        ]
        
        results = {
            "specs": {},
            "status": "PASS"
        }
        
        for spec in build_specs:
            spec_path = self.project_root / spec
            if spec_path.exists():
                try:
                    import yaml
                    with open(spec_path, 'r') as f:
                        data = yaml.safe_load(f)
                    
                    # Check required fields
                    has_required = all(field in data for field in 
                                     ["name", "version", "builder_config", "modules"])
                    
                    if has_required:
                        results["specs"][spec] = "valid"
                        print(f"  ✅ {spec}: valid")
                    else:
                        results["specs"][spec] = "invalid"
                        self.warnings.append(f"Invalid spec: {spec}")
                        print(f"  ⚠️  {spec}: missing required fields")
                except Exception as e:
                    results["specs"][spec] = f"error: {e}"
                    self.warnings.append(f"Cannot parse {spec}: {e}")
                    print(f"  ❌ {spec}: parse error")
            else:
                results["specs"][spec] = "missing"
                results["status"] = "FAIL"
                self.critical_issues.append(f"Missing build spec: {spec}")
                print(f"  ❌ {spec}: missing")
        
        if results["status"] == "PASS":
            self.checks_passed += 1
        else:
            self.checks_failed += 1
            
        return results
    
    def generate_summary(self) -> Dict:
        """Generate summary and recommendations"""
        summary = {
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "critical_issues": self.critical_issues,
            "warnings": self.warnings,
            "fixes_applied": self.fixes_applied,
            "ready_to_build": len(self.critical_issues) == 0
        }
        
        # Generate recommendations
        recommendations = []
        
        if self.critical_issues:
            recommendations.append("FIX CRITICAL ISSUES BEFORE BUILDING:")
            for issue in self.critical_issues:
                recommendations.append(f"  • {issue}")
        
        if self.warnings:
            recommendations.append("\nCONSIDER ADDRESSING WARNINGS:")
            for warning in self.warnings[:5]:  # First 5 warnings
                recommendations.append(f"  • {warning}")
        
        if not self.critical_issues:
            recommendations.append("\n✅ SYSTEM READY FOR BUILD")
            recommendations.append("\nRECOMMENDED BUILD COMMANDS:")
            recommendations.append("  • GUI: ./launch-enhanced-gui.sh")
            recommendations.append("  • Stable: sudo python3 build.py --spec build_specs/build_spec_stable.yml")
            recommendations.append("  • Fast: sudo python3 build.py --spec build_specs/build_spec_outside_packages.yml")
        
        summary["recommendations"] = recommendations
        
        return summary
    
    def print_summary(self, results: Dict):
        """Print formatted summary"""
        summary = results["summary"]
        
        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        print(f"\nChecks Passed: {summary['checks_passed']}/10")
        print(f"Checks Failed: {summary['checks_failed']}/10")
        
        if summary["critical_issues"]:
            print(f"\n❌ CRITICAL ISSUES ({len(summary['critical_issues'])})")
            for issue in summary["critical_issues"]:
                print(f"  • {issue}")
        
        if summary["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(summary['warnings'])})")
            for warning in summary["warnings"][:5]:
                print(f"  • {warning}")
            if len(summary["warnings"]) > 5:
                print(f"  • ... and {len(summary['warnings']) - 5} more")
        
        if summary["fixes_applied"]:
            print(f"\n✅ FIXES APPLIED ({len(summary['fixes_applied'])})")
            for fix in summary["fixes_applied"]:
                print(f"  • {fix}")
        
        print("\n" + "=" * 80)
        print("RECOMMENDATIONS")
        print("=" * 80)
        for rec in summary["recommendations"]:
            print(rec)
        
        if summary["ready_to_build"]:
            print("\n" + "=" * 80)
            print("🚀 SYSTEM IS READY TO BUILD!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("⚠️  PLEASE ADDRESS CRITICAL ISSUES BEFORE BUILDING")
            print("=" * 80)

def main():
    """Main diagnostic function"""
    tool = BuildDiagnosticTool()
    
    # Run all checks
    results = tool.run_all_checks()
    
    # Print summary
    tool.print_summary(results)
    
    # Save results
    results_file = Path("/opt/github/Z-FORGE/diagnostic_results.json")
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\nDetailed results saved to: {results_file}")
    
    return 0 if results["summary"]["ready_to_build"] else 1

if __name__ == "__main__":
    sys.exit(main())