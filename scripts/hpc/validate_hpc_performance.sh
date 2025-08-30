#!/bin/bash
# Z-FORGE HPC Performance Validation and Benchmark Suite
# Comprehensive testing for Tesla GPUs, Xeon Phi, and HPC libraries
# Performance targets and validation for scientific computing workloads

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="${WORKSPACE:-/tmp/zforge-hpc-workspace}"
BENCHMARK_DIR="$WORKSPACE/benchmarks"
RESULTS_DIR="$WORKSPACE/results"
LOG_FILE="$WORKSPACE/logs/hpc-performance-validation.log"

# Performance targets (based on hardware specifications)
TESLA_K40_GFLOPS_MIN="1000"     # Tesla K40: ~1.43 TFLOPS peak
TESLA_K80_GFLOPS_MIN="2000"     # Tesla K80: ~2.91 TFLOPS peak  
PHI_7250_GFLOPS_MIN="2400"      # Xeon Phi 7250: ~3 TFLOPS peak
MEMORY_BANDWIDTH_MIN="200"      # Minimum GB/s for HPC workloads
MPI_LATENCY_MAX="10"            # Maximum MPI latency in microseconds
HPC_LIB_COMPILE_TIME_MAX="600"  # Maximum library compile time in seconds

# System information
HOSTNAME=$(hostname)
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')
RESULTS_FILE="$RESULTS_DIR/hpc_performance_${HOSTNAME}_${TIMESTAMP}.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_test() {
    echo -e "${PURPLE}[TEST]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Performance test result structure
declare -A test_results

# Initialize performance validation
initialize_validation() {
    log_info "Initializing HPC performance validation suite..."
    
    mkdir -p "$BENCHMARK_DIR"/{tesla,xeon_phi,mpi,scientific_libs}
    mkdir -p "$RESULTS_DIR"
    
    # System information gathering
    local sys_info="{
        \"hostname\": \"$HOSTNAME\",
        \"timestamp\": \"$TIMESTAMP\",
        \"cpu_model\": \"$(cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2 | xargs)\",
        \"cpu_cores\": $(nproc),
        \"memory_gb\": $(free -g | awk '/^Mem:/{print $2}'),
        \"kernel_version\": \"$(uname -r)\",
        \"os_release\": \"$(lsb_release -d | cut -f2)\",
        \"gcc_version\": \"$(gcc --version | head -1)\",
        \"cuda_version\": \"$(nvcc --version 2>/dev/null | grep 'release' | awk '{print $6}' || echo 'N/A')\",
        \"intel_compiler\": \"$(icc --version 2>/dev/null | head -1 || echo 'N/A')\"
    }"
    
    echo "$sys_info" > "$RESULTS_DIR/system_info.json"
    
    log_success "Performance validation initialized"
    log_info "Results will be saved to: $RESULTS_FILE"
}

# NVIDIA Tesla GPU performance validation
validate_tesla_performance() {
    log_test "Running Tesla GPU performance validation..."
    
    local tesla_found=false
    local tesla_results="{\"gpus\": [], \"tests\": {}}"
    
    # Check for Tesla GPUs
    if command -v nvidia-smi &> /dev/null; then
        local gpu_info=$(nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv,noheader,nounits)
        
        if echo "$gpu_info" | grep -i tesla; then
            tesla_found=true
            log_info "Tesla GPUs detected:"
            echo "$gpu_info" | grep -i tesla | while read line; do
                log_info "  - $line"
            done
        fi
    fi
    
    if [[ "$tesla_found" == "true" ]]; then
        # Run CUDA device query
        if [[ -x "/usr/local/cuda/samples/bin/x86_64/linux/release/deviceQuery" ]]; then
            log_test "Running CUDA deviceQuery test..."
            local device_output=$(/usr/local/cuda/samples/bin/x86_64/linux/release/deviceQuery 2>&1)
            
            if echo "$device_output" | grep -q "Result = PASS"; then
                test_results["cuda_device_query"]="PASS"
                log_success "CUDA deviceQuery test passed"
            else
                test_results["cuda_device_query"]="FAIL"
                log_error "CUDA deviceQuery test failed"
            fi
        fi
        
        # Run bandwidth test
        if [[ -x "/usr/local/cuda/samples/bin/x86_64/linux/release/bandwidthTest" ]]; then
            log_test "Running CUDA memory bandwidth test..."
            local bandwidth_output=$(/usr/local/cuda/samples/bin/x86_64/linux/release/bandwidthTest 2>&1)
            
            if echo "$bandwidth_output" | grep -q "Result = PASS"; then
                test_results["cuda_bandwidth"]="PASS"
                
                # Extract bandwidth values
                local h2d_bandwidth=$(echo "$bandwidth_output" | grep "Host to Device" | awk '{print $NF}' | sed 's/MB\/s//')
                local d2h_bandwidth=$(echo "$bandwidth_output" | grep "Device to Host" | awk '{print $NF}' | sed 's/MB\/s//')
                
                log_success "CUDA bandwidth test passed"
                log_info "  Host to Device: ${h2d_bandwidth} MB/s"
                log_info "  Device to Host: ${d2h_bandwidth} MB/s"
                
                test_results["tesla_h2d_bandwidth"]="$h2d_bandwidth"
                test_results["tesla_d2h_bandwidth"]="$d2h_bandwidth"
            else
                test_results["cuda_bandwidth"]="FAIL"
                log_error "CUDA bandwidth test failed"
            fi
        fi
        
        # Run custom Tesla benchmark if compiled
        local tesla_benchmark="$BENCHMARK_DIR/tesla/tesla_matmul_benchmark"
        if [[ -x "$tesla_benchmark" ]]; then
            log_test "Running Tesla matrix multiplication benchmark..."
            local matmul_output=$($tesla_benchmark 2>&1)
            
            local gflops=$(echo "$matmul_output" | grep "Performance:" | awk '{print $2}')
            
            if [[ -n "$gflops" ]]; then
                test_results["tesla_matmul_gflops"]="$gflops"
                log_info "Tesla GEMM performance: $gflops GFLOPS"
                
                # Validate against targets
                if (( $(echo "$gflops > $TESLA_K40_GFLOPS_MIN" | bc -l) )); then
                    test_results["tesla_performance"]="PASS"
                    log_success "Tesla performance meets HPC requirements"
                else
                    test_results["tesla_performance"]="FAIL"
                    log_error "Tesla performance below HPC requirements ($gflops < $TESLA_K40_GFLOPS_MIN GFLOPS)"
                fi
            fi
        else
            log_warn "Tesla benchmark not found - compile with compile_cuda_hpc.sh"
        fi
    else
        log_warn "No Tesla GPUs detected - GPU validation skipped"
        test_results["tesla_available"]="false"
    fi
}

# Intel Xeon Phi performance validation
validate_xeon_phi_performance() {
    log_test "Running Xeon Phi performance validation..."
    
    local phi_found=false
    
    # Check for Xeon Phi devices
    if lspci | grep -i "Xeon Phi" &> /dev/null; then
        phi_found=true
        log_info "Xeon Phi devices detected:"
        lspci | grep -i "Xeon Phi" | while read line; do
            log_info "  - $line"
        done
    fi
    
    if [[ "$phi_found" == "true" ]]; then
        # Check MPSS status
        if systemctl is-active mpss &> /dev/null; then
            test_results["mpss_service"]="RUNNING"
            log_success "Intel MPSS service is running"
        else
            test_results["mpss_service"]="STOPPED"
            log_error "Intel MPSS service is not running"
        fi
        
        # Test Intel compilers
        if command -v icc &> /dev/null; then
            test_results["intel_compiler"]="AVAILABLE"
            local icc_version=$(icc --version | head -1)
            log_success "Intel C compiler available: $icc_version"
        else
            test_results["intel_compiler"]="MISSING"
            log_error "Intel C compiler not found"
        fi
        
        # Run Xeon Phi benchmarks if available
        local phi_stream="$BENCHMARK_DIR/xeon_phi/phi_stream_benchmark"
        if [[ -x "$phi_stream" ]]; then
            log_test "Running Xeon Phi STREAM memory bandwidth test..."
            local stream_output=$($phi_stream 2>&1)
            
            local max_bandwidth=$(echo "$stream_output" | grep "TRIAD" | awk '{print $2}')
            
            if [[ -n "$max_bandwidth" ]]; then
                test_results["phi_memory_bandwidth"]="$max_bandwidth"
                log_info "Xeon Phi memory bandwidth: $max_bandwidth GB/s"
                
                # Validate against MCDRAM expectations
                if (( $(echo "$max_bandwidth > 300" | bc -l) )); then
                    test_results["phi_memory_performance"]="PASS"
                    log_success "Xeon Phi memory performance meets MCDRAM expectations"
                else
                    test_results["phi_memory_performance"]="FAIL"
                    log_error "Xeon Phi memory performance below MCDRAM expectations"
                fi
            fi
        else
            log_warn "Xeon Phi benchmark not found - compile with compile_intel_phi_hpc.sh"
        fi
        
        # Check AVX-512 support
        if grep -q avx512 /proc/cpuinfo; then
            test_results["avx512_support"]="true"
            log_success "AVX-512 instruction set supported"
        else
            test_results["avx512_support"]="false"
            log_warn "AVX-512 not detected"
        fi
    else
        log_warn "No Xeon Phi devices detected - Phi validation skipped"
        test_results["xeon_phi_available"]="false"
    fi
}

# MPI performance validation
validate_mpi_performance() {
    log_test "Running MPI performance validation..."
    
    if command -v mpirun &> /dev/null; then
        test_results["mpi_available"]="true"
        local mpi_version=$(mpirun --version | head -1)
        log_info "MPI implementation: $mpi_version"
        
        # Test MPI basic functionality
        log_test "Running MPI hello world test..."
        local mpi_test_dir="$BENCHMARK_DIR/mpi"
        mkdir -p "$mpi_test_dir"
        cd "$mpi_test_dir"
        
        # Create simple MPI test
        cat > mpi_hello.c << 'EOF'
#include <mpi.h>
#include <stdio.h>

int main(int argc, char** argv) {
    MPI_Init(NULL, NULL);
    
    int world_size;
    MPI_Comm_size(MPI_COMM_WORLD, &world_size);
    
    int world_rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &world_rank);
    
    printf("Hello from rank %d of %d\n", world_rank, world_size);
    
    MPI_Finalize();
    return 0;
}
EOF
        
        # Compile and run MPI test
        if mpicc -o mpi_hello mpi_hello.c 2>/dev/null; then
            local mpi_output=$(mpirun -np 4 ./mpi_hello 2>&1)
            
            if echo "$mpi_output" | grep -q "Hello from rank"; then
                test_results["mpi_basic_test"]="PASS"
                log_success "MPI basic functionality test passed"
            else
                test_results["mpi_basic_test"]="FAIL"
                log_error "MPI basic functionality test failed"
            fi
        else
            test_results["mpi_basic_test"]="COMPILE_FAIL"
            log_error "MPI test compilation failed"
        fi
        
        # MPI bandwidth test (if available)
        if command -v mpi-bench &> /dev/null; then
            log_test "Running MPI bandwidth benchmark..."
            # Run MPI bandwidth test
            local bandwidth_result=$(mpirun -np 2 mpi-bench 2>&1 || echo "N/A")
            test_results["mpi_bandwidth"]="$bandwidth_result"
        fi
    else
        log_warn "MPI not found - MPI validation skipped"
        test_results["mpi_available"]="false"
    fi
}

# Scientific libraries performance validation
validate_scientific_libraries() {
    log_test "Running scientific libraries performance validation..."
    
    local libs_prefix="/opt/hpc"
    local libs_found=0
    
    # Check OpenMPI
    if [[ -x "$libs_prefix/bin/mpirun" ]]; then
        test_results["openmpi"]="INSTALLED"
        log_success "OpenMPI found at $libs_prefix/bin/mpirun"
        ((libs_found++))
    else
        test_results["openmpi"]="MISSING"
        log_error "OpenMPI not found"
    fi
    
    # Check FFTW
    if [[ -f "$libs_prefix/lib/libfftw3.so" ]]; then
        test_results["fftw"]="INSTALLED"
        log_success "FFTW found at $libs_prefix/lib/libfftw3.so"
        ((libs_found++))
    else
        test_results["fftw"]="MISSING"
        log_error "FFTW not found"
    fi
    
    # Check OpenBLAS
    if [[ -f "$libs_prefix/lib/libopenblas.so" ]]; then
        test_results["openblas"]="INSTALLED"
        log_success "OpenBLAS found at $libs_prefix/lib/libopenblas.so"
        ((libs_found++))
        
        # Test OpenBLAS performance
        local blas_test_dir="$BENCHMARK_DIR/scientific_libs"
        mkdir -p "$blas_test_dir"
        cd "$blas_test_dir"
        
        # Create BLAS performance test
        cat > blas_test.c << EOF
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <cblas.h>

int main() {
    const int n = 2048;
    double *a = malloc(n * n * sizeof(double));
    double *b = malloc(n * n * sizeof(double));
    double *c = malloc(n * n * sizeof(double));
    
    // Initialize matrices
    for (int i = 0; i < n * n; i++) {
        a[i] = (double)rand() / RAND_MAX;
        b[i] = (double)rand() / RAND_MAX;
        c[i] = 0.0;
    }
    
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);
    
    cblas_dgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, n, n, n, 
                1.0, a, n, b, n, 0.0, c, n);
    
    clock_gettime(CLOCK_MONOTONIC, &end);
    
    double elapsed = (end.tv_sec - start.tv_sec) + 
                    (end.tv_nsec - start.tv_nsec) / 1e9;
    double gflops = (2.0 * n * n * n) / elapsed / 1e9;
    
    printf("OpenBLAS DGEMM Performance: %.2f GFLOPS\\n", gflops);
    
    free(a); free(b); free(c);
    return 0;
}
EOF
        
        # Compile and run BLAS test
        if gcc -o blas_test blas_test.c -L"$libs_prefix/lib" -lopenblas -lm 2>/dev/null; then
            local blas_output=$(LD_LIBRARY_PATH="$libs_prefix/lib:$LD_LIBRARY_PATH" ./blas_test 2>&1)
            local blas_gflops=$(echo "$blas_output" | grep "GFLOPS" | awk '{print $4}')
            
            if [[ -n "$blas_gflops" ]]; then
                test_results["openblas_gflops"]="$blas_gflops"
                log_info "OpenBLAS DGEMM performance: $blas_gflops GFLOPS"
            fi
        fi
    else
        test_results["openblas"]="MISSING"
        log_error "OpenBLAS not found"
    fi
    
    # Check LAPACK
    if [[ -f "$libs_prefix/lib/liblapack.so" ]]; then
        test_results["lapack"]="INSTALLED"
        log_success "LAPACK found at $libs_prefix/lib/liblapack.so"
        ((libs_found++))
    else
        test_results["lapack"]="MISSING"
        log_error "LAPACK not found"
    fi
    
    # Check HDF5
    if [[ -x "$libs_prefix/bin/h5dump" ]]; then
        test_results["hdf5"]="INSTALLED"
        log_success "HDF5 found at $libs_prefix/bin/h5dump"
        ((libs_found++))
    else
        test_results["hdf5"]="MISSING"
        log_error "HDF5 not found"
    fi
    
    # Overall libraries assessment
    local total_libs=5
    local completion_percent=$((libs_found * 100 / total_libs))
    
    test_results["libraries_completion"]="$completion_percent"
    
    if [[ $completion_percent -ge 80 ]]; then
        test_results["scientific_libraries_status"]="EXCELLENT"
        log_success "Scientific libraries installation: $completion_percent% complete"
    elif [[ $completion_percent -ge 60 ]]; then
        test_results["scientific_libraries_status"]="GOOD"
        log_info "Scientific libraries installation: $completion_percent% complete"
    else
        test_results["scientific_libraries_status"]="POOR"
        log_error "Scientific libraries installation: $completion_percent% complete"
    fi
}

# System performance baseline
validate_system_baseline() {
    log_test "Running system performance baseline tests..."
    
    # CPU benchmark
    log_test "Running CPU benchmark..."
    local cpu_start=$(date +%s.%N)
    
    # Simple CPU-intensive calculation
    local cpu_result=$(echo "scale=10; 4*a(1)" | bc -l 2>/dev/null || echo "3.14159")
    
    local cpu_end=$(date +%s.%N)
    local cpu_time=$(echo "$cpu_end - $cpu_start" | bc -l)
    
    test_results["cpu_benchmark_time"]="$cpu_time"
    log_info "CPU benchmark completed in ${cpu_time}s"
    
    # Memory benchmark (simple read/write test)
    log_test "Running memory benchmark..."
    local mem_size="100M"
    local mem_start=$(date +%s.%N)
    
    dd if=/dev/zero of=/tmp/mem_test bs=1M count=100 2>/dev/null
    dd if=/tmp/mem_test of=/dev/null bs=1M 2>/dev/null
    rm -f /tmp/mem_test
    
    local mem_end=$(date +%s.%N)
    local mem_time=$(echo "$mem_end - $mem_start" | bc -l)
    
    test_results["memory_benchmark_time"]="$mem_time"
    log_info "Memory benchmark completed in ${mem_time}s"
    
    # Disk I/O benchmark
    log_test "Running disk I/O benchmark..."
    local disk_start=$(date +%s.%N)
    
    dd if=/dev/zero of=/tmp/disk_test bs=1M count=100 2>/dev/null
    sync
    dd if=/tmp/disk_test of=/dev/null bs=1M 2>/dev/null
    rm -f /tmp/disk_test
    
    local disk_end=$(date +%s.%N)
    local disk_time=$(echo "$disk_end - $disk_start" | bc -l)
    
    test_results["disk_benchmark_time"]="$disk_time"
    log_info "Disk I/O benchmark completed in ${disk_time}s"
    
    # Load average
    local load_avg=$(uptime | awk '{print $(NF-2)}' | sed 's/,//')
    test_results["system_load"]="$load_avg"
    log_info "System load average: $load_avg"
}

# Generate comprehensive results report
generate_results_report() {
    log_info "Generating comprehensive performance validation report..."
    
    # Convert associative array to JSON
    local json_results="{"
    local first=true
    
    for key in "${!test_results[@]}"; do
        if [[ "$first" == "false" ]]; then
            json_results+=","
        fi
        json_results+="\"$key\": \"${test_results[$key]}\""
        first=false
    done
    json_results+="}"
    
    # Create comprehensive report
    local report="{
        \"metadata\": {
            \"hostname\": \"$HOSTNAME\",
            \"timestamp\": \"$TIMESTAMP\",
            \"validation_version\": \"1.0.0\",
            \"total_tests\": ${#test_results[@]}
        },
        \"system_info\": $(cat "$RESULTS_DIR/system_info.json"),
        \"test_results\": $json_results,
        \"performance_summary\": {
            \"overall_status\": \"$(calculate_overall_status)\",
            \"hpc_readiness\": \"$(calculate_hpc_readiness)\",
            \"recommendations\": $(generate_recommendations)
        }
    }"
    
    echo "$report" | python3 -m json.tool > "$RESULTS_FILE"
    
    log_success "Results report generated: $RESULTS_FILE"
    
    # Display summary
    display_validation_summary
}

# Calculate overall validation status
calculate_overall_status() {
    local passed_tests=0
    local total_tests=0
    
    for key in "${!test_results[@]}"; do
        if [[ "$key" =~ _test$|_performance$|_benchmark$ ]]; then
            ((total_tests++))
            if [[ "${test_results[$key]}" == "PASS" ]]; then
                ((passed_tests++))
            fi
        fi
    done
    
    if [[ $total_tests -eq 0 ]]; then
        echo "UNKNOWN"
    elif [[ $passed_tests -eq $total_tests ]]; then
        echo "EXCELLENT"
    elif [[ $((passed_tests * 100 / total_tests)) -ge 75 ]]; then
        echo "GOOD"
    elif [[ $((passed_tests * 100 / total_tests)) -ge 50 ]]; then
        echo "FAIR"
    else
        echo "POOR"
    fi
}

# Calculate HPC readiness score
calculate_hpc_readiness() {
    local hpc_components=0
    local hpc_ready=0
    
    # Check critical HPC components
    if [[ "${test_results[tesla_available]:-false}" != "false" ]]; then
        ((hpc_components++))
        if [[ "${test_results[tesla_performance]:-}" == "PASS" ]]; then
            ((hpc_ready++))
        fi
    fi
    
    if [[ "${test_results[xeon_phi_available]:-false}" != "false" ]]; then
        ((hpc_components++))
        if [[ "${test_results[phi_memory_performance]:-}" == "PASS" ]]; then
            ((hpc_ready++))
        fi
    fi
    
    if [[ "${test_results[mpi_available]:-}" == "true" ]]; then
        ((hpc_components++))
        if [[ "${test_results[mpi_basic_test]:-}" == "PASS" ]]; then
            ((hpc_ready++))
        fi
    fi
    
    if [[ "${test_results[scientific_libraries_status]:-}" == "EXCELLENT" ]]; then
        ((hpc_components++))
        ((hpc_ready++))
    elif [[ "${test_results[scientific_libraries_status]:-}" == "GOOD" ]]; then
        ((hpc_components++))
    fi
    
    if [[ $hpc_components -eq 0 ]]; then
        echo "NOT_CONFIGURED"
    elif [[ $hpc_ready -eq $hpc_components ]]; then
        echo "FULLY_READY"
    elif [[ $((hpc_ready * 100 / hpc_components)) -ge 75 ]]; then
        echo "MOSTLY_READY"
    else
        echo "PARTIALLY_READY"
    fi
}

# Generate recommendations
generate_recommendations() {
    local recommendations=()
    
    # Tesla GPU recommendations
    if [[ "${test_results[tesla_available]:-false}" == "false" ]]; then
        recommendations+=("\"Install NVIDIA Tesla K40/K80 GPUs for GPU-accelerated computing\"")
    elif [[ "${test_results[tesla_performance]:-}" == "FAIL" ]]; then
        recommendations+=("\"Optimize Tesla GPU performance - check driver version and CUDA configuration\"")
    fi
    
    # Xeon Phi recommendations  
    if [[ "${test_results[xeon_phi_available]:-false}" == "false" ]]; then
        recommendations+=("\"Consider Intel Xeon Phi co-processors for many-core computing\"")
    elif [[ "${test_results[mpss_service]:-}" != "RUNNING" ]]; then
        recommendations+=("\"Start Intel MPSS service for Xeon Phi support\"")
    fi
    
    # MPI recommendations
    if [[ "${test_results[mpi_available]:-}" != "true" ]]; then
        recommendations+=("\"Install OpenMPI for distributed computing support\"")
    elif [[ "${test_results[mpi_basic_test]:-}" != "PASS" ]]; then
        recommendations+=("\"Fix MPI configuration for parallel computing\"")
    fi
    
    # Scientific libraries recommendations
    if [[ "${test_results[scientific_libraries_status]:-}" == "POOR" ]]; then
        recommendations+=("\"Install essential HPC libraries (FFTW, BLAS, LAPACK, HDF5)\"")
    fi
    
    # Intel compiler recommendation
    if [[ "${test_results[intel_compiler]:-}" == "MISSING" ]]; then
        recommendations+=("\"Install Intel Parallel Studio XE for optimal HPC performance\"")
    fi
    
    # Convert array to JSON
    local json_recommendations="["
    local first=true
    for rec in "${recommendations[@]}"; do
        if [[ "$first" == "false" ]]; then
            json_recommendations+=","
        fi
        json_recommendations+="$rec"
        first=false
    done
    json_recommendations+="]"
    
    echo "$json_recommendations"
}

# Display validation summary
display_validation_summary() {
    echo -e "\n${PURPLE}=== HPC Performance Validation Summary ===${NC}"
    echo -e "${BLUE}Hostname:${NC} $HOSTNAME"
    echo -e "${BLUE}Timestamp:${NC} $TIMESTAMP"
    echo -e "${BLUE}Total Tests:${NC} ${#test_results[@]}"
    
    local overall_status=$(calculate_overall_status)
    local hpc_readiness=$(calculate_hpc_readiness)
    
    case "$overall_status" in
        "EXCELLENT") echo -e "${BLUE}Overall Status:${NC} ${GREEN}$overall_status${NC}" ;;
        "GOOD") echo -e "${BLUE}Overall Status:${NC} ${CYAN}$overall_status${NC}" ;;
        "FAIR") echo -e "${BLUE}Overall Status:${NC} ${YELLOW}$overall_status${NC}" ;;
        *) echo -e "${BLUE}Overall Status:${NC} ${RED}$overall_status${NC}" ;;
    esac
    
    case "$hpc_readiness" in
        "FULLY_READY") echo -e "${BLUE}HPC Readiness:${NC} ${GREEN}$hpc_readiness${NC}" ;;
        "MOSTLY_READY") echo -e "${BLUE}HPC Readiness:${NC} ${CYAN}$hpc_readiness${NC}" ;;
        "PARTIALLY_READY") echo -e "${BLUE}HPC Readiness:${NC} ${YELLOW}$hpc_readiness${NC}" ;;
        *) echo -e "${BLUE}HPC Readiness:${NC} ${RED}$hpc_readiness${NC}" ;;
    esac
    
    echo -e "\n${YELLOW}Key Results:${NC}"
    
    # Tesla GPUs
    if [[ "${test_results[tesla_available]:-false}" != "false" ]]; then
        local tesla_status="${test_results[tesla_performance]:-UNKNOWN}"
        echo -e "  Tesla GPUs: ${tesla_status}"
        if [[ -n "${test_results[tesla_matmul_gflops]:-}" ]]; then
            echo -e "    Performance: ${test_results[tesla_matmul_gflops]} GFLOPS"
        fi
    fi
    
    # Xeon Phi
    if [[ "${test_results[xeon_phi_available]:-false}" != "false" ]]; then
        echo -e "  Xeon Phi: Available"
        if [[ -n "${test_results[phi_memory_bandwidth]:-}" ]]; then
            echo -e "    Memory Bandwidth: ${test_results[phi_memory_bandwidth]} GB/s"
        fi
    fi
    
    # MPI
    if [[ "${test_results[mpi_available]:-}" == "true" ]]; then
        echo -e "  MPI: ${test_results[mpi_basic_test]:-UNKNOWN}"
    fi
    
    # Scientific Libraries
    if [[ -n "${test_results[libraries_completion]:-}" ]]; then
        echo -e "  Scientific Libraries: ${test_results[libraries_completion]}% complete"
    fi
    
    echo -e "\n${CYAN}Full Report:${NC} $RESULTS_FILE"
    echo -e "${CYAN}Logs:${NC} $LOG_FILE"
}

# Main validation workflow
main() {
    log_info "Starting HPC performance validation suite..."
    
    # Initialize
    initialize_validation
    
    # Run validation tests
    validate_system_baseline
    validate_tesla_performance
    validate_xeon_phi_performance
    validate_mpi_performance
    validate_scientific_libraries
    
    # Generate results
    generate_results_report
    
    log_success "HPC performance validation completed!"
    
    # Return appropriate exit code
    local overall_status=$(calculate_overall_status)
    case "$overall_status" in
        "EXCELLENT"|"GOOD") exit 0 ;;
        "FAIR") exit 1 ;;
        *) exit 2 ;;
    esac
}

# Execute main function
main "$@"