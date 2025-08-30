# HPC Compilation UI Module for Calamares

## Overview

This module provides a comprehensive UI for managing extended HPC driver compilation during Z-FORGE installation. It handles 1.5-3 hour compilation sessions with real-time progress, error handling, and system monitoring.

## Features

### Real-Time Progress Display
- **Multi-phase compilation tracking**: CUDA, Intel Phi, Mellanox, Scientific libraries
- **Per-component progress bars**: Shows progress for each compilation zone
- **Time estimates**: Elapsed time, remaining time, and total estimates
- **Current file display**: Shows which file is currently being compiled
- **Compilation speed**: Files per minute metric

### Error Handling
- **Intelligent error detection**: Parses compiler output for errors/warnings
- **Recovery suggestions**: Provides solutions for common compilation issues
- **Retry mechanism**: Allows retrying failed zones
- **Fallback to prebuilt**: Can skip to prebuilt packages if compilation fails

### System Monitoring
- **CPU usage tracking**: Real-time CPU utilization
- **Memory monitoring**: RAM usage with OOM prevention
- **Temperature monitoring**: Thermal protection with automatic throttling
- **Compilation log**: Last 20 lines of output always visible

### User Controls
- **Pause/Resume**: Can pause compilation at any time
- **Skip zones**: Skip non-critical compilation zones
- **Abort compilation**: Emergency stop with cleanup
- **Parallelism control**: Adjust number of parallel compilation jobs

## Installation

### 1. Enable Module in Calamares

Edit `/etc/calamares/settings.conf`:

```yaml
sequence:
  - show:
    - welcome
    - locale
    - keyboard
    - partition
    - users
    - summary
  - exec:
    - partition
    - mount
    - unpackfs
    - hpc_compilation_ui  # Add this line
    - machineid
    - fstab
    - locale
    - keyboard
    - localecfg
    - users
    - displaymanager
    - networkcfg
    - hwclock
    - services-systemd
    - bootloader
    - umount
  - show:
    - finished
```

### 2. Configure Module

Create `/etc/calamares/modules/hpc_compilation_ui.conf`:

```yaml
# HPC Compilation Configuration
---
# Hardware detection
detect_hardware: true
hardware_types:
  - tesla_k40
  - tesla_k80
  - xeon_phi
  - mellanox
  - dell_servers

# Compilation zones (can be disabled)
compilation_zones:
  cuda:
    enabled: true
    timeout: 3600  # 1 hour
    required: false
  intel_phi:
    enabled: true
    timeout: 4800  # 1.3 hours
    required: false
  mellanox:
    enabled: true
    timeout: 1800  # 30 minutes
    required: false
  scientific:
    enabled: true
    timeout: 2400  # 40 minutes
    required: true
  python:
    enabled: true
    timeout: 2100  # 35 minutes
    required: true

# UI configuration
ui:
  show_advanced: true
  allow_skip: true
  auto_retry: true
  max_retries: 3

# System limits
limits:
  max_parallel_jobs: 0  # 0 = auto (nproc)
  max_memory_percent: 80
  max_temperature: 95  # Celsius
  
# Logging
logging:
  save_logs: true
  log_path: /var/log/calamares-hpc-compilation.log
  verbose: false
```

## Usage

### GUI Mode (Default)

The module provides a Qt5-based interface with:
- **Overview Tab**: Shows overall progress and current status
- **Details Tab**: Detailed compilation output and logs
- **System Tab**: CPU, memory, temperature monitoring
- **Control Tab**: Pause, resume, skip controls

### TUI Mode (Fallback)

For text-mode installations, an ncurses interface provides:
- Progress bars using ASCII characters
- Scrollable log viewer
- Keyboard controls (p=pause, r=resume, s=skip, q=quit)

### Automated Mode

Can run without user interaction:
```yaml
# In hpc_compilation_ui.conf
automation:
  enabled: true
  skip_on_error: true
  use_prebuilt_fallback: true
```

## Compilation Phases

### Phase 1: Hardware Detection (1-2 minutes)
- Detects Tesla K40/K80 GPUs
- Detects Intel Xeon Phi co-processors
- Detects Mellanox network cards
- Determines optimal compilation strategy

### Phase 2: CUDA Compilation (30-45 minutes)
- CUDA 11.8 toolkit installation
- NVIDIA driver 470.x compilation
- cuDNN and NCCL libraries
- CUDA samples compilation

### Phase 3: Intel Phi Compilation (45-60 minutes)
- Intel Parallel Studio XE
- MPSS (Manycore Platform Software Stack)
- MKL optimized libraries
- Knights Landing optimization

### Phase 4: Mellanox OFED (20-30 minutes)
- OFED driver compilation
- RoCE v2 configuration
- SR-IOV setup
- InfiniBand configuration

### Phase 5: Scientific Libraries (30-40 minutes)
- OpenMPI with CUDA support
- FFTW3 with AVX optimization
- OpenBLAS with threading
- ScaLAPACK for distributed computing

### Phase 6: Python HPC Stack (25-35 minutes)
- Anaconda installation
- NumPy with MKL
- CuPy for GPU
- mpi4py for parallel Python

### Phase 7: Optimization (15-20 minutes)
- Hardware-specific flags
- Library path configuration
- Environment setup
- Performance validation

## Error Handling

### Common Issues and Solutions

#### Out of Memory
**Detection**: "fatal error: out of memory" in logs
**Solution**: Reduce parallel jobs or add swap
**UI Action**: Automatically reduces -j flag and retries

#### Missing Dependencies
**Detection**: "not found" or "No such file"
**Solution**: Verify source files present
**UI Action**: Offers to skip zone or use prebuilt

#### Thermal Throttling
**Detection**: Temperature > 95°C
**Solution**: Pause compilation until cooled
**UI Action**: Auto-pause with countdown timer

#### Permission Errors
**Detection**: "Permission denied"
**Solution**: Check installer privileges
**UI Action**: Prompts for root/sudo

## Performance Considerations

### Memory Requirements
- Minimum: 16GB RAM
- Recommended: 32GB RAM
- Optimal: 64GB+ RAM

### CPU Requirements
- Minimum: 4 cores
- Recommended: 8-16 cores
- Optimal: 32+ cores

### Compilation Times (Approximate)
| Hardware | Cores | RAM | Total Time |
|----------|-------|-----|------------|
| Minimal | 4 | 16GB | 3-4 hours |
| Standard | 8 | 32GB | 2-3 hours |
| Optimal | 32 | 64GB | 1.5-2 hours |

## Monitoring and Logs

### Real-time Monitoring
- CPU usage via `/proc/stat`
- Memory via `/proc/meminfo`
- Temperature via `/sys/class/thermal/`
- Process monitoring via subprocess

### Log Files
- Main log: `/var/log/calamares-hpc-compilation.log`
- Zone logs: `/var/log/calamares-hpc-{zone}.log`
- Error log: `/var/log/calamares-hpc-errors.log`

### Debug Mode
Enable verbose logging:
```bash
CALAMARES_DEBUG=1 calamares
```

## Integration with Z-FORGE

### Build System Integration
The module integrates with Z-FORGE's build system:
- Reads hardware profile from detection phase
- Uses source files from ISO bundle
- Writes compiled binaries to target system
- Updates system configuration

### Post-Installation
After successful compilation:
- Libraries installed to `/opt/`
- Environment configured in `/etc/profile.d/`
- Kernel modules loaded via DKMS
- Services started automatically

## Troubleshooting

### Module Not Loading
1. Check module is in `/usr/lib/calamares/modules/`
2. Verify `module.desc` syntax
3. Check Calamares log for Python errors

### Compilation Hanging
1. Check system resources (CPU, RAM, temp)
2. Look for deadlocks in process tree
3. Try reducing parallel jobs

### UI Not Responding
1. Check Qt5 dependencies
2. Verify X11/Wayland running
3. Try TUI mode as fallback

## Development

### Testing the Module
```bash
# Test standalone
python3 hpc_compilation_handler.py

# Test in Calamares (debug mode)
calamares -d -c /etc/calamares
```

### Adding New Compilation Zones
1. Add zone to `compilation_zones` in handler
2. Create compilation script generator
3. Add progress parser patterns
4. Update time estimates

### Custom Hardware Support
1. Add detection in hardware profile
2. Create specific compilation scripts
3. Add to zone selection logic
4. Update documentation

## License

Part of Z-FORGE project. See main project license.

## Support

For issues related to HPC compilation UI:
- Check this README first
- Review compilation logs
- Report issues to Z-FORGE project

---

*Module Version: 1.0*  
*Compatible with: Calamares 3.2+*  
*Z-FORGE HPC System*