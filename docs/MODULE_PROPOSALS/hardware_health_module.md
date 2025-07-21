# Hardware Health Monitor Module for Z-FORGE

## Overview
Comprehensive hardware monitoring setup during installation, crucial for Dell PowerEdge servers.

## Features

### Temperature Monitoring
- **CPU Temperature**: Per-core temperature monitoring
- **Disk Temperature**: SMART-based HDD/SSD temperature
- **Ambient Temperature**: Chassis intake/exhaust sensors
- **GPU Temperature**: For systems with discrete GPUs

### Storage Health
- **SMART Monitoring**: Automated smartd configuration
- **RAID Health**: PERC controller status monitoring
- **Predictive Failure**: Early warning system
- **Disk Usage Alerts**: Capacity threshold monitoring

### Power Monitoring
- **Power Supply Status**: Redundancy and failure detection
- **Power Consumption**: Real-time wattage monitoring
- **UPS Integration**: NUT (Network UPS Tools) setup
- **Power Capping**: Dell DRAC power limit configuration

### Alert Configuration
```yaml
alerts:
  temperature:
    cpu_critical: 85°C
    disk_warning: 50°C
    disk_critical: 60°C
  
  storage:
    smart_attributes:
      - id: 5   # Reallocated sectors
        threshold: 1
      - id: 197 # Current pending sectors
        threshold: 1
    
  power:
    redundancy_loss: critical
    consumption_threshold: 80%
```

## Integration Points
- **Prometheus**: Metrics export for monitoring
- **IPMI/iDRAC**: Hardware sensor access
- **Email/SMS**: Alert notification setup
- **Grafana**: Dashboard provisioning

## UI Design
```
┌─────────────────────────────────────────────┐
│ Hardware Monitoring Configuration            │
├─────────────────────────────────────────────┤
│ Monitoring Services:                         │
│ [x] Temperature Monitoring (lm-sensors)      │
│ [x] Disk Health (smartmontools)            │
│ [x] RAID Status (megacli/perccli)          │
│ [x] Power Monitoring (IPMI)                 │
│                                             │
│ Alert Destinations:                         │
│ Email: [admin@example.com_______]           │
│ [x] Local syslog                           │
│ [ ] Remote syslog: [___________]           │
│ [ ] Pushover API:  [___________]           │
│                                             │
│ Thresholds:                                 │
│ CPU Temp Warning:   [75]°C                 │
│ CPU Temp Critical:  [85]°C                 │
│ Disk Temp Warning:  [50]°C                 │
│ Disk Space Warning: [80]%                  │
└─────────────────────────────────────────────┘
```

## Benefits
- Prevents hardware failures through early detection
- Optimizes cooling and power efficiency
- Provides historical data for capacity planning
- Reduces downtime through predictive maintenance