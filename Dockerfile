# Z-FORGE RAM Server Build Container
# Debian Trixie base with all dependencies pre-installed

FROM debian:trixie

# Build arguments
ARG DEBIAN_FRONTEND=noninteractive
ARG ZFORGE_VERSION=3.0

# Labels
LABEL maintainer="Z-FORGE Build System"
LABEL version="${ZFORGE_VERSION}" 
LABEL description="Z-FORGE RAM Server Build Environment - Full Proxmox VE 9 + ZFS 2.3.3"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Core build tools
    python3 python3-pip python3-venv \
    debootstrap squashfs-tools xorriso \
    git curl wget \
    # ZFS dependencies
    build-essential autoconf automake libtool gawk \
    alien fakeroot dkms \
    libblkid-dev uuid-dev libudev-dev \
    libssl-dev zlib1g-dev libaio-dev libattr1-dev \
    libelf-dev python3-dev python3-setuptools \
    python3-cffi libffi-dev python3-packaging \
    # Kernel dependencies
    linux-headers-generic \
    # Dracut (no initramfs-tools conflicts)
    dracut-core dracut \
    # Network tools
    ca-certificates apt-transport-https \
    # Proxmox dependencies
    gnupg lsb-release \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies via APT (Debian Trixie externally-managed)
RUN apt-get update && apt-get install -y \
    python3-yaml \
    python3-psutil \
    python3-jinja2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for builds
RUN useradd -m -s /bin/bash zforge && \
    usermod -aG sudo zforge && \
    echo "zforge ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up tmpfs mount point for RAM builds
RUN mkdir -p /workspace && \
    chown zforge:zforge /workspace

# Copy Z-FORGE source
COPY . /zforge/
WORKDIR /zforge
RUN chown -R zforge:zforge /zforge

# Switch to zforge user
USER zforge

# Set environment variables
ENV ZFORGE_CONTAINER=true
ENV WORKSPACE=/workspace
ENV PYTHONPATH=/zforge

# Create symbolic link for easy access
RUN ln -sf /zforge/build.py /home/zforge/build && \
    ln -sf /zforge/launch-enhanced-gui.sh /home/zforge/gui

# Default command
CMD ["/bin/bash", "-c", "echo 'Z-FORGE RAM Server Build Container v3.0'; echo 'Ready to build Full Proxmox VE 9 servers!'; /bin/bash"]

# Expose any needed ports (for GUI if applicable)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python3 /zforge/tools/build_diagnostic_tool.py --quick || exit 1

# Volume mounts
VOLUME ["/workspace", "/zforge/logs"]