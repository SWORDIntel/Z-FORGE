# Add to builder/modules/__init__.py

# Proxmox VE Integration Modules
from .proxmox_repo_setup import ProxmoxRepoSetup
from .proxmox_package_install import ProxmoxPackageInstall
from .proxmox_storage_config import ProxmoxStorageConfig
from .proxmox_network_config import ProxmoxNetworkConfig
from .proxmox_service_config import ProxmoxServiceConfig
from .proxmox_cluster_setup import ProxmoxClusterSetup

PROXMOX_MODULES = [
    ProxmoxRepoSetup,
    ProxmoxPackageInstall,
    ProxmoxStorageConfig,
    ProxmoxNetworkConfig,
    ProxmoxServiceConfig,
    ProxmoxClusterSetup
]
