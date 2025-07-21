# Z-FORGE Advanced Features Documentation

## Overview
This document describes the advanced features implemented in Z-FORGE including automated testing, configuration presets, and hardware optimization.

## Table of Contents
1. [Automated Testing Framework](#automated-testing-framework)
2. [Module Configuration Templates](#module-configuration-templates)
3. [Hardware Detection Database](#hardware-detection-database)
4. [Auto-Optimization System](#auto-optimization-system)

## Automated Testing Framework

### Overview
The testing framework ensures all Z-FORGE modules work correctly across different configurations.

### Running Tests

```bash
# Install test dependencies
./run_tests.py --install-deps

# Run all tests
./run_tests.py

# Run specific module tests
./run_tests.py --module networkconfig

# Run with coverage
./run_tests.py --coverage

# Run only unit tests
./run_tests.py --type unit
```

### Test Structure
```
tests/
├── conftest.py          # Shared fixtures
├── module_tests/        # Unit tests for each module
│   ├── test_networkconfig.py
│   ├── test_hardwarehealth.py
│   └── test_gpupassthrough.py
├── integration_tests/   # Full workflow tests
│   └── test_full_install.py
└── ci/                  # CI/CD configuration
    └── github_actions.yml
```

### Writing Tests
Example test for a new module:

```python
import pytest
from mymodule import main

class TestMyModule:
    def test_module_import(self):
        assert hasattr(main, 'run')
    
    def test_configuration(self, mock_libcalamares):
        result = main.run()
        assert result is None  # Success
```

### CI/CD Integration
The GitHub Actions workflow automatically:
- Runs tests on Python 3.9, 3.10, and 3.11
- Checks code coverage
- Performs security scanning
- Validates module descriptors

## Module Configuration Templates

### Overview
Presets provide pre-configured settings optimized for different use cases.

### Available Presets

1. **homelab** - Home virtualization servers
2. **datacenter** - Enterprise production environments
3. **development** - Developer workstations
4. **gaming** - Gaming VM hosts with GPU passthrough

### Using Presets

```bash
# List available presets
python3 builder/modules/preset_loader.py list

# Show preset details
python3 builder/modules/preset_loader.py show homelab

# Apply preset
python3 builder/modules/preset_loader.py apply homelab \
    -o /tmp/config \
    -v DNS_SERVER_1=1.1.1.1 \
    -v DOMAIN=example.com
```

### Preset Structure
```yaml
name: "Preset Display Name"
description: "What this preset is for"

modules:
  networkconfig:
    preset: "network_profile"
    interfaces:
      primary:
        type: "static"
        bridge: true
    
  hardwarehealth:
    monitoring:
      temperature: true
      smart: true
    alerts:
      cpu_temp_warning: 70

system_tweaks:
  zfs:
    arc_max_percent: 50
  kernel:
    vm_swappiness: 10

additional_packages:
  - package1
  - package2
```

### Creating Custom Presets

1. Create a YAML file in `config/module_presets/`
2. Define module configurations
3. Add system optimizations
4. Test with: `python3 builder/modules/preset_loader.py validate mypreset`

### Variable Substitution
Presets support environment variables and custom variables:

```yaml
dns:
  servers:
    - "${DNS_PRIMARY}"
    - "${DNS_SECONDARY:-8.8.8.8}"  # With default
```

## Hardware Detection Database

### Overview
Automatically detects hardware and provides optimal configurations.

### Running Hardware Detection

```bash
# Basic detection
python3 builder/modules/hardware_db.py

# Full report
python3 builder/modules/hardware_db.py --report

# JSON output
python3 builder/modules/hardware_db.py --json

# Show optimal settings
python3 builder/modules/hardware_db.py --settings
```

### Supported Hardware

#### Dell Servers
- PowerEdge R730, R740, R640
- Optimal PERC controller settings
- iDRAC integration

#### HP/HPE Servers
- ProLiant DL380 Gen10
- Smart Array configuration
- iLO management

#### Supermicro
- X11DPH-T motherboard
- IPMI configuration

#### Consumer Hardware
- AMD Ryzen 9 5950X
- Intel Core i9-13900K
- Desktop optimizations

### Hardware Profiles
Each profile includes:
- Optimal ZFS settings
- Kernel parameters
- Known issues and workarounds
- Special features
- BIOS recommendations

### Adding Hardware Profiles

```python
NEW_HARDWARE = {
    "Model Name": HardwareProfile(
        name="Display Name",
        vendor="Vendor",
        model="Model",
        type="server",  # or workstation, laptop
        optimal_settings={
            "zfs": {
                "arc_max_percent": 50,
                "l2arc_write_max": "32M"
            },
            "kernel": {
                "vm_swappiness": 10
            }
        },
        known_issues=["Issue 1", "Issue 2"],
        special_features=["Feature 1"],
        tested=True
    )
}
```

## Auto-Optimization System

### Overview
Combines hardware detection and presets to automatically optimize Z-FORGE installation.

### Using Auto-Optimizer

```bash
# Analyze system and generate config
python3 builder/modules/auto_optimizer.py

# Analyze only
python3 builder/modules/auto_optimizer.py --analyze-only

# Override preset selection
python3 builder/modules/auto_optimizer.py --preset datacenter

# Test generated configuration
python3 builder/modules/auto_optimizer.py --test
```

### Optimization Process

1. **Hardware Detection**
   - Identifies system manufacturer and model
   - Detects CPU, memory, storage, network
   - Checks for GPUs and special features

2. **Profile Matching**
   - Matches against known hardware database
   - Selects appropriate preset
   - Identifies compatibility issues

3. **Configuration Generation**
   - Creates Calamares module configs
   - Generates optimization scripts
   - Applies hardware-specific tweaks

4. **Testing**
   - Validates YAML syntax
   - Checks script syntax
   - Verifies module compatibility

### Generated Files

```
optimized_config/
├── networkconfig.conf       # Network module config
├── hardwarehealth.conf      # Monitoring config
├── hardware_overrides.yaml  # Hardware-specific settings
├── optimization_report.json # Full analysis report
└── scripts/
    ├── optimize_zfs.sh      # ZFS tuning
    ├── optimize_kernel.sh   # Kernel parameters
    └── run_all_optimizations.sh
```

### Integration with ISO Build

```bash
# Generate optimized config
python3 builder/modules/auto_optimizer.py -o /tmp/optimal

# Use in ISO build
./build-iso --config /tmp/optimal
```

## Best Practices

### Testing
1. Always run tests after module changes
2. Add tests for new features
3. Check coverage reports
4. Use CI/CD for automated testing

### Presets
1. Start with existing preset as template
2. Test on target hardware
3. Document special requirements
4. Use variables for site-specific values

### Hardware Support
1. Test on actual hardware when possible
2. Document BIOS settings required
3. Include known issues and workarounds
4. Update when new firmware releases

### Optimization
1. Measure before and after performance
2. Consider workload characteristics
3. Balance performance vs. reliability
4. Document trade-offs made

## Troubleshooting

### Test Failures
- Check Python version compatibility
- Ensure mock objects are properly configured
- Review test output for specific errors
- Run with `-v` for verbose output

### Preset Issues
- Validate YAML syntax
- Check variable substitution
- Ensure all referenced modules exist
- Test with minimal configuration first

### Hardware Detection
- Run as root for full hardware access
- Install required tools (dmidecode, lspci)
- Check system logs for errors
- Fallback to generic profile if needed

### Optimization Problems
- Review optimization report
- Check for conflicting settings
- Test scripts individually
- Monitor system after applying

## Future Enhancements

1. **Machine Learning Optimization**
   - Learn from performance metrics
   - Suggest improvements over time

2. **Cloud Integration**
   - Download latest hardware profiles
   - Share optimization results

3. **A/B Testing Framework**
   - Test different configurations
   - Measure performance impact

4. **Automated Benchmarking**
   - Run standard benchmarks
   - Compare against baseline

---
Generated: 2025-07-20
Version: 1.0