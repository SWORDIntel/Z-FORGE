# Z-FORGE GUI Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Z-FORGE GUI application in various environments, from development systems to production deployments.

## Pre-Deployment Validation

### System Readiness Check
```bash
# Run comprehensive validation
python3 test_gui_integration.py

# Expected output:
# 🎉 ALL INTEGRATION TESTS PASSED!
# 🚀 GUI is ready for production deployment!
```

### Requirements Verification
```bash
# Check Z-FORGE system status
python3 builder/modules/build_pipeline_validator.py

# Expected: Checks: 100/100 passed
# Status: ALL_CHECKS_PASSED
```

## Deployment Methods

### Method 1: Local Development Deployment

#### Quick Setup
```bash
# 1. Navigate to Z-FORGE directory
cd /opt/github/Z-FORGE

# 2. Verify dependencies
python3 test_gui.py

# 3. Launch GUI directly
python3 zforge_gui.py
```

#### Enhanced Setup with Launcher
```bash
# 1. Make launcher executable
chmod +x launch-gui.sh

# 2. Use launcher (includes dependency checks)
./launch-gui.sh

# 3. Create desktop shortcut (optional)
cp zforge-gui.desktop ~/Desktop/
```

### Method 2: System-Wide Installation

#### Install GUI System-Wide
```bash
# 1. Copy GUI files to system location
sudo mkdir -p /opt/zforge-gui
sudo cp zforge_gui.py /opt/zforge-gui/
sudo cp launch-gui.sh /opt/zforge-gui/
sudo cp GUI_GUIDE.md /opt/zforge-gui/

# 2. Create system launcher
sudo cat > /usr/local/bin/zforge-gui << 'EOF'
#!/bin/bash
cd /opt/github/Z-FORGE
exec python3 zforge_gui.py "$@"
EOF

sudo chmod +x /usr/local/bin/zforge-gui

# 3. Install desktop file
sudo cp zforge-gui.desktop /usr/share/applications/
sudo update-desktop-database
```

#### Usage After System Installation
```bash
# Launch from command line
zforge-gui

# Or launch from desktop environment
# Look for "Z-FORGE Build System" in applications menu
```

### Method 3: Multi-User Environment

#### Setup for Multiple Users
```bash
# 1. Create shared Z-FORGE installation
sudo mkdir -p /opt/zforge
sudo cp -r /opt/github/Z-FORGE/* /opt/zforge/
sudo chown -R root:zforge /opt/zforge
sudo chmod -R g+rx /opt/zforge

# 2. Create zforge group
sudo groupadd zforge
sudo usermod -a -G zforge $USER

# 3. Create user launcher script
cat > ~/bin/zforge-gui << 'EOF'
#!/bin/bash
cd /opt/zforge
exec python3 zforge_gui.py "$@"
EOF

chmod +x ~/bin/zforge-gui
```

### Method 4: Container Deployment

#### Docker Container Setup
```dockerfile
# Dockerfile.zforge-gui
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-tk \
    python3-yaml \
    python3-psutil \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy Z-FORGE
COPY . /opt/zforge
WORKDIR /opt/zforge

# Setup GUI
RUN chmod +x zforge_gui.py launch-gui.sh

# Create entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python3", "zforge_gui.py"]
```

```bash
# docker-entrypoint.sh
#!/bin/bash
# Start virtual display if no DISPLAY set
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:99
    Xvfb :99 -screen 0 1024x768x24 &
    sleep 2
fi

exec "$@"
```

#### Build and Run Container
```bash
# Build container
docker build -f Dockerfile.zforge-gui -t zforge-gui .

# Run with X11 forwarding (Linux)
docker run -it --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $(pwd)/workspace:/workspace \
    zforge-gui

# Run with VNC (any OS)
docker run -it --rm \
    -p 5901:5901 \
    -v $(pwd)/workspace:/workspace \
    zforge-gui-vnc
```

## Environment-Specific Deployments

### Ubuntu/Debian Systems

#### Package Installation
```bash
# Install system dependencies
sudo apt update
sudo apt install -y python3-tk python3-yaml python3-psutil

# Verify installation
python3 -c "import tkinter, yaml, psutil; print('All dependencies installed')"
```

#### Service Integration
```bash
# Create systemd user service (optional)
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/zforge-gui.service << 'EOF'
[Unit]
Description=Z-FORGE GUI Application
Requires=graphical-session.target

[Service]
Type=simple
WorkingDirectory=/opt/github/Z-FORGE
ExecStart=/usr/bin/python3 zforge_gui.py
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# Enable and start service
systemctl --user daemon-reload
systemctl --user enable zforge-gui.service
```

### CentOS/RHEL/Fedora Systems

#### Package Installation
```bash
# Install dependencies
sudo dnf install -y python3-tkinter python3-pyyaml python3-psutil

# Or for older systems
sudo yum install -y python3-tkinter python3-pyyaml python3-psutil
```

### macOS Systems

#### Dependencies via Homebrew
```bash
# Install Python and dependencies
brew install python-tk

# Install Python packages
pip3 install pyyaml psutil

# Launch GUI
python3 zforge_gui.py
```

### Windows Systems (WSL)

#### WSL GUI Setup
```bash
# Install WSL GUI support
# Windows 11: GUI support built-in
# Windows 10: Install VcXsrv or X410

# Install dependencies in WSL
sudo apt install python3-tk python3-yaml python3-psutil

# Set DISPLAY variable (Windows 10)
export DISPLAY=$(ip route list default | awk '{print $3}'):0

# Launch GUI
python3 zforge_gui.py
```

## Configuration Management

### System Configuration

#### GUI Configuration File
```yaml
# ~/.config/zforge/gui.yaml
gui_settings:
  default_build_type: "Stable Build (Recommended)"
  default_jobs: 4
  default_workspace: "~/zforge_workspace"
  auto_detect_hardware: true
  debug_mode: false
  
window_settings:
  geometry: "900x700"
  remember_position: true
  
build_settings:
  auto_save_output: true
  output_history_size: 10
  show_build_notifications: true
```

#### Environment Variables
```bash
# Add to ~/.bashrc or ~/.profile
export ZFORGE_GUI_CONFIG=~/.config/zforge/gui.yaml
export ZFORGE_WORKSPACE=~/zforge_workspace
export ZFORGE_DEBUG=false
```

### Build Configuration

#### Default Build Specifications
Ensure all build specifications are present and validated:
```bash
# Verify all specs exist and are valid
for spec in build_spec*.yml; do
    echo "Checking $spec..."
    python3 -c "
import yaml
with open('$spec') as f:
    data = yaml.safe_load(f)
    assert 'name' in data, 'Missing name field'
    assert 'version' in data, 'Missing version field'
    print('✅ $spec is valid')
"
done
```

## Security Considerations

### File Permissions
```bash
# Set secure permissions on GUI files
chmod 755 zforge_gui.py launch-gui.sh
chmod 644 *.md *.yml *.desktop

# Protect configuration files
chmod 600 ~/.config/zforge/gui.yaml

# Ensure workspace permissions
mkdir -p ~/zforge_workspace
chmod 755 ~/zforge_workspace
```

### Network Security
- GUI operates locally, no network services exposed
- Build processes may download packages (normal operation)
- Consider firewall rules for package repositories

### User Permissions
- GUI runs with user permissions (not root)
- Build processes may require sudo for system operations
- Consider using sudo timeout for security

## Performance Optimization

### System Resource Allocation

#### Memory Optimization
```bash
# For systems with limited RAM
# Enable low memory mode in GUI configuration
# Or set environment variable
export ZFORGE_LOW_MEMORY=true
```

#### CPU Optimization
```bash
# Set optimal job count based on system
# GUI auto-detects, but can be overridden
export MAKEFLAGS=-j$(nproc)
```

#### Storage Optimization
```bash
# Use fastest available storage for workspace
# Prefer SSD over HDD
# Ensure adequate space (20GB+ recommended)
ln -sf /fast/ssd/zforge_workspace ~/zforge_workspace
```

### Build Performance

#### Prebuilt Package Strategy
- Use "Outside Packages Build" for fastest builds
- Consider pre-downloading packages for offline builds
- Cache build artifacts for repeated builds

## Monitoring and Maintenance

### Health Monitoring

#### Automated Health Checks
```bash
# Create monitoring script
cat > /usr/local/bin/zforge-gui-health << 'EOF'
#!/bin/bash
cd /opt/github/Z-FORGE

# Test GUI components
python3 test_gui_integration.py > /var/log/zforge-gui-health.log 2>&1

# Check system validation
python3 builder/modules/build_pipeline_validator.py >> /var/log/zforge-gui-health.log 2>&1

# Report status
if [ $? -eq 0 ]; then
    echo "$(date): Z-FORGE GUI healthy" >> /var/log/zforge-gui-health.log
else
    echo "$(date): Z-FORGE GUI issues detected" >> /var/log/zforge-gui-health.log
fi
EOF

chmod +x /usr/local/bin/zforge-gui-health

# Schedule regular checks
echo "0 6 * * * /usr/local/bin/zforge-gui-health" | crontab -
```

### Update Procedures

#### GUI Updates
```bash
# Update GUI application
cd /opt/github/Z-FORGE
git pull origin main

# Test after update
python3 test_gui_integration.py

# Restart any running GUI instances
pkill -f zforge_gui.py
```

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Verify GUI still works after system updates
python3 test_gui.py
```

## Troubleshooting Deployment Issues

### Common Deployment Problems

#### GUI Won't Start
```bash
# Check dependencies
python3 -c "import tkinter, yaml, psutil"

# Check display
echo $DISPLAY

# Check file permissions
ls -la zforge_gui.py

# Check system validation
python3 builder/modules/build_pipeline_validator.py
```

#### Build Process Fails
```bash
# Check disk space
df -h

# Check permissions
ls -la ~/zforge_workspace

# Check system validation
python3 builder/modules/build_pipeline_validator.py

# Enable debug mode for detailed output
```

#### Performance Issues
```bash
# Check system resources
free -h
df -h
top

# Reduce parallel jobs
# Enable low memory mode
# Use faster storage
```

### Recovery Procedures

#### GUI Recovery
```bash
# Reset GUI configuration
rm -rf ~/.config/zforge/

# Clear workspace if corrupted
rm -rf ~/zforge_workspace
mkdir ~/zforge_workspace

# Reinstall dependencies
pip3 install --upgrade pyyaml psutil
```

#### System Recovery
```bash
# Reset Z-FORGE to known good state
cd /opt/github/Z-FORGE
git checkout main
git pull origin main

# Run complete validation
python3 builder/modules/build_pipeline_validator.py
```

## Production Deployment Checklist

### Pre-Deployment
- [ ] All integration tests pass (8/8)
- [ ] System validation shows 100/100
- [ ] All build specifications validated
- [ ] Dependencies installed and tested
- [ ] Documentation reviewed and current

### Deployment
- [ ] GUI files deployed to target location
- [ ] Permissions set correctly
- [ ] Launcher scripts functional
- [ ] Desktop integration working
- [ ] Configuration files in place

### Post-Deployment
- [ ] GUI launches successfully
- [ ] All build types selectable
- [ ] System status accurate
- [ ] Build process completes
- [ ] User training completed

### Validation
- [ ] Manual testing successful
- [ ] Automated tests pass
- [ ] Performance acceptable
- [ ] User feedback positive
- [ ] Documentation accessible

## Support and Maintenance

### User Support
- Provide GUI_GUIDE.md to users
- Create quick reference cards
- Set up help desk procedures
- Document common issues and solutions

### Ongoing Maintenance
- Schedule regular health checks
- Monitor system performance
- Update documentation as needed
- Collect user feedback for improvements

The Z-FORGE GUI is now ready for production deployment with comprehensive testing, documentation, and support procedures in place.