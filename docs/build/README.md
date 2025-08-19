# Build System Documentation

## Files in this directory

| File | Description | Last Updated |
|------|-------------|--------------|
| [`BUILD_READY.md`](./BUILD_READY.md) | Current build system readiness status and remaining tasks | Recent |
| [`POST_REBOOT_RESUME.md`](./POST_REBOOT_RESUME.md) | Network recovery procedures after system reboot | Jul 27 |

## Quick Reference

### Current Build Status
- **Primary Issue**: DracutConfig module failure
- **Root Cause**: Missing 90zforge-toram dracut module
- **Network**: DNS bypass fixes implemented

### Key Commands
```bash
# Resume build after fixes
sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume

# Check build environment
scripts/testing/pre-build-check.sh
```

### Related Documentation
- Main build instructions: [`../project/CLAUDE.md`](../project/CLAUDE.md)
- Hardware requirements: [`../hardware/SUPPORTED_HARDWARE.md`](../hardware/SUPPORTED_HARDWARE.md)