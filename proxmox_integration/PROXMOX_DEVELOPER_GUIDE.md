# Proxmox VE Integration Developer Guide

## Architecture Overview

The Proxmox integration adds several new modules to Z-FORGE:

```
builder/modules/
├── proxmox_repo_setup.py      # Repository configuration
├── proxmox_package_install.py  # Package installation
├── proxmox_storage_config.py   # Storage setup
├── proxmox_network_config.py   # Network configuration
├── proxmox_service_config.py   # Service setup
└── proxmox_cluster_setup.py    # Cluster preparation
```

## Module Development

### Creating a New Proxmox Module

```python
from builder.core.module import BaseModule

class ProxmoxCustomModule(BaseModule):
    """Custom Proxmox module"""
    
    def __init__(self, workspace: Path, config: Dict[str, Any]):
        super().__init__(workspace, config)
        self.proxmox_config = config.get('proxmox_config', {})
        
    def execute(self, resume_data: Optional[Dict] = None) -> Dict:
        # Implementation
        pass
```

### Integration Points

1. **Configuration**: Add to `proxmox_config` section
2. **Build sequence**: Register in `PROXMOX_MODULES`
3. **Dependencies**: Declare in module metadata

## Testing

### Unit Tests
```bash
python -m pytest tests/test_proxmox_integration.py
```

### Integration Tests
```bash
./tests/integration/test_proxmox_build.sh
```

## Contributing

1. Follow Z-FORGE coding standards
2. Add tests for new features
3. Update documentation
4. Submit PR with clear description
