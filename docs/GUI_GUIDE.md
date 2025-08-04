# Z-FORGE GUI Guide

## Overview

The Z-FORGE GUI provides a user-friendly graphical interface for building custom Linux distributions. It simplifies the process of selecting build types, configuring parameters, and monitoring build progress.

## Features

### 🎯 Build Selection
- **6 validated build types** with descriptions and features
- **Visual build cards** showing specifications and capabilities
- **Automatic recommendations** based on use case

### ⚙️ Configuration Management
- **CPU core optimization** with intelligent job scaling
- **Memory management** with low-memory mode option
- **Workspace configuration** with directory browser
- **Advanced options** for debug mode and custom arguments

### 📊 System Integration
- **Real-time system status** with validation checking
- **Hardware detection** (CPU, memory, disk space)
- **Build specification validation** ensuring all configs are ready

### 🔄 Build Monitoring
- **Live build output** with real-time streaming
- **Build progress tracking** with start/stop controls
- **Output saving** and management features

## Quick Start

### Installation Requirements
```bash
# Required system packages (Debian/Ubuntu)
sudo apt install python3-tk python3-yaml python3-psutil

# Or install via pip
pip3 install pyyaml psutil
```

### Launching the GUI
```bash
# Method 1: Direct launch
python3 zforge_gui.py

# Method 2: Using launcher script (recommended)
./launch-gui.sh

# Method 3: From desktop (if installed)
# Click Z-FORGE Build System icon
```

### First Run Checklist
1. **System Status Check** - Click "System Status" tab to verify all components
2. **Build Selection** - Choose appropriate build type for your needs
3. **Configuration** - Adjust CPU cores and workspace settings
4. **Start Build** - Click "Start Build" to begin process

## Build Types Guide

### 🟢 Stable Build (Recommended for beginners)
- **Use Case**: Production systems, first-time builds
- **Base**: Debian Bookworm stable packages
- **Build Time**: 45-90 minutes
- **Features**: Conservative, proven, long-term support

### ⚡ Outside Packages Build (Fastest)
- **Use Case**: Development, testing, quick iterations
- **Base**: Prebuilt packages
- **Build Time**: 15-30 minutes
- **Features**: Minimal compilation, maximum speed

### 🔧 Full Featured Build
- **Use Case**: Complete distributions, all features needed
- **Base**: Latest packages with full ZFS integration
- **Build Time**: 90-180 minutes
- **Features**: Complete feature set, Proxmox integration

### 🏠 No /tmp Build
- **Use Case**: Systems with noexec /tmp, workspace builds
- **Base**: HOME directory workspace
- **Build Time**: 60-120 minutes
- **Features**: Avoids /tmp issues, better permissions

### 🏢 Proxmox Builds (Full & V9)
- **Use Case**: Enterprise environments, virtualization
- **Base**: Proxmox VE integration
- **Build Time**: 120-240 minutes
- **Features**: Enterprise storage, clustering, management

## Configuration Options

### Performance Settings

#### CPU Configuration
- **Parallel Jobs**: Controls `-j` flag for make operations
- **Automatic scaling**: GUI adjusts based on build type
- **Range**: 1 to available CPU cores
- **Recommendation**: 
  - Fast builds (Outside Packages): Up to 8 cores
  - Complex builds (Full Featured): 2-4 cores

#### Memory Management
- **Low Memory Mode**: Reduces parallel operations
- **Enable when**: System has <8GB RAM or other memory constraints
- **Effect**: Slower build but more stable on limited RAM

#### Storage Configuration
- **Workspace Directory**: Where build files are stored
- **Default**: `~/zforge_workspace`
- **Requirements**: 20GB+ free space
- **Tip**: Use fastest available storage (SSD preferred)

### Advanced Options

#### Debug Settings
- **Debug Mode**: Enables verbose output and detailed logging
- **Keep Temp Files**: Preserves temporary files after build
- **Use for**: Troubleshooting build issues

#### Custom Configuration
- **Additional Arguments**: Extra command-line options for build.py
- **Environment Variables**: Custom environment for build process
- **Examples**:
  ```bash
  # Additional arguments
  --no-cleanup --verbose
  
  # Environment variables
  MAKEFLAGS=-j2
  DEBIAN_FRONTEND=noninteractive
  ```

## Using the Interface

### Build Selection Tab

1. **Choose Build Type**
   - Review build cards with descriptions
   - Select radio button for desired build
   - Check features list matches your needs

2. **Review Selection**
   - Build file name shown in parentheses
   - Features list shows what's included
   - Description explains use case

3. **Start Build**
   - Click "Start Build" button
   - Confirm dialog shows selected options
   - Build begins automatically

### Configuration Tab

#### Performance Tab
1. **Set CPU Cores**
   - Use slider to adjust parallel jobs
   - GUI shows recommended values
   - Higher values = faster builds (if system supports)

2. **Configure Memory**
   - Check low memory mode if needed
   - Monitor system memory usage

3. **Set Workspace**
   - Use default or browse for custom location
   - Ensure adequate free space available

#### Advanced Tab
1. **Debug Options**
   - Enable debug mode for detailed output
   - Keep temp files for analysis

2. **Custom Settings**
   - Add extra build arguments
   - Set environment variables

### System Status Tab
- **Validation Results**: Shows system health check
- **System Information**: Hardware and software details
- **Build Specifications**: Lists available build configs
- **Refresh Button**: Updates all status information

### Build Output Tab
- **Real-time Output**: Live streaming of build progress
- **Control Buttons**: Start, stop, clear output
- **Save Output**: Export build log to file
- **Auto-scroll**: Follows build progress automatically

## Troubleshooting

### Common Issues

#### GUI Won't Start
```bash
# Check dependencies
python3 -c "import tkinter, yaml, psutil"

# Check display
echo $DISPLAY

# Run test suite
python3 test_gui.py
```

#### Build Fails to Start
1. **Check system status** in GUI
2. **Verify build spec exists** and is valid
3. **Ensure adequate disk space** (20GB+)
4. **Check permissions** on workspace directory

#### Build Errors
1. **Enable debug mode** for detailed output
2. **Check build output tab** for specific errors
3. **Run validation** from system status tab
4. **Save output** and analyze error messages

#### Performance Issues
1. **Reduce parallel jobs** if system struggles
2. **Enable low memory mode** for limited RAM
3. **Use faster storage** for workspace
4. **Close other applications** during build

### Debug Mode Usage

When troubleshooting:
1. **Enable debug mode** in Configuration → Advanced
2. **Keep temp files** for analysis
3. **Save build output** to file
4. **Check system logs** in `/var/log/`

### Getting Help

#### Built-in Help
- **System Status tab** - Shows current system state
- **Validation output** - Identifies specific issues
- **Build specifications** - Lists available options

#### Documentation
- **README.md** - Main project documentation
- **VALIDATION_GUIDE.md** - System health procedures
- **BUILD_SPECIFICATIONS.md** - Detailed build config info
- **SYSTEM_MAINTENANCE.md** - Maintenance and troubleshooting

#### Command Line Equivalent
The GUI generates commands equivalent to:
```bash
# Example: Stable build with 4 cores
export MAKEFLAGS=-j4
python3 build.py --spec build_spec_stable.yml --workspace ~/zforge_workspace
```

## Performance Tips

### Build Speed Optimization
1. **Choose appropriate build type**:
   - Outside Packages: Fastest
   - Stable: Good balance
   - Full Featured: Slowest but complete

2. **Optimize CPU usage**:
   - Fast builds: Use more cores (6-8)
   - Complex builds: Use fewer cores (2-4)
   - Monitor system load during build

3. **Storage optimization**:
   - Use SSD for workspace if available
   - Ensure 30GB+ free space
   - Avoid network drives

4. **System preparation**:
   - Close unnecessary applications
   - Disable resource-intensive services
   - Ensure stable power supply

### Memory Management
- **8GB+ RAM**: Use default settings
- **4-8GB RAM**: Enable low memory mode
- **<4GB RAM**: Use command line with custom config

### Network Optimization
- **Stable internet**: Required for package downloads
- **Local mirrors**: Configure for faster downloads
- **Proxy settings**: Set if required by network

## Advanced Usage

### Custom Build Configurations
1. **Copy existing spec**: `cp build_spec_stable.yml custom.yml`
2. **Modify configuration**: Edit YAML file
3. **Validate changes**: Run validation tool
4. **GUI will detect**: New spec automatically appears

### Batch Building
```bash
# Build multiple configurations
for spec in build_spec_stable.yml build_spec_outside_packages.yml; do
    python3 build.py --spec $spec
done
```

### Integration with Build System
The GUI integrates with the complete Z-FORGE build system:
- **Validation system**: 100% compatible
- **Build specifications**: Uses same YAML configs
- **Module system**: Full module support
- **Error handling**: Same error recovery

### Automation
```bash
# Headless operation (for automation)
export DISPLAY=:99  # Virtual display
Xvfb :99 -screen 0 1024x768x24 &
python3 zforge_gui.py &
# Control via command line or scripts
```

## Security Notes

### Safe Operation
- **GUI runs with user permissions** (not root)
- **Build process requires sudo** for system operations
- **Workspace isolation** prevents conflicts
- **No network services** exposed by GUI

### Best Practices
1. **Verify build specifications** before starting
2. **Use dedicated workspace** directory
3. **Monitor system resources** during builds
4. **Keep system updated** for security

### File Permissions
- GUI files: User readable/writable
- Build outputs: User owned
- System modifications: Require sudo (prompted)

The Z-FORGE GUI provides a safe, user-friendly way to build custom Linux distributions with full control over the build process.