# Z-FORGE Build Order Optimization

## Current Issues with Build Order

The current build order has several dependencies that are not properly sequenced:

1. **DracutConfig** runs before **ZFSBuild** - but dracut needs ZFS modules
2. **KernelAcquisition** should ensure kernel headers are installed before **ZFSBuild**
3. **ProxmoxIntegration** may need ZFS already built
4. **BootloaderSetup** and **SecurityHardening** are missing from the pipeline
5. **EncryptionSupport** is missing from the pipeline

## Optimal Build Order

### Phase 1: Base System Setup
1. **WorkspaceSetup** - Create workspace directories
2. **Debootstrap** - Bootstrap base Debian system with essential packages

### Phase 2: Kernel and Core Modules
3. **KernelAcquisition** - Install kernel and headers (required for DKMS)
4. **ZFSBuild** - Build/install ZFS (needs kernel headers)

### Phase 3: Boot Infrastructure
5. **DracutConfig** - Configure dracut (can now use ZFS modules)
6. **BootloaderSetup** - Configure bootloader with ZFS support

### Phase 4: System Integration
7. **ProxmoxIntegration** - Install Proxmox (can use ZFS storage)
8. **SecurityHardening** - Apply security configurations
9. **EncryptionSupport** - Setup encryption support

### Phase 5: Live Environment
10. **LiveEnvironment** - Setup live system
11. **CalamaresIntegration** - Configure installer
12. **ISOGeneration** - Generate final ISO

## Dependencies Matrix

| Module | Depends On | Required By |
|--------|-----------|-------------|
| WorkspaceSetup | None | All modules |
| Debootstrap | WorkspaceSetup | All subsequent modules |
| KernelAcquisition | Debootstrap | ZFSBuild, DracutConfig |
| ZFSBuild | KernelAcquisition | DracutConfig, ProxmoxIntegration |
| DracutConfig | ZFSBuild | BootloaderSetup |
| BootloaderSetup | DracutConfig | LiveEnvironment |
| ProxmoxIntegration | ZFSBuild | None |
| SecurityHardening | Debootstrap | None |
| EncryptionSupport | ZFSBuild | DracutConfig |
| LiveEnvironment | BootloaderSetup | ISOGeneration |
| CalamaresIntegration | LiveEnvironment | ISOGeneration |
| ISOGeneration | All above | None |

## Implementation Changes Needed

1. Update `build-iso.sh` to use correct module order
2. Ensure each module checks for its dependencies
3. Add module status tracking for better error handling
4. Consider parallel execution where possible (e.g., SecurityHardening can run in parallel with other modules)

## Parallel Execution Opportunities

Some modules can run in parallel after their dependencies are met:

- **Group A** (after ZFSBuild): ProxmoxIntegration, SecurityHardening, EncryptionSupport
- **Group B** (after Debootstrap): Hardware-specific optimizations

## Error Recovery

Each module should:
1. Check if its dependencies completed successfully
2. Verify required files/packages exist
3. Create a checkpoint after successful completion
4. Support resuming from checkpoint on failure