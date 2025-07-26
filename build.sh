#!/bin/bash
# Z-FORGE Automated Build Wrapper
# Run as: sudo ./build.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}                Z-FORGE V3  AUTOMATED BUILD${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}[!] Please run as root (use sudo)${NC}"
    exit 1
fi

# Set workspace if not already set
if [ -z "$ZFORGE_WORKSPACE" ]; then
    export ZFORGE_WORKSPACE="/tmp/zforge_workspace"
    echo -e "${YELLOW}[*] Using default workspace: $ZFORGE_WORKSPACE${NC}"
fi

# Check build environment
echo -e "${BLUE}[*] Checking build environment...${NC}"
if ! bash scripts/check_build_env.sh; then
    echo -e "${RED}[!] Build environment check failed${NC}"
    exit 1
fi

# Run the build
echo -e "${GREEN}[*] Starting automated build...${NC}"
echo -e "${GREEN}[*] This will take 30-60 minutes${NC}"
echo -e "${GREEN}[*] Progress will be shown below${NC}"
echo

# Run Python build script
exec python3 build-auto.py