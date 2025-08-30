#!/bin/bash
# Z-FORGE HPC Intel Xeon Phi Compilation Script
# Specialized for Knights Landing and Knights Corner architectures
# Intel Parallel Studio XE with MPSS integration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-/tmp/zforge-hpc-workspace}"
INTEL_DIR="$WORKSPACE/intel"
BUILD_DIR="$WORKSPACE/build/intel"
LOG_FILE="$WORKSPACE/logs/intel-phi-compilation.log"

# Intel Xeon Phi configuration
INTEL_PARALLEL_STUDIO_VERSION="2020.4"
MPSS_VERSION="4.7.1"
XEON_PHI_SDK_VERSION="1.6"

# Detected Xeon Phi information (populated by hardware detector)
PHI_ARCHITECTURE="${PHI_ARCHITECTURE:-knights_landing}"
PHI_CORES="${PHI_CORES:-64}"
PHI_THREADS="${PHI_THREADS:-256}"
MCDRAM_SIZE="${MCDRAM_SIZE:-16}"
AVX512_SUPPORT="${AVX512_SUPPORT:-true}"

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

# Prepare Intel Xeon Phi environment
prepare_phi_environment() {
    log_info "Preparing Intel Xeon Phi compilation environment..."
    
    mkdir -p "$BUILD_DIR"/{parallel_studio,mpss,sdk,benchmarks}
    mkdir -p "$INTEL_DIR"/{compilers,libraries,tools,runtime}
    
    # Set Intel environment variables
    export INTEL_HOME="/opt/intel"
    export INTEL_LICENSE_FILE="$INTEL_HOME/licenses"
    
    # Xeon Phi specific environment
    export MIC_KMP_AFFINITY="granularity=fine,balanced"
    export MIC_OMP_NUM_THREADS="$PHI_THREADS"
    export MIC_LD_LIBRARY_PATH="/opt/intel/lib/mic"
    
    # MCDRAM optimization
    if [[ "$MCDRAM_SIZE" -gt 0 ]]; then
        export MIC_MCDRAM_SIZE="${MCDRAM_SIZE}GB"
        export MIC_USE_2MB_BUFFERS="2M"
    fi
    
    # AVX-512 optimization flags
    if [[ "$AVX512_SUPPORT" == "true" ]]; then
        export INTEL_AVX512_FLAGS="-mavx512f -mavx512cd -mavx512er -mavx512pf"
        export INTEL_ARCH_FLAGS="-march=knl -mtune=knl"
    fi
    
    log_success "Intel Xeon Phi environment prepared"
    log_info "Target architecture: $PHI_ARCHITECTURE"
    log_info "Cores: $PHI_CORES, Threads: $PHI_THREADS"
    log_info "MCDRAM: ${MCDRAM_SIZE}GB, AVX-512: $AVX512_SUPPORT"
}

# Install Intel Parallel Studio XE
install_parallel_studio() {
    log_info "Installing Intel Parallel Studio XE for Xeon Phi..."
    
    local studio_archive=$(find "$WORKSPACE/downloads/intel" -name "*parallel_studio*" -type f | head -1)
    
    if [[ -z "$studio_archive" ]]; then
        log_error "Intel Parallel Studio XE archive not found"
        log_info "Download required from: https://registrationcenter.intel.com/"
        log_info "Required components: C++ Compiler, Fortran, MKL, MPI, TBB, VTune, Inspector"
        return 1
    fi
    
    # Extract archive
    local extract_dir="$BUILD_DIR/parallel_studio"
    case "$studio_archive" in
        *.tgz|*.tar.gz)
            tar -xzf "$studio_archive" -C "$extract_dir" --strip-components=1
            ;;
        *.tar)
            tar -xf "$studio_archive" -C "$extract_dir" --strip-components=1
            ;;
        *)
            log_error "Unknown Intel Parallel Studio archive format"
            return 1
            ;;
    esac
    
    # Create silent installation configuration
    cat > "$extract_dir/silent_install.cfg" << EOF
# Intel Parallel Studio XE Silent Installation Configuration
ACCEPT_EULA=accept
CONTINUE_WITH_OPTIONAL_ERROR=yes
PSET_INSTALL_DIR=/opt/intel
CONTINUE_WITH_INSTALLDIR_OVERWRITE=yes

# Components for HPC and Xeon Phi
COMPONENTS=DEFAULTS;intel-comp-nomcu-vars__x86_64;intel-comp-vars__x86_64;intel-compxe-pset

# Xeon Phi support
COMPONENTS=;intel-comp-nomcu-vars-knl__x86_64;intel-comp-vars-knl__x86_64

# Performance libraries
COMPONENTS=;intel-mkl__x86_64;intel-mkl-common__noarch;intel-mkl-installer-license__noarch
COMPONENTS=;intel-tbb-libs__x86_64;intel-tbb-common__noarch

# MPI for cluster computing
COMPONENTS=;intel-mpi-libs__x86_64;intel-mpi-common__noarch

# Development and profiling tools
COMPONENTS=;intel-vtune-amplifier-xe__x86_64;intel-inspector-xe__x86_64

# Xeon Phi specific components
COMPONENTS=;intel-comp-nomcu-mic__x86_64;intel-comp-mic__x86_64;intel-mkl-mic__x86_64

INTEL_SW_IMPROVEMENT_PROGRAM_CONSENT=no
PHONEHOME_SEND_USAGE_DATA=no
EOF
    
    # Run silent installation
    log_info "Running Intel Parallel Studio XE installation (this may take 30-60 minutes)..."
    cd "$extract_dir"
    
    sudo ./install.sh -s silent_install.cfg 2>&1 | tee -a "$LOG_FILE"
    
    if [[ ${PIPESTATUS[0]} -eq 0 ]]; then
        log_success "Intel Parallel Studio XE installed successfully"
    else
        log_error "Intel Parallel Studio XE installation failed"
        return 1
    fi
    
    # Source Intel environment
    if [[ -f "/opt/intel/bin/compilervars.sh" ]]; then
        source /opt/intel/bin/compilervars.sh intel64
        log_success "Intel compiler environment loaded"
    else
        log_error "Intel compiler environment not found"
        return 1
    fi
    
    # Verify installation
    if command -v icc &> /dev/null; then
        local icc_version=$(icc --version | head -1)
        log_info "Intel C Compiler: $icc_version"
    else
        log_error "Intel C Compiler not found"
        return 1
    fi
    
    if command -v ifort &> /dev/null; then
        local ifort_version=$(ifort --version | head -1)
        log_info "Intel Fortran Compiler: $ifort_version"
    fi
}

# Install Intel MPSS (Manycore Platform Software Stack)
install_intel_mpss() {
    log_info "Installing Intel MPSS for Xeon Phi support..."
    
    local mpss_archive=$(find "$WORKSPACE/downloads/intel" -name "*mpss*" -type f | head -1)
    
    if [[ -z "$mpss_archive" ]]; then
        log_warn "Intel MPSS archive not found"
        log_info "Download from Intel Developer Zone for Xeon Phi support"
        return 1
    fi
    
    # Extract MPSS
    local mpss_dir="$BUILD_DIR/mpss"
    tar -xf "$mpss_archive" -C "$mpss_dir" --strip-components=1
    
    # Install MPSS components
    cd "$mpss_dir"
    
    # Install host-side MPSS
    log_info "Installing MPSS host components..."
    sudo ./install.sh --prefix=/opt/intel/mpss 2>&1 | tee -a "$LOG_FILE"
    
    # Configure MPSS service
    sudo systemctl enable mpss
    
    # Install Xeon Phi device drivers
    if [[ -d "/opt/intel/mpss/bin" ]]; then
        sudo /opt/intel/mpss/bin/micctrl --initdefaults
        log_success "MPSS installed and configured"
    else
        log_error "MPSS installation failed"
        return 1
    fi
    
    # Create MPSS configuration
    create_mpss_config
}

# Create MPSS configuration for Xeon Phi
create_mpss_config() {
    log_info "Creating MPSS configuration for detected Xeon Phi devices..."
    
    # Configure MCDRAM mode
    if [[ "$MCDRAM_SIZE" -gt 0 ]]; then
        log_info "Configuring MCDRAM in flat mode for maximum performance..."
        
        cat > "/etc/mpss/mcdram.conf" << EOF
# MCDRAM Configuration for Xeon Phi Knights Landing
# Flat mode provides maximum memory capacity
MCDRAM_MODE=flat
MCDRAM_SIZE=${MCDRAM_SIZE}GB

# Memory interleaving for optimal bandwidth
MEMORY_INTERLEAVING=quad_0
CLUSTER_MODE=quadrant

# Performance optimizations
NUMA_BALANCING=1
TRANSPARENT_HUGEPAGES=always
EOF
    fi
    
    # Create Xeon Phi runtime configuration
    cat > "/opt/intel/mpss/phi_runtime.conf" << EOF
# Xeon Phi Runtime Configuration
PHI_CORES=$PHI_CORES
PHI_THREADS=$PHI_THREADS
PHI_ARCHITECTURE=$PHI_ARCHITECTURE

# Threading optimization
KMP_AFFINITY=granularity=fine,balanced
OMP_NUM_THREADS=$PHI_THREADS

# Memory optimization
MIC_USE_2MB_BUFFERS=2M
MIC_STACK_SIZE=16M

# AVX-512 optimization
MIC_AVX512_OPTIMIZATION=enabled
EOF
    
    log_success "MPSS configuration created"
}

# Compile Intel MKL with Xeon Phi optimizations
compile_intel_mkl() {
    log_info "Configuring Intel MKL for Xeon Phi optimization..."
    
    # Source Intel MKL environment
    if [[ -f "/opt/intel/mkl/bin/mklvars.sh" ]]; then
        source /opt/intel/mkl/bin/mklvars.sh intel64
    else
        log_error "Intel MKL not found"
        return 1
    fi
    
    # Create MKL test application
    local mkl_test_dir="$BUILD_DIR/mkl_test"
    mkdir -p "$mkl_test_dir"
    
    # Create MKL BLAS test for Xeon Phi
    cat > "$mkl_test_dir/mkl_phi_test.c" << 'EOF'
// Intel MKL BLAS Test for Xeon Phi
#include <stdio.h>
#include <stdlib.h>
#include <mkl.h>
#include <omp.h>
#include <time.h>

int main() {
    const int n = 4096;
    const int iterations = 10;
    
    double *a = (double*)mkl_malloc(n * n * sizeof(double), 64);
    double *b = (double*)mkl_malloc(n * n * sizeof(double), 64);
    double *c = (double*)mkl_malloc(n * n * sizeof(double), 64);
    
    if (!a || !b || !c) {
        printf("Memory allocation failed\n");
        return 1;
    }
    
    // Initialize matrices
    #pragma omp parallel for
    for (int i = 0; i < n * n; i++) {
        a[i] = (double)rand() / RAND_MAX;
        b[i] = (double)rand() / RAND_MAX;
        c[i] = 0.0;
    }
    
    printf("Intel MKL DGEMM Test for Xeon Phi\n");
    printf("Matrix size: %dx%d\n", n, n);
    printf("OpenMP threads: %d\n", omp_get_max_threads());
    
    // Warm up
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, n, n, n, 
                1.0, a, n, b, n, 0.0, c, n);
    
    // Benchmark
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    for (int iter = 0; iter < iterations; iter++) {
        cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, n, n, n, 
                    1.0, a, n, b, n, 0.0, c, n);
    }
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    
    double elapsed = (end.tv_sec - start.tv_sec) + 
                    (end.tv_nsec - start.tv_nsec) / 1e9;
    
    double gflops = (2.0 * n * n * n * iterations) / elapsed / 1e9;
    
    printf("Time: %.3f seconds\n", elapsed);
    printf("Performance: %.2f GFLOPS\n", gflops);
    
    // Performance expectations for Xeon Phi
    double expected_phi_gflops = 3000;  // Knights Landing theoretical peak
    
    if (gflops > expected_phi_gflops * 0.6) {
        printf("RESULT: PASS (Good Xeon Phi performance)\n");
    } else {
        printf("RESULT: FAIL (Below expected Xeon Phi performance)\n");
    }
    
    mkl_free(a);
    mkl_free(b);
    mkl_free(c);
    
    return 0;
}
EOF
    
    # Compile MKL test
    log_info "Compiling Intel MKL test for Xeon Phi..."
    cd "$mkl_test_dir"
    
    # Xeon Phi specific compilation flags
    local phi_flags="-march=knl -mtune=knl -mavx512f -mavx512cd -mavx512er -mavx512pf"
    local mkl_flags="-lmkl_intel_lp64 -lmkl_sequential -lmkl_core -lpthread -lm -ldl"
    
    icc $phi_flags -O3 -qopenmp -mkl=sequential mkl_phi_test.c -o mkl_phi_test $mkl_flags 2>&1 | tee -a "$LOG_FILE"
    
    if [[ -x "mkl_phi_test" ]]; then
        log_success "Intel MKL test compiled successfully"
        
        # Run test
        log_info "Running Intel MKL performance test..."
        ./mkl_phi_test 2>&1 | tee -a "$LOG_FILE"
    else
        log_error "Intel MKL test compilation failed"
        return 1
    fi
}

# Compile OpenMP applications for Xeon Phi
compile_openmp_phi() {
    log_info "Creating OpenMP applications optimized for Xeon Phi many-core architecture..."
    
    local omp_dir="$BUILD_DIR/openmp_phi"
    mkdir -p "$omp_dir"
    
    # Many-core parallel reduction benchmark
    cat > "$omp_dir/phi_parallel_reduction.c" << 'EOF'
// Xeon Phi Many-Core Parallel Reduction Benchmark
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
#include <time.h>
#include <math.h>

double parallel_reduction(double* array, size_t size, int num_threads) {
    double sum = 0.0;
    
    #pragma omp parallel for reduction(+:sum) num_threads(num_threads)
    for (size_t i = 0; i < size; i++) {
        sum += sqrt(array[i] * array[i] + 1.0);
    }
    
    return sum;
}

int main() {
    const size_t size = 100000000;  // 100M elements
    const int max_threads = 256;    // Xeon Phi thread count
    
    double* array = (double*)malloc(size * sizeof(double));
    if (!array) {
        printf("Memory allocation failed\n");
        return 1;
    }
    
    // Initialize array
    #pragma omp parallel for
    for (size_t i = 0; i < size; i++) {
        array[i] = (double)i / size;
    }
    
    printf("Xeon Phi Many-Core Parallel Reduction Benchmark\n");
    printf("Array size: %zu elements (%.2f GB)\n", size, size * sizeof(double) / 1e9);
    printf("Testing thread scalability up to %d threads\n\n", max_threads);
    
    // Test different thread counts
    int thread_counts[] = {1, 4, 16, 64, 128, 256};
    int num_tests = sizeof(thread_counts) / sizeof(thread_counts[0]);
    
    for (int t = 0; t < num_tests; t++) {
        int threads = thread_counts[t];
        if (threads > omp_get_max_threads()) continue;
        
        struct timespec start, end;
        clock_gettime(CLOCK_MONOTONIC, &start);
        
        double result = parallel_reduction(array, size, threads);
        
        clock_gettime(CLOCK_MONOTONIC, &end);
        
        double elapsed = (end.tv_sec - start.tv_sec) + 
                        (end.tv_nsec - start.tv_nsec) / 1e9;
        
        double throughput = size / elapsed / 1e6;  // Million elements per second
        
        printf("Threads: %3d | Time: %8.3f s | Throughput: %8.2f Melem/s | Sum: %e\n", 
               threads, elapsed, throughput, result);
    }
    
    free(array);
    
    printf("\nXeon Phi many-core scaling test completed\n");
    return 0;
}
EOF
    
    # Compile OpenMP benchmark
    cd "$omp_dir"
    log_info "Compiling OpenMP Xeon Phi benchmark..."
    
    local phi_flags="-march=knl -mtune=knl -mavx512f -qopenmp"
    icc $phi_flags -O3 phi_parallel_reduction.c -o phi_parallel_reduction -lm 2>&1 | tee -a "$LOG_FILE"
    
    if [[ -x "phi_parallel_reduction" ]]; then
        log_success "OpenMP Xeon Phi benchmark compiled successfully"
    else
        log_error "OpenMP benchmark compilation failed"
        return 1
    fi
}

# Create Xeon Phi system integration
create_phi_system_integration() {
    log_info "Creating Xeon Phi system integration configuration..."
    
    # Create Xeon Phi environment script
    cat > "/etc/profile.d/xeon-phi.sh" << EOF
# Intel Xeon Phi Environment Configuration
export INTEL_HOME="/opt/intel"
export INTEL_LICENSE_FILE="/opt/intel/licenses"

# Compiler environment
if [[ -f "/opt/intel/bin/compilervars.sh" ]]; then
    source /opt/intel/bin/compilervars.sh intel64
fi

# MKL environment
if [[ -f "/opt/intel/mkl/bin/mklvars.sh" ]]; then
    source /opt/intel/mkl/bin/mklvars.sh intel64
fi

# MPSS environment
export PATH="/opt/intel/mpss/bin:\$PATH"

# Xeon Phi specific optimizations
export MIC_KMP_AFFINITY="granularity=fine,balanced"
export MIC_OMP_NUM_THREADS=$PHI_THREADS
export MIC_LD_LIBRARY_PATH="/opt/intel/lib/mic"

# MCDRAM optimization
export MIC_USE_2MB_BUFFERS="2M"
export MIC_STACK_SIZE="16M"

# Performance settings
export OMP_PROC_BIND=spread
export OMP_PLACES=threads
export KMP_BLOCKTIME=0

# AVX-512 optimization
export INTEL_AVX512_ENABLED=1
EOF
    
    # Create Xeon Phi compiler wrapper
    cat > "/usr/local/bin/icc-phi" << EOF
#!/bin/bash
# Xeon Phi optimized Intel C compiler wrapper
exec icc \\
    -march=knl -mtune=knl \\
    -mavx512f -mavx512cd -mavx512er -mavx512pf \\
    -O3 -qopenmp \\
    -qopt-streaming-stores always \\
    -qopt-threads-per-core=4 \\
    -mkl \\
    "\$@"
EOF
    
    chmod +x "/usr/local/bin/icc-phi"
    
    # Create Fortran wrapper
    cat > "/usr/local/bin/ifort-phi" << EOF
#!/bin/bash
# Xeon Phi optimized Intel Fortran compiler wrapper
exec ifort \\
    -march=knl -mtune=knl \\
    -mavx512f -mavx512cd -mavx512er -mavx512pf \\
    -O3 -qopenmp \\
    -qopt-streaming-stores always \\
    -qopt-threads-per-core=4 \\
    -mkl \\
    "\$@"
EOF
    
    chmod +x "/usr/local/bin/ifort-phi"
    
    log_success "Xeon Phi system integration created"
}

# Generate Xeon Phi performance benchmarks
create_phi_benchmarks() {
    log_info "Creating comprehensive Xeon Phi performance benchmarks..."
    
    local benchmark_dir="$WORKSPACE/benchmarks/xeon_phi"
    mkdir -p "$benchmark_dir"
    
    # STREAM benchmark for memory bandwidth
    cat > "$benchmark_dir/phi_stream_benchmark.c" << 'EOF'
// STREAM Benchmark optimized for Xeon Phi MCDRAM
#include <stdio.h>
#include <stdlib.h>
#include <omp.h>
#include <time.h>
#include <string.h>

#ifndef N
#define N 100000000  // Large enough to exceed cache sizes
#endif

static double a[N], b[N], c[N];

int main() {
    const int iterations = 100;
    double scalar = 3.0;
    
    printf("Xeon Phi STREAM Memory Bandwidth Benchmark\n");
    printf("Array size: %d elements (%.2f MB per array)\n", N, N * sizeof(double) / 1e6);
    printf("Total memory: %.2f MB\n", 3 * N * sizeof(double) / 1e6);
    printf("OpenMP threads: %d\n", omp_get_max_threads());
    
    // Initialize arrays
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        a[i] = 1.0;
        b[i] = 2.0;
        c[i] = 0.0;
    }
    
    struct timespec start, end;
    double times[4];
    
    // COPY: c = a
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (int k = 0; k < iterations; k++) {
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            c[i] = a[i];
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    times[0] = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // SCALE: b = scalar * c
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (int k = 0; k < iterations; k++) {
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            b[i] = scalar * c[i];
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    times[1] = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // ADD: c = a + b
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (int k = 0; k < iterations; k++) {
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            c[i] = a[i] + b[i];
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    times[2] = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // TRIAD: a = b + scalar * c
    clock_gettime(CLOCK_MONOTONIC, &start);
    for (int k = 0; k < iterations; k++) {
        #pragma omp parallel for
        for (int i = 0; i < N; i++) {
            a[i] = b[i] + scalar * c[i];
        }
    }
    clock_gettime(CLOCK_MONOTONIC, &end);
    times[3] = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;
    
    // Calculate bandwidths
    char *labels[] = {"Copy", "Scale", "Add", "Triad"};
    double bytes[] = {2 * sizeof(double), 2 * sizeof(double), 3 * sizeof(double), 3 * sizeof(double)};
    
    printf("\nFunction    Best Rate GB/s  Avg time     Min time     Max time\n");
    
    for (int i = 0; i < 4; i++) {
        double bandwidth = (N * bytes[i] * iterations) / times[i] / 1e9;
        printf("%-10s  %11.1f  %11.6f  %11.6f  %11.6f\n", 
               labels[i], bandwidth, times[i]/iterations, times[i]/iterations, times[i]/iterations);
    }
    
    // Expected Xeon Phi Knights Landing MCDRAM bandwidth: ~400-490 GB/s
    double max_bandwidth = 0;
    for (int i = 0; i < 4; i++) {
        double bw = (N * bytes[i] * iterations) / times[i] / 1e9;
        if (bw > max_bandwidth) max_bandwidth = bw;
    }
    
    if (max_bandwidth > 300) {
        printf("\nRESULT: PASS (Good Xeon Phi MCDRAM performance: %.1f GB/s)\n", max_bandwidth);
    } else {
        printf("\nRESULT: FAIL (Low Xeon Phi memory performance: %.1f GB/s)\n", max_bandwidth);
    }
    
    return 0;
}
EOF
    
    # Benchmark compilation script
    cat > "$benchmark_dir/compile_phi_benchmarks.sh" << 'EOF'
#!/bin/bash
# Compile Xeon Phi benchmarks with Intel compilers

echo "Compiling Xeon Phi performance benchmarks..."

# Source Intel environment
source /opt/intel/bin/compilervars.sh intel64

# STREAM benchmark
icc -march=knl -mtune=knl -mavx512f -O3 -qopenmp \
    phi_stream_benchmark.c -o phi_stream_benchmark

echo "Xeon Phi benchmarks compiled successfully"
echo "Run STREAM test: ./phi_stream_benchmark"
EOF
    
    chmod +x "$benchmark_dir/compile_phi_benchmarks.sh"
    
    log_success "Xeon Phi benchmarks created in $benchmark_dir"
}

# Main Intel Xeon Phi compilation workflow
main() {
    log_info "Starting Intel Xeon Phi HPC compilation..."
    
    # Prepare environment
    prepare_phi_environment
    
    # Install Intel Parallel Studio XE
    install_parallel_studio || exit 1
    
    # Install MPSS for Xeon Phi support
    install_intel_mpss || log_warn "MPSS installation failed - some Xeon Phi features unavailable"
    
    # Compile and test Intel MKL
    compile_intel_mkl || exit 1
    
    # Compile OpenMP applications
    compile_openmp_phi || exit 1
    
    # Create system integration
    create_phi_system_integration
    
    # Create performance benchmarks
    create_phi_benchmarks
    
    log_success "Intel Xeon Phi HPC compilation completed successfully!"
    log_info "Xeon Phi ready for many-core high-performance computing"
    
    # Final system status
    if command -v micinfo &> /dev/null; then
        log_info "Xeon Phi device information:"
        micinfo 2>&1 | tee -a "$LOG_FILE"
    fi
    
    # Display optimization summary
    echo -e "\nXeon Phi Optimization Summary:"
    echo -e "Architecture: $PHI_ARCHITECTURE"
    echo -e "Cores: $PHI_CORES, Threads: $PHI_THREADS" 
    echo -e "MCDRAM: ${MCDRAM_SIZE}GB"
    echo -e "AVX-512: $AVX512_SUPPORT"
    echo -e "Compilers: Intel C/C++ and Fortran with Xeon Phi optimization"
    echo -e "Libraries: Intel MKL, TBB, MPI optimized for many-core"
}

# Execute main function
main "$@"