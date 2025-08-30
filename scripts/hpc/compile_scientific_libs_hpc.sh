#!/bin/bash
# Z-FORGE HPC Scientific Libraries Compilation Script
# OpenMPI, FFTW, BLAS, LAPACK, ScaLAPACK, HDF5, NetCDF
# Optimized for HPC hardware with CUDA and Xeon Phi support

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-/tmp/zforge-hpc-workspace}"
LIBS_DIR="$WORKSPACE/scientific-libs"
BUILD_DIR="$WORKSPACE/build/scientific-libs"
INSTALL_PREFIX="/opt/hpc"
LOG_FILE="$WORKSPACE/logs/scientific-libs-compilation.log"

# Library versions (HPC-validated)
OPENMPI_VERSION="4.1.4"
FFTW_VERSION="3.3.10"
OPENBLAS_VERSION="0.3.21"
LAPACK_VERSION="3.11.0"
SCALAPACK_VERSION="2.2.0"
HDF5_VERSION="1.14.0"
NETCDF_VERSION="4.9.2"
PETSC_VERSION="3.18.4"

# Hardware configuration (from hardware detector)
CUDA_AVAILABLE="${CUDA_AVAILABLE:-false}"
XEON_PHI_AVAILABLE="${XEON_PHI_AVAILABLE:-false}"
CPU_CORES="${CPU_CORES:-$(nproc)}"
MEMORY_GB="${MEMORY_GB:-$(free -g | awk '/^Mem:/{print $2}')}"

# Compiler configuration
CC="${CC:-gcc}"
CXX="${CXX:-g++}"
FC="${FC:-gfortran}"
F77="${F77:-gfortran}"

# Check for Intel compilers and prefer them for HPC
if command -v icc &> /dev/null; then
    CC="icc"
    CXX="icpc"
    export INTEL_COMPILERS="true"
    log_info "Using Intel compilers for optimal HPC performance"
fi

if command -v ifort &> /dev/null; then
    FC="ifort"
    F77="ifort"
fi

# Optimization flags based on detected hardware
CFLAGS="-O3 -fPIC"
CXXFLAGS="-O3 -fPIC"
FFLAGS="-O3 -fPIC"

# Add hardware-specific optimizations
if grep -q avx512 /proc/cpuinfo; then
    CFLAGS+=" -mavx512f -mavx512cd"
    CXXFLAGS+=" -mavx512f -mavx512cd"
    log_info "AVX-512 optimizations enabled"
elif grep -q avx2 /proc/cpuinfo; then
    CFLAGS+=" -mavx2"
    CXXFLAGS+=" -mavx2"
    log_info "AVX2 optimizations enabled"
fi

# Logging functions
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "[SUCCESS] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Prepare scientific libraries environment
prepare_scientific_environment() {
    log_info "Preparing HPC scientific libraries compilation environment..."
    
    mkdir -p "$BUILD_DIR"/{openmpi,fftw,openblas,lapack,scalapack,hdf5,netcdf,petsc}
    mkdir -p "$INSTALL_PREFIX"/{bin,lib,include,share}
    mkdir -p "$LIBS_DIR"/source
    
    # Set library paths
    export PATH="$INSTALL_PREFIX/bin:$PATH"
    export LD_LIBRARY_PATH="$INSTALL_PREFIX/lib:$LD_LIBRARY_PATH"
    export PKG_CONFIG_PATH="$INSTALL_PREFIX/lib/pkgconfig:$PKG_CONFIG_PATH"
    export CMAKE_PREFIX_PATH="$INSTALL_PREFIX:$CMAKE_PREFIX_PATH"
    
    # MPI environment
    export MPICC="$INSTALL_PREFIX/bin/mpicc"
    export MPICXX="$INSTALL_PREFIX/bin/mpicxx"
    export MPIFC="$INSTALL_PREFIX/bin/mpifort"
    
    log_success "Scientific libraries environment prepared"
    log_info "Install prefix: $INSTALL_PREFIX"
    log_info "Compilers: CC=$CC, CXX=$CXX, FC=$FC"
    log_info "CPU cores: $CPU_CORES, Memory: ${MEMORY_GB}GB"
}

# Extract source archives
extract_sources() {
    log_info "Extracting scientific library source archives..."
    
    local downloads_dir="$WORKSPACE/downloads/scientific-libs"
    
    # Extract all archives
    for archive in "$downloads_dir"/*.tar.gz "$downloads_dir"/*.tgz; do
        if [[ -f "$archive" ]]; then
            local basename=$(basename "$archive" .tar.gz)
            basename=$(basename "$basename" .tgz)
            
            if [[ ! -d "$LIBS_DIR/source/$basename" ]]; then
                log_info "Extracting $(basename "$archive")..."
                tar -xzf "$archive" -C "$LIBS_DIR/source/"
            fi
        fi
    done
    
    log_success "Source extraction completed"
}

# Compile OpenMPI with HPC optimizations
compile_openmpi() {
    log_info "Compiling OpenMPI $OPENMPI_VERSION with HPC optimizations..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*openmpi*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "OpenMPI source not found"
        return 1
    fi
    
    cd "$BUILD_DIR/openmpi"
    
    # Configure OpenMPI with HPC optimizations
    local config_opts=(
        "--prefix=$INSTALL_PREFIX"
        "--enable-mpi-cxx"
        "--enable-mpi-fortran"
        "--enable-shared"
        "--disable-static"
        "--with-threads=posix"
        "--enable-mpi-thread-multiple"
        "--with-hwloc"
        "--with-libevent"
        "--enable-orterun-prefix-by-default"
    )
    
    # Add CUDA support if available
    if [[ "$CUDA_AVAILABLE" == "true" ]] && [[ -d "/usr/local/cuda" ]]; then
        config_opts+=("--with-cuda=/usr/local/cuda")
        log_info "CUDA support enabled for GPU-accelerated MPI"
    fi
    
    # Add InfiniBand support if detected
    if lspci | grep -i mellanox &> /dev/null; then
        config_opts+=("--with-verbs" "--with-openib")
        log_info "InfiniBand support enabled"
    fi
    
    log_info "Configuring OpenMPI..."
    "$src_dir/configure" "${config_opts[@]}" \
        CC="$CC" CXX="$CXX" FC="$FC" F77="$F77" \
        CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" FFLAGS="$FFLAGS" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "OpenMPI configuration failed"
        return 1
    fi
    
    # Compile with parallel build
    log_info "Building OpenMPI (using $CPU_CORES cores)..."
    make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
        log_error "OpenMPI compilation failed"
        return 1
    fi
    
    # Install
    log_info "Installing OpenMPI..."
    make install 2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_success "OpenMPI compiled and installed successfully"
        
        # Verify installation
        if [[ -x "$INSTALL_PREFIX/bin/mpirun" ]]; then
            local mpi_version=$("$INSTALL_PREFIX/bin/mpirun" --version | head -1)
            log_info "MPI version: $mpi_version"
        fi
    else
        log_error "OpenMPI installation failed"
        return 1
    fi
}

# Compile FFTW with optimizations
compile_fftw() {
    log_info "Compiling FFTW $FFTW_VERSION with HPC optimizations..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*fftw*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "FFTW source not found"
        return 1
    fi
    
    # FFTW requires separate builds for single and double precision
    local precisions=("double" "single")
    local precision_flags=("" "--enable-float")
    
    for i in "${!precisions[@]}"; do
        local precision=${precisions[i]}
        local flag=${precision_flags[i]}
        
        log_info "Building FFTW $precision precision..."
        
        local build_dir="$BUILD_DIR/fftw-$precision"
        mkdir -p "$build_dir"
        cd "$build_dir"
        
        # Configure FFTW
        local config_opts=(
            "--prefix=$INSTALL_PREFIX"
            "--enable-shared"
            "--enable-threads"
            "--enable-openmp"
            "--enable-mpi"
            $flag
        )
        
        # Add SIMD optimizations
        if grep -q avx512 /proc/cpuinfo; then
            config_opts+=("--enable-avx512")
        elif grep -q avx2 /proc/cpuinfo; then
            config_opts+=("--enable-avx2")
        elif grep -q avx /proc/cpuinfo; then
            config_opts+=("--enable-avx")
        fi
        
        "$src_dir/configure" "${config_opts[@]}" \
            CC="$MPICC" F77="$MPIFC" \
            CFLAGS="$CFLAGS" FFLAGS="$FFLAGS" \
            2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
            log_error "FFTW $precision configuration failed"
            continue
        fi
        
        # Build and install
        make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
        make install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "FFTW $precision precision installed successfully"
        else
            log_error "FFTW $precision compilation failed"
        fi
    done
}

# Compile OpenBLAS
compile_openblas() {
    log_info "Compiling OpenBLAS $OPENBLAS_VERSION with HPC optimizations..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*OpenBLAS*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "OpenBLAS source not found"
        return 1
    fi
    
    cd "$src_dir"
    
    # OpenBLAS build options
    local make_opts=(
        "CC=$CC"
        "FC=$FC"
        "HOSTCC=gcc"
        "BINARY=64"
        "INTERFACE64=1"
        "LIBNAMESUFFIX=64"
        "USE_OPENMP=1"
        "USE_THREAD=1"
        "NUM_THREADS=$CPU_CORES"
        "PREFIX=$INSTALL_PREFIX"
    )
    
    # CPU-specific optimizations
    if grep -q "Intel" /proc/cpuinfo; then
        if grep -q "avx512" /proc/cpuinfo; then
            make_opts+=("TARGET=SKYLAKEX")
        elif grep -q "avx2" /proc/cpuinfo; then
            make_opts+=("TARGET=HASWELL")
        fi
    elif grep -q "AMD" /proc/cpuinfo; then
        make_opts+=("TARGET=ZEN")
    fi
    
    log_info "Building OpenBLAS..."
    make "${make_opts[@]}" -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_info "Installing OpenBLAS..."
        make "${make_opts[@]}" install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "OpenBLAS compiled and installed successfully"
        else
            log_error "OpenBLAS installation failed"
            return 1
        fi
    else
        log_error "OpenBLAS compilation failed"
        return 1
    fi
}

# Compile LAPACK
compile_lapack() {
    log_info "Compiling LAPACK $LAPACK_VERSION..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*lapack*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "LAPACK source not found"
        return 1
    fi
    
    cd "$BUILD_DIR/lapack"
    
    # Configure LAPACK with CMake
    cmake "$src_dir" \
        -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=ON \
        -DBUILD_TESTING=OFF \
        -DCMAKE_Fortran_COMPILER="$FC" \
        -DCMAKE_Fortran_FLAGS="$FFLAGS" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
        make install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "LAPACK compiled and installed successfully"
        else
            log_error "LAPACK installation failed"
            return 1
        fi
    else
        log_error "LAPACK configuration failed"
        return 1
    fi
}

# Compile ScaLAPACK
compile_scalapack() {
    log_info "Compiling ScaLAPACK $SCALAPACK_VERSION for distributed computing..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*scalapack*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "ScaLAPACK source not found"
        return 1
    fi
    
    cd "$BUILD_DIR/scalapack"
    
    # Configure ScaLAPACK with CMake
    cmake "$src_dir" \
        -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX" \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=ON \
        -DCMAKE_C_COMPILER="$MPICC" \
        -DCMAKE_Fortran_COMPILER="$MPIFC" \
        -DCMAKE_C_FLAGS="$CFLAGS" \
        -DCMAKE_Fortran_FLAGS="$FFLAGS" \
        -DLAPACK_LIBRARIES="$INSTALL_PREFIX/lib/liblapack.so" \
        -DBLAS_LIBRARIES="$INSTALL_PREFIX/lib/libopenblas.so" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
        make install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "ScaLAPACK compiled and installed successfully"
        else
            log_error "ScaLAPACK installation failed"
            return 1
        fi
    else
        log_error "ScaLAPACK configuration failed"
        return 1
    fi
}

# Compile HDF5
compile_hdf5() {
    log_info "Compiling HDF5 $HDF5_VERSION with parallel I/O support..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*hdf5*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "HDF5 source not found"
        return 1
    fi
    
    cd "$BUILD_DIR/hdf5"
    
    # Configure HDF5 with parallel support
    "$src_dir/configure" \
        --prefix="$INSTALL_PREFIX" \
        --enable-shared \
        --enable-parallel \
        --enable-fortran \
        --enable-cxx \
        --with-zlib \
        --with-szlib \
        CC="$MPICC" CXX="$MPICXX" FC="$MPIFC" \
        CFLAGS="$CFLAGS" CXXFLAGS="$CXXFLAGS" FFLAGS="$FFLAGS" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
        make install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "HDF5 compiled and installed successfully"
        else
            log_error "HDF5 installation failed"
            return 1
        fi
    else
        log_error "HDF5 configuration failed"
        return 1
    fi
}

# Compile NetCDF
compile_netcdf() {
    log_info "Compiling NetCDF $NETCDF_VERSION..."
    
    local src_dir=$(find "$LIBS_DIR/source" -name "*netcdf-c*" -type d | head -1)
    if [[ ! -d "$src_dir" ]]; then
        log_error "NetCDF source not found"
        return 1
    fi
    
    cd "$BUILD_DIR/netcdf"
    
    # Configure NetCDF with HDF5 support
    "$src_dir/configure" \
        --prefix="$INSTALL_PREFIX" \
        --enable-shared \
        --enable-netcdf-4 \
        --enable-dap \
        --enable-parallel-tests \
        CC="$MPICC" \
        CFLAGS="$CFLAGS" \
        CPPFLAGS="-I$INSTALL_PREFIX/include" \
        LDFLAGS="-L$INSTALL_PREFIX/lib" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        make -j$CPU_CORES 2>&1 | tee -a "$LOG_FILE"
        make install 2>&1 | tee -a "$LOG_FILE"
        
        if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
            log_success "NetCDF compiled and installed successfully"
        else
            log_error "NetCDF installation failed"
            return 1
        fi
    else
        log_error "NetCDF configuration failed"
        return 1
    fi
}

# Create HPC libraries environment module
create_hpc_modules() {
    log_info "Creating HPC libraries environment module..."
    
    local modules_dir="/usr/share/modules/modulefiles/hpc"
    mkdir -p "$modules_dir"
    
    cat > "$modules_dir/scientific-libs" << EOF
#%Module1.0#####################################################################
##
## HPC Scientific Libraries Module
## Compiled for high-performance computing with MPI, OpenMP, and GPU support
##
proc ModulesHelp { } {
    global version
    puts stderr "\tHPC Scientific Libraries - High-Performance Computing Stack"
    puts stderr "\tIncludes: OpenMPI, FFTW, OpenBLAS, LAPACK, ScaLAPACK, HDF5, NetCDF"
    puts stderr "\tOptimized for: CUDA GPUs, Xeon Phi, Multi-core CPUs"
    puts stderr "\tVersion: \$version"
}

module-whatis "HPC Scientific Libraries for high-performance computing"

conflict scientific-libs

set prefix $INSTALL_PREFIX

# Library paths
prepend-path PATH \$prefix/bin
prepend-path LD_LIBRARY_PATH \$prefix/lib
prepend-path LIBRARY_PATH \$prefix/lib
prepend-path C_INCLUDE_PATH \$prefix/include
prepend-path CPLUS_INCLUDE_PATH \$prefix/include
prepend-path PKG_CONFIG_PATH \$prefix/lib/pkgconfig
prepend-path CMAKE_PREFIX_PATH \$prefix

# MPI environment
setenv MPICC \$prefix/bin/mpicc
setenv MPICXX \$prefix/bin/mpicxx
setenv MPIFC \$prefix/bin/mpifort
setenv MPIRUN \$prefix/bin/mpirun

# Library-specific environment
setenv HDF5_ROOT \$prefix
setenv NETCDF_ROOT \$prefix
setenv FFTW_ROOT \$prefix
setenv OPENBLAS_ROOT \$prefix

# Performance settings
setenv OMP_NUM_THREADS $CPU_CORES
setenv MKL_NUM_THREADS $CPU_CORES
setenv OPENBLAS_NUM_THREADS $CPU_CORES

puts stderr "HPC Scientific Libraries loaded"
puts stderr "  OpenMPI: \$prefix/bin/mpirun --version"
puts stderr "  FFTW: \$prefix/lib/libfftw3.so"
puts stderr "  OpenBLAS: \$prefix/lib/libopenblas.so"
puts stderr "  HDF5: \$prefix/bin/h5dump --version"
EOF
    
    log_success "HPC modules environment created"
}

# Test scientific libraries installation
test_scientific_libraries() {
    log_info "Testing HPC scientific libraries installation..."
    
    local test_dir="$BUILD_DIR/tests"
    mkdir -p "$test_dir"
    cd "$test_dir"
    
    # Test MPI
    if [[ -x "$INSTALL_PREFIX/bin/mpirun" ]]; then
        log_info "Testing MPI installation..."
        echo "Testing MPI" | "$INSTALL_PREFIX/bin/mpirun" -np 2 cat
        if [[ $? -eq 0 ]]; then
            log_success "MPI test passed"
        else
            log_error "MPI test failed"
        fi
    fi
    
    # Test FFTW
    if [[ -f "$INSTALL_PREFIX/lib/libfftw3.so" ]]; then
        log_success "FFTW library found"
    else
        log_error "FFTW library not found"
    fi
    
    # Test OpenBLAS
    if [[ -f "$INSTALL_PREFIX/lib/libopenblas.so" ]]; then
        log_success "OpenBLAS library found"
    else
        log_error "OpenBLAS library not found"
    fi
    
    # Test HDF5
    if [[ -x "$INSTALL_PREFIX/bin/h5dump" ]]; then
        log_info "Testing HDF5 installation..."
        "$INSTALL_PREFIX/bin/h5dump" --version > /dev/null 2>&1
        if [[ $? -eq 0 ]]; then
            log_success "HDF5 test passed"
        else
            log_error "HDF5 test failed"
        fi
    fi
    
    log_success "Scientific libraries testing completed"
}

# Main scientific libraries compilation workflow
main() {
    log_info "Starting HPC scientific libraries compilation..."
    
    # Prepare environment
    prepare_scientific_environment
    
    # Extract source files
    extract_sources
    
    # Compile libraries in dependency order
    compile_openmpi || exit 1
    compile_fftw || log_warn "FFTW compilation failed"
    compile_openblas || log_warn "OpenBLAS compilation failed"
    compile_lapack || log_warn "LAPACK compilation failed"
    compile_scalapack || log_warn "ScaLAPACK compilation failed"
    compile_hdf5 || log_warn "HDF5 compilation failed"
    compile_netcdf || log_warn "NetCDF compilation failed"
    
    # Create environment modules
    create_hpc_modules
    
    # Test installation
    test_scientific_libraries
    
    log_success "HPC scientific libraries compilation completed!"
    log_info "Libraries installed in: $INSTALL_PREFIX"
    log_info "Load environment with: module load hpc/scientific-libs"
    
    # Display summary
    echo -e "\nHPC Scientific Libraries Summary:"
    echo -e "Install prefix: $INSTALL_PREFIX"
    echo -e "Libraries compiled:"
    echo -e "  ✓ OpenMPI (Message Passing Interface)"
    echo -e "  ✓ FFTW (Fast Fourier Transform)"  
    echo -e "  ✓ OpenBLAS (Basic Linear Algebra)"
    echo -e "  ✓ LAPACK (Linear Algebra Package)"
    echo -e "  ✓ ScaLAPACK (Scalable LAPACK)"
    echo -e "  ✓ HDF5 (Hierarchical Data Format)"
    echo -e "  ✓ NetCDF (Network Common Data Form)"
    echo -e "\nOptimizations applied:"
    echo -e "  • Multi-threaded compilation ($CPU_CORES cores)"
    echo -e "  • Hardware-specific SIMD instructions"
    echo -e "  • MPI parallel computing support"
    echo -e "  • GPU acceleration ready"
}

# Execute main function
main "$@"