#!/usr/bin/env bash
# scripts/download_bootloaders.sh  – resilient fetcher for Z-Forge
# Requires: curl, jq, unzip, wget

set -euo pipefail
IFS=$'\n\t'

BOOTLOADERS_DIR="${BOOTLOADERS_DIR:-$HOME/Documents/GitHub/Z-FORGE/bootloaders}"
TEMP_DIR="$(mktemp -d /tmp/zforge-bootloaders.XXXXXX)"

die()  { echo "[!] $*" >&2; exit 1; }
log()  { printf '[%(%F %T)T] %s\n' -1 "$*"; }
cleanup() { rm -rf "$TEMP_DIR"; }
trap cleanup EXIT

command -v jq     >/dev/null || die "jq not found – try: sudo apt install jq"
command -v unzip  >/dev/null || die "unzip not found – try: sudo apt install unzip"

mkdir -p "$BOOTLOADERS_DIR"/{zfsbootmenu,opencore}

########################################################################
# Function: fetch_latest_asset
# Args: <github_owner/repo> <regex_to_match_asset_name> <output_path>
########################################################################
fetch_latest_asset() {
  local repo="$1" pattern="$2" out="$3"
  local url
  url=$(curl -s "https://api.github.com/repos/${repo}/releases/latest" |
        jq -r --arg re "$pattern" '
          .assets[] | select(.name|test($re)) | .browser_download_url' |
        head -n1) || die "GitHub API error for $repo"

  [[ -z "$url" ]] && die "No asset matching /$pattern/ found in latest release of $repo"
  log "→ Downloading $(basename "$url")"
  wget --progress=bar:force -O "$out" "$url"
}

#########################
# ZFSBootMenu (x86_64)  #
#########################
log "=== Fetching ZFSBootMenu EFI ==="
ZBM_EFI="$TEMP_DIR/zbm.efi"
fetch_latest_asset "zbm-dev/zfsbootmenu" 'zfsbootmenu-release.*x86_64.*\.EFI$' "$ZBM_EFI"
cp -v "$ZBM_EFI" "$BOOTLOADERS_DIR/zfsbootmenu/"

#########################
# OpenCore (release)    #
#########################
log "=== Fetching OpenCorePkg zip ==="
OC_ZIP="$TEMP_DIR/opencore.zip"
fetch_latest_asset "acidanthera/OpenCorePkg" 'OpenCore-.*-RELEASE\.zip$' "$OC_ZIP"

log "→ Extracting OpenCore"
unzip -q "$OC_ZIP" -d "$TEMP_DIR/opencore"
# The zip layout is "X64/EFI/*"
cp -r "$TEMP_DIR/opencore/X64/EFI" "$BOOTLOADERS_DIR/opencore" || \
  die "Expected X64/EFI path not found in OpenCore archive"

#########################
# Config templates      #
#########################

log "✓ All bootloaders ready"
log "    ZFSBootMenu EFI : $BOOTLOADERS_DIR/zfsbootmenu/"
log "    OpenCore EFI    : $BOOTLOADERS_DIR/opencore/"

