# Z-FORGE System Architecture

Comprehensive overview of the Z-FORGE build system architecture.

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Z-FORGE Build System                    │
├─────────────────────────────────────────────────────────────┤
│ User Interfaces                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ Enhanced GUI│ │ Command Line│ │ TUI Launcher│           │
│ │ + Recovery  │ │ Interface   │ │ (Legacy)    │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Core Systems                                                │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ Build Engine│ │ Diagnostic  │ │ Recovery    │           │
│ │             │ │ System      │ │ System      │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│ Build Pipeline                                              │
│ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐         │
│ │ 1 │→│ 2 │→│ 3 │→│ 4 │→│ 5 │→│ 6 │→│ 7 │→│ 8 │         │
│ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘ └───┘         │
├─────────────────────────────────────────────────────────────┤
│ Support Systems                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│ │ Validation  │ │ Monitoring  │ │ Statistics  │           │
│ │ & Testing   │ │ & Logging   │ │ & Learning  │           │
│ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🖥️ User Interface Layer

### Enhanced GUI (Primary Interface)
**File**: `zforge_gui_enhanced.py`

**Components**:
- **Main Application**: `ZForgeGUIEnhanced` class
- **Diagnostic Integration**: `BuildDiagnosticTool` integration
- **Recovery Integration**: `BuildRecoveryTool` integration
- **Thread Management**: Message queue for safe GUI updates
- **Dark Theme**: Complete UI styling system

**Key Features**:
- Real-time build monitoring
- Automatic failure recovery
- Error analysis and categorization
- Build statistics tracking
- Pre-build validation

### Command Line Interface
**File**: `build.py`

**Architecture**:
```python
class ZForgeBuildSystem:
    def __init__(self, config_path: str)
    def load_configuration(self)
    def validate_environment(self)
    def execute_build_pipeline(self)
    def cleanup_and_finalize(self)
```

### TUI Launcher (Legacy)
**File**: `zforge-launcher.sh`
- Interactive text-based menu system
- Build type selection
- Basic configuration options

## 🔧 Core Systems

### Build Engine
**Location**: `builder/core/`

**Components**:
```
builder/core/
├── builder.py          # Main build orchestrator
├── config.py           # Configuration management
├── module_loader.py    # Dynamic module loading
└── pipeline.py         # Build pipeline execution
```

**Architecture**:
```python
class BuildEngine:
    def __init__(self, workspace: Path, config: Dict)
    def load_modules(self) -> List[BuildModule]
    def execute_pipeline(self) -> BuildResult
    def handle_module_failure(self, module: str, error: Exception)
```

### Diagnostic System
**File**: `tools/build_diagnostic_tool.py`

**Class**: `BuildDiagnosticTool`

**Checks Performed**:
1. **System Requirements**: CPU, RAM, disk space
2. **Dependencies**: System tools and Python modules
3. **Workspace**: Directory permissions and space
4. **Network**: Connectivity and DNS resolution
5. **APT System**: Lock files and package integrity
6. **Kernel**: Compatibility and headers
7. **ZFS**: Build readiness and dependencies
8. **Dracut**: Installation and configuration
9. **Permissions**: File access and sudo rights
10. **Build Specs**: YAML validity and completeness

### Recovery System
**File**: `tools/build_recovery_tool.py`

**Class**: `BuildRecoveryTool`

**Recovery Methods**:
```python
recovery_methods = {
    'dpkg_error': fix_dpkg_errors,
    'apt_lock': fix_apt_locks,
    'broken_packages': fix_broken_packages,
    'zfs_install': fix_zfs_installation,
    'kernel_install': fix_kernel_installation,
    'network_error': fix_network_issues,
    'disk_space': fix_disk_space,
    'mount_error': fix_mount_issues,
    'chroot_error': fix_chroot_environment,
    'initramfs_error': fix_initramfs_generation
}
```

## 🔄 Build Pipeline

### Module Architecture
**Location**: `builder/modules/`

**Base Module Interface**:
```python
class BuildModule:
    def __init__(self, workspace: Path, config: Dict)
    def validate_prerequisites(self) -> bool
    def execute(self, resume_data: Optional[Dict] = None) -> Dict
    def cleanup(self) -> None
    def get_progress_info(self) -> Dict
```

### Pipeline Stages

#### 1. Workspace Setup
**Module**: `workspace_setup.py`
- Creates build directory structure
- Sets up chroot environment
- Configures mount points
- Validates permissions

#### 2. Debootstrap
**Module**: `debootstrap.py`
- Downloads base Debian system
- Installs core packages
- Configures locale and timezone
- Sets up package management

#### 3. Kernel Acquisition
**Module**: `kernel_acquisition.py`
- Installs Linux kernel packages
- Configures kernel modules
- Sets up build dependencies
- Handles DKMS integration

#### 4. Dracut Configuration
**Module**: `dracut_config.py`
- Removes initramfs-tools conflicts
- Installs and configures dracut
- Sets up ZFS boot support
- Generates initramfs images

#### 5. ZFS Build
**Module**: `zfs_build.py`
- Compiles ZFS kernel modules
- Installs ZFS utilities
- Configures ZFS pools
- Sets up encryption support

#### 6. Live Environment
**Module**: `live_environment.py`
- Installs desktop environment
- Configures live user
- Sets up hardware detection
- Installs applications

#### 7. ISO Generation
**Module**: `iso_generation.py`
- Creates SquashFS filesystem
- Builds bootable ISO image
- Configures bootloaders
- Adds hybrid boot support

#### 8. Validation & Cleanup
**Module**: `build_pipeline_validator.py`
- Validates build completeness
- Runs integration tests
- Cleans temporary files
- Generates build report

## 🔍 Support Systems

### Validation & Testing

#### Build Pipeline Validator
**File**: `builder/modules/build_pipeline_validator.py`
```python
class BuildPipelineValidator:
    def validate_complete_pipeline(self) -> ValidationReport
    def validate_module_configuration(self, module: str) -> bool
    def validate_system_integration(self) -> bool
    def generate_validation_report(self) -> Dict
```

#### Integration Test Suite
**File**: `tools/test_full_integration.py`
- 15 comprehensive integration tests
- Build specification validation
- Module import testing
- GUI component verification
- System compatibility checks

### Monitoring & Logging

#### Logging Architecture
```python
import logging

# Module-specific loggers
logger = logging.getLogger(f"ZForge.{module_name}")

# Log levels
logger.debug("Detailed debugging information")
logger.info("General information")  
logger.warning("Warning conditions")
logger.error("Error conditions")
logger.critical("Critical failures")
```

#### Log File Organization
```
logs/
├── zforge_build_YYYYMMDD_HHMMSS.log    # Main build logs
├── tests/
│   └── test_build_pipeline_*.log        # Test execution logs
└── modules/
    ├── kernel_acquisition_*.log         # Module-specific logs
    ├── zfs_build_*.log
    └── iso_generation_*.log
```

### Statistics & Learning

#### Build Statistics Tracking
**File**: `logs/build_statistics.json`
```json
{
  "total_attempts": 10,
  "successful_builds": 7,
  "failed_builds": 3,
  "recovered_builds": 2,
  "average_time": 2745,
  "success_by_type": {
    "outside_packages": 0.95,
    "stable": 0.85,
    "full_featured": 0.70
  }
}
```

#### Learning System
```python
class BuildLearningSystem:
    def record_build_attempt(self, spec: str, result: bool, time: int)
    def analyze_failure_patterns(self) -> List[Pattern]
    def recommend_optimal_build(self, system_info: Dict) -> str
    def update_success_rates(self)
```

## 🏗️ Build Specifications

### YAML Configuration Structure
```yaml
name: "Build Name"
version: "1.0"
description: "Build description"

builder_config:
  workspace_path: "/home/john/zforge_workspace"
  enable_cache: true
  parallel_jobs: 4
  debug_mode: false

modules:
  - name: workspace_setup
    enabled: true
    config:
      chroot_size: "10G"
      mount_devpts: true
      
  - name: debootstrap
    enabled: true
    config:
      suite: "trixie"
      mirror: "http://deb.debian.org/debian"
      
  - name: kernel_acquisition
    enabled: true
    config:
      version: "6.14.8-1"
      enable_zfs: true
      
  - name: dracut_config
    enabled: true
    config:
      compression: "zstd"
      early_microcode: true
```

### Build Type Configurations

#### Outside Packages Build (95% Success)
- Uses prebuilt ZFS packages
- Minimal compilation required
- Fastest build time
- Highest reliability

#### Stable Build (85% Success)
- Debian Bookworm base
- Conservative package versions
- Proven stability
- Good hardware support

#### Full Featured Build (70% Success)
- All modules enabled
- Complete feature set
- Longer build time
- Higher complexity

## 🔄 Error Handling & Recovery

### Error Detection Pipeline
```python
class ErrorDetectionSystem:
    def scan_build_output(self, line: str) -> Optional[Error]
    def categorize_error(self, error: Error) -> ErrorType
    def determine_recovery_strategy(self, error: Error) -> RecoveryAction
    def execute_recovery(self, action: RecoveryAction) -> bool
```

### Recovery Strategy Matrix
```python
RECOVERY_STRATEGIES = {
    'dpkg_error': [
        'configure_pending_packages',
        'fix_broken_packages', 
        'clean_package_cache',
        'update_package_lists'
    ],
    'apt_lock': [
        'check_running_processes',
        'remove_lock_files',
        'restart_apt_services'
    ],
    'disk_space': [
        'clean_apt_cache',
        'remove_old_kernels',
        'clean_build_artifacts'
    ]
}
```

## 🔐 Security Architecture

### Permission Model
- **Build requires sudo**: System-level operations
- **User workspace**: `/home/john/zforge_workspace`
- **Chroot isolation**: Contained build environment
- **GPG verification**: Package integrity (configurable)

### Security Boundaries
```
┌─────────────────────────────────────────┐
│ Host System (requires sudo)            │
│ ┌─────────────────────────────────────┐ │
│ │ Build Workspace                     │ │
│ │ ┌─────────────────────────────────┐ │ │
│ │ │ Chroot Environment              │ │ │
│ │ │ (isolated build target)        │ │ │
│ │ └─────────────────────────────────┘ │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## 📊 Performance Characteristics

### Resource Usage Patterns
```
Build Stage          CPU    Memory   Disk I/O   Time
────────────────────────────────────────────────────
Workspace Setup      Low    Low      Medium     2min
Debootstrap          Medium  Medium   High       8min
Kernel Acquisition   High   Medium   Medium     10min
Dracut Config        Low    Low      Low        2min
ZFS Build            High   High     Medium     15min
Live Environment     Medium Medium   High       8min
ISO Generation       High   Low      High       5min
```

### Scalability Factors
- **CPU cores**: Linear improvement with parallel jobs
- **Memory**: 4GB minimum, 8GB+ recommended
- **Storage**: SSD significantly faster than HDD
- **Network**: Affects package download times

## 🔄 Future Architecture Considerations

### Planned Enhancements
1. **Distributed builds** across multiple machines
2. **Container-based** build environments
3. **Cloud integration** for scalable building
4. **Plugin architecture** for custom modules
5. **REST API** for programmatic access

### Scalability Improvements
1. **Parallel module execution** where possible
2. **Build caching** for repeated builds
3. **Incremental builds** for faster iterations
4. **Resource optimization** based on system capabilities

---

This architecture provides a robust, scalable foundation for building ZFS-enabled Linux distributions with automatic failure recovery and intelligent system optimization.