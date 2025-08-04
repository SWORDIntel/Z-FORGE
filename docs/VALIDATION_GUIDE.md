# Z-FORGE Validation Guide

## System Validation

The Z-FORGE build system includes comprehensive validation to ensure all components are properly configured and ready for builds.

### Quick Validation Check

```bash
# Run complete system validation
python3 builder/modules/build_pipeline_validator.py

# Expected output for healthy system:
# Validation Results: ALL_CHECKS_PASSED
# Checks: 100/100 passed
# Critical: 0, Errors: 0, Warnings: 0
```

### Validation Categories

#### 1. Configuration Validation
- Build specification completeness
- Required metadata fields (name, version)
- Module configuration syntax
- Hardware profile settings

#### 2. Module Loading
- Python module imports
- Class definitions
- Method availability
- Dependency resolution

#### 3. System Dependencies
- Required packages installed
- System tools available
- File permissions correct
- Directory structure valid

#### 4. Build Pipeline
- Module execution order
- Integration points
- Error handling mechanisms
- Recovery procedures

#### 5. APT System Health
- Package manager permissions
- Repository access
- Cache directories writable
- Partial directory permissions

### Troubleshooting Validation Issues

#### Permission Errors
```bash
# Fix APT permissions
sudo chown -R _apt:nogroup /var/lib/apt/lists/partial
sudo chmod 755 /var/lib/apt/lists/partial
sudo chown -R _apt:nogroup /var/cache/apt/archives/partial
sudo chmod 755 /var/cache/apt/archives/partial
```

#### Missing Configuration Fields
```bash
# Check for missing name/version in build specs
python3 scripts/test/show_validation_warnings.py
```

#### Module Import Issues
```bash
# Verify all Python imports
python3 scripts/test/check_python_imports.py
```

### Validation History

The system has achieved perfect validation:
- **August 3, 2025**: 100/100 checks passing
- **Zero critical issues**
- **Zero errors**
- **Zero warnings**
- **All APT permissions resolved**

### Advanced Validation

#### Individual Component Testing
```bash
# Test specific modules
python3 scripts/test/check_all_module_naming.py
python3 scripts/test/check_execute_methods.py
python3 scripts/test/check_all_issues.py
```

#### Build Specification Validation
```bash
# Validate all build specs
for spec in build_spec*.yml; do
    echo "Validating $spec..."
    python3 builder/modules/build_pipeline_validator.py --spec "$spec"
done
```

## Maintenance

### Regular Health Checks
Run validation weekly or after system changes:
```bash
# Schedule validation check
echo "0 9 * * 1 cd /opt/github/Z-FORGE && python3 builder/modules/build_pipeline_validator.py" | crontab -
```

### Monitoring
- Watch for new warnings in validation output
- Monitor system dependencies
- Check APT permissions after system updates
- Verify module integrity after code changes

The validation system ensures Z-FORGE maintains production quality and reliability.