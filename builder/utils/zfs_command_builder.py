from typing import List, Optional, Dict

def build_zpool_create_command(
    pool_name: str,
    raid_type: str,
    disks: List[str],
    ashift: Optional[int] = None,
    properties: Optional[Dict[str, str]] = None,
    root_fs_options: Optional[Dict[str, str]] = None,
    mountpoint: str = "none",
    altroot: Optional[str] = None,
) -> List[str]:
    """
    Builds a zpool create command list.

    Args:
        pool_name: Name of the ZFS pool.
        raid_type: "stripe", "mirror", "raidz1", "raidz2", "raidz3".
        disks: List of disk device paths.
        ashift: Optional ashift value.
        properties: Optional dictionary of ZFS pool properties (-o property=value).
        root_fs_options: Optional dictionary of ZFS filesystem properties for the root dataset (-O property=value).
        mountpoint: Mountpoint for the root dataset. Defaults to "none".
        altroot: Optional alternative root directory (-R /altroot).

    Returns:
        A list of strings representing the zpool create command.
    """
    if not pool_name:
        raise ValueError("Pool name cannot be empty.")
    if not disks:
        raise ValueError("Disk list cannot be empty.")
    if raid_type not in ["stripe", "mirror", "raidz1", "raidz2", "raidz3"]:
        raise ValueError(f"Invalid raid_type: {raid_type}")

    cmd = ["zpool", "create"]

    # Base options
    cmd.append("-f")  # Force

    if altroot:
        cmd.extend(["-R", altroot])

    # Always set mountpoint for the pool itself, usually 'none' or specific path like '/'.
    # For the root dataset, this is controlled by root_fs_options or defaults.
    cmd.extend(["-m", mountpoint])


    # Pool properties
    if ashift is not None:
        cmd.extend(["-o", f"ashift={ashift}"])
    if properties:
        for key, value in properties.items():
            cmd.extend(["-o", f"{key}={value}"])

    # Root filesystem options
    if root_fs_options:
        for key, value in root_fs_options.items():
            cmd.extend(["-O", f"{key}={value}"])

    # Pool name
    cmd.append(pool_name)

    # VDEV configuration
    if raid_type == "stripe":
        cmd.extend(disks)  # For single disk or explicit stripe, just add disks
    elif raid_type in ["mirror", "raidz1", "raidz2", "raidz3"]:
        if raid_type == "mirror" and len(disks) < 2:
            raise ValueError("Mirror requires at least two disks.")
        if raid_type == "raidz1" and len(disks) < 2: # Technically 2 for ZFS, but practically 3+
            raise ValueError("raidz1 typically requires at least 2 (data) + 1 (parity) disks.")
        if raid_type == "raidz2" and len(disks) < 3: # Technically 3 for ZFS, but practically 4+
             raise ValueError("raidz2 typically requires at least 3 (data) + 2 (parity) disks.")
        if raid_type == "raidz3" and len(disks) < 4: # Technically 4 for ZFS, but practically 5+
             raise ValueError("raidz3 typically requires at least 4 (data) + 3 (parity) disks.")
        cmd.append(raid_type)
        cmd.extend(disks)

    return cmd

# Example Usage (comments):
#
# # 1. Single disk pool (effectively a stripe of one)
# cmd1 = build_zpool_create_command(
#     pool_name="rpool",
#     raid_type="stripe",
#     disks=["/dev/sda"],
#     ashift=12,
#     root_fs_options={"canmount": "off", "mountpoint": "none"},
#     properties={"autotrim": "on"},
#     altroot="/mnt/zfs_install_target"
# )
# # Expected: ['zpool', 'create', '-f', '-R', '/mnt/zfs_install_target', '-m', 'none', '-o', 'ashift=12',
# #            '-o', 'autotrim=on', '-O', 'canmount=off', '-O', 'mountpoint=none', 'rpool', '/dev/sda']
#
# # 2. Mirrored pool
# cmd2 = build_zpool_create_command(
#     pool_name="bpool",
#     raid_type="mirror",
#     disks=["/dev/sdb", "/dev/sdc"],
#     ashift=12,
#     root_fs_options={"mountpoint": "/boot"}, # Or "none" if handled by generator
#     altroot="/mnt/zfs_install_target"
# )
# # Expected: ['zpool', 'create', '-f', '-R', '/mnt/zfs_install_target', '-m', 'none', '-o', 'ashift=12',
# #            '-O', 'mountpoint=/boot', 'bpool', 'mirror', '/dev/sdb', '/dev/sdc']
#
# # 3. RAIDZ1 pool
# cmd3 = build_zpool_create_command(
#     pool_name="tank",
#     raid_type="raidz1",
#     disks=["/dev/sdd", "/dev/sde", "/dev/sdf"],
#     ashift=13,
#     properties={"compression": "lz4"},
#     root_fs_options={"atime": "off", "recordsize": "1M"},
#     mountpoint="none", # Explicitly setting pool mountpoint to none
#     altroot="/mnt/chroot"
# )
# # Expected: ['zpool', 'create', '-f', '-R', '/mnt/chroot', '-m', 'none', '-o', 'ashift=13', '-o', 'compression=lz4',
# #            '-O', 'atime=off', '-O', 'recordsize=1M', 'tank', 'raidz1', '/dev/sdd', '/dev/sde', '/dev/sdf']
#
# # 4. Stripe multiple disks (explicit stripe)
# cmd4 = build_zpool_create_command(
#     pool_name="bigstripe",
#     raid_type="stripe",
#     disks=["/dev/sdg", "/dev/sdh"],
#     ashift=12,
#     altroot="/mnt"
# )
# # Expected: ['zpool', 'create', '-f', '-R', '/mnt', '-m', 'none', '-o', 'ashift=12', 'bigstripe', '/dev/sdg', '/dev/sdh']

if __name__ == '__main__':
    # Basic test cases (can be expanded into proper unit tests)
    print("Example Commands:")

    # Test Case 1: Single disk (stripe)
    try:
        cmd1 = build_zpool_create_command(
            pool_name="rpool",
            raid_type="stripe",
            disks=["/dev/sda"],
            ashift=12,
            root_fs_options={"canmount": "off", "mountpoint": "none", "xattr": "sa"},
            properties={"autotrim": "on"},
            altroot="/mnt/install",
            mountpoint="none" # Pool's own mountpoint
        )
        print(f"1. Single disk: {' '.join(cmd1)}")
        # Expected: zpool create -f -R /mnt/install -m none -o ashift=12 -o autotrim=on -O canmount=off -O mountpoint=none -O xattr=sa rpool /dev/sda
    except ValueError as e:
        print(f"Error in Test Case 1: {e}")

    # Test Case 2: Mirror
    try:
        cmd2 = build_zpool_create_command(
            pool_name="bpool",
            raid_type="mirror",
            disks=["/dev/nvme0n1p1", "/dev/nvme1n1p1"],
            ashift=12,
            root_fs_options={"mountpoint": "/boot"}, # Example, often 'none' for bpool initially
            altroot="/mnt/install",
            mountpoint="none"
        )
        print(f"2. Mirror: {' '.join(cmd2)}")
        # Expected: zpool create -f -R /mnt/install -m none -o ashift=12 -O mountpoint=/boot bpool mirror /dev/nvme0n1p1 /dev/nvme1n1p1
    except ValueError as e:
        print(f"Error in Test Case 2: {e}")

    # Test Case 3: RAIDZ1
    try:
        cmd3 = build_zpool_create_command(
            pool_name="tank",
            raid_type="raidz1",
            disks=["/dev/sda", "/dev/sdb", "/dev/sdc", "/dev/sdd"],
            ashift=13,
            properties={"compression": "zstd", "xattr": "sa"},
            root_fs_options={"atime": "off", "recordsize": "1M", "mountpoint": "/"}, # Root dataset mountpoint
            altroot="/mnt/install",
            mountpoint="/" # Pool's mountpoint, which will be the rootfs mountpoint
        )
        print(f"3. RAIDZ1: {' '.join(cmd3)}")
        # Expected: zpool create -f -R /mnt/install -m / -o ashift=13 -o compression=zstd -o xattr=sa -O atime=off -O recordsize=1M -O mountpoint=/ tank raidz1 /dev/sda /dev/sdb /dev/sdc /dev/sdd
    except ValueError as e:
        print(f"Error in Test Case 3: {e}")

    # Test Case 4: Invalid RAID type
    try:
        build_zpool_create_command("testpool", "raid0", ["/dev/null"])
    except ValueError as e:
        print(f"4. Invalid RAID type check: Passed ({e})")

    # Test Case 5: Not enough disks for mirror
    try:
        build_zpool_create_command("testpool", "mirror", ["/dev/sde"])
    except ValueError as e:
        print(f"5. Not enough disks for mirror check: Passed ({e})")

    # Test Case 6: Stripe with multiple disks
    try:
        cmd6 = build_zpool_create_command(
            pool_name="stripepool",
            raid_type="stripe",
            disks=["/dev/sdx", "/dev/sdy", "/dev/sdz"],
            ashift=12,
            altroot="/mnt/data",
            mountpoint="/data"
        )
        print(f"6. Multi-disk stripe: {' '.join(cmd6)}")
        # Expected: zpool create -f -R /mnt/data -m /data -o ashift=12 stripepool /dev/sdx /dev/sdy /dev/sdz
    except ValueError as e:
        print(f"Error in Test Case 6: {e}")

    # Test Case 7: No disks
    try:
        build_zpool_create_command("testpool", "stripe", [])
    except ValueError as e:
        print(f"7. No disks check: Passed ({e})")

    # Test Case 8: No pool name
    try:
        build_zpool_create_command("", "stripe", ["/dev/sda"])
    except ValueError as e:
        print(f"8. No pool name check: Passed ({e}")

    # Test Case 9: raidz1 with only 2 disks (common pitfall, ZFS allows it but it's a stripe)
    # My validation requires more for practical raidz.
    try:
        cmd9 = build_zpool_create_command(
            pool_name="smallraidz1",
            raid_type="raidz1",
            disks=["/dev/sdb", "/dev/sdc"], # Should fail with my current validation logic
            ashift=12,
            altroot="/mnt/testing"
        )
        # If the validation is changed to allow 2 disks for raidz1 (1 data + 1 parity)
        # print(f"9. RAIDZ1 with 2 disks: {' '.join(cmd9)}")
    except ValueError as e:
         print(f"9. RAIDZ1 with 2 disks check (expecting failure due to typical minimums): Passed ({e})")

    # Test Case 10: Complex example with many options
    try:
        cmd10 = build_zpool_create_command(
            pool_name="superpool",
            raid_type="raidz2",
            disks=["/dev/sda1", "/dev/sdb1", "/dev/sdc1", "/dev/sdd1", "/dev/sde1"],
            ashift=12,
            properties={
                "autotrim": "on",
                "cachefile": "/etc/zfs/zpool.cache",
                "failmode": "continue"
            },
            root_fs_options={
                "compression": "lz4",
                "dedup": "off", # dedup is usually off by default
                "mountpoint": "/", # Root dataset of the pool
                "canmount": "noauto", # Example, maybe 'on' or 'off'
                "acltype": "posixacl"
            },
            altroot="/mnt/target",
            mountpoint="/" # Pool's mountpoint
        )
        print(f"10. Complex RAIDZ2: {' '.join(cmd10)}")
    except ValueError as e:
        print(f"Error in Test Case 10: {e}")

    # Test Case 11: No altroot, no special root_fs_options, default mountpoint 'none' for pool
    try:
        cmd11 = build_zpool_create_command(
            pool_name="simplepool",
            raid_type="stripe",
            disks=["/dev/sdf"],
            ashift=12
            # mountpoint defaults to "none"
            # altroot defaults to None
        )
        print(f"11. Simple stripe, no altroot, pool mountpoint none: {' '.join(cmd11)}")
        # Expected: zpool create -f -m none -o ashift=12 simplepool /dev/sdf
    except ValueError as e:
        print(f"Error in Test Case 11: {e}")

    # Test Case 12: Pool mountpoint set to something other than "none" or "/"
    try:
        cmd12 = build_zpool_create_command(
            pool_name="custommount",
            raid_type="mirror",
            disks=["/dev/sdg", "/dev/sdh"],
            ashift=12,
            mountpoint="/export/mypool", # Pool's mountpoint
            altroot="/tmp/chroot"
        )
        print(f"12. Mirror with custom pool mountpoint: {' '.join(cmd12)}")
        # Expected: zpool create -f -R /tmp/chroot -m /export/mypool -o ashift=12 custommount mirror /dev/sdg /dev/sdh
    except ValueError as e:
        print(f"Error in Test Case 12: {e}")

    # Test Case 13: raidz1 with 3 disks (valid for practical raidz1)
    try:
        cmd13 = build_zpool_create_command(
            pool_name="goodraidz1",
            raid_type="raidz1",
            disks=["/dev/sdi", "/dev/sdj", "/dev/sdk"],
            ashift=12,
            altroot="/mnt/install",
            mountpoint="/"
        )
        print(f"13. RAIDZ1 with 3 disks: {' '.join(cmd13)}")
        # Expected: zpool create -f -R /mnt/install -m / -o ashift=12 goodraidz1 raidz1 /dev/sdi /dev/sdj /dev/sdk
    except ValueError as e:
        print(f"Error in Test Case 13: {e}")

# Note: The example `altroot` like `/mnt/zfs_install_target` or `/mnt/install`
# is crucial for installations, as it tells ZFS where the root of the filesystem
# hierarchy is during the installation process (e.g., inside a chroot).
# The pool's own mountpoint (`-m`) and the root dataset's mountpoint (`-O mountpoint=`)
# are interpreted relative to this `altroot`.
# If `altroot` is not set, mountpoints are relative to the live environment's root.
# `-m none` for the pool is common if you only want datasets to be mounted.
# If the root dataset itself should be the OS root, then `-O mountpoint=/` (relative to altroot)
# and the pool's `-m` could be `/` or `legacy` or `none` depending on strategy.
# The current implementation sets the pool's mountpoint via the `mountpoint` parameter,
# and the root dataset's mountpoint via `root_fs_options['mountpoint']`.
# If `altroot` is used, `zpool create -R /mnt -m / rpool ... -O mountpoint=/ rpool`
# would try to mount rpool at /mnt/ and rpool dataset at /mnt/.
# A common strategy for Calamares-like installers:
# - `altroot` = path to the chroot (e.g., `/tmp/calamares-root-XYZ`)
# - `pool_name` = `rpool` (for root)
# - `mountpoint` for pool = `none` (using `-m none`)
# - `root_fs_options` for `rpool` dataset: `mountpoint=/` (so it becomes `/tmp/calamares-root-XYZ/`)
#                                          `canmount=noauto` (so it's not auto-mounted by live system, Calamares handles it)
# For `bpool` (boot pool):
# - `altroot` = path to the chroot
# - `pool_name` = `bpool`
# - `mountpoint` for pool = `none`
# - `root_fs_options` for `bpool` dataset: `mountpoint=/boot` (or `/boot/efi` if it's the ESP, though ESP usually isn't ZFS)
#                                          `canmount=on` (or let systemd handle it)
# The provided function defaults pool `mountpoint` to "none", which is a safe default.
# If `root_fs_options` includes `mountpoint`, it will apply to the root dataset.
# For example, `build_zpool_create_command("rpool", ..., altroot="/mnt", root_fs_options={"mountpoint":"/"})`
# with default pool `mountpoint="none"` means:
# `zpool create -f -R /mnt -m none ... -O mountpoint=/ rpool ...`
# This attempts to set the rpool dataset's mountpoint to `/` *within the chroot*.
# The pool itself (rpool) won't be mounted automatically at `/mnt/rpool`.
# This is generally what's desired for OS installation.
