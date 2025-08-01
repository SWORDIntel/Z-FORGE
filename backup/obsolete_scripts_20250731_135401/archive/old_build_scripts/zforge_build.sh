#!/bin/bash
# Z-FORGE Build Wrapper Script
# Simplifies building the Z-FORGE ISO with proper configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILDER_DIR="$SCRIPT_DIR/builder"

# Default values
CONFIG_FILE=""
CLEAN_BUILD=false
VERBOSE=false
RESUME=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --clean)
            CLEAN_BUILD=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --resume)
            RESUME=true
            shift
            ;;
        --help)
            echo "Z-FORGE Build Wrapper"
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --config FILE    Use specific configuration file"
            echo "  --clean          Clean workspace before building"
            echo "  --verbose        Enable verbose output"
            echo "  --resume         Resume from last checkpoint"
            echo "  --help           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Build with default config"
            echo "  $0 --clean --verbose   # Clean build with verbose output"
            echo "  $0 --config custom.yaml # Use custom configuration"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ ERROR: This script must be run with sudo${NC}"
   echo "Please run: sudo $0"
   exit 1
fi

# Banner
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                      Z-FORGE ISO Builder                          ║"
echo "║                   ZFS-on-Root Installation Media                  ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check builder directory
if [ ! -d "$BUILDER_DIR" ]; then
    echo -e "${RED}❌ ERROR: Builder directory not found: $BUILDER_DIR${NC}"
    exit 1
fi

# Check builder script
if [ ! -f "$BUILDER_DIR/z-forge.py" ]; then
    echo -e "${RED}❌ ERROR: z-forge.py not found in $BUILDER_DIR${NC}"
    exit 1
fi

# Clean workspace if requested
if [ "$CLEAN_BUILD" = true ]; then
    echo -e "${YELLOW}🧹 Cleaning workspace...${NC}"
    rm -rf /tmp/zforge_workspace /tmp/zforge_workspace_*
    echo -e "${GREEN}✅ Workspace cleaned${NC}"
fi

# Build command
BUILD_CMD="python3 $BUILDER_DIR/z-forge.py"

# Add config file if specified
if [ -n "$CONFIG_FILE" ]; then
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}❌ ERROR: Config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    BUILD_CMD="$BUILD_CMD --config $CONFIG_FILE"
fi

# Add verbose flag
if [ "$VERBOSE" = true ]; then
    BUILD_CMD="$BUILD_CMD --verbose"
fi

# Add resume flag
if [ "$RESUME" = true ]; then
    BUILD_CMD="$BUILD_CMD --resume"
fi

# Show build configuration
echo -e "${YELLOW}Build Configuration:${NC}"
echo "  Builder: $BUILDER_DIR/z-forge.py"
if [ -n "$CONFIG_FILE" ]; then
    echo "  Config: $CONFIG_FILE"
else
    echo "  Config: Default configuration"
fi
echo "  Clean Build: $CLEAN_BUILD"
echo "  Verbose: $VERBOSE"
echo "  Resume: $RESUME"
echo ""

# Confirm build
read -p "Start build? [Y/n] " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
    echo -e "${YELLOW}Build cancelled${NC}"
    exit 0
fi

# Start build
echo -e "${GREEN}🚀 Starting Z-FORGE build...${NC}"
echo "Command: $BUILD_CMD"
echo ""

# Execute build
cd "$SCRIPT_DIR"
$BUILD_CMD

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
    
    # Look for ISO files
    ISO_FILES=$(find . -name "*.iso" -type f -mtime -1 2>/dev/null)
    if [ -n "$ISO_FILES" ]; then
        echo -e "${GREEN}📀 ISO files created:${NC}"
        echo "$ISO_FILES"
    fi
else
    echo ""
    echo -e "${RED}❌ Build failed!${NC}"
    echo "Check the logs for details"
    exit 1
fi