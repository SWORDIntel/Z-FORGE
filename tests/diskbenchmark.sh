#!/bin/bash

#####################################################################
# ZFS Performance Tester
# Purpose: Comprehensive testing of storage devices, CPU, and RAM
#          to determine optimal ZFS settings
#
# Requirements: sysbench, fio, dialog
# Usage: sudo bash ./zfs_performance_test.sh
#####################################################################

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root. Please use sudo."
    exit 1
fi

# Check required packages
check_requirements() {
    local missing_packages=()

    for pkg in sysbench fio dialog smartmontools lshw; do
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
    echo "" >> "$report_file"

    echo "Log file created at: $log_file"
    echo "Report file will be saved to: $report_file"
}

# Function to log messages to both console and log file
log_message() {
    echo "$1" | tee -a "$log_file"
    # Calculate percentage for progress bar if provided
    if [ $# -eq 2 ]; then
        echo "$2" > "$log_dir/progress.txt"
    fi
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
    mapfile -t devices < <(lsblk -d -o NAME,TYPE,SIZE,MODEL | grep -E 'disk' | awk '{print $1}')

    if [ ${#devices[@]} -eq 0 ]; then
        log_message "No storage devices found!" 25
        return 1
    fi

    device_info="| Device | Model | Size | Type | Rotational | SMART Status |\n"
    device_info+="| ------ | ----- | ---- | ---- | ---------- | ------------ |\n"

    for device in "${devices[@]}"; do
        model=$(lsblk -d -o NAME,MODEL | grep "$device" | awk '{$1=""; print $0}' | sed 's/^[ \t]*//')
        size=$(lsblk -d -o NAME,SIZE | grep "$device" | awk '{print $2}')
        is_rotational=$(cat "/sys/block/$device/queue/rotational")
        type="HDD"
        if [ "$is_rotational" -eq 0 ]; then
            type="SSD"
        fi

        # Check SMART status if available
        if command -v smartctl &> /dev/null; then
            smart_status=$(smartctl -H "/dev/$device" | grep "SMART overall-health" | awk '{print $6}')
            if [ -z "$smart_status" ]; then
                smart_status="N/A"
            fi
        else
            smart_status="N/A (smartmontools not installed)"
        fi

        device_info+="| /dev/$device | $model | $size | $type | $is_rotational | $smart_status |\n"

        # Add to global arrays for later
        all_devices+=("/dev/$device")
        device_types+=("$type")
    done

    echo -e "$device_info" | column -t -s "|" >> "$report_file"
    echo "" >> "$report_file"
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

# Run storage benchmarks with fio
run_storage_benchmark() {
    log_message "## Storage Benchmark Testing" 60
    echo "## Storage Device Benchmarks" >> "$report_file"

    # Create array to store device benchmark data for comparison
    declare -a device_results

    for i in "${!all_devices[@]}"; do
        device=${all_devices[$i]}
        device_name=$(basename "$device")
        device_type=${device_types[$i]}

        log_message "Testing device $device ($device_type)..." $((60 + i*10/total_devices))

        # Create a test directory
        test_dir="/tmp/zfs_test_${device_name}"
        mkdir -p "$test_dir"

        # Run sequential read test
        log_message "Running sequential read test on $device..."
        seq_read=$(fio --name=seq-read --filename="$device" --direct=1 --rw=read --bs=1M --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

        # Run sequential write test
        log_message "Running sequential write test on $device..."
        seq_write=$(fio --name=seq-write --filename="$device" --direct=1 --rw=write --bs=1M --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

        # Run random read test
        log_message "Running random read test on $device..."
        rand_read=$(fio --name=rand-read --filename="$device" --direct=1 --rw=randread --bs=4k --size=1G --numjobs=1 --time_based --runtime=30 --group_reporting --output-format=json 2>/dev/null || echo '{"error": "Device access failed"}')

        # Run random write test
        log_message "Running random write test on $device..."
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

        # Record results in report
        echo "### Device: $device ($device_type)" >> "$report_file"
        echo "| Test Type | Performance |" >> "$report_file"
        echo "| --------- | ----------- |" >> "$report_file"
        echo "| Sequential Read | $seq_read_bw |" >> "$report_file"
        echo "| Sequential Write | $seq_write_bw |" >> "$report_file"
        echo "| Random Read | $rand_read_iops |" >> "$report_file"
        echo "| Random Write | $rand_write_iops |" >> "$report_file"
        echo "" >> "$report_file"

        rm -rf "$test_dir"
    done
}

# Generate ZFS recommendations based on test results
generate_zfs_recommendations() {
    log_message "## Generating ZFS Recommendations" 90
    echo "## ZFS Recommendations" >> "$report_file"

    # Sort devices by sequential read performance
    IFS=$'\n' sorted_devices=($(for dev in "${device_results[@]}"; do
        echo "$dev";
    done | sort -t: -k2 -r))

    # Identify fastest devices
    fastest_device=$(echo "${sorted_devices[0]}" | cut -d: -f1)
    fastest_device_type=$(echo "${sorted_devices[0]}" | cut -d: -f6)

    # Count SSDs and HDDs
    ssd_count=0
    hdd_count=0

    for device in "${device_results[@]}"; do
        device_type=$(echo "$device" | cut -d: -f6)
        if [[ "$device_type" == "SSD" ]]; then
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

    echo "# Set recordsize based on workload" >> "$report_file"
    echo "# For databases:" >> "$report_file"
    echo "# zfs set recordsize=8K datapool/database" >> "$report_file"
    echo "# For general storage:" >> "$report_file"
    echo "# zfs set recordsize=128K datapool/storage" >> "$report_file"
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
    echo "# options zfs zfs_arc_max=$arc_bytes" >> "$report_file"

    if [[ "$cpu_cores" -ge 8 ]]; then
        echo "# options zfs zfs_prefetch_disable=0" >> "$report_file"
    else
        echo "# options zfs zfs_prefetch_disable=1" >> "$report_file"
    fi

    echo '```' >> "$report_file"

    log_message "ZFS recommendations generated and saved to $report_file" 95
}

# Main dialog GUI function
show_dialog() {
    # Get terminal size
    term_height=$(tput lines)
    term_width=$(tput cols)
    dialog_height=$((term_height - 6))
    dialog_width=$((term_width - 10))

    # Welcome dialog
    dialog --title "ZFS Performance Tester" \
           --msgbox "This tool will analyze your system hardware and provide optimal ZFS configuration recommendations.\n\nThe following tests will be performed:\n- System information collection\n- CPU benchmark\n- Memory benchmark\n- Storage device benchmarks\n\nPress OK to start." \
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
}

# Global variables
declare -a all_devices
declare -a device_types
total_devices=0

# Main execution
show_dialog

# Final cleanup
clear
echo "ZFS Performance Test Completed"
echo "==============================="
echo ""
echo "Results and recommendations have been saved to:"
echo "$report_file"
echo ""
echo "Thank you for using the ZFS Performance Tester!"
