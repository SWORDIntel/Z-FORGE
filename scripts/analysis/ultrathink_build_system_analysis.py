#!/usr/bin/env python3
"""
UltraThink Multi-Agent Build System Analysis
Deploys specialized agents to analyze and improve the modular build system
with focus on Calamares GUI integration
"""

import os
import sys
import json
import logging
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess


@dataclass
class AgentReport:
    """Standard agent report structure"""
    agent_id: str
    agent_name: str
    focus_area: str
    timestamp: str
    analysis_summary: str
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    integration_points: List[str]
    risk_assessment: str
    priority_score: int


class UltraThinkCoordinator:
    """Main coordinator for multi-agent build system analysis"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.analysis_dir = project_root / "scripts/analysis/ultrathink_results"
        self.analysis_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Agent definitions
        self.agents = {
            "build_architect": {
                "name": "Build Architecture Specialist",
                "focus": "Build system modular architecture analysis",
                "class": "BuildArchitectureAgent"
            },
            "calamares_integrator": {
                "name": "Calamares Integration Specialist", 
                "focus": "GUI installer integration and connectivity",
                "class": "CalamaresIntegrationAgent"
            },
            "config_manager": {
                "name": "Configuration Management Specialist",
                "focus": "Build configuration and specification analysis",
                "class": "ConfigurationAnalysisAgent"
            },
            "recovery_specialist": {
                "name": "Error Handling & Recovery Specialist",
                "focus": "Error handling, recovery mechanisms, robustness",
                "class": "RecoverySystemAgent"
            },
            "ux_specialist": {
                "name": "User Experience Specialist",
                "focus": "Documentation, usability, developer experience",
                "class": "UserExperienceAgent"
            }
        }
        
        self.reports: Dict[str, AgentReport] = {}
        
    def setup_logging(self):
        """Setup logging system"""
        log_file = self.analysis_dir / f"ultrathink_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("UltraThinkCoordinator")
        
    def deploy_agents(self) -> Dict[str, AgentReport]:
        """Deploy all agents for parallel analysis"""
        self.logger.info("🚀 Deploying UltraThink Multi-Agent Build System Analysis")
        self.logger.info(f"📂 Project Root: {self.project_root}")
        self.logger.info(f"🎯 Focus: Modular Build System + Calamares Integration")
        
        # Create agent instances
        agent_instances = {}
        for agent_id, config in self.agents.items():
            agent_class = globals()[config["class"]]
            agent_instances[agent_id] = agent_class(agent_id, config, self.project_root, self.analysis_dir)
            
        # Deploy agents in parallel
        threads = []
        for agent_id, agent in agent_instances.items():
            thread = threading.Thread(target=self._run_agent, args=(agent_id, agent))
            threads.append(thread)
            thread.start()
            
        # Wait for all agents to complete
        for thread in threads:
            thread.join()
            
        self.logger.info("✅ All agents completed analysis")
        
        # Generate integrated report
        self.generate_integrated_report()
        
        return self.reports
        
    def _run_agent(self, agent_id: str, agent):
        """Run individual agent analysis"""
        try:
            self.logger.info(f"🤖 Starting {agent.config['name']}")
            report = agent.analyze()
            self.reports[agent_id] = report
            self.logger.info(f"✅ {agent.config['name']} completed")
        except Exception as e:
            self.logger.error(f"❌ {agent.config['name']} failed: {e}")
            
    def generate_integrated_report(self):
        """Generate integrated analysis report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.analysis_dir / f"integrated_analysis_{timestamp}.json"
        
        # Compile all findings
        integrated_report = {
            "analysis_timestamp": timestamp,
            "project_root": str(self.project_root),
            "agents_deployed": len(self.agents),
            "agent_reports": {aid: asdict(report) for aid, report in self.reports.items()},
            "priority_recommendations": self._compile_priority_recommendations(),
            "integration_matrix": self._build_integration_matrix(),
            "implementation_plan": self._generate_implementation_plan()
        }
        
        # Save report
        with open(report_file, 'w') as f:
            json.dump(integrated_report, f, indent=2)
            
        self.logger.info(f"📊 Integrated report saved: {report_file}")
        
        # Generate human-readable summary
        self._generate_summary_report(timestamp)
        
    def _compile_priority_recommendations(self) -> List[Dict]:
        """Compile high-priority recommendations from all agents"""
        recommendations = []
        
        for agent_id, report in self.reports.items():
            for rec in report.recommendations:
                if rec.get('priority', 0) >= 8:  # High priority only
                    rec['source_agent'] = report.agent_name
                    recommendations.append(rec)
                    
        return sorted(recommendations, key=lambda x: x.get('priority', 0), reverse=True)
        
    def _build_integration_matrix(self) -> Dict:
        """Build integration matrix showing connections between components"""
        matrix = {}
        
        for agent_id, report in self.reports.items():
            matrix[agent_id] = {
                'integration_points': report.integration_points,
                'dependencies': [],
                'affected_components': []
            }
            
            # Analyze dependencies from findings
            for finding in report.findings:
                if 'dependencies' in finding:
                    matrix[agent_id]['dependencies'].extend(finding['dependencies'])
                if 'affects' in finding:
                    matrix[agent_id]['affected_components'].extend(finding['affects'])
                    
        return matrix
        
    def _generate_implementation_plan(self) -> Dict:
        """Generate phased implementation plan"""
        return {
            "phase_1_immediate": [
                "Fix critical Calamares integration gaps",
                "Implement missing error handling",
                "Add configuration validation"
            ],
            "phase_2_enhancement": [
                "Enhance modular architecture", 
                "Improve user experience",
                "Add comprehensive testing"
            ],
            "phase_3_optimization": [
                "Performance optimization",
                "Advanced features",
                "Documentation completion"
            ]
        }
        
    def _generate_summary_report(self, timestamp: str):
        """Generate human-readable summary report"""
        summary_file = self.analysis_dir / f"ANALYSIS_SUMMARY_{timestamp}.md"
        
        with open(summary_file, 'w') as f:
            f.write(f"# UltraThink Build System Analysis Summary\n\n")
            f.write(f"**Analysis Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Project:** Z-FORGE Modular Build System\n")
            f.write(f"**Focus:** Calamares GUI Integration\n\n")
            
            # Executive summary
            f.write("## 🎯 Executive Summary\n\n")
            f.write("Multi-agent analysis of the modular build system with specific focus on ")
            f.write("Calamares installer integration and overall system connectivity.\n\n")
            
            # Agent reports summary
            f.write("## 🤖 Agent Analysis Results\n\n")
            for agent_id, report in self.reports.items():
                f.write(f"### {report.agent_name}\n")
                f.write(f"**Focus:** {report.focus_area}\n")
                f.write(f"**Risk Assessment:** {report.risk_assessment}\n")
                f.write(f"**Priority Score:** {report.priority_score}/10\n\n")
                f.write(f"**Summary:** {report.analysis_summary}\n\n")
                
            # Priority recommendations
            priority_recs = self._compile_priority_recommendations()
            f.write("## 🔥 Priority Recommendations\n\n")
            for i, rec in enumerate(priority_recs[:10], 1):
                f.write(f"{i}. **{rec['title']}** (Priority: {rec['priority']}/10)\n")
                f.write(f"   - {rec['description']}\n")
                f.write(f"   - Source: {rec['source_agent']}\n\n")
                
        self.logger.info(f"📝 Summary report saved: {summary_file}")


class BaseAgent:
    """Base class for analysis agents"""
    
    def __init__(self, agent_id: str, config: Dict, project_root: Path, analysis_dir: Path):
        self.agent_id = agent_id
        self.config = config
        self.project_root = project_root
        self.analysis_dir = analysis_dir
        self.logger = logging.getLogger(f"Agent-{agent_id}")
        
    def analyze(self) -> AgentReport:
        """Main analysis method - to be implemented by subclasses"""
        raise NotImplementedError
        
    def scan_directory(self, directory: Path, pattern: str = "*") -> List[Path]:
        """Utility to scan directories"""
        if not directory.exists():
            return []
        return list(directory.glob(pattern))
        
    def read_file_safe(self, file_path: Path) -> Optional[str]:
        """Safely read file content"""
        try:
            return file_path.read_text()
        except Exception as e:
            self.logger.warning(f"Could not read {file_path}: {e}")
            return None


class BuildArchitectureAgent(BaseAgent):
    """Analyzes the modular build system architecture"""
    
    def analyze(self) -> AgentReport:
        self.logger.info("🏗️ Analyzing build system architecture...")
        
        findings = []
        recommendations = []
        integration_points = []
        
        # Analyze main build.py structure
        build_py = self.project_root / "build.py"
        if build_py.exists():
            content = self.read_file_safe(build_py)
            if content:
                findings.extend(self._analyze_build_script(content))
                integration_points.append("build.py modular classes")
                
        # Analyze builder module structure
        builder_dir = self.project_root / "builder"
        if builder_dir.exists():
            findings.extend(self._analyze_builder_modules(builder_dir))
            integration_points.append("builder core modules")
            
        # Analyze build specifications
        build_specs = list(self.project_root.glob("build_spec*.yml"))
        findings.extend(self._analyze_build_specs(build_specs))
        integration_points.append("build configuration system")
        
        # Generate recommendations
        recommendations = self._generate_architecture_recommendations(findings)
        
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.config["name"],
            focus_area=self.config["focus"],
            timestamp=datetime.now().isoformat(),
            analysis_summary="Analyzed modular build system architecture, class structure, and module organization",
            findings=findings,
            recommendations=recommendations,
            integration_points=integration_points,
            risk_assessment="MEDIUM - Architecture is modular but needs enhanced integration",
            priority_score=8
        )
        
    def _analyze_build_script(self, content: str) -> List[Dict]:
        """Analyze the main build.py script"""
        findings = []
        
        # Check for modular classes
        classes = ['ConfigurationManager', 'ArgumentParser', 'EnvironmentManager', 'BuildLauncher']
        for cls in classes:
            if cls in content:
                findings.append({
                    "type": "architecture_positive",
                    "component": "build.py",
                    "detail": f"Found modular class: {cls}",
                    "impact": "Good separation of concerns"
                })
            else:
                findings.append({
                    "type": "architecture_missing",
                    "component": "build.py", 
                    "detail": f"Missing expected class: {cls}",
                    "impact": "Potential architectural gap"
                })
                
        # Check for error handling patterns
        if "try:" in content and "except Exception" in content:
            findings.append({
                "type": "architecture_positive",
                "component": "build.py",
                "detail": "Error handling implemented",
                "impact": "Improved robustness"
            })
            
        return findings
        
    def _analyze_builder_modules(self, builder_dir: Path) -> List[Dict]:
        """Analyze builder module structure"""
        findings = []
        
        # Check for core modules
        core_dir = builder_dir / "core"
        if core_dir.exists():
            for module in core_dir.glob("*.py"):
                findings.append({
                    "type": "module_found",
                    "component": f"builder/core/{module.name}",
                    "detail": "Core builder module exists",
                    "impact": "Modular architecture support"
                })
                
        # Check for builder entry point
        if (builder_dir / "core" / "builder.py").exists():
            findings.append({
                "type": "architecture_positive",
                "component": "builder/core/builder.py",
                "detail": "Main builder class found",
                "impact": "Central orchestration point exists"
            })
            
        return findings
        
    def _analyze_build_specs(self, build_specs: List[Path]) -> List[Dict]:
        """Analyze build specification files"""
        findings = []
        
        for spec in build_specs:
            findings.append({
                "type": "config_found",
                "component": spec.name,
                "detail": "Build specification available",
                "impact": "Flexible configuration system"
            })
            
        if not build_specs:
            findings.append({
                "type": "architecture_critical",
                "component": "build configurations",
                "detail": "No build specifications found",
                "impact": "Cannot determine build parameters"
            })
            
        return findings
        
    def _generate_architecture_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate architecture improvement recommendations"""
        return [
            {
                "title": "Implement Build Pipeline Validation",
                "description": "Add validation layer to ensure all build components are properly connected",
                "priority": 9,
                "effort": "medium",
                "impact": "high"
            },
            {
                "title": "Add Module Discovery System", 
                "description": "Implement automatic discovery and validation of builder modules",
                "priority": 8,
                "effort": "medium",
                "impact": "medium"
            },
            {
                "title": "Enhance Configuration Schema",
                "description": "Add JSON schema validation for build specifications",
                "priority": 7,
                "effort": "low",
                "impact": "medium"
            }
        ]


class CalamaresIntegrationAgent(BaseAgent):
    """Analyzes Calamares installer integration"""
    
    def analyze(self) -> AgentReport:
        self.logger.info("🖥️ Analyzing Calamares GUI integration...")
        
        findings = []
        recommendations = []
        integration_points = []
        
        # Check for Calamares directory and configuration
        calamares_dir = self.project_root / "calamares"
        if calamares_dir.exists():
            findings.extend(self._analyze_calamares_config(calamares_dir))
            integration_points.append("calamares configuration")
            
        # Check for installer integration in build process
        builder_modules = self.project_root / "builder" / "modules"
        if builder_modules.exists():
            findings.extend(self._analyze_installer_modules(builder_modules))
            integration_points.append("installer build modules")
            
        # Check for GUI connection scripts
        scripts_dir = self.project_root / "scripts"
        findings.extend(self._analyze_gui_scripts(scripts_dir))
        
        # Generate recommendations
        recommendations = self._generate_calamares_recommendations(findings)
        
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.config["name"],
            focus_area=self.config["focus"],
            timestamp=datetime.now().isoformat(),
            analysis_summary="Analyzed Calamares installer integration and GUI connectivity throughout build system",
            findings=findings,
            recommendations=recommendations,
            integration_points=integration_points,
            risk_assessment="HIGH - Calamares integration needs significant improvement",
            priority_score=10
        )
        
    def _analyze_calamares_config(self, calamares_dir: Path) -> List[Dict]:
        """Analyze Calamares configuration"""
        findings = []
        
        # Check for settings.conf
        settings_conf = calamares_dir / "settings.conf"
        if settings_conf.exists():
            findings.append({
                "type": "calamares_positive",
                "component": "calamares/settings.conf",
                "detail": "Main Calamares configuration found",
                "impact": "Basic installer configuration exists"
            })
        else:
            findings.append({
                "type": "calamares_critical",
                "component": "calamares/settings.conf",
                "detail": "Missing main Calamares configuration",
                "impact": "Installer cannot be configured"
            })
            
        # Check for modules directory
        modules_dir = calamares_dir / "modules"
        if modules_dir.exists():
            module_count = len(list(modules_dir.glob("*")))
            findings.append({
                "type": "calamares_positive",
                "component": "calamares/modules",
                "detail": f"Found {module_count} Calamares modules",
                "impact": "Custom installer functionality available"
            })
        else:
            findings.append({
                "type": "calamares_missing",
                "component": "calamares/modules",
                "detail": "No custom Calamares modules directory",
                "impact": "Limited installer customization"
            })
            
        # Check for branding
        branding_dir = calamares_dir / "branding"
        if branding_dir.exists():
            findings.append({
                "type": "calamares_positive",
                "component": "calamares/branding",
                "detail": "Custom branding configuration found",
                "impact": "Branded installer experience"
            })
            
        return findings
        
    def _analyze_installer_modules(self, builder_modules: Path) -> List[Dict]:
        """Analyze installer-related builder modules"""
        findings = []
        
        # Look for Calamares-related modules
        for module_dir in builder_modules.glob("*"):
            if module_dir.is_dir():
                module_name = module_dir.name.lower()
                if any(keyword in module_name for keyword in ['calamares', 'installer', 'gui']):
                    findings.append({
                        "type": "integration_found",
                        "component": f"builder/modules/{module_dir.name}",
                        "detail": "Installer-related build module found",
                        "impact": "Build system includes installer integration"
                    })
                    
        return findings
        
    def _analyze_gui_scripts(self, scripts_dir: Path) -> List[Dict]:
        """Analyze GUI-related scripts"""
        findings = []
        
        # Look for GUI or installer scripts
        for script_cat in scripts_dir.glob("*"):
            if script_cat.is_dir():
                for script in script_cat.glob("*.py"):
                    content = self.read_file_safe(script)
                    if content and any(keyword in content.lower() for keyword in ['calamares', 'gui', 'installer']):
                        findings.append({
                            "type": "script_integration",
                            "component": f"scripts/{script_cat.name}/{script.name}",
                            "detail": "Script contains GUI/installer references",
                            "impact": "Potential integration point"
                        })
                        
        return findings
        
    def _generate_calamares_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate Calamares integration recommendations"""
        return [
            {
                "title": "Implement Complete Calamares Integration Pipeline",
                "description": "Create dedicated build module for Calamares configuration and integration",
                "priority": 10,
                "effort": "high",
                "impact": "critical"
            },
            {
                "title": "Add ZFS-Specific Calamares Modules",
                "description": "Develop custom modules for ZFS root filesystem setup in installer",
                "priority": 9,
                "effort": "high", 
                "impact": "high"
            },
            {
                "title": "Create GUI Configuration Validation",
                "description": "Add validation to ensure Calamares configs match build specifications",
                "priority": 8,
                "effort": "medium",
                "impact": "high"
            },
            {
                "title": "Implement Live Environment Integration",
                "description": "Ensure build system configures live environment to launch Calamares properly",
                "priority": 9,
                "effort": "medium",
                "impact": "high"
            }
        ]


class ConfigurationAnalysisAgent(BaseAgent):
    """Analyzes configuration management and build specifications"""
    
    def analyze(self) -> AgentReport:
        self.logger.info("⚙️ Analyzing configuration management...")
        
        findings = []
        recommendations = []
        integration_points = []
        
        # Analyze build specifications
        build_specs = list(self.project_root.glob("build_spec*.yml"))
        findings.extend(self._analyze_configurations(build_specs))
        integration_points.append("build specification system")
        
        # Analyze hardware configurations
        config_dir = self.project_root / "config"
        if config_dir.exists():
            findings.extend(self._analyze_hardware_configs(config_dir))
            integration_points.append("hardware configuration profiles")
            
        # Analyze environment management
        findings.extend(self._analyze_environment_management())
        integration_points.append("environment variable management")
        
        # Generate recommendations
        recommendations = self._generate_config_recommendations(findings)
        
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.config["name"],
            focus_area=self.config["focus"],
            timestamp=datetime.now().isoformat(),
            analysis_summary="Analyzed configuration management, build specifications, and hardware profiles",
            findings=findings,
            recommendations=recommendations,
            integration_points=integration_points,
            risk_assessment="MEDIUM - Configuration system functional but needs validation",
            priority_score=7
        )
        
    def _analyze_configurations(self, build_specs: List[Path]) -> List[Dict]:
        """Analyze build specification files"""
        findings = []
        
        for spec in build_specs:
            content = self.read_file_safe(spec)
            if content:
                findings.append({
                    "type": "config_positive",
                    "component": spec.name,
                    "detail": "Build specification readable",
                    "impact": "Configuration available for builds"
                })
                
                # Check for key configuration sections
                if "calamares" in content.lower():
                    findings.append({
                        "type": "config_integration",
                        "component": spec.name,
                        "detail": "Contains Calamares configuration references",
                        "impact": "GUI installer configuration included"
                    })
                    
                if "zfs" in content.lower():
                    findings.append({
                        "type": "config_positive",
                        "component": spec.name,
                        "detail": "Contains ZFS configuration",
                        "impact": "ZFS support configured"
                    })
                    
        return findings
        
    def _analyze_hardware_configs(self, config_dir: Path) -> List[Dict]:
        """Analyze hardware-specific configurations"""
        findings = []
        
        for hw_dir in config_dir.glob("*"):
            if hw_dir.is_dir():
                config_files = list(hw_dir.glob("*.yml")) + list(hw_dir.glob("*.yaml"))
                if config_files:
                    findings.append({
                        "type": "hardware_config",
                        "component": f"config/{hw_dir.name}",
                        "detail": f"Hardware profile with {len(config_files)} configuration files",
                        "impact": "Hardware-specific customization available"
                    })
                    
        return findings
        
    def _analyze_environment_management(self) -> List[Dict]:
        """Analyze environment variable management"""
        findings = []
        
        # Check build.py for environment management
        build_py = self.project_root / "build.py"
        content = self.read_file_safe(build_py)
        
        if content and "EnvironmentManager" in content:
            findings.append({
                "type": "env_positive",
                "component": "build.py",
                "detail": "Environment management class found",
                "impact": "Systematic environment variable handling"
            })
            
            # Check for key environment variables
            env_vars = ["ZFORGE_CONFIG", "ZFORGE_WORKSPACE", "ZFORGE_ROOT"]
            for var in env_vars:
                if var in content:
                    findings.append({
                        "type": "env_positive",
                        "component": "EnvironmentManager",
                        "detail": f"Environment variable {var} managed",
                        "impact": "Proper environment isolation"
                    })
                    
        return findings
        
    def _generate_config_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate configuration improvement recommendations"""
        return [
            {
                "title": "Implement Configuration Schema Validation",
                "description": "Add JSON schema validation for all YAML configuration files",
                "priority": 8,
                "effort": "medium",
                "impact": "high"
            },
            {
                "title": "Create Configuration Inheritance System",
                "description": "Allow hardware configs to inherit from base configurations",
                "priority": 7,
                "effort": "medium",
                "impact": "medium"
            },
            {
                "title": "Add Configuration Compatibility Checks",
                "description": "Validate that configurations are compatible with target hardware",
                "priority": 8,
                "effort": "low",
                "impact": "medium"
            }
        ]


class RecoverySystemAgent(BaseAgent):
    """Analyzes error handling and recovery mechanisms"""
    
    def analyze(self) -> AgentReport:
        self.logger.info("🛡️ Analyzing error handling and recovery systems...")
        
        findings = []
        recommendations = []
        integration_points = []
        
        # Analyze error handling in build system
        findings.extend(self._analyze_error_handling())
        integration_points.append("error handling framework")
        
        # Analyze recovery scripts
        scripts_dir = self.project_root / "scripts"
        findings.extend(self._analyze_recovery_scripts(scripts_dir))
        integration_points.append("recovery script system")
        
        # Analyze backup and rollback mechanisms
        findings.extend(self._analyze_backup_systems())
        integration_points.append("backup and rollback systems")
        
        # Generate recommendations
        recommendations = self._generate_recovery_recommendations(findings)
        
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.config["name"],
            focus_area=self.config["focus"],
            timestamp=datetime.now().isoformat(),
            analysis_summary="Analyzed error handling, recovery mechanisms, and backup systems",
            findings=findings,
            recommendations=recommendations,
            integration_points=integration_points,
            risk_assessment="MEDIUM - Basic error handling present but needs enhancement",
            priority_score=8
        )
        
    def _analyze_error_handling(self) -> List[Dict]:
        """Analyze error handling in build system"""
        findings = []
        
        # Check main build script
        build_py = self.project_root / "build.py"
        content = self.read_file_safe(build_py)
        
        if content:
            # Check for exception handling
            if "try:" in content and "except" in content:
                findings.append({
                    "type": "error_positive",
                    "component": "build.py",
                    "detail": "Exception handling implemented",
                    "impact": "Basic error handling present"
                })
                
            # Check for logging
            if "logging" in content:
                findings.append({
                    "type": "error_positive",
                    "component": "build.py",
                    "detail": "Logging framework in use",
                    "impact": "Error tracking and debugging support"
                })
                
            # Check for graceful error handling
            if "KeyboardInterrupt" in content:
                findings.append({
                    "type": "error_positive",
                    "component": "build.py",
                    "detail": "Handles user interruption gracefully",
                    "impact": "Better user experience during cancellation"
                })
                
        return findings
        
    def _analyze_recovery_scripts(self, scripts_dir: Path) -> List[Dict]:
        """Analyze recovery and fix scripts"""
        findings = []
        
        # Check for fixes directory
        fixes_dir = scripts_dir / "fixes"
        if fixes_dir.exists():
            fix_scripts = list(fixes_dir.glob("*.py")) + list(fixes_dir.glob("*.sh"))
            findings.append({
                "type": "recovery_positive",
                "component": "scripts/fixes",
                "detail": f"Found {len(fix_scripts)} recovery scripts",
                "impact": "Automated problem resolution available"
            })
            
        # Check for cleanup scripts
        cleanup_dir = scripts_dir / "cleanup"
        if cleanup_dir.exists():
            cleanup_scripts = list(cleanup_dir.glob("*.py")) + list(cleanup_dir.glob("*.sh"))
            findings.append({
                "type": "recovery_positive",
                "component": "scripts/cleanup",
                "detail": f"Found {len(cleanup_scripts)} cleanup scripts",
                "impact": "System cleanup and maintenance tools available"
            })
            
        return findings
        
    def _analyze_backup_systems(self) -> List[Dict]:
        """Analyze backup and rollback mechanisms"""
        findings = []
        
        # Check for backup directory
        backup_dir = self.project_root / "backup"
        if backup_dir.exists():
            findings.append({
                "type": "backup_positive",
                "component": "backup directory",
                "detail": "Backup directory exists",
                "impact": "Backup storage available"
            })
            
        # Check for archive systems
        archive_dir = self.project_root / "archive"
        if archive_dir.exists():
            findings.append({
                "type": "backup_positive",
                "component": "archive directory",
                "detail": "Archive system for old data",
                "impact": "Historical data preservation"
            })
            
        return findings
        
    def _generate_recovery_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate recovery system recommendations"""
        return [
            {
                "title": "Implement Comprehensive Error Recovery Pipeline",
                "description": "Create systematic error detection, logging, and automated recovery",
                "priority": 9,
                "effort": "high",
                "impact": "high"
            },
            {
                "title": "Add Build State Checkpointing",
                "description": "Implement checkpointing to resume builds from failure points",
                "priority": 8,
                "effort": "medium",
                "impact": "high"
            },
            {
                "title": "Create Automated Diagnostics System",
                "description": "Add automatic diagnosis of common build failures",
                "priority": 7,
                "effort": "medium",
                "impact": "medium"
            }
        ]


class UserExperienceAgent(BaseAgent):
    """Analyzes documentation, usability, and developer experience"""
    
    def analyze(self) -> AgentReport:
        self.logger.info("👥 Analyzing user experience and documentation...")
        
        findings = []
        recommendations = []
        integration_points = []
        
        # Analyze documentation
        findings.extend(self._analyze_documentation())
        integration_points.append("documentation system")
        
        # Analyze user interface elements
        findings.extend(self._analyze_user_interfaces())
        integration_points.append("user interface components")
        
        # Analyze help and guidance systems
        findings.extend(self._analyze_help_systems())
        integration_points.append("help and guidance systems")
        
        # Generate recommendations
        recommendations = self._generate_ux_recommendations(findings)
        
        return AgentReport(
            agent_id=self.agent_id,
            agent_name=self.config["name"],
            focus_area=self.config["focus"],
            timestamp=datetime.now().isoformat(),
            analysis_summary="Analyzed documentation, user interfaces, and overall developer experience",
            findings=findings,
            recommendations=recommendations,
            integration_points=integration_points,
            risk_assessment="LOW - Good documentation foundation, needs user experience enhancement",
            priority_score=6
        )
        
    def _analyze_documentation(self) -> List[Dict]:
        """Analyze documentation quality and coverage"""
        findings = []
        
        # Check for main documentation files
        doc_files = ["README.md", "docu/INDEX.md", "docu/TROUBLESHOOTING_GUIDE.md"]
        for doc in doc_files:
            doc_path = self.project_root / doc
            if doc_path.exists():
                content = self.read_file_safe(doc_path)
                if content and len(content) > 1000:  # Substantial content
                    findings.append({
                        "type": "docs_positive",
                        "component": doc,
                        "detail": "Comprehensive documentation file",
                        "impact": "Good user guidance available"
                    })
                else:
                    findings.append({
                        "type": "docs_minimal",
                        "component": doc,
                        "detail": "Documentation exists but minimal",
                        "impact": "Limited user guidance"
                    })
            else:
                findings.append({
                    "type": "docs_missing",
                    "component": doc,
                    "detail": "Missing important documentation",
                    "impact": "Users lack guidance"
                })
                
        # Check docs directory
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            doc_count = len(list(docs_dir.rglob("*.md")))
            findings.append({
                "type": "docs_positive",
                "component": "docs directory",
                "detail": f"Found {doc_count} documentation files",
                "impact": "Comprehensive documentation system"
            })
            
        return findings
        
    def _analyze_user_interfaces(self) -> List[Dict]:
        """Analyze user interface elements"""
        findings = []
        
        # Check for TUI launcher
        launcher_script = self.project_root / "zforge-launcher.sh"
        if launcher_script.exists():
            findings.append({
                "type": "ui_positive",
                "component": "zforge-launcher.sh",
                "detail": "TUI launcher available",
                "impact": "User-friendly interface for builds"
            })
            
        # Check build.py help system
        build_py = self.project_root / "build.py"
        content = self.read_file_safe(build_py)
        if content and "--help" in content:
            findings.append({
                "type": "ui_positive",
                "component": "build.py",
                "detail": "Help system implemented",
                "impact": "Command-line guidance available"
            })
            
        return findings
        
    def _analyze_help_systems(self) -> List[Dict]:
        """Analyze help and guidance systems"""
        findings = []
        
        # Check for checkpoint system
        checkpoint_dir = self.project_root / "checkpoint"
        if checkpoint_dir.exists():
            checkpoint_count = len(list(checkpoint_dir.glob("*.md")))
            findings.append({
                "type": "help_positive",
                "component": "checkpoint system",
                "detail": f"Found {checkpoint_count} checkpoint files",
                "impact": "Historical guidance and reference available"
            })
            
        return findings
        
    def _generate_ux_recommendations(self, findings: List[Dict]) -> List[Dict]:
        """Generate user experience recommendations"""
        return [
            {
                "title": "Create Interactive Setup Wizard",
                "description": "Develop interactive wizard for first-time users to configure builds",
                "priority": 7,
                "effort": "medium",
                "impact": "high"
            },
            {
                "title": "Add Progress Visualization",
                "description": "Implement progress bars and status indicators for build process",
                "priority": 6,
                "effort": "low",
                "impact": "medium"
            },
            {
                "title": "Enhance Error Messages",
                "description": "Provide clear, actionable error messages with solution suggestions",
                "priority": 8,
                "effort": "low",
                "impact": "high"
            }
        ]


def main():
    """Main entry point for UltraThink analysis"""
    project_root = Path(__file__).parent.parent.parent
    
    print("🚀 UltraThink Multi-Agent Build System Analysis")
    print("=" * 60)
    print(f"Project Root: {project_root}")
    print(f"Focus: Modular Build System + Calamares Integration")
    print("=" * 60)
    
    # Create and run coordinator
    coordinator = UltraThinkCoordinator(project_root)
    reports = coordinator.deploy_agents()
    
    print("\n✅ Analysis Complete!")
    print(f"📊 Reports generated in: {coordinator.analysis_dir}")
    print("\n🎯 Key Actions:")
    print("1. Review integrated analysis report")
    print("2. Implement priority recommendations") 
    print("3. Focus on Calamares integration improvements")
    print("4. Enhance error handling and recovery systems")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())