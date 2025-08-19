# Proxmox Integration API Reference

## Configuration Schema

```yaml
proxmox_config:
  enabled: boolean           # Enable Proxmox installation
  repository: string         # Repository type: enterprise|no-subscription|test
  hostname: string          # Node hostname
  domain: string           # Domain name
  cluster_name: string     # Cluster name (for future joining)
  storage_config:          # Storage configuration
    <name>:
      type: string       # Storage type
      path: string       # Path or pool
      content: list      # Content types
```

## Module APIs

### ProxmoxRepoSetup

```python
class ProxmoxRepoSetup:
    def execute(resume_data: Optional[Dict] = None) -> Dict:
        """
        Returns:
            {
                'status': 'success|error',
                'repositories_configured': bool,
                'repository_type': str
            }
        """
```

### ProxmoxStorageConfig

```python
class ProxmoxStorageConfig:
    def execute(resume_data: Optional[Dict] = None) -> Dict:
        """
        Returns:
            {
                'status': 'success|error',
                'storage_configured': bool,
                'storage_types': List[str]
            }
        """
```

## Build Sequence Hooks

### Pre-Proxmox Hook
Called before Proxmox modules execute:
```python
def pre_proxmox_hook(context: BuildContext) -> None:
    # Custom preparation
    pass
```

### Post-Proxmox Hook
Called after Proxmox modules complete:
```python
def post_proxmox_hook(context: BuildContext) -> None:
    # Custom finalization
    pass
```
