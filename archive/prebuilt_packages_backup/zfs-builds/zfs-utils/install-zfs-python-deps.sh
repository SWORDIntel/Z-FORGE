#!/bin/bash
# Install all Python 3.13 dependencies for ZFS build

set -e

echo "=== Installing Python 3.13 Dependencies for ZFS ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo"
    exit 1
fi

# Update package list
apt update

# Install Python 3.13 development packages
echo "Installing Python 3.13 packages from apt..."
apt install -y \
    python3.13 \
    python3.13-dev \
    python3.13-venv \
    python3-pip \
    python3-dev \
    python3-cffi \
    python3-cffi-backend \
    libffi-dev \
    build-essential

# Ensure pip is available for Python 3.13
echo "Setting up pip for Python 3.13..."
python3.13 -m ensurepip --upgrade || true

# Install all required Python modules
echo "Installing Python modules via pip..."
python3.13 -m pip install --upgrade --break-system-packages \
    setuptools \
    wheel \
    cffi \
    packaging \
    distlib \
    ply

# Verify installations
echo ""
echo "=== Verification ==="
echo "Python version: $(python3.13 --version)"
echo ""
echo "Checking installed modules:"
python3.13 -c "import setuptools; print(f'setuptools: {setuptools.__version__}')"
python3.13 -c "import cffi; print(f'cffi: {cffi.__version__}')"
python3.13 -c "import packaging; print(f'packaging: {packaging.__version__}')"
python3.13 -c "import distlib; print(f'distlib: {distlib.__version__}')"

echo ""
echo "All Python 3.13 dependencies installed!"
echo "You can now run: sudo /opt/scripts/build-zfs-2.3.3-from-source.sh"