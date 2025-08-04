#!/bin/bash
# Resume build using stable snapshot

echo "=== Resuming build with stable Trixie snapshot ==="

# Force snapshot usage
sudo ./scripts/force_use_snapshot.sh

# Resume the build
echo "Resuming build..."
sudo python3 build.py --spec build_spec_proxmox9.yml --resume

echo "Build complete!"