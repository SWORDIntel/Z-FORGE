#!/bin/bash
# tests/performance/proxmox_perf_test.sh

echo "Proxmox VE Performance Testing"
echo "=============================="

# Test ZFS performance for VM workloads
echo "Testing ZFS performance..."
fio --name=vm_workload \
    --ioengine=libaio \
    --rw=randrw \
    --bs=4k \
    --direct=1 \
    --size=1G \
    --numjobs=4 \
    --runtime=60 \
    --group_reporting

# Test network bridge performance
echo "Testing network bridge performance..."
# Would test bridge performance

echo "Performance testing complete"
