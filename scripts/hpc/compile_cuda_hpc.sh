#!/bin/bash
# Z-FORGE HPC CUDA Compilation Script
# Specialized for NVIDIA Tesla K40/K80 (Kepler architecture)
# CUDA 11.8 with legacy driver support

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-/tmp/zforge-hpc-workspace}"
CUDA_DIR="$WORKSPACE/cuda"
BUILD_DIR="$WORKSPACE/build/cuda"
LOG_FILE="$WORKSPACE/logs/cuda-compilation.log"

# CUDA configuration for Tesla K40/K80
CUDA_VERSION="11.8.0"
CUDA_DRIVER_VERSION="520.61.05"
TESLA_COMPUTE_CAPS="3.5,3.7"  # Kepler compute capabilities
TESLA_ARCHITECTURES="sm_35,sm_37"

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

# Prepare CUDA installation environment
prepare_cuda_environment() {
    log_info "Preparing CUDA compilation environment for Tesla GPUs..."
    
    mkdir -p "$BUILD_DIR"
    mkdir -p "$CUDA_DIR"/{toolkit,driver,samples,docs}
    
    # Set CUDA environment variables
    export CUDA_HOME="/usr/local/cuda"
    export PATH="/usr/local/cuda/bin:$PATH"
    export LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH"
    export CUDA_CACHE_PATH="$BUILD_DIR/cuda-cache"
    
    # Tesla-specific optimizations
    export CUDA_VISIBLE_DEVICES="all"
    export NVIDIA_DRIVER_CAPABILITIES="all"
    export CUDA_DEVICE_ORDER="PCI_BUS_ID"
    
    log_success "CUDA environment prepared"
}

# Install CUDA Toolkit with Tesla optimizations
install_cuda_toolkit() {
    log_info "Installing CUDA $CUDA_VERSION toolkit with Tesla K40/K80 optimizations..."
    
    local cuda_installer="cuda_${CUDA_VERSION}_${CUDA_DRIVER_VERSION}_linux.run"
    local installer_path="$WORKSPACE/downloads/cuda/$cuda_installer"
    
    if [[ ! -f "$installer_path" ]]; then
        log_error "CUDA installer not found: $installer_path"
        log_info "Download CUDA 11.8 from: https://developer.nvidia.com/cuda-toolkit-archive"
        return 1
    fi
    
    # Make installer executable
    chmod +x "$installer_path"
    
    # Silent installation with Tesla-specific configuration
    log_info "Running CUDA installer (silent mode)..."
    "$installer_path" \
        --silent \
        --toolkit \
        --samples \
        --no-opengl-libs \
        --override \
        --driver \
        --installpath="/usr/local/cuda" \
        --samplespath="/usr/local/cuda/samples" \
        --toolkitpath="/usr/local/cuda" \
        --librarypath="/usr/lib" \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "CUDA toolkit installed successfully"
    else
        log_error "CUDA toolkit installation failed"
        return 1
    fi
    
    # Verify installation
    if [[ -f "/usr/local/cuda/bin/nvcc" ]]; then
        local nvcc_version=$(/usr/local/cuda/bin/nvcc --version | grep "release")
        log_info "NVCC version: $nvcc_version"
    else
        log_error "NVCC not found after installation"
        return 1
    fi
}

# Install Tesla-compatible NVIDIA driver
install_tesla_driver() {
    log_info "Installing Tesla-compatible NVIDIA driver..."
    
    local driver_version="470.199.02"  # Last version supporting Tesla K40/K80
    local driver_installer="NVIDIA-Linux-x86_64-${driver_version}.run"
    local driver_path="$WORKSPACE/downloads/nvidia-drivers/$driver_installer"
    
    if [[ ! -f "$driver_path" ]]; then
        log_error "Tesla driver not found: $driver_path"
        log_info "Download from: https://www.nvidia.com/en-us/drivers/unix/legacy-gpu/"
        return 1
    fi
    
    # Check if driver is already installed
    if nvidia-smi &>/dev/null; then
        local current_version=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -1)
        log_info "Current NVIDIA driver: $current_version"
        
        if [[ "$current_version" == *"470"* ]]; then
            log_info "Compatible Tesla driver already installed"
            return 0
        fi
    fi
    
    # Install Tesla driver
    chmod +x "$driver_path"
    log_info "Installing NVIDIA driver $driver_version for Tesla GPUs..."
    
    "$driver_path" \
        --silent \
        --no-opengl-files \
        --no-x-check \
        --no-nouveau-check \
        --disable-nouveau \
        --dkms \
        2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "Tesla driver installed successfully"
        log_info "Reboot required to activate driver"
    else
        log_error "Tesla driver installation failed"
        return 1
    fi
}

# Compile CUDA samples with Tesla optimizations
compile_cuda_samples() {
    log_info "Compiling CUDA samples with Tesla K40/K80 optimizations..."
    
    local samples_dir="/usr/local/cuda/samples"
    local build_samples_dir="$BUILD_DIR/cuda-samples"
    
    if [[ ! -d "$samples_dir" ]]; then
        log_error "CUDA samples directory not found: $samples_dir"
        return 1
    fi
    
    # Copy samples for compilation
    cp -r "$samples_dir" "$build_samples_dir"
    cd "$build_samples_dir"
    
    # Set Tesla-specific compilation flags
    export NVCCFLAGS="-O3 -gencode arch=compute_35,code=sm_35 -gencode arch=compute_37,code=sm_37"
    export CCFLAGS="-O3 -march=haswell -mtune=haswell"
    
    # Compile samples
    log_info "Building CUDA samples (this may take 10-15 minutes)..."
    make -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
    
    if [[ $? -eq 0 ]]; then
        log_success "CUDA samples compiled successfully"
        
        # Test key samples
        test_cuda_samples
    else
        log_error "CUDA samples compilation failed"
        return 1
    fi
}

# Test CUDA functionality with Tesla GPUs
test_cuda_samples() {
    log_info "Testing CUDA functionality with compiled samples..."
    
    local samples_bin="$BUILD_DIR/cuda-samples/bin/x86_64/linux/release"
    
    if [[ -d "$samples_bin" ]]; then
        cd "$samples_bin"
        
        # Test device query
        if [[ -x "deviceQuery" ]]; then
            log_info "Running deviceQuery test..."
            ./deviceQuery 2>&1 | tee -a "$LOG_FILE"
            
            if ./deviceQuery | grep -q "Result = PASS"; then
                log_success "Device query test passed"
            else
                log_error "Device query test failed"
            fi
        fi
        
        # Test bandwidth test
        if [[ -x "bandwidthTest" ]]; then
            log_info "Running bandwidth test..."
            ./bandwidthTest 2>&1 | tee -a "$LOG_FILE"
            
            if ./bandwidthTest | grep -q "Result = PASS"; then
                log_success "Bandwidth test passed"
            else
                log_error "Bandwidth test failed"
            fi
        fi
        
        # Test matrix multiplication (Tesla specific)
        if [[ -x "matrixMul" ]]; then
            log_info "Running matrix multiplication test..."
            ./matrixMul 2>&1 | tee -a "$LOG_FILE"
        fi
    else
        log_error "CUDA samples binaries not found"
        return 1
    fi
}

# Install cuDNN for deep learning workloads
install_cudnn() {
    log_info "Checking for cuDNN installation..."
    
    local cudnn_dir="$WORKSPACE/downloads/cuda"
    local cudnn_archive=$(find "$cudnn_dir" -name "*cudnn*" -type f | head -1)
    
    if [[ -n "$cudnn_archive" ]]; then
        log_info "Installing cuDNN from: $cudnn_archive"
        
        case "$cudnn_archive" in
            *.tgz|*.tar.gz)
                tar -xzf "$cudnn_archive" -C "/tmp"
                local cudnn_extracted="/tmp/cuda"
                
                # Copy cuDNN files to CUDA installation
                if [[ -d "$cudnn_extracted" ]]; then
                    cp -r "$cudnn_extracted/include"/* "/usr/local/cuda/include/"
                    cp -r "$cudnn_extracted/lib64"/* "/usr/local/cuda/lib64/"
                    
                    # Set permissions
                    chmod a+r "/usr/local/cuda/include/cudnn.h"
                    chmod a+r "/usr/local/cuda/lib64/libcudnn*"
                    
                    log_success "cuDNN installed successfully"
                else
                    log_error "cuDNN extraction failed"
                fi
                ;;
            *.deb)
                dpkg -i "$cudnn_archive" 2>&1 | tee -a "$LOG_FILE"
                log_success "cuDNN installed via deb package"
                ;;
            *)
                log_warn "Unknown cuDNN archive format: $cudnn_archive"
                ;;
        esac
    else
        log_warn "cuDNN not found - download manually from NVIDIA Developer portal"
        log_info "cuDNN download: https://developer.nvidia.com/cudnn"
    fi
}

# Create Tesla-optimized CUDA configuration
create_tesla_cuda_config() {
    log_info "Creating Tesla-optimized CUDA configuration..."
    
    # Create CUDA profile for Tesla GPUs
    cat > "/etc/profile.d/cuda-tesla.sh" << 'EOF'
# CUDA Environment for Tesla K40/K80
export CUDA_HOME="/usr/local/cuda"
export PATH="/usr/local/cuda/bin:$PATH"
export LD_LIBRARY_PATH="/usr/local/cuda/lib64:$LD_LIBRARY_PATH"

# Tesla-specific optimizations
export CUDA_VISIBLE_DEVICES="all"
export NVIDIA_DRIVER_CAPABILITIES="all"
export CUDA_DEVICE_ORDER="PCI_BUS_ID"
export CUDA_CACHE_PATH="/tmp/cuda-cache"

# Kepler architecture optimizations
export CUDA_ARCH_LIST="3.5,3.7"
export NVCC_GENCODE="-gencode arch=compute_35,code=sm_35 -gencode arch=compute_37,code=sm_37"

# Performance optimizations
export CUDA_LAUNCH_BLOCKING=0
export CUDA_CACHE_DISABLE=0
export CUDA_FORCE_PTX_JIT=0

# Memory management
export CUDA_MANAGED_FORCE_DEVICE_ALLOC=1
export CUDA_DEVICE_MAX_CONNECTIONS=32
EOF
    
    # Create CUDA compiler wrapper for Tesla optimization
    cat > "/usr/local/bin/nvcc-tesla" << 'EOF'
#!/bin/bash
# Tesla-optimized NVCC wrapper
exec /usr/local/cuda/bin/nvcc \
    -O3 \
    -gencode arch=compute_35,code=sm_35 \
    -gencode arch=compute_37,code=sm_37 \
    -Xptxas -O3 \
    -use_fast_math \
    -lineinfo \
    "$@"
EOF
    
    chmod +x "/usr/local/bin/nvcc-tesla"
    
    log_success "Tesla CUDA configuration created"
}

# Generate Tesla performance benchmarks
create_tesla_benchmarks() {
    log_info "Creating Tesla GPU performance benchmarks..."
    
    local benchmark_dir="$WORKSPACE/benchmarks/tesla"
    mkdir -p "$benchmark_dir"
    
    # Matrix multiplication benchmark
    cat > "$benchmark_dir/tesla_matmul_benchmark.cu" << 'EOF'
// Tesla K40/K80 Matrix Multiplication Benchmark
#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <iostream>
#include <chrono>

#define CHECK_CUDA(call) do { \
    cudaError_t err = call; \
    if (err != cudaSuccess) { \
        std::cerr << "CUDA error at " << __FILE__ << ":" << __LINE__ << " - " << cudaGetErrorString(err) << std::endl; \
        exit(1); \
    } \
} while(0)

int main() {
    const int N = 4096;  // Large enough to stress Tesla memory bandwidth
    const int iterations = 100;
    
    float *h_A, *h_B, *h_C;
    float *d_A, *d_B, *d_C;
    
    // Allocate host memory
    h_A = (float*)malloc(N * N * sizeof(float));
    h_B = (float*)malloc(N * N * sizeof(float));
    h_C = (float*)malloc(N * N * sizeof(float));
    
    // Initialize matrices
    for (int i = 0; i < N * N; i++) {
        h_A[i] = rand() / (float)RAND_MAX;
        h_B[i] = rand() / (float)RAND_MAX;
    }
    
    // Allocate device memory
    CHECK_CUDA(cudaMalloc(&d_A, N * N * sizeof(float)));
    CHECK_CUDA(cudaMalloc(&d_B, N * N * sizeof(float)));
    CHECK_CUDA(cudaMalloc(&d_C, N * N * sizeof(float)));
    
    // Copy data to device
    CHECK_CUDA(cudaMemcpy(d_A, h_A, N * N * sizeof(float), cudaMemcpyHostToDevice));
    CHECK_CUDA(cudaMemcpy(d_B, h_B, N * N * sizeof(float), cudaMemcpyHostToDevice));
    
    // Create cuBLAS handle
    cublasHandle_t handle;
    cublasCreate(&handle);
    
    const float alpha = 1.0f, beta = 0.0f;
    
    // Warm up
    cublasSgemm(handle, CUBLAS_OP_N, CUBLAS_OP_N, N, N, N, &alpha, d_A, N, d_B, N, &beta, d_C, N);
    cudaDeviceSynchronize();
    
    // Benchmark
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        cublasSgemm(handle, CUBLAS_OP_N, CUBLAS_OP_N, N, N, N, &alpha, d_A, N, d_B, N, &beta, d_C, N);
    }
    
    cudaDeviceSynchronize();
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    // Calculate performance metrics
    double gflops = (2.0 * N * N * N * iterations) / (duration.count() / 1000.0) / 1e9;
    
    std::cout << "Tesla GPU Matrix Multiplication Benchmark" << std::endl;
    std::cout << "Matrix size: " << N << "x" << N << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;
    std::cout << "Time: " << duration.count() << " ms" << std::endl;
    std::cout << "Performance: " << gflops << " GFLOPS" << std::endl;
    
    // Performance expectations for Tesla K40/K80
    double expected_gflops_k40 = 1430;  // Peak single precision
    double expected_gflops_k80 = 2910;  // Peak single precision (dual GPU)
    
    if (gflops > expected_gflops_k40 * 0.7) {
        std::cout << "RESULT: PASS (Good Tesla performance)" << std::endl;
    } else {
        std::cout << "RESULT: FAIL (Below expected Tesla performance)" << std::endl;
    }
    
    // Cleanup
    cublasDestroy(handle);
    cudaFree(d_A);
    cudaFree(d_B);
    cudaFree(d_C);
    free(h_A);
    free(h_B);
    free(h_C);
    
    return 0;
}
EOF
    
    # Memory bandwidth benchmark
    cat > "$benchmark_dir/tesla_memory_benchmark.cu" << 'EOF'
// Tesla K40/K80 Memory Bandwidth Benchmark
#include <cuda_runtime.h>
#include <iostream>
#include <chrono>

__global__ void memoryBandwidthKernel(float* data, int size, int iterations) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < size) {
        float val = data[idx];
        for (int i = 0; i < iterations; i++) {
            val = val * 1.01f + 0.01f;
        }
        data[idx] = val;
    }
}

int main() {
    const size_t size = 256 * 1024 * 1024;  // 256MB - large enough for Tesla memory
    const int iterations = 1000;
    const int kernel_iterations = 100;
    
    float *d_data;
    
    cudaMalloc(&d_data, size * sizeof(float));
    
    // Initialize memory
    cudaMemset(d_data, 0, size * sizeof(float));
    
    dim3 block(256);
    dim3 grid((size + block.x - 1) / block.x);
    
    // Warm up
    memoryBandwidthKernel<<<grid, block>>>(d_data, size, kernel_iterations);
    cudaDeviceSynchronize();
    
    // Benchmark
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < iterations; i++) {
        memoryBandwidthKernel<<<grid, block>>>(d_data, size, kernel_iterations);
    }
    
    cudaDeviceSynchronize();
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    // Calculate bandwidth
    double bytes_transferred = size * sizeof(float) * iterations * 2; // Read + Write
    double bandwidth_gb_s = bytes_transferred / (duration.count() / 1e6) / 1e9;
    
    std::cout << "Tesla GPU Memory Bandwidth Benchmark" << std::endl;
    std::cout << "Data size: " << (size * sizeof(float)) / (1024*1024) << " MB" << std::endl;
    std::cout << "Iterations: " << iterations << std::endl;
    std::cout << "Time: " << duration.count() << " μs" << std::endl;
    std::cout << "Memory bandwidth: " << bandwidth_gb_s << " GB/s" << std::endl;
    
    // Tesla K40: ~288 GB/s, Tesla K80: ~480 GB/s theoretical
    if (bandwidth_gb_s > 200) {
        std::cout << "RESULT: PASS (Good Tesla memory performance)" << std::endl;
    } else {
        std::cout << "RESULT: FAIL (Low Tesla memory performance)" << std::endl;
    }
    
    cudaFree(d_data);
    return 0;
}
EOF
    
    # Benchmark compilation script
    cat > "$benchmark_dir/compile_benchmarks.sh" << 'EOF'
#!/bin/bash
# Compile Tesla benchmarks

echo "Compiling Tesla GPU benchmarks..."

# Matrix multiplication benchmark
nvcc -O3 -gencode arch=compute_35,code=sm_35 -gencode arch=compute_37,code=sm_37 \
     -lcublas tesla_matmul_benchmark.cu -o tesla_matmul_benchmark

# Memory bandwidth benchmark
nvcc -O3 -gencode arch=compute_35,code=sm_35 -gencode arch=compute_37,code=sm_37 \
     tesla_memory_benchmark.cu -o tesla_memory_benchmark

echo "Tesla benchmarks compiled successfully"
echo "Run with: ./tesla_matmul_benchmark && ./tesla_memory_benchmark"
EOF
    
    chmod +x "$benchmark_dir/compile_benchmarks.sh"
    
    log_success "Tesla benchmarks created in $benchmark_dir"
}

# Main compilation workflow
main() {
    log_info "Starting CUDA HPC compilation for Tesla K40/K80..."
    
    # Prepare environment
    prepare_cuda_environment
    
    # Install CUDA toolkit
    install_cuda_toolkit || exit 1
    
    # Install Tesla driver
    install_tesla_driver || exit 1
    
    # Compile samples
    compile_cuda_samples || exit 1
    
    # Install cuDNN if available
    install_cudnn
    
    # Create optimized configuration
    create_tesla_cuda_config
    
    # Create benchmarks
    create_tesla_benchmarks
    
    log_success "CUDA HPC compilation completed successfully!"
    log_info "Tesla GPUs ready for high-performance computing workloads"
    
    # Final verification
    if command -v nvidia-smi &> /dev/null; then
        log_info "NVIDIA driver status:"
        nvidia-smi 2>&1 | tee -a "$LOG_FILE"
    fi
}

# Execute main function
main "$@"