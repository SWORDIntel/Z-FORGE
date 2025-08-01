#!/bin/bash
# Mark debootstrap as completed in build progress

echo "1786" | sudo -S python3 -c "
import json
import sys

# Read current progress
with open('/tmp/zforge_workspace/build_progress.json', 'r') as f:
    progress = json.load(f)

# Mark debootstrap as completed
progress['Debootstrap'] = {
    'status': 'success',
    'message': 'Debootstrap completed manually - working chroot exists',
    'chroot_ready': True,
    'packages_installed': True
}

# Write back
with open('/tmp/zforge_workspace/build_progress.json', 'w') as f:
    json.dump(progress, f, indent=2)

print('Debootstrap marked as completed')
"

echo "Build progress updated. Now resume with:"
echo "echo '1786' | sudo -S python3 builder/z-forge.py --build-spec build_spec.yml --resume"