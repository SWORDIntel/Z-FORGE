#!/usr/bin/env python3
"""
UltraThink Log Analyzer Agent

Intelligent agent that analyzes Z-FORGE build logs to identify issues,
patterns, and provide actionable recommendations for fixing problems.
"""

import os
import sys
import re
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [LogAnalyzer] %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'log_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

@dataclass
class LogEntry:
    """Represents a single log entry"""
    timestamp: str
    level: str
    module: str
    message: str
    raw_line: str

@dataclass
class Issue:
    """Represents an identified issue"""
    severity: str  # critical, high, medium, low
    category: str  # error, warning, timeout, dependency, etc.
    title: str
    description: str
    location: str  # file:line or module
    recommendation: str
    occurrences: int = 1

class LogAnalyzerAgent:
    """Intelligent log analysis agent"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.log_patterns = self._initialize_patterns()
        self.issues = []
        self.statistics = {}
        
    def _initialize_patterns(self) -> Dict[str, Dict]:
        """Initialize patterns for issue detection"""
        return {
            # Critical errors
            'module_failures': {
                'pattern': r'(\w+) - ERROR - (.+) failed: (.+)',
                'severity': 'critical',
                'category': 'module_failure'
            },
            'build_failures': {
                'pattern': r'Command failed: (.+)',
                'severity': 'critical', 
                'category': 'build_failure'
            },
            'package_not_found': {
                'pattern': r"Package '([^']+)' has no installation candidate|Unable to locate package ([^\s]+)",
                'severity': 'high',
                'category': 'dependency'
            },
            'permission_denied': {
                'pattern': r'Permission denied|sudo: a password is required',
                'severity': 'high',
                'category': 'permission'
            },
            'file_not_found': {
                'pattern': r'No such file or directory: ([^\s]+)',
                'severity': 'medium',
                'category': 'file_missing'
            },
            'timeout_errors': {
                'pattern': r'TimeoutExpired|Command timed out',
                'severity': 'medium',
                'category': 'timeout'
            },
            'zfs_issues': {
                'pattern': r'Failed to (install|find) ZFS|zfs.*not found|ZFS.*failed',
                'severity': 'high',
                'category': 'zfs_issue'
            },
            'kernel_issues': {
                'pattern': r'kernel.*failed|Unable to.*kernel|Kernel.*not found',
                'severity': 'high',
                'category': 'kernel_issue'
            },
            'chroot_issues': {
                'pattern': r'chroot.*failed|Failed to.*chroot',
                'severity': 'medium',
                'category': 'chroot_issue'
            },
            'apt_issues': {
                'pattern': r'apt-get.*failed|dpkg.*error|E: (.+)',
                'severity': 'medium',
                'category': 'package_manager'
            }
        }
        
    def analyze_logs(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Analyze recent Z-FORGE logs"""
        self.logger.info("Starting intelligent log analysis...")
        
        # Find log files
        log_files = self._find_recent_logs(max_age_hours)
        self.logger.info(f"Found {len(log_files)} recent log files")
        
        if not log_files:
            return {
                'status': 'no_logs_found',
                'message': f'No log files found in the last {max_age_hours} hours'
            }
            
        # Analyze each log file
        all_entries = []
        for log_file in log_files:
            entries = self._parse_log_file(log_file)
            all_entries.extend(entries)
            self.logger.info(f"Parsed {len(entries)} entries from {log_file.name}")
            
        # Detect issues
        self._detect_issues(all_entries)
        
        # Generate statistics
        self._generate_statistics(all_entries)
        
        # Create analysis report
        report = self._create_report(log_files)
        
        return report
        
    def _find_recent_logs(self, max_age_hours: int) -> List[Path]:
        """Find recent Z-FORGE log files"""
        log_files = []
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        # Search patterns for different log locations
        search_paths = [
            Path('/opt/github/Z-FORGE'),
            Path('/opt/github/Z-FORGE/logs'),
            Path('/opt/github/Z-FORGE/builder'),
            Path('/tmp')
        ]
        
        # Log file patterns
        patterns = [
            '*zforge*.log',
            '*ultrathink*.log', 
            '*rebuild*.log',
            '*build*.log',
            'z-forge*.log'
        ]
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
                
            for pattern in patterns:
                for log_file in search_path.glob(pattern):
                    if log_file.is_file():
                        # Check modification time
                        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                        if mtime > cutoff_time:
                            log_files.append(log_file)
                            
        # Sort by modification time (newest first)
        log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return log_files
        
    def _parse_log_file(self, log_file: Path) -> List[LogEntry]:
        """Parse a log file into structured entries"""
        entries = []
        
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    entry = self._parse_log_line(line)
                    if entry:
                        entries.append(entry)
                        
        except Exception as e:
            self.logger.warning(f"Failed to parse {log_file}: {e}")
            
        return entries
        
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line"""
        # Common log patterns
        patterns = [
            # Standard Python logging: 2025-07-29 13:25:20,586 - [Agent] INFO - Message
            r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d+) - \[([^\]]+)\] (\w+) - (.+)$',
            # Z-FORGE format: 2025-07-29 06:54:07,725 - ModuleName - INFO - Message  
            r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}[,\.]\d+) - ([^\s]+) - (\w+) - (.+)$',
            # Simple format: [INFO] ModuleName: Message
            r'^\[(\w+)\] ([^:]+): (.+)$',
            # Bare format: ERROR: Message
            r'^(\w+): (.+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                
                if len(groups) == 4:  # Full format
                    timestamp, module, level, message = groups
                elif len(groups) == 3:  # [LEVEL] Module: Message
                    level, module, message = groups
                    timestamp = ''
                elif len(groups) == 2:  # LEVEL: Message
                    level, message = groups
                    module, timestamp = '', ''
                else:
                    continue
                    
                return LogEntry(
                    timestamp=timestamp,
                    level=level.upper(),
                    module=module,
                    message=message,
                    raw_line=line
                )
                
        # If no pattern matches, create a generic entry
        return LogEntry(
            timestamp='',
            level='UNKNOWN',
            module='unknown',
            message=line,
            raw_line=line
        )
        
    def _detect_issues(self, entries: List[LogEntry]):
        """Detect issues in log entries"""
        self.logger.info("Detecting issues in log entries...")
        
        issue_counts = defaultdict(int)
        
        for entry in entries:
            full_text = f"{entry.module} {entry.message}"
            
            for pattern_name, pattern_info in self.log_patterns.items():
                match = re.search(pattern_info['pattern'], full_text, re.IGNORECASE)
                if match:
                    issue_key = f"{pattern_info['category']}_{pattern_name}"
                    issue_counts[issue_key] += 1
                    
                    # Create issue if not already exists
                    existing_issue = next((i for i in self.issues 
                                         if i.category == pattern_info['category'] 
                                         and pattern_name in i.title), None)
                    
                    if existing_issue:
                        existing_issue.occurrences += 1
                    else:
                        issue = self._create_issue_from_pattern(
                            pattern_name, pattern_info, match, entry
                        )
                        self.issues.append(issue)
                        
        self.logger.info(f"Detected {len(self.issues)} unique issues")
        
    def _create_issue_from_pattern(self, pattern_name: str, pattern_info: Dict,
                                  match: re.Match, entry: LogEntry) -> Issue:
        """Create an issue from a detected pattern"""
        
        # Generate recommendations based on issue type
        recommendations = {
            'dependency': self._get_dependency_recommendation(match, entry),
            'zfs_issue': self._get_zfs_recommendation(match, entry),
            'kernel_issue': self._get_kernel_recommendation(match, entry),
            'permission': self._get_permission_recommendation(match, entry),
            'build_failure': self._get_build_failure_recommendation(match, entry),
            'timeout': self._get_timeout_recommendation(match, entry),
            'package_manager': self._get_package_manager_recommendation(match, entry)
        }
        
        category = pattern_info['category']
        recommendation = recommendations.get(category, "Review the error message and check system configuration.")
        
        return Issue(
            severity=pattern_info['severity'],
            category=category,
            title=f"{pattern_name.replace('_', ' ').title()}",
            description=entry.message,
            location=f"{entry.module}",
            recommendation=recommendation,
            occurrences=1
        )
        
    def _get_dependency_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for dependency issues"""
        package = match.group(1) if match.groups() else "unknown package"
        return f"""Package '{package}' not found. Try:
1. Update package lists: sudo apt-get update
2. Enable contrib repository if ZFS-related
3. Check if package name is correct for Debian Trixie
4. Use pre-built ZFS packages: sudo python3 ultrathink_zfs_prebuilder.py"""
        
    def _get_zfs_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for ZFS issues"""
        return """ZFS installation issue detected. Solutions:
1. Use ZFS pre-builder: sudo python3 ultrathink_zfs_prebuilder.py
2. Check if contrib repository is enabled
3. Verify kernel headers are installed
4. Try building ZFS from source as fallback"""
        
    def _get_kernel_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for kernel issues"""
        return """Kernel-related issue detected. Solutions:
1. Verify kernel version compatibility
2. Install matching kernel headers
3. Check if virtualization is enabled in BIOS
4. Ensure DKMS is properly installed"""
        
    def _get_permission_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for permission issues"""
        return """Permission issue detected. Solutions:
1. Run build with sudo: sudo ./build.sh
2. Check file ownership and permissions
3. Ensure user is in required groups (sudo, disk)
4. Verify chroot directory permissions"""
        
    def _get_build_failure_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for build failures"""
        return """Build command failed. Solutions:
1. Check for missing dependencies
2. Verify disk space availability
3. Review full error output for specific issues
4. Try cleaning workspace and rebuilding"""
        
    def _get_timeout_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for timeout issues"""
        return """Command timeout detected. Solutions:
1. Check network connectivity for downloads
2. Increase timeout values if needed
3. Verify system resources (CPU, memory)
4. Monitor system load during build"""
        
    def _get_package_manager_recommendation(self, match: re.Match, entry: LogEntry) -> str:
        """Get recommendation for package manager issues"""
        return """Package manager issue detected. Solutions:
1. Run: sudo apt-get update && sudo apt-get upgrade
2. Fix broken packages: sudo apt-get install -f
3. Clean package cache: sudo apt-get clean
4. Check disk space in /var/cache/apt"""
        
    def _generate_statistics(self, entries: List[LogEntry]):
        """Generate statistics from log entries"""
        self.statistics = {
            'total_entries': len(entries),
            'by_level': dict(Counter(entry.level for entry in entries)),
            'by_module': dict(Counter(entry.module for entry in entries)),
            'issues_by_severity': dict(Counter(issue.severity for issue in self.issues)),
            'issues_by_category': dict(Counter(issue.category for issue in self.issues)),
            'most_common_issues': [(issue.title, issue.occurrences) 
                                 for issue in sorted(self.issues, 
                                                   key=lambda x: x.occurrences, 
                                                   reverse=True)[:5]]
        }
        
    def _create_report(self, log_files: List[Path]) -> Dict[str, Any]:
        """Create comprehensive analysis report"""
        
        # Categorize issues by severity
        critical_issues = [i for i in self.issues if i.severity == 'critical']
        high_issues = [i for i in self.issues if i.severity == 'high']
        medium_issues = [i for i in self.issues if i.severity == 'medium']
        low_issues = [i for i in self.issues if i.severity == 'low']
        
        # Overall health score (0-100)
        health_score = self._calculate_health_score()
        
        report = {
            'analysis_time': datetime.now().isoformat(),
            'log_files_analyzed': [str(f) for f in log_files],
            'health_score': health_score,
            'statistics': self.statistics,
            'issues': {
                'total': len(self.issues),
                'critical': len(critical_issues),
                'high': len(high_issues), 
                'medium': len(medium_issues),
                'low': len(low_issues)
            },
            'critical_issues': [self._issue_to_dict(i) for i in critical_issues],
            'high_issues': [self._issue_to_dict(i) for i in high_issues],
            'recommendations': self._generate_top_recommendations(),
            'summary': self._generate_summary()
        }
        
        return report
        
    def _calculate_health_score(self) -> int:
        """Calculate overall system health score"""
        if not self.issues:
            return 100
            
        # Weight issues by severity
        severity_weights = {'critical': 30, 'high': 20, 'medium': 10, 'low': 5}
        total_penalty = sum(severity_weights.get(issue.severity, 0) * issue.occurrences 
                           for issue in self.issues)
        
        # Cap at reasonable maximum penalty
        max_penalty = 100
        penalty = min(total_penalty, max_penalty)
        
        return max(0, 100 - penalty)
        
    def _issue_to_dict(self, issue: Issue) -> Dict[str, Any]:
        """Convert issue to dictionary"""
        return {
            'severity': issue.severity,
            'category': issue.category,
            'title': issue.title,
            'description': issue.description,
            'location': issue.location,
            'recommendation': issue.recommendation,
            'occurrences': issue.occurrences
        }
        
    def _generate_top_recommendations(self) -> List[str]:
        """Generate top recommendations based on issues"""
        recommendations = []
        
        # Check for common patterns
        zfs_issues = [i for i in self.issues if 'zfs' in i.category.lower()]
        dependency_issues = [i for i in self.issues if i.category == 'dependency']
        permission_issues = [i for i in self.issues if i.category == 'permission']
        
        if zfs_issues:
            recommendations.append("🔧 ZFS issues detected: Run 'sudo python3 ultrathink_zfs_prebuilder.py' to build ZFS from source")
            
        if dependency_issues:
            recommendations.append("📦 Package issues detected: Update repositories with 'sudo apt-get update'")
            
        if permission_issues:
            recommendations.append("🔐 Permission issues detected: Ensure you're running build commands with 'sudo'")
            
        # Add based on most common issues
        for issue_title, count in self.statistics.get('most_common_issues', [])[:3]:
            if count > 1:
                recommendations.append(f"⚠️  Recurring issue: {issue_title} (occurred {count} times)")
                
        return recommendations
        
    def _generate_summary(self) -> str:
        """Generate human-readable summary"""
        if not self.issues:
            return "✅ No significant issues detected in recent logs."
            
        critical_count = len([i for i in self.issues if i.severity == 'critical'])
        high_count = len([i for i in self.issues if i.severity == 'high'])
        
        if critical_count > 0:
            return f"🚨 {critical_count} critical issues require immediate attention. Build likely failed."
        elif high_count > 0:
            return f"⚠️  {high_count} high-priority issues detected. Build may have issues."
        else:
            return f"ℹ️  {len(self.issues)} minor issues detected. Build likely successful with warnings."

def main():
    """Main entry point"""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                UltraThink Log Analyzer Agent                       ║")
    print("║            Intelligent Z-FORGE Build Log Analysis                 ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Analyze Z-FORGE build logs')
    parser.add_argument('--hours', type=int, default=24, 
                       help='Analyze logs from last N hours (default: 24)')
    parser.add_argument('--output', type=str, 
                       help='Save detailed report to JSON file')
    parser.add_argument('--verbose', action='store_true',
                       help='Show verbose output')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = LogAnalyzerAgent()
    
    # Analyze logs
    print(f"🔍 Analyzing Z-FORGE logs from the last {args.hours} hours...")
    print("=" * 70)
    
    report = analyzer.analyze_logs(args.hours)
    
    # Display results
    if report.get('status') == 'no_logs_found':
        print("❌ No recent log files found")
        print(f"   Looked for logs modified in the last {args.hours} hours")
        print("   Try running a build first or increase --hours")
        return 1
        
    # Show summary
    print("📊 ANALYSIS RESULTS")
    print("=" * 70)
    print(f"Health Score: {report['health_score']}/100")
    print(f"Log Files: {len(report['log_files_analyzed'])}")
    print(f"Total Issues: {report['issues']['total']}")
    print()
    
    # Show issue breakdown
    issues = report['issues']
    if issues['critical'] > 0:
        print(f"🚨 Critical: {issues['critical']}")
    if issues['high'] > 0:
        print(f"⚠️  High: {issues['high']}")
    if issues['medium'] > 0:
        print(f"ℹ️  Medium: {issues['medium']}")
    if issues['low'] > 0:
        print(f"💡 Low: {issues['low']}")
        
    print()
    print("📋 SUMMARY")
    print("-" * 40)
    print(report['summary'])
    
    # Show top recommendations
    if report['recommendations']:
        print()
        print("🎯 TOP RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")
            
    # Show critical issues details
    if report['critical_issues']:
        print()
        print("🚨 CRITICAL ISSUES")
        print("-" * 40)
        for issue in report['critical_issues']:
            print(f"• {issue['title']}")
            print(f"  Location: {issue['location']}")
            print(f"  {issue['description']}")
            print(f"  💡 {issue['recommendation']}")
            print()
            
    # Show high priority issues
    if report['high_issues'] and args.verbose:
        print("⚠️  HIGH PRIORITY ISSUES")
        print("-" * 40)
        for issue in report['high_issues'][:3]:  # Show top 3
            print(f"• {issue['title']} (occurred {issue['occurrences']} times)")
            print(f"  💡 {issue['recommendation']}")
            print()
            
    # Save detailed report if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Detailed report saved to: {args.output}")
        
    # Statistics
    if args.verbose:
        print("\n📈 STATISTICS")
        print("-" * 40)
        stats = report['statistics']
        print(f"Total log entries: {stats['total_entries']}")
        
        print("\nBy severity:")
        for level, count in stats['by_level'].items():
            print(f"  {level}: {count}")
            
        print("\nMost active modules:")
        for module, count in list(stats['by_module'].items())[:5]:
            print(f"  {module}: {count}")
            
    return 0

if __name__ == "__main__":
    sys.exit(main())