# Z-FORGE Makefile for automated builds

.PHONY: all build check clean help

# Default target
all: build

# Run the full build
build: check
	@echo "Starting Z-FORGE automated build..."
	@sudo python3 scripts/build/build-auto.py

# Check build environment
check:
	@echo "Checking build environment..."
	@bash scripts/build/check_build_env.sh

# Clean build artifacts
clean:
	@echo "Cleaning build workspace..."
	@sudo rm -rf /tmp/zforge_workspace
	@sudo rm -rf /var/tmp/zforge_workspace
	@rm -f logs/*.log
	@echo "Cleanup complete"

# Install build dependencies (Debian/Ubuntu)
deps:
	@echo "Installing build dependencies..."
	@sudo apt-get update
	@sudo apt-get install -y \
		python3 python3-requests python3-yaml \
		debootstrap git curl wget \
		xorriso squashfs-tools \
		grub-common grub-pc-bin grub-efi-amd64-bin \
		build-essential autoconf automake libtool gawk \
		dkms zfsutils-linux \
		libblkid-dev uuid-dev libudev-dev libssl-dev \
		zlib1g-dev libaio-dev libattr1-dev libelf-dev

# Quick build with custom workspace
build-custom:
	@read -p "Enter workspace path [/tmp/zforge_workspace]: " ws; \
	export ZFORGE_WORKSPACE=$${ws:-/tmp/zforge_workspace}; \
	sudo -E python3 scripts/build/build-auto.py

# Build in verbose/debug mode
debug: check
	@echo "Starting Z-FORGE build in debug mode..."
	@sudo python3 scripts/build/build-auto.py --debug

# Build using the main builder script with build spec
build-spec: check
	@echo "Starting Z-FORGE build with build spec..."
	@sudo python3 builder/z-forge.py --build-spec build_spec.yml

# Resume a failed build
resume: 
	@echo "Resuming Z-FORGE build from last checkpoint..."
	@sudo python3 builder/z-forge.py --build-spec build_spec.yml --resume

# Clean and build from scratch
rebuild: clean build

# Show help
help:
	@echo "Z-FORGE Build System"
	@echo "==================="
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build       - Run the full automated build (default)"
	@echo "  build-spec  - Build using main builder with build_spec.yml"
	@echo "  resume      - Resume a failed build from last checkpoint"
	@echo "  rebuild     - Clean workspace and build from scratch"
	@echo "  check       - Check build environment"
	@echo "  clean       - Clean build artifacts and workspace"
	@echo "  deps        - Install build dependencies (Debian/Ubuntu)"
	@echo "  debug       - Build with debug output"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Environment Variables:"
	@echo "  ZFORGE_WORKSPACE - Set custom workspace location"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Run full build"
	@echo "  make rebuild            # Clean and build from scratch"
	@echo "  make resume             # Resume failed build"
	@echo "  make build-spec         # Build with specific build_spec.yml"
	@echo "  make clean && make      # Manual clean and build"
	@echo "  ZFORGE_WORKSPACE=/data/build make build"