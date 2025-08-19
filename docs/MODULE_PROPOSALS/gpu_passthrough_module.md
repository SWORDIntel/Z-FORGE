# GPU Passthrough Configuration Module for Z-FORGE

## Overview
Automated GPU passthrough setup for Proxmox VE, essential for gaming VMs, AI workloads, and VDI.

## Features

### Device Detection
- **GPU Identification**: NVIDIA, AMD, Intel Arc detection
- **IOMMU Groups**: Automatic grouping analysis
- **Reset Support**: Function level reset capability check
- **Multi-GPU**: Support for multiple GPU configurations

### Configuration Steps
1. **IOMMU Enable**: BIOS/GRUB configuration
2. **Driver Blacklist**: Prevent host driver loading
3. **VFIO Binding**: Early binding for passthrough
4. **Group Isolation**: ACS override if needed
5. **VM Preparation**: PCI device ID configuration

### Automated Setup
```bash
# GRUB configuration
GRUB_CMDLINE_LINUX="intel_iommu=on iommu=pt"

# Module blacklist
blacklist nouveau
blacklist nvidia
blacklist radeon
blacklist amdgpu

# VFIO configuration
options vfio-pci ids=10de:2206,10de:1aef
```

## Advanced Features
- **SR-IOV Support**: For compatible Intel/NVIDIA GPUs
- **vGPU Setup**: NVIDIA GRID/vGPU configuration
- **Looking Glass**: Shared framebuffer setup
- **Audio Passthrough**: HDMI/DP audio routing
- **USB Controller**: Paired USB passthrough

## UI Mockup
```
┌─────────────────────────────────────────────┐
│ GPU Passthrough Configuration                │
├─────────────────────────────────────────────┤
│ Detected GPUs:                               │
│ ┌───────────────────────────────────────┐   │
│ │ [x] NVIDIA RTX 4090                   │   │
│ │     PCI: 01:00.0 | IOMMU Group: 1    │   │
│ │     [x] Include HDMI Audio (01:00.1) │   │
│ │     Reset: [✓] Supported              │   │
│ └───────────────────────────────────────┘   │
│ ┌───────────────────────────────────────┐   │
│ │ [ ] Intel UHD Graphics 770            │   │
│ │     PCI: 00:02.0 | IOMMU Group: 0    │   │
│ │     Reset: [✓] Supported              │   │
│ └───────────────────────────────────────┘   │
│                                             │
│ Configuration Options:                      │
│ [x] Enable IOMMU in bootloader             │
│ [x] Blacklist GPU drivers                  │
│ [x] Configure VFIO early binding           │
│ [ ] Enable ACS override (reduces security) │
│                                             │
│ [Generate Configuration]                    │
└─────────────────────────────────────────────┘
```

## Use Cases
- **Gaming VMs**: Windows 11 with full GPU acceleration
- **AI/ML Workloads**: CUDA/ROCm in containers
- **VDI Solutions**: GPU-accelerated virtual desktops
- **Transcoding**: Hardware video encoding/decoding