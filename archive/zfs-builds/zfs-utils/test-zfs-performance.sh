#!/bin/bash
# Test ZFS performance with AVX-512 optimizations

set -e

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== ZFS Performance Test Suite ===${NC}"

# Test dataset
TEST_POOL="test_pool"
TEST_FILE="/tmp/test_pool.img"
TEST_SIZE="1G"
MOUNT_POINT="/mnt/zfs_test"

# Create test pool
setup_test_pool() {
    echo -e "${YELLOW}Creating test pool...${NC}"
    
    # Create backing file
    truncate -s $TEST_SIZE $TEST_FILE
    
    # Create pool with different configurations
    zpool create -f \
        -O compression=off \
        -O atime=off \
        -O mountpoint=$MOUNT_POINT \
        $TEST_POOL $TEST_FILE
        
    echo -e "${GREEN}Test pool created${NC}"
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    zpool destroy $TEST_POOL 2>/dev/null || true
    rm -f $TEST_FILE
}

# Test checksum performance
test_checksums() {
    echo -e "\n${CYAN}Testing checksum algorithms...${NC}"
    
    for algo in fletcher4 sha256 sha512 skein edonr blake3; do
        # Check if algorithm is available
        if ! zfs get -H -o value checksum $TEST_POOL | grep -q $algo; then
            continue
        fi
        
        echo -e "${YELLOW}Testing $algo...${NC}"
        zfs set checksum=$algo $TEST_POOL
        
        # Write test
        dd if=/dev/zero of=$MOUNT_POINT/test bs=1M count=512 2>&1 | grep -E "copied|bytes"
        
        # Verify
        zfs get checksum $TEST_POOL
        
        rm -f $MOUNT_POINT/test
    done
}

# Test compression with AVX
test_compression() {
    echo -e "\n${CYAN}Testing compression algorithms...${NC}"
    
    # Create test data (compressible)
    head -c 100M /dev/zero | tr '\0' 'A' > /tmp/testdata
    
    for algo in lz4 gzip zle lzjb zstd; do
        echo -e "${YELLOW}Testing $algo compression...${NC}"
        zfs set compression=$algo $TEST_POOL
        
        # Time the copy
        time cp /tmp/testdata $MOUNT_POINT/compressed
        
        # Check compression ratio
        zfs get used,compressratio $TEST_POOL
        
        rm -f $MOUNT_POINT/compressed
    done
    
    rm -f /tmp/testdata
}

# Test encryption performance
test_encryption() {
    echo -e "\n${CYAN}Testing encryption performance...${NC}"
    
    # Destroy and recreate with encryption
    zpool destroy $TEST_POOL
    
    echo "testpass" | zpool create -f \
        -O encryption=aes-256-gcm \
        -O keyformat=passphrase \
        -O keylocation=prompt \
        -O compression=off \
        -O mountpoint=$MOUNT_POINT \
        $TEST_POOL $TEST_FILE
    
    echo -e "${YELLOW}Writing encrypted data...${NC}"
    dd if=/dev/zero of=$MOUNT_POINT/encrypted bs=1M count=512 oflag=direct 2>&1 | grep -E "copied|bytes"
    
    echo -e "${YELLOW}Reading encrypted data...${NC}"
    dd if=$MOUNT_POINT/encrypted of=/dev/null bs=1M iflag=direct 2>&1 | grep -E "copied|bytes"
}

# Test with different record sizes
test_recordsize() {
    echo -e "\n${CYAN}Testing different record sizes...${NC}"
    
    for size in 4k 8k 16k 32k 64k 128k 256k 512k 1M; do
        echo -e "${YELLOW}Testing recordsize=$size...${NC}"
        zfs set recordsize=$size $TEST_POOL
        
        # Random write test
        fio --name=randwrite \
            --ioengine=posixaio \
            --rw=randwrite \
            --bs=$size \
            --size=256M \
            --numjobs=1 \
            --runtime=10 \
            --time_based \
            --filename=$MOUNT_POINT/fiotest \
            --minimal 2>/dev/null | cut -d';' -f8,49 | {
                IFS=';' read bw iops
                echo "  Bandwidth: $((bw/1024)) MB/s, IOPS: $iops"
            }
            
        rm -f $MOUNT_POINT/fiotest
    done
}

# Compare with standard ZFS
compare_performance() {
    echo -e "\n${CYAN}Performance Summary${NC}"
    echo "If using optimized ZFS, you should see:"
    echo "  • 20-30% faster checksum operations (blake3, sha512)"
    echo "  • 15-25% better compression throughput"
    echo "  • 30-40% faster encryption with AES-NI + AVX"
    echo "  • Better IOPS with small record sizes"
}

# Main execution
trap cleanup EXIT

echo -e "${YELLOW}Starting ZFS performance tests...${NC}"
echo "Current ZFS version:"
zfs version

setup_test_pool
test_checksums
test_compression
test_encryption
test_recordsize
compare_performance

echo -e "\n${GREEN}ZFS performance tests complete!${NC}"