#!/bin/bash
# Convenience wrapper for downloading ZFS 2.3.4 to current directory
# No sudo required - downloads to current working directory

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the actual download script
exec "${SCRIPT_DIR}/scripts/download/download_zfs_2_3_4.sh" "$@"