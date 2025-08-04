#!/usr/bin/env python3
"""
Z-FORGE Build Failure Analysis Tool
Analyzes build logs to identify common failure patterns and provides solutions
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

class BuildFailureAnalyzer:
    """Analyze build failures and identify patterns"""
    
    def __init__(self):
        self.project_root = Path("/opt/github/Z-FORGE")
        self.logs_dir = self.project_root / "logs"
        self.failure_patterns = self._define_failure_patterns()
        self.solutions = self._define_solutions()
        
    def _define_failure_patterns(self) -> Dict[str, Dict]:
        """Define common failure patterns with regex"""
        return {
            "dpkg_error": {
                "pattern": r"E: Sub-process /usr/bin/dpkg returned an error code \((\d+)\)",
                "category": "Package Installation",
                "severity": "critical"
            },
            "apt_error_100": {
                "pattern": r"returned non-zero exit status 100",
                "category": "APT Repository",
                "severity": "critical"
            },
            "zfs_package_fail": {
                "pattern": r"Failed to install \[.*zfs.*\]",
                "category": "ZFS Installation",
                "severity": "critical"
            },
            "kernel_acquisition_fail": {
                "pattern": r"Kernel acquisition failed",
                "category": "Kernel Installation",
                "severity": "critical"
            },
            "missing_dependency": {
                "pattern": r"Package .* is not available",
                "category": "Dependencies",
                "severity": "high"
            },
            "gpg_key_error": {
                "pattern": r"GPG error|NO_PUBKEY",
                "category": "GPG Keys",
                "severity": "medium"
            },
            "disk_space": {
                "pattern": r"No space left on device|insufficient space",
                "category": "Resources",
                "severity": "critical"
            },
            "network_error": {
                "pattern": r"Could not resolve|Connection refused|Network is unreachable",
                "category": "Network",
                "severity": "high"
            },
            "permission_denied": {
                "pattern": r"Permission denied|Operation not permitted",
                "category": "Permissions",
                "severity": "high"
            },
            "chroot_error": {
                "pattern": r"chroot.*failed|cannot run command.*chroot",
                "category": "Chroot Environment",
                "severity": "critical"
            },
            "module_import_error": {
                "pattern": r"ModuleNotFoundError|ImportError",
                "category": "Python Modules",
                "severity": "high"
            },
            "initramfs_error": {
                "pattern": r"update-initramfs.*failed|dracut.*failed",
                "category": "Initramfs Generation",
                "severity": "critical"
            },
            "broken_packages": {
                "pattern": r"broken packages|unmet dependencies",
                "category": "Package Dependencies",
                "severity": "critical"
            },
            "locale_error": {
                "pattern": r"locale.*cannot|perl: warning: Setting locale failed",
                "category": "Locale Configuration",
                "severity": "low"
            },
            "mount_error": {
                "pattern": r"mount.*failed|already mounted|target is busy",
                "category": "Filesystem Mount",
                "severity": "high"
            }
        }
        
    def _define_solutions(self) -> Dict[str, List[str]]:
        """Define solutions for each failure pattern"""
        return {
            "dpkg_error": [
                "Run: sudo dpkg --configure -a",
                "Clear APT cache: sudo apt-get clean",
                "Fix broken packages: sudo apt-get install -f",
                "Remove lock files: sudo rm /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock",
                "Reconfigure packages: sudo dpkg-reconfigure -a"
            ],
            "apt_error_100": [
                "Update package lists: sudo apt-get update",
                "Check /etc/apt/sources.list for correct repositories",
                "For Trixie: ensure 'testing' repositories are enabled",
                "Clear APT cache: sudo rm -rf /var/lib/apt/lists/*",
                "Regenerate package cache: sudo apt-get update --fix-missing"
            ],
            "zfs_package_fail": [
                "Install kernel headers first: sudo apt-get install linux-headers-$(uname -r)",
                "Add ZFS repository: sudo apt-add-repository contrib non-free",
                "Install DKMS: sudo apt-get install dkms",
                "Try manual ZFS build from source (use zfs_build module)",
                "Check kernel compatibility with ZFS version"
            ],
            "kernel_acquisition_fail": [
                "Verify kernel package names: apt-cache search linux-image",
                "Install generic kernel: sudo apt-get install linux-image-generic",
                "For specific version, check availability: apt-cache policy linux-image-*",
                "Ensure dracut is installed: sudo apt-get install dracut dracut-core",
                "Remove initramfs-tools conflicts: sudo apt-get remove initramfs-tools"
            ],
            "missing_dependency": [
                "Update package database: sudo apt-get update",
                "Search for package: apt-cache search <package_name>",
                "Check if package is in different repository",
                "Consider using backports or testing repositories",
                "Build from source if package unavailable"
            ],
            "gpg_key_error": [
                "Import missing key: sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys <KEY>",
                "Update keyring: sudo apt-get install debian-keyring",
                "Disable GPG checking temporarily: APT::Get::AllowUnauthenticated=true",
                "Download and add key manually: wget -qO - <key_url> | sudo apt-key add -"
            ],
            "disk_space": [
                "Check disk usage: df -h",
                "Clean build workspace: rm -rf /home/john/zforge_workspace/chroot",
                "Clear APT cache: sudo apt-get clean && sudo apt-get autoclean",
                "Remove old kernels: sudo apt-get autoremove --purge",
                "Increase workspace partition size or use different location"
            ],
            "network_error": [
                "Check network connectivity: ping -c 4 8.8.8.8",
                "Check DNS resolution: nslookup debian.org",
                "Configure proxy if needed: export http_proxy=...",
                "Use local mirror: modify /etc/apt/sources.list",
                "Retry with --retry-connrefused flag"
            ],
            "permission_denied": [
                "Run with sudo: sudo python3 build.py",
                "Check file ownership: ls -la <file>",
                "Fix permissions: sudo chmod 755 <directory>",
                "Check if filesystem mounted with noexec",
                "Verify user is in required groups (sudo, docker, etc.)"
            ],
            "chroot_error": [
                "Ensure chroot is properly set up: check /proc, /sys, /dev mounts",
                "Mount required filesystems: builder/modules/workspace_setup.py",
                "Check if chroot path exists and is accessible",
                "Verify architecture compatibility (amd64)",
                "Clean and rebuild chroot environment"
            ],
            "module_import_error": [
                "Install missing Python packages: pip3 install -r requirements.txt",
                "Check Python path: sys.path",
                "Verify module files exist in builder/modules/",
                "Check for circular imports",
                "Ensure __init__.py files are present"
            ],
            "initramfs_error": [
                "Ensure dracut is installed: apt-get install dracut",
                "Remove initramfs-tools: apt-get remove initramfs-tools",
                "Regenerate initramfs: dracut -f",
                "Check kernel modules: lsmod",
                "Verify /boot has sufficient space"
            ],
            "broken_packages": [
                "Fix broken packages: sudo apt-get install -f",
                "Remove problematic packages: sudo dpkg --remove --force-remove-reinstreq <package>",
                "Clear package cache: sudo apt-get clean",
                "Reconfigure dpkg: sudo dpkg --configure -a",
                "Use aptitude for smarter dependency resolution: sudo aptitude install <package>"
            ],
            "locale_error": [
                "Generate locale: sudo locale-gen en_US.UTF-8",
                "Set default locale: sudo update-locale LANG=en_US.UTF-8",
                "Export locale vars: export LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8",
                "Reconfigure locales: sudo dpkg-reconfigure locales"
            ],
            "mount_error": [
                "Check current mounts: mount | grep chroot",
                "Unmount if needed: sudo umount -l <path>",
                "Check for processes using mount: lsof | grep <path>",
                "Kill processes if needed: fuser -km <path>",
                "Use lazy unmount: umount -l <path>"
            ]
        }
    
    def analyze_log_file(self, log_path: Path) -> Dict:
        """Analyze a single log file for failures"""
        failures = []
        
        try:
            with open(log_path, 'r') as f:
                content = f.read()
                
            # Check each pattern
            for pattern_name, pattern_info in self.failure_patterns.items():
                matches = re.findall(pattern_info["pattern"], content, re.IGNORECASE)
                if matches:
                    failures.append({
                        "type": pattern_name,
                        "category": pattern_info["category"],
                        "severity": pattern_info["severity"],
                        "occurrences": len(matches),
                        "details": matches[:3]  # First 3 matches
                    })
                    
            # Extract module context
            module_match = re.search(r"(\w+) - ERROR", content)
            module = module_match.group(1) if module_match else "Unknown"
            
            # Extract timestamp
            time_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)
            timestamp = time_match.group(1) if time_match else "Unknown"
            
            return {
                "log_file": log_path.name,
                "timestamp": timestamp,
                "module": module,
                "failures": failures,
                "total_errors": len(failures)
            }
            
        except Exception as e:
            return {
                "log_file": log_path.name,
                "error": str(e)
            }
    
    def analyze_all_logs(self) -> Dict:
        """Analyze all log files in the logs directory"""
        results = {
            "analysis_time": datetime.now().isoformat(),
            "logs_analyzed": 0,
            "total_failures": 0,
            "failure_summary": defaultdict(int),
            "category_summary": defaultdict(int),
            "severity_summary": defaultdict(int),
            "log_details": []
        }
        
        # Find all log files
        log_files = list(self.logs_dir.glob("**/*.log"))
        results["logs_analyzed"] = len(log_files)
        
        # Analyze each log
        for log_file in log_files:
            analysis = self.analyze_log_file(log_file)
            
            if "failures" in analysis and analysis["failures"]:
                results["log_details"].append(analysis)
                results["total_failures"] += analysis["total_errors"]
                
                # Update summaries
                for failure in analysis["failures"]:
                    results["failure_summary"][failure["type"]] += failure["occurrences"]
                    results["category_summary"][failure["category"]] += failure["occurrences"]
                    results["severity_summary"][failure["severity"]] += failure["occurrences"]
        
        return results
    
    def generate_report(self, analysis: Dict) -> str:
        """Generate a human-readable report"""
        report = []
        report.append("=" * 80)
        report.append("Z-FORGE BUILD FAILURE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"\nAnalysis Date: {analysis['analysis_time']}")
        report.append(f"Logs Analyzed: {analysis['logs_analyzed']}")
        report.append(f"Total Failure Patterns Found: {analysis['total_failures']}")
        
        # Severity Summary
        report.append("\n" + "=" * 40)
        report.append("SEVERITY BREAKDOWN")
        report.append("=" * 40)
        for severity in ["critical", "high", "medium", "low"]:
            count = analysis["severity_summary"].get(severity, 0)
            if count > 0:
                report.append(f"  {severity.upper():10} : {count} occurrences")
        
        # Category Summary
        report.append("\n" + "=" * 40)
        report.append("FAILURE CATEGORIES")
        report.append("=" * 40)
        for category, count in sorted(analysis["category_summary"].items(), 
                                     key=lambda x: x[1], reverse=True):
            report.append(f"  {category:25} : {count} occurrences")
        
        # Top Failure Patterns
        report.append("\n" + "=" * 40)
        report.append("TOP FAILURE PATTERNS")
        report.append("=" * 40)
        top_failures = sorted(analysis["failure_summary"].items(), 
                            key=lambda x: x[1], reverse=True)[:10]
        for pattern, count in top_failures:
            pattern_info = self.failure_patterns[pattern]
            report.append(f"\n  Pattern: {pattern}")
            report.append(f"  Category: {pattern_info['category']}")
            report.append(f"  Severity: {pattern_info['severity']}")
            report.append(f"  Occurrences: {count}")
            
            # Add solutions
            if pattern in self.solutions:
                report.append("  Solutions:")
                for solution in self.solutions[pattern][:3]:
                    report.append(f"    • {solution}")
        
        # Recent Failures
        report.append("\n" + "=" * 40)
        report.append("RECENT FAILURES (Last 5)")
        report.append("=" * 40)
        recent_logs = sorted(analysis["log_details"], 
                           key=lambda x: x.get("timestamp", ""), 
                           reverse=True)[:5]
        
        for log in recent_logs:
            report.append(f"\n  Log: {log['log_file']}")
            report.append(f"  Time: {log.get('timestamp', 'Unknown')}")
            report.append(f"  Module: {log.get('module', 'Unknown')}")
            report.append(f"  Failures:")
            for failure in log.get("failures", [])[:3]:
                report.append(f"    • {failure['type']} ({failure['severity']})")
        
        # Recommendations
        report.append("\n" + "=" * 40)
        report.append("RECOMMENDATIONS")
        report.append("=" * 40)
        
        recommendations = self._generate_recommendations(analysis)
        for i, rec in enumerate(recommendations, 1):
            report.append(f"  {i}. {rec}")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Check for critical failures
        if analysis["severity_summary"].get("critical", 0) > 0:
            recommendations.append("URGENT: Address critical failures immediately - these block builds")
        
        # Check for package issues
        if analysis["category_summary"].get("Package Installation", 0) > 0:
            recommendations.append("Run pre-build validation: python3 builder/modules/build_pipeline_validator.py")
            recommendations.append("Clear APT cache and fix broken packages: sudo apt-get clean && sudo apt-get install -f")
        
        # Check for ZFS issues
        if analysis["category_summary"].get("ZFS Installation", 0) > 0:
            recommendations.append("Consider using prebuilt ZFS packages (build_specs/build_spec_outside_packages.yml)")
            recommendations.append("Ensure kernel headers match running kernel")
        
        # Check for kernel issues
        if analysis["category_summary"].get("Kernel Installation", 0) > 0:
            recommendations.append("Use stable kernel from Bookworm (build_specs/build_spec_stable.yml)")
            recommendations.append("Verify dracut is properly configured")
        
        # Check for network issues
        if analysis["category_summary"].get("Network", 0) > 0:
            recommendations.append("Check network connectivity and DNS resolution")
            recommendations.append("Consider using local package mirror")
        
        # Check for resource issues
        if analysis["category_summary"].get("Resources", 0) > 0:
            recommendations.append("Ensure at least 50GB free disk space in workspace")
            recommendations.append("Clean old build artifacts: rm -rf /home/john/zforge_workspace/chroot")
        
        # General recommendations
        recommendations.append("Run integration tests: python3 test_full_integration.py")
        recommendations.append("Use Enhanced GUI for easier build management: ./launch-enhanced-gui.sh")
        
        return recommendations

def main():
    """Main analysis function"""
    print("Starting Z-FORGE Build Failure Analysis...")
    
    analyzer = BuildFailureAnalyzer()
    
    # Analyze all logs
    analysis = analyzer.analyze_all_logs()
    
    # Generate report
    report = analyzer.generate_report(analysis)
    print(report)
    
    # Save report
    report_path = Path("/opt/github/Z-FORGE/BUILD_FAILURE_ANALYSIS.md")
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # Save JSON data for further processing
    json_path = Path("/opt/github/Z-FORGE/build_failure_data.json")
    with open(json_path, 'w') as f:
        # Convert defaultdict to dict for JSON serialization
        analysis["failure_summary"] = dict(analysis["failure_summary"])
        analysis["category_summary"] = dict(analysis["category_summary"])
        analysis["severity_summary"] = dict(analysis["severity_summary"])
        json.dump(analysis, f, indent=2)
    
    print(f"JSON data saved to: {json_path}")
    
    return 0 if analysis["total_failures"] == 0 else 1

if __name__ == "__main__":
    exit(main())