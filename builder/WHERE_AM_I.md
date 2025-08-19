# WHERE AM I - Builder Directory

## 📍 Current Location: Core Build System
**Path**: `/opt/github/Z-FORGE/builder/`

## 🎯 Directory Purpose
This directory contains the **core build system modules** that execute the actual Linux distribution building process. This is the engine that powers Z-FORGE.

## 🏗️ Build System Architecture

### **Module Directory Structure**
```
builder/
├── modules/                    # Core build modules (30+ modules)
│   ├── auto_optimizer.py      # Build optimization
│   ├── debootstrap.py         # Base system bootstrap
│   ├── kernel_acquisition*.py # Kernel handling (multiple variants)
│   ├── zfs_*.py               # ZFS integration modules (multiple)
│   ├── calamares_*.py         # Installer integration
│   ├── live_environment*.py   # Live system creation
│   └── [20+ more modules]     # Specialized build components
│
└── [configuration files]      # Module configuration and metadata
```

## 🔧 Key Build Modules

### **System Foundation**
- `debootstrap.py` - **Base system bootstrap** (Debian foundation)
- `live_environment.py` - **Live system creation** (bootable environment)
- `iso_generation.py` - **ISO building** (final image creation)

### **Kernel & Boot System**
- `kernel_acquisition_perfect.py` - **Optimal kernel handling**
- `kernel_acquisition_workaround.py` - **Fallback kernel methods**
- `opencore_enhanced.py` - **Boot system configuration**

### **ZFS Integration** (Multiple Specialized Modules)
- `zfs_build.py` - **Core ZFS building**
- `zfs_build_perfect.py` - **Optimized ZFS build**
- `zfs_encryption.py` - **ZFS encryption setup**
- `zfs_pool_config.py` - **Pool configuration**
- `zfs_compression_optimizer.py` - **Performance optimization**
- `zfsbootmenu_install.py` - **ZFS boot menu integration**

### **Installer Integration**
- `calamares_zfs_enhanced.py` - **Enhanced ZFS installer**
- `calamares_zfstargetselector.py` - **ZFS target selection**
- `calamares_install_prebuilt.py` - **Prebuilt installer packages**

### **System Optimization**
- `auto_optimizer.py` - **Automatic build optimization**
- `build_pipeline_validator.py` - **Pipeline validation**
- `integrated_build_orchestrator.py` - **Build coordination**

## 🚀 Module Execution Flow

### **Phase 1: Foundation**
1. `debootstrap.py` - Creates base Debian system
2. `live_environment.py` - Configures live boot environment
3. Package installation and configuration

### **Phase 2: Kernel & Boot**
1. `kernel_acquisition_perfect.py` - Acquires compatible kernel
2. `opencore_enhanced.py` - Configures boot system
3. Dracut initramfs generation

### **Phase 3: ZFS Integration**
1. `zfs_build_perfect.py` - Builds ZFS modules
2. `zfs_encryption.py` - Sets up encryption
3. `zfs_pool_config.py` - Optimizes pool settings
4. `zfsbootmenu_install.py` - Integrates boot menu

### **Phase 4: Installer & Finalization**
1. `calamares_zfs_enhanced.py` - Integrates installer
2. `iso_generation.py` - Creates final ISO
3. Validation and cleanup

## 📊 Module Statistics

### Module Categories
- **ZFS Modules**: 8 specialized ZFS components
- **Kernel Modules**: 4 kernel handling variants
- **Calamares Modules**: 5 installer integration modules
- **System Modules**: 10+ foundation and optimization modules

### Success Rates by Module Type
- **Foundation Modules**: 95% reliability (debootstrap, live environment)
- **ZFS Modules**: 90% reliability (with proper environment)
- **Kernel Modules**: 85% reliability (hardware dependent)
- **Installer Modules**: 95% reliability (well-tested)

## 🔧 Module Development

### **Module Structure** (Standard Pattern)
```python
class ModuleName:
    def __init__(self, config):
        self.config = config
        
    def validate_requirements(self):
        """Pre-execution validation"""
        
    def execute(self):
        """Main module execution"""
        
    def cleanup(self):
        """Post-execution cleanup"""
        
    def get_status(self):
        """Module status reporting"""
```

### **Module Integration**
- **Configuration**: Via YAML build specifications
- **Orchestration**: Through `integrated_build_orchestrator.py`
- **Validation**: Using `build_pipeline_validator.py`
- **Error Handling**: Integrated with recovery system

## 🎯 Module Customization

### **Configuration Points**
1. **Build Specifications**: `../build_specs/` control module selection
2. **Module Parameters**: Each module accepts configuration
3. **Environment Variables**: System-wide build settings
4. **Runtime Switches**: Dynamic behavior modification

### **Adding New Modules**
1. **Follow Pattern**: Use standard module structure
2. **Register**: Add to build specification files
3. **Test**: Validate with integration tests
4. **Document**: Update module reference documentation

## 🔍 Related Components

### **From Project Root**
- `../build.py` - **Main orchestrator** that loads and executes modules
- `../build_specs/` - **Configuration files** that select modules
- `../tools/` - **Diagnostic tools** that validate modules

### **Integration Points**
- `../calamares/` - **Installer components** that modules integrate with
- `../scripts/` - **Shell scripts** that modules may execute
- `../linux-6.14.5/` - **ZFS source** that ZFS modules may utilize

## 🛠️ Development Workflow

### **Module Testing**
```bash
# From project root
python3 tools/test_build_pipeline.py

# Test specific module
python3 -c "from builder.modules.zfs_build_perfect import *; test_module()"

# Integration testing
python3 tools/test_full_integration.py
```

### **Module Diagnostics**
```bash
# Validate module loading
python3 tools/build_diagnostic_tool.py

# Check module dependencies
python3 builder/modules/build_pipeline_validator.py
```

## 🎯 Agent Development Guide

### **Understanding Modules**
1. **Read**: `../docs/technical/MODULE_REFERENCE.md`
2. **Examine**: Individual module source files here
3. **Test**: Use diagnostic tools to validate
4. **Modify**: Follow standard patterns for changes

### **Build System Integration**
1. **Configuration**: Modify `../build_specs/` to include modules
2. **Orchestration**: Understanding `integrated_build_orchestrator.py`
3. **Validation**: Use `build_pipeline_validator.py`
4. **Testing**: Run full integration tests

### **ZFS Module Development**
1. **Source Access**: Use `../linux-6.14.5/zfs-build/` for development
2. **Module Pattern**: Follow existing ZFS module patterns
3. **Integration**: Test with various build specifications
4. **Performance**: Use compression and optimization modules

---
**Agent Navigation**: This is the build system core. Modules here execute the actual building process controlled by build specifications.