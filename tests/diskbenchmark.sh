#!/bin/bash
#####################################################################
# ZFS Performance Tester
# Purpose: Comprehensive testing of storage devices, CPU, and RAM
#          to determine optimal ZFS settings
#
# Requirements: sysbench, fio, dialog, smartmontools, jq
# Usage: sudo bash ./zfs_performance_test.sh [--safe-mode]
#####################################################################

VERSION="2.0"

# Process command line arguments
SAFE_MODE=false
COMMAND_MODE=false
SELECTED_DEVICES=""

for arg in "$@"; do
    case $arg in
        --safe-mode)
            SAFE_MODE=true
            shift
            ;;
        --command-line)
            COMMAND_MODE=true
            shift
            ;;
        --devices=*)
            SELECTED_DEVICES="${arg#*=}"
            shift
            ;;
        --help)
            echo "ZFS Performance Tester v$VERSION"
            echo "Usage: sudo bash $0 [options]"
            echo ""
            echo "Options:"
            echo "  --safe-mode         Run in safe mode (non-destructive tests only)"
            echo "  --command-line      Run in command-line mode (no dialog UI)"
            echo "  --devices=dev1,dev2 Specify comma-separated device list to test"
            echo "  --help              Show this help message"
            exit 0
            ;;
    esac
done

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Check required packages
check_requirements() {
    local missing_packages=()
    for pkg in sysbench fio dialog smartmontools lshw jq; do
        if ! command -v "$pkg" &> /dev/null; then
            missing_packages+=("$pkg")
        fi
    done

    if [ ${#missing_packages[@]} -ne 0 ]; then
        echo "Missing required packages: ${missing_packages[*]}"
        read -p "Install them now? (y/n): " install_choice
        if [[ "$install_choice" == "y" || "$install_choice" == "Y" ]]; then
            apt-get update
            apt-get install -y "${missing_packages[@]}"
        else
            echo "Required packages missing. Exiting."
            exit 1
        fi
    fi
}

# Initialize log file with timestamp
init_log_file() {
    log_dir="$HOME/zfs_test_results"
    mkdir -p "$log_dir"
    timestamp=$(date +"%Y%m%d_%H%M%S")
    log_file="$log_dir/zfs_test_$timestamp.log"
    report_file="$log_dir/zfs_test_report_$timestamp.md"

    echo "# ZFS Performance Test Results" > "$report_file"
    echo "Date: $(date)" >> "$report_file"
    echo "System: $(hostname)" >> "$report_file"
    echo "Test Mode: $(if $SAFE_MODE; then echo "Safe Mode (Non-destructive)"; else echo "Standard Mode"; fi)" >> "$report_file"
    echo "" >> "$report_file"

    echo "Log file created at: $log_file"
    echo "Report file will be saved to: $report_file"
}

# Function to log messages to both console and log file
log_message() {
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] $1" | tee -a "$log_file"
    # Calculate percentage for progress bar if provided
    if [ $# -eq 2 ]; then
        echo "$2" > "$log_dir/progress.txt"
    fi
}

# Function to check if a device is safe to test
check_device_safety() {
    local device=$1

    # Check if device is mounted
    if grep -q "$device " /proc/mounts; then
        log_message "WARNING: Device $device is currently mounted. Testing mounted devices can cause data corruption."
        if $COMMAND_MODE; then
            log_message "Skipping device $device in command-line mode for safety"
            return 1
        fi
        dialog --title "WARNING" --yesno "Device $device is currently mounted. Testing mounted devices can cause data corruption.\n\nDo you want to continue testing this device?" 10 60
        if [ $? -ne 0 ]; then
            log_message "User chose to skip testing mounted device $device"
            return 1
        fi
        log_message "User chose to test mounted device $device despite warnings"
    fi

    # Check if device is part of a RAID or ZFS pool
    if command -v mdadm &> /dev/null && mdadm --detail "$device" &> /dev/null; then
        log_message "WARNING: Device $device appears to be part of a RAID array."
        if $COMMAND_MODE; then
            log_message "Skipping device $device in command-line mode for safety"
            return 1
        fi
        dialog --title "WARNING" --yesno "Device $device appears to be part of a RAID array.\n\nDo you want to continue testing this device?" 10 60
        if [ $? -ne 0 ]; then
            log_message "User chose to skip testing device $device in RAID array"
            return 1
        fi
        log_message "User chose to test device $device in RAID array despite warnings"
    fi

    if command -v zpool &> /dev/null && zpool status 2>/dev/null | grep -q "$(basename "$device")"; then
        log_message "WARNING: Device $device appears to be part of a ZFS pool."
        if $COMMAND_MODE; then
            log_message "Skipping device $device in command-line mode for safety"
            return 1
        fi
        dialog --title "WARNING" --yesno "Device $device appears to be part of a ZFS pool.\n\nDo you want to continue testing this device?" 10 60
        if [ $? -ne 0 ]; then
            log_message "User chose to skip testing device $device in ZFS pool"
            return 1
        fi
        log_message "User chose to test device $device in ZFS pool despite warnings"
    fi

    return 0
}

# Function to run non-destructive test (safe mode)
run_nondestructive_test() {
    local device=$1
    local device_name=$(basename "$device")
    local device_type=$2

    log_message "Running non-destructive test on $device..."

    # Create temp file for testing
    local test_dir="/tmp/zfs_test_${device_name}"
    mkdir -p "$test_dir"
    local test_file="$test_dir/${device_name}_test.bin"

    # Create test file only if it doesn't exist
    if [ ! -f "$test_file" ]; then
        log_message "Creating test file for non-destructive testing..."
        dd if=/dev/zero of="$test_file" bs=1M count=1024 status=none
    fi

    # Run read tests only
    log_message "Running sequential read test on test file..."
    local seq_read=$(fio --name=seq-read --filename="$test_file" --direct=1 --rw=read --bs=1M --size=1G --numjobs=1 --time_based --runtime=10 --group_reporting --output-format=json 2>/dev/null)

    log_message "Running random read test on test file..."
    local rand_read=$(fio --name=rand-read --filename="$test_file" --direct=1 --rw=randread --bs=4k --size=1G --numjobs=1 --time_based --runtime=10 --group_reporting --output-format=json 2>/dev/null)

    # Process results
    local seq_read_bw=$(echo "$seq_read" | jq -r '.jobs[0].read.bw' 2>/dev/null)
    seq_read_bw=$((seq_read_bw / 1024))" MB/s"

    local rand_read_iops=$(echo "$rand_read" | jq -r '.jobs[0].read.iops' 2>/dev/null)
    rand_read_iops=$(printf "%.0f" "$rand_read_iops")" IOPS"

    # Cleanup
    rm -f "$test_file"
    rmdir "$test_dir" 2>/dev/null

    # Return formatted result (device:seq_read:seq_write:rand_read:rand_write:type)
    echo "$device:$seq_read_bw:N/A (safe mode):$rand_read_iops:N/A (safe mode):$device_type"
}

# Get system information
get_system_info() {
    log_message "## System Information" 5
    log_message "### CPU Information" 7
    cpu_info=$(lscpu)
    log_message "$cpu_info" 10
    cpu_model=$(echo "$cpu_info" | grep "Model name" | cut -d: -f2 | sed 's/^[ \t]*//')
    cpu_cores=$(echo "$cpu_info" | grep "^CPU(s):" | cut -d: -f2 | sed 's/^[ \t]*//')

    log_message "### Memory Information" 12
    mem_info=$(free -h)
    log_message "$mem_info" 15
    total_mem=$(echo "$mem_info" | grep "Mem:" | awk '{print $2}')

    log_message "### Storage Devices" 17
    lshw_info=$(lshw -class disk -short)
    log_message "$lshw_info" 20

    echo "## System Information" >> "$report_file"
    echo "- CPU: $cpu_model ($cpu_cores cores)" >> "$report_file"
    echo "- Memory: $total_mem" >> "$report_file"
    echo "" >> "$report_file"
    echo "## Storage Devices" >> "$report_file"

    # Get list of storage devices
    if [ -n "$SELECTED_DEVICES" ]; then
        # Use manually selected devices
        IFS=',' read -ra devices <<< "$SELECTED_DEVICES"
        # Convert to full device paths if needed
        for i in "${!devices[@]}"; do
            if [[ "${devices[$i]}" != /dev/* ]]; then
                devices[$i]="/dev/${devices[$i]}"
            fi
        done
    else
        # Get all disk devices
        mapfile -t devices < <(lsblk -d -o NAME,TYPE,SIZE,MODEL | grep -E 'disk' | awk '{print "/dev/"$1}')
    fi

    if [ ${#devices[@]} -eq 0 ]; then
        log_message "No storage devices found!" 25
        return 1
    fi

    device_info="| Device | Model | Size | Type | Rotational | SMART Status |\n"
    device_info+="| ------ | ----- | ---- | ---- | ---------- | ------------ |\n"

    for device in "${devices[@]}"; do
        device_name=$(basename "$device")
        model=$(lsblk -d -o NAME,MODEL | grep "$device_name" | awk '{$1=""; print $0}' | sed 's/^[ \t]*//')
        size=$(lsblk -d -o NAME,SIZE | grep "$device_name" | awk '{print $2}')
        is_rotational=$(cat "/sys/block/$device_name/queue/rotational" 2>/dev/null || echo "?")

        type="HDD"
        if [ "$is_rotational" = "0" ]; then
            type="SSD"
        fi

        # Check SMART status if available
        if command -v smartctl &> /dev/null; then
            smart_status=$(smartctl -H "$device" | grep "SMART overall-health" | awk '{print $6}' || echo "N/A")
            if [ -z "$smart_status" ]; then
                smart_status="N/A"
            fi
        else
            smart_status="N/A (smartmontools not installed)"
        fi

        device_info+="| $device | $model | $size | $type | $is_rotational | $smart_status |\n"

        # Add to global arrays for later if safety check passes
        if check_device_safety "$device"; then
            all_devices+=("$device")
            device_types+=("$type")
        fi
    done

    echo -e "$device_info" | column -t -s "|" >> "$report_file"
    echo "" >> "$report_file"

    # Update total count of tested devices
    total_devices=${#all_devices[@]}

    # Device selection in command-line mode if not specified
    if $COMMAND_MODE && [ -z "$SELECTED_DEVICES" ]; then
        echo "Detected devices:"
        for i in "${!all_devices[@]}"; do
            echo "  [$i] ${all_devices[$i]} (${device_types[$i]})"
        done
        read -p "Enter device numbers to test (comma-separated, or 'all'): " device_selection

        if [ "$device_selection" != "all" ]; then
            local selected_indices=()
            IFS=',' read -ra indices <<< "$device_selection"
            for idx in "${indices[@]}"; do
                if [ "$idx" -lt "${#all_devices[@]}" ]; then
                    selected_indices+=("$idx")
                fi
            done

            if [ ${#selected_indices[@]} -gt 0 ]; then
                local selected_devices=()
                local selected_types=()
                for idx in "${selected_indices[@]}"; do
                    selected_devices+=("${all_devices[$idx]}")
                    selected_types+=("${device_types[$idx]}")
                done
                all_devices=("${selected_devices[@]}")
                device_types=("${selected_types[@]}")
                total_devices=${#all_devices[@]}
            fi
        fi
    fi

    log_message "Selected ${#all_devices[@]} devices for testing"
    for i in "${!all_devices[@]}"; do
        log_message "  - ${all_devices[$i]} (${device_types[$i]})"
    done
}

# Run CPU benchmarks with sysbench
run_cpu_benchmark() {
    log_message "## CPU Benchmark Testing" 30
    echo "## CPU Benchmark Results" >> "$report_file"

    # Single-threaded CPU test
    log_message "Running single-threaded CPU test..." 32
    cpu_single=$(sysbench cpu --cpu-max-prime=20000 --threads=1 run 2>&1)
    log_message "Single-threaded CPU test completed" 35
    log_message "$cpu_single" 36

    # Multi-threaded CPU test
    log_message "Running multi-threaded CPU test..." 38
    cpu_multi=$(sysbench cpu --cpu-max-prime=20000 --threads="$cpu_cores" run 2>&1)
    log_message "Multi-threaded CPU test completed" 42
    log_message "$cpu_multi" 43

    # Extract results for the report
    single_events=$(echo "$cpu_single" | grep "events per second" | awk '{print $4}')
    multi_events=$(echo "$cpu_multi" | grep "events per second" | awk '{print $4}')

    echo "### Single-threaded Performance" >> "$report_file"
    echo "- Events per second: $single_events" >> "$report_file"
    echo "" >> "$report_file"

    echo "### Multi-threaded Performance" >> "$report_file"
    echo "- Events per second: $multi_events" >> "$report_file"
    echo "- Thread count: $cpu_cores" >> "$report_file"
    echo "" >> "$report_file"
}

# Run memory benchmarks with sysbench
run_memory_benchmark() {
    log_message "## Memory Benchmark Testing" 45
    echo "## Memory Benchmark Results" >> "$report_file"

    # Memory read test
    log_message "Running memory read test..." 47
    mem_read=$(sysbench memory --memory-block-size=1K --memory-total-size=100G --memory-access-mode=seq read run 2>&1)
    log_message "Memory read test completed" 50
    log_message "$mem_read" 51

    # Memory write test
    log_message "Running memory write test..." 53
    mem_write=$(sysbench memory --memory-block-size=1K --memory-total-size=100G --memory-access-mode=seq write run 2>&1)
    log_message "Memory write test completed" 55
    log_message "$mem_write" 56

    # Extract results
    read_ops=$(echo "$mem_read" | grep "transferred" | awk '{print $4" "$5}')
    read_speed=$(echo "$mem_read" | grep "MiB/sec" | awk '{print $2}')
    write_ops=$(echo "$mem_write" | grep "transferred" | awk '{print $4" "$5}')
    write_speed=$(echo "$mem_write" | grep "MiB/sec" | awk '{print $2}')

    echo "### Memory Performance" >> "$report_file"
    echo "- Read operations: $read_ops" >> "$report_file"
    echo "- Read speed: $read_speed MiB/sec" >> "$report_file"
    echo "- Write operations: $write_ops" >> "$report_file"
    echo "- Write speed: $write_speed MiB/sec" >> "$report_file"
    echo "" >> "$report_file"
}

# Run ZFS-specific workload tests
run_zfs_specific_tests() {
    log_message "## Running ZFS-specific workload tests" 80

    # Create test directory
    test_dir="/tmp/zfs_workload_test"
    mkdir -p "$test_dir"

    echo "### ZFS-Specific Workload Testing" >> "$report_file"
    echo "The following tests simulate real-world ZFS workloads:" >> "$report_file"
    echo "" >> "$report_file"

    # Deduplication workload test (random data with repetition)
    log_message "Testing deduplication-like workload..."
    dedup_test=$(fio --name=dedup-test --directory="$test_dir" --size=1G \
                    --bs=128K --buffer_pattern=0xdeadbeef \
                    --dedupe_percentage=30 \
                    --rw=randrw --rwmixread=70 --direct=1 --group_reporting \
                    --output-format=json 2>/dev/null || echo '{"error": "Test failed"}')

    # Database-like workload (small random I/O)
    log_message "Testing database-like workload..."
    db_test=$(fio --name=db-test --directory="$test_dir" --size=1G \
              --bs=8K --rw=randrw --rwmixread=70 --direct=1 --group_reporting \
              --output-format=json 2>/dev/null || echo '{"error": "Test failed"}')

    # VM workload (mixed block size, mixed read/write)
    log_message "Testing VM-like workload..."
    vm_test=$(fio --name=vm-test --directory="$test_dir" --size=1G \
             --bsrange=4K-64K --rw=randrw --rwmixread=60 \
             --rate_process=poisson --direct=1 --group_reporting \
             --output-format=json 2>/dev/null || echo '{"error": "Test failed"}')

    # Clean up
    rm -rf "$test_dir"

    # Add results to report
    echo "| Workload Type | Read IOPS | Write IOPS | Read BW | Write BW |" >> "$report_file"
    echo "| ------------ | --------- | ---------- | ------- | -------- |" >> "$report_file"

    # Process dedup workload results
    if [[ "$dedup_test" == *"error"* ]]; then
        echo "| Deduplication | Error | Error | Error | Error |" >> "$report_file"
    else
        dedup_read_iops=$(echo "$dedup_test" | jq -r '.jobs[0].read.iops' 2>/dev/null || echo "N/A")
        dedup_write_iops=$(echo "$dedup_test" | jq -r '.jobs[0].write.iops' 2>/dev/null || echo "N/A")
        dedup_read_bw=$(($(echo "$dedup_test" | jq -r '.jobs[0].read.bw' 2>/dev/null || echo 0) / 1024))
        dedup_write_bw=$(($(echo "$dedup_test" | jq -r '.jobs[0].write.bw' 2>/dev/null || echo 0) / 1024))
        echo "| Deduplication | $dedup_read_iops | $dedup_write_iops | $dedup_read_bw MB/s | $dedup_write_bw MB/s |" >> "$report_file"
    fi

    # Process database workload results
    if [[ "$db_test" == *"error"* ]]; then
        echo "| Database | Error | Error | Error | Error |" >> "$report_file"
    else
        db_read_iops=$(echo "$db_test" | jq -r '.jobs[0].read.iops' 2>/dev/null || echo "N/A")
        db_write_iops=$(echo "$db_test" | jq -r '.jobs[0].write.iops' 2>/dev/null || echo "N/A")
        db_read_bw=$(($(echo "$db_test" | jq -r '.jobs[0].read.bw' 2>/dev/null || echo 0) / 1024))
        db_write_bw=$(($(echo "$db_test" | jq -r '.jobs[0].write.bw' 2>/dev/null || echo 0) / 1024))
        echo "| Database | $db_read_iops | $db_write_iops | $db_read_bw MB/s | $db_write_bw MB/s |" >> "$report_file"
    fi

    # Process VM workload results
    if [[ "$vm_test" == *"error"* ]]; then
        echo "| VM | Error | Error | Error | Error |" >> "$report_file"
    else
        vm_read_iops=$(echo "$vm_test" | jq -r '.jobs[0].read.iops' 2>/dev/null || echo "N/A")
        vm_write_iops=$(echo "$vm_test" | jq -r '.jobs[0].write.iops' 2>/dev/null || echo "N/A")
        vm_read_bw=$(($(echo "$vm_test" | jq -r '.jobs[0].read.bw' 2>/dev/null || echo 0) / 1024))
        vm_write_bw=$(($(echo "$vm_test" | jq -r '.jobs[0].write.bw' 2>/dev/null || echo 0) / 1024))
        echo "| VM | $vm_read_iops | $vm_write_iops | $vm_read_bw MB/s | $vm_write_bw MB/s |" >> "$report_file"
    fi

    echo "" >> "$report_file"
    echo "These workloads help determine optimal ZFS configuration for specific use cases:" >> "$report_file"
    echo "- **Deduplication**: Tests performance with partially duplicate data (important for dedup settings)" >> "$report_file"
    echo "- **Database**: Small block size random I/O typical of database workloads" >> "$report_file"
    echo "- **VM**: Variable block size with mixed read/write typical of virtual machine storage" >> "$report_file"
    echo "" >> "$report_file"
}

# Run storage benchmarks with fio
run_storage_benchmark() {
    log_message "## Storage Benchmark Testing" 60
    echo "## Storage Device Benchmarks" >> "$report_file"

    # Create array to store device benchmark data for comparison
    declare -a device_results

    # Progress variables for more accurate reporting
    local total_tests=$(($total_devices * 4))  # 4 tests per device
    local test_num=0

    for i in "${!all_devices[@]}"; do
        device=${all_devices[$i]}
        device_name=$(basename "$device")
        device_type=${device_types[$i]}

        log_message "Testing device $device ($device_type)..." $((60 + i*10/total_devices))

        # Handle safe mode vs. standard mode testing
        if $SAFE_MODE; then
            log_message "Running non-destructive tests in safe mode"
            result=$(run_nondestructive_test "$device" "$device_type")
            device_results+=("$result")
        else
            # Create a test directory
            test_dir="/tmp/zfs_test_${device_name}"
            mkdir -p "$test_dir"

            # Run sequential read test
            test_num=$((test_num + 1))
            log_message "Running sequential read test on $device... (test $test_num/$total_tests)"
            seq_read=$(fio --name=seq-read --filename="$device" --direct=1 --rw=read --bs=1M --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

            # Run sequential write test
            test_num=$((test_num + 1))
            log_message "Running sequential write test on $device... (test $test_num/$total_tests)"
            seq_write=$(fio --name=seq-write --filename="$device" --direct=1 --rw=write --bs=1M --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

            # Run random read test
            test_num=$((test_num + 1))
            log_message "Running random read test on $device... (test $test_num/$total_tests)"
            rand_read=$(fio --name=rand-read --filename="$device" --direct=1 --rw=randread --bs=4k --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

            # Run random write test
            test_num=$((test_num + 1))
            log_message "Running random write test on $device... (test $test_num/$total_tests)"
            rand_write=$(fio --name=rand-write --filename="$device" --direct=1 --rw=randwrite --bs=4k --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

            # Extract results
            if [[ "$seq_read" == *"error"* ]]; then
                seq_read_bw="ERROR"
                log_message "Error testing $device. Make sure it's not mounted or in use."
            else
                seq_read_bw=$(echo "$seq_read" | jq -r '.jobs[0].read.bw' 2>/dev/null || echo "N/A")
                seq_read_bw=$((seq_read_bw / 1024))" MB/s"
            fi

            if [[ "$seq_write" == *"error"* ]]; then
                seq_write_bw="ERROR"
            else
                seq_write_bw=$(echo "$seq_write" | jq -r '.jobs[0].write.bw' 2>/dev/null || echo "N/A")
                seq_write_bw=$((seq_write_bw / 1024))" MB/s"
            fi

            if [[ "$rand_read" == *"error"* ]]; then
                rand_read_iops="ERROR"
            else
                rand_read_iops=$(echo "$rand_read" | jq -r '.jobs[0].read.iops' 2>/dev/null || echo "N/A")
                rand_read_iops=$(printf "%.0f" "$rand_read_iops")" IOPS"
            fi

            if [[ "$rand_write" == *"error"* ]]; then
                rand_write_iops="ERROR"
            else
                rand_write_iops=$(echo "$rand_write" | jq -r '.jobs[0].write.iops' 2>/dev/null || echo "N/A")
                rand_write_iops=$(printf "%.0f" "$rand_write_iops")" IOPS"
            fi

            # Store results for comparison
            if [[ "$seq_read_bw" != "ERROR" ]]; then
                device_results+=("$device:$seq_read_bw:$seq_write_bw:$rand_read_iops:$rand_write_iops:$device_type")
            fi

            rm -rf "$test_dir"
        fi

        # Record results in report
        echo "### Device: $device ($device_type)" >> "$report_file"

        if $SAFE_MODE; then
            # Safe mode results
            read -r device seq_read_bw seq_write_bw rand_read_iops rand_write_iops device_type <<< $(echo "${device_results[-1]}" | tr ':' ' ')
            echo "**Note: Running in safe mode with non-destructive tests only**" >> "$report_file"
        fi

        echo "| Test Type | Performance |" >> "$report_file"
        echo "| --------- | ----------- |" >> "$report_file"
        echo "| Sequential Read | $seq_read_bw |" >> "$report_file"
        echo "| Sequential Write | $seq_write_bw |" >> "$report_file"
        echo "| Random Read | $rand_read_iops |" >> "$report_file"
        echo "| Random Write | $rand_write_iops |" >> "$report_file"
        echo "" >> "$report_file"
    done

    # Run ZFS-specific workload tests
    if ! $SAFE_MODE; then
        run_zfs_specific_tests
    else
        echo "### ZFS-Specific Workload Testing" >> "$report_file"
        echo "**Note: ZFS workload tests were skipped in safe mode.**" >> "$report_file"
        echo "" >> "$report_file"
    fi
}

# Generate ZFS recommendations based on test results
generate_zfs_recommendations() {
    log_message "## Generating ZFS Recommendations" 90
    echo "## ZFS Recommendations" >> "$report_file"

    # Sort devices by sequential read performance
    if [ ${#device_results[@]} -gt 0 ]; then
        IFS=$'\n' sorted_devices=($(for dev in "${device_results[@]}"; do
            echo "$dev";
        done | sort -t: -k2 -r))

        # Identify fastest devices
        fastest_device=$(echo "${sorted_devices[0]}" | cut -d: -f1)
        fastest_device_type=$(echo "${sorted_devices[0]}" | cut -d: -f6)
    else
        fastest_device="unknown"
        fastest_device_type="unknown"
    fi

    # Count SSDs and HDDs
    ssd_count=0
    hdd_count=0
    for device in "${device_types[@]}"; do
        if [[ "$device" == "SSD" ]]; then
            ((ssd_count++))
        else
            ((hdd_count++))
        fi
    done

    # Generate recommendations
    echo "Based on the benchmark results, here are some recommended ZFS configurations:" >> "$report_file"
    echo "" >> "$report_file"

    # Pool configuration recommendations
    echo "### Pool Configuration" >> "$report_file"
    if [[ $ssd_count -ge 2 && $hdd_count -ge 2 ]]; then
        echo "**Recommended: Hybrid Pool Configuration**" >> "$report_file"
        echo "" >> "$report_file"
        echo "- Create a mirror or RAID-Z1 with SSDs for LOG and cache devices" >> "$report_file"
        echo "- Use HDDs in RAID-Z2 for the main storage pool" >> "$report_file"
        echo "- Command example:" >> "$report_file"
        echo '```bash' >> "$report_file"
        echo "# Create main pool with HDDs" >> "$report_file"
        echo "zpool create datapool raidz2 /dev/hdd1 /dev/hdd2 /dev/hdd3 /dev/hdd4" >> "$report_file"
        echo "" >> "$report_file"
        echo "# Add SSD special devices" >> "$report_file"
        echo "zpool add datapool log mirror /dev/ssd1 /dev/ssd2" >> "$report_file"
        echo "zpool add datapool cache /dev/ssd3" >> "$report_file"
        echo '```' >> "$report_file"
    elif [[ $ssd_count -ge 4 ]]; then
        echo "**Recommended: All-Flash Pool Configuration**" >> "$report_file"
        echo "" >> "$report_file"
        echo "- Create a RAID-Z1 or mirror configuration with SSDs" >> "$report_file"
        echo "- Command example:" >> "$report_file"
        echo '```bash' >> "$report_file"
        echo "# Create all-flash pool with SSDs in RAID-Z1" >> "$report_file"
        echo "zpool create datapool raidz1 /dev/ssd1 /dev/ssd2 /dev/ssd3 /dev/ssd4" >> "$report_file"
        echo '```' >> "$report_file"
    elif [[ $hdd_count -ge 4 ]]; then
        echo "**Recommended: HDD-based Pool with SSD Cache**" >> "$report_file"
        echo "" >> "$report_file"
        echo "- Create a RAID-Z2 configuration with HDDs" >> "$report_file"
        echo "- If available, use an SSD for ZIL/LOG and L2ARC cache" >> "$report_file"
        echo "- Command example:" >> "$report_file"
        echo '```bash' >> "$report_file"
        echo "# Create HDD-based pool" >> "$report_file"
        echo "zpool create datapool raidz2 /dev/hdd1 /dev/hdd2 /dev/hdd3 /dev/hdd4" >> "$report_file"
        if [[ $ssd_count -ge 1 ]]; then
            echo "" >> "$report_file"
            echo "# Add SSD as cache" >> "$report_file"
            echo "zpool add datapool cache /dev/ssd1" >> "$report_file"
        fi
        echo '```' >> "$report_file"
    else
        echo "**Recommended: Basic Mirror Configuration**" >> "$report_file"
        echo "" >> "$report_file"
        echo "- Create a mirror configuration with available devices" >> "$report_file"
        echo "- Command example:" >> "$report_file"
        echo '```bash' >> "$report_file"
        echo "# Create mirror pool" >> "$report_file"
        echo "zpool create datapool mirror /dev/disk1 /dev/disk2" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    # ZFS properties recommendations
    echo "### ZFS Properties" >> "$report_file"
    echo "Based on system analysis, the following ZFS properties are recommended:" >> "$report_file"
    echo "" >> "$report_file"
    echo "**General Settings:**" >> "$report_file"
    echo '```bash' >> "$report_file"
    echo "# Set compression" >> "$report_file"
    if [[ "$cpu_cores" -ge 8 ]]; then
        echo "zfs set compression=zstd-3 datapool" >> "$report_file"
    else
        echo "zfs set compression=lz4 datapool" >> "$report_file"
    fi
    echo "" >> "$report_file"
    echo "# Set atime" >> "$report_file"
    echo "zfs set atime=off datapool" >> "$report_file"
    echo "" >> "$report_file"
    if [[ $ssd_count -ge 1 ]]; then
        echo "# Set special_small_blocks" >> "$report_file"
        echo "zfs set special_small_blocks=16K datapool" >> "$report_file"
        echo "" >> "$report_file"
    fi

    # Add workload-specific recommendations based on ZFS workload tests
    echo "# Workload-specific settings" >> "$report_file"
    echo "# For databases:" >> "$report_file"
    echo "zfs create datapool/database" >> "$report_file"
    echo "zfs set recordsize=8K datapool/database" >> "$report_file"
    echo "zfs set primarycache=metadata datapool/database" >> "$report_file"
    echo "zfs set logbias=throughput datapool/database" >> "$report_file"
    echo "" >> "$report_file"

    echo "# For VM storage:" >> "$report_file"
    echo "zfs create datapool/vm" >> "$report_file"
    echo "zfs set recordsize=64K datapool/vm" >> "$report_file"
    echo "zfs set checksum=fletcher4 datapool/vm" >> "$report_file"
    echo "" >> "$report_file"

    echo "# For general storage:" >> "$report_file"
    echo "zfs create datapool/storage" >> "$report_file"
    echo "zfs set recordsize=128K datapool/storage" >> "$report_file"
    echo '```' >> "$report_file"

    # System tuning recommendations
    echo "### System Tuning for ZFS" >> "$report_file"
    echo "Recommended settings for /etc/sysctl.conf:" >> "$report_file"
    echo "" >> "$report_file"
    echo '```bash' >> "$report_file"

    # Calculate ARC size (50% of RAM but not more than 16GB)
    ram_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    ram_gb=$((ram_kb / 1024 / 1024))
    arc_size=$((ram_gb * 50 / 100))
    if [[ $arc_size -gt 16 ]]; then
        arc_size=16
    fi
    arc_bytes=$((arc_size * 1024 * 1024 * 1024))

    echo "# Maximum ARC size ($arc_size GB)" >> "$report_file"
    echo "vm.swappiness=10" >> "$report_file"
    echo "vm.min_free_kbytes=524288" >> "$report_file"
    echo "vm.dirty_background_ratio=10" >> "$report_file"
    echo "vm.dirty_ratio=20" >> "$report_file"
    echo "kernel.sched_migration_cost_ns=5000000" >> "$report_file"
    echo "" >> "$report_file"

    echo "# ZFS specific parameters" >> "$report_file"
    echo "# Note: These should be added to /etc/modprobe.d/zfs.conf" >> "$report_file"
    echo "options zfs zfs_arc_max=$arc_bytes" >> "$report_file"

    if [[ "$cpu_cores" -ge 8 ]]; then
        echo "options zfs zfs_prefetch_disable=0" >> "$report_file"
    else
        echo "options zfs zfs_prefetch_disable=1" >> "$report_file"
    fi
    echo '```' >> "$report_file"

    # L2ARC sizing recommendations if SSDs are available
    if [[ $ssd_count -ge 1 ]]; then
        echo "### L2ARC and Special VDEV Recommendations" >> "$report_file"
        echo "" >> "$report_file"
        echo "Based on the system configuration with $ssd_count SSDs and $ram_gb GB RAM:" >> "$report_file"
        echo "" >> "$report_file"
        echo "- **L2ARC Size**: Recommend setting L2ARC size to ${arc_size}GB (matching ARC size)" >> "$report_file"
        echo "- **L2ARC Write Rate**: Set l2arc_write_max to 8MB/s to avoid excessive SSD wear" >> "$report_file"
        echo "" >> "$report_file"
        echo '```bash' >> "$report_file"
        echo "# L2ARC tuning parameters for /etc/modprobe.d/zfs.conf" >> "$report_file"
        echo "options zfs l2arc_write_max=8388608    # 8MB/s" >> "$report_file"
        echo '```' >> "$report_file"
    fi

    log_message "ZFS recommendations generated and saved to $report_file" 95
}

# Command-line mode implementation
run_command_line_mode() {
    echo "ZFS Performance Tester v$VERSION - Command Line Mode"
    echo "==================================================="

    # Check requirements
    echo -n "Checking requirements... "
    check_requirements
    echo "done"

    # Initialize log
    echo -n "Creating log files... "
    init_log_file
    echo "done"

    # System information
    echo -n "Gathering system information... "
    get_system_info
    echo "done"

    # CPU benchmark
    echo "Running CPU benchmark..."
    run_cpu_benchmark
    echo "CPU benchmark completed"

    # Memory benchmark
    echo "Running memory benchmark..."
    run_memory_benchmark
    echo "Memory benchmark completed"

    # Storage benchmark
    echo "Running storage benchmark (this will take some time)..."
    run_storage_benchmark
    echo "Storage benchmark completed"

    # Generate recommendations
    echo "Generating ZFS recommendations..."
    generate_zfs_recommendations
    echo "Done"

    # Final output
    echo -e "\nZFS Performance Test Completed"
    echo "==============================="
    echo ""
    echo "Results and recommendations have been saved to:"
    echo "$report_file"
    echo ""
    echo "Thank you for using the ZFS Performance Tester!"
}

# Main dialog GUI function
show_dialog() {
    # Get terminal size
    term_height=$(tput lines)
    term_width=$(tput cols)
    dialog_height=$((term_height - 6))
    dialog_width=$((term_width - 10))

    # Welcome dialog
    dialog --title "ZFS Performance Tester v$VERSION" \
           --msgbox "This tool will analyze your system hardware and provide optimal ZFS configuration recommendations.\n\nThe following tests will be performed:\n- System information collection\n- CPU benchmark\n- Memory benchmark\n- Storage device benchmarks\n\nTest Mode: $(if $SAFE_MODE; then echo "SAFE MODE (non-destructive testing)"; else echo "STANDARD MODE"; fi)\n\nPress OK to start." \
           $dialog_height $dialog_width

    # Check requirements
    dialog --title "Checking Requirements" \
           --infobox "Verifying required packages..." \
           5 $dialog_width
    check_requirements

    # Initialize log
    dialog --title "Initializing" \
           --infobox "Creating log files..." \
           5 $dialog_width
    init_log_file

    # Progress gauge - this will run in a loop
    {
        # Run tests, updating progress
        get_system_info
        echo "25"
        sleep 1
        run_cpu_benchmark
        echo "50"
        sleep 1
        run_memory_benchmark
        echo "75"
        sleep 1
        run_storage_benchmark
        echo "90"
        sleep 1
        generate_zfs_recommendations
        echo "100"
        sleep 1
    } | dialog --title "ZFS Performance Test" \
               --gauge "Running system analysis..." \
               10 $dialog_width 0

    # Final results
    dialog --title "Test Complete" \
           --msgbox "All tests have been completed!\n\nResults and recommendations have been saved to:\n$report_file\n\nPress OK to exit." \
           10 $dialog_width

    # Option to open the report
    dialog --title "View Report" \
           --yesno "Would you like to view the report now?" \
           7 $dialog_width

    if [ $? -eq 0 ]; then
        # Check for available pagers in order of preference
        if command -v less &> /dev/null; then
            less "$report_file"
        elif command -v more &> /dev/null; then
            more "$report_file"
        elif command -v cat &> /dev/null; then
            cat "$report_file"
        else
            dialog --title "Error" \
                   --msgbox "No text viewer available. Please open $report_file manually." \
                   7 $dialog_width
        fi
    fi
}

# Global variables
declare -a all_devices
declare -a device_types
total_devices=0

# Main execution
if $COMMAND_MODE; then
    run_command_line_mode
else
    show_dialog
fi

# Final cleanup
clear
echo "ZFS Performance Test Completed"
echo "==============================="
echo ""
echo "Results and recommendations have been saved to:"
echo "$report_file"
echo ""
echo "Thank you for using the ZFS Performance Tester!"
