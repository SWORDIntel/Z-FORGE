# ZFS Configuration Module Documentation

## 1. Introduction
   - Purpose of the ZFS Configuration module in the Calamares installer.
   - Overview of ZFS benefits (data integrity, flexibility, snapshots, etc.).
   - Target audience for this guide (users performing ZFS installations).

## 2. Getting Started: Pool Creation Mode
   - **2.1. Use Existing ZFS Pool**
     - Explanation: Selecting this mode allows installation onto an already created and imported ZFS pool.
     - UI Element: "Use Existing ZFS Pool" radio button.
     - Workflow: User selects this, then chooses a pool from the "Available ZFS Pools" list.
   - **2.2. Create New ZFS Pool**
     - Explanation: Selecting this mode enables the UI for defining a new ZFS pool from available disks.
     - UI Element: "Create New ZFS Pool" radio button.
     - Workflow: User selects this, then proceeds to configure the new pool (disk selection, RAID type, etc.).

## 3. Configuring a New ZFS Pool (If "Create New ZFS Pool" is selected)
   - **3.1. Disk Selection**
     - UI Element: "Select Disks for New Pool" TreeView.
     - Columns: Select (Checkbox), Device Path, Model, Size.
     - Action: Users must select one or more disks to include in the new pool.
     - Considerations:
       - Disk types (HDD vs. SSD).
       - Warning about selecting disks with existing data (data will be lost).
       - Recommendation to use whole disks, not partitions, for ZFS.
   - **3.2. RAID Type Selection**
     - UI Element: "RAID Type" ComboBox.
     - Options:
       - **stripe:** (Default) Data is striped across all selected disks. No redundancy. Max capacity. Min 1 disk.
       - **mirror:** Data is mirrored across pairs of disks. High redundancy. Capacity of smallest disk in a pair. Min 2 disks. Multiple mirrors can be created (e.g., 4 disks = 2 mirrors).
       - **raidz1:** Single parity. Similar to RAID-5. Good balance of capacity and redundancy. Min 2 disks (practically 3+ recommended).
       - **raidz2:** Double parity. Similar to RAID-6. Higher redundancy than raidz1. Min 3 disks (practically 4+ recommended).
       - **raidz3:** Triple parity. Highest redundancy. Min 4 disks (practically 5+ recommended).
     - Guidance: Explain capacity, performance, and redundancy trade-offs for each type. Link to OpenZFS documentation for detailed explanations.
   - **3.3. New Pool Name**
     - UI Element: "New Pool Name" Entry.
     - Default: `rpool` (common for root pools).
     - Validation: Must be a valid ZFS pool name (alphanumeric, `_-.`, starts with letter, no trailing hyphen).

## 4. Common Configuration (Applies to both New and Existing Pools)
   - **4.1. Target Dataset Name**
     - UI Element: "Target Dataset" Entry.
     - Explanation: Defines the name of the ZFS dataset where the OS will be installed (e.g., `ROOT/pve` or `system/root`).
     - For Existing Pools: This is created within the selected existing pool (e.g., `selected_pool/ROOT/pve`).
     - For New Pools: This is created within the newly defined pool (e.g., `new_pool_name/ROOT/pve`). The `zpool create` command itself creates `new_pool_name`; subsequent `zfs create` commands (handled by Calamares job) create the nested datasets.
     - Default: `ROOT/proxmox`.
   - **4.2. Installation Mode (For Existing Pools Only)**
     - UI Element: "Installation Mode" Radio Buttons.
     - Options:
       - "Create new root dataset": Creates the specified "Target Dataset" on the selected existing pool. Fails if it already exists.
       - "Replace existing Proxmox installation": (Details TBD - assumes detection of a previous install and re-uses its dataset name, possibly formatting it).
       - "Install alongside existing": (Details TBD - likely creates the "Target Dataset" with a modified name if the default exists).
   - **4.3. Workload Profile**
     - UI Element: "Workload Profile" ComboBox.
     - Purpose: Provides predefined sets of ZFS properties tailored to common use cases, simplifying advanced configuration.
     - Profiles:
       - **General Desktop:** Balanced settings for everyday use. (lz4, relatime, 128K recordsize, ashift=auto, ARC auto).
       - **Virtual Machine Host:** Optimized for running VMs. (lz4, atime=off, smaller recordsize e.g., 64K).
       - **Bulk File Storage/NAS:** Optimized for large file storage and throughput. (zstd, atime=off, 1M recordsize).
       - **Custom:** Unlocks "Advanced ZFS Settings" for manual tuning. All other profiles will set defaults and collapse/disable advanced settings.
   - **4.4. Full Disk Encryption (Dataset Encryption)**
     - UI Element: "Enable Full Disk Encryption" Checkbox.
     - Functionality: Encrypts the target installation dataset (and potentially child datasets via inheritance).
     - UI Elements (when enabled):
       - Password Entry & Confirmation.
       - Encryption Algorithm ComboBox (aes-256-gcm, aes-256-ccm, chacha20-poly1305).
     - Key Points:
       - Password strength recommendations.
       - Algorithm choice (aes-256-gcm is common default).
       - Key management: `keyformat=passphrase`, `keylocation=prompt`. User will be prompted for passphrase on boot.
       - For new pools, the root dataset of the pool itself will have encryption enabled. For existing pools, the new target dataset will be encrypted.

## 5. Advanced ZFS Settings (When "Custom" profile is selected or expander is opened)
   - UI Element: "Advanced ZFS Settings" Expander.
   - **5.1. ashift**
     - UI Element: `ashift_combo` (Auto-detect, 9, 12, 13).
     - Help Tooltip: Explains ashift (2^ashift), recommends "Auto-detect", warns about performance impact and permanence. Common values (12 for 4K, 13 for 8K).
     - Warning Label: Dynamic warning if not "Auto-detect".
     - Applies to: New pool creation only.
   - **5.2. Compression**
     - Algorithm: `compression_algo_combo` (lz4, zstd, gzip, off).
     - Help Tooltip: Describes each algorithm.
     - Zstd Level: `zstd_level_scale` (1-19), visible if "zstd" is chosen.
     - Help Tooltip (Zstd Level): Explains levels and CPU cost.
     - Helper Label: Dynamic text about compression trade-offs.
     - Applies to: Datasets on new or existing pools.
   - **5.3. Record Size**
     - UI Element: `recordsize_combo` (Default (128K), 16K, 64K, 1M, etc.).
     - Help Tooltip: Explains recordsize, default, and impact of different sizes.
     - Applies to: Datasets on new or existing pools.
   - **5.4. atime**
     - UI Element: `atime_combo` (relatime, off, on).
     - Help Tooltip: Explains options and performance impact.
     - Applies to: Datasets on new or existing pools.
   - **5.5. xattr (Extended Attributes)**
     - UI Element: `xattr_combo` (sa, posix).
     - Help Tooltip: Explains `sa` vs `posix` for xattrs.
     - Applies to: Datasets on new or existing pools.
   - **5.6. dnodesize**
     - UI Element: `dnodesize_combo` (auto, legacy).
     - Help Tooltip: Explains dnodesize, relevance for xattr=sa.
     - Applies to: Datasets on new or existing pools.
   - **5.7. ARC Max Size (GB)**
     - UI Element: `arc_max_gb_spinbutton` (0 for auto).
     - Help Tooltip: Explains ARC, auto mode (0GB = 50% RAM), manual tuning considerations.
     - Warning Label: Dynamic warning/info based on value.
     - Applies to: System-wide setting (module collects it, applied via sysfs/modprobe post-install).
   - **5.8. L2ARC Device(s)**
     - UI Element: `l2arc_devices_entry` (space-separated paths).
     - Help Tooltip: Explains L2ARC, device requirements, caching behavior.
     - Warning Label: Static guidance on usage.
     - Applies to: New pool creation. (Adding L2ARC to existing pools is a post-setup `zpool add` operation).

## 6. Configuration Summary Panel
   - UI Element: `summary_label` within `summary_frame`.
   - Content: Dynamically updates to show:
     - Selected Pool Creation Mode.
     - If New Pool: Pool name, RAID type, selected disks (count and list), ashift.
     - If Existing Pool: Selected existing pool name.
     - Workload Profile.
     - Key ZFS Properties: Compression, Record Size, atime, xattr, dnodesize, ARC Max, L2ARC (if new pool).
     - Sanity Check Warnings: e.g., high Zstd level, manual ashift reminder, insufficient disks for RAID.

## 7. Controls
   - **7.1. Reset to Recommended Defaults Button**
     - Action: Resets all ZFS settings to the "General Desktop" profile defaults. Advanced expander collapses.
   - **7.2. Cancel Button**
     - Action: Exits the ZFS configuration module without saving changes.
   - **7.3. Next Button**
     - Action: Validates current selections. If valid, saves all configuration settings to `libcalamares.globalstorage` and proceeds to the next installation step.

## 8. Data Storage in `libcalamares.globalstorage` (For Calamares Job Modules)
   - `zfs_operation_mode`: "new_pool" or "existing_pool".
   - **If "new_pool"**:
     - `zfs_new_pool_command`: List of strings for `zpool create ...` command.
     - `zfs_new_pool_name`: Name of the new pool.
     - `zfs_install_dataset_relative`: Relative path for the root dataset on the new pool (e.g., `ROOT/pve`).
   - **If "existing_pool"**:
     - `install_pool`: Name of the selected existing pool. (Legacy key)
     - `install_dataset`: Full path of the target dataset (e.g., `existing_pool/ROOT/pve`). (Legacy key)
     - `install_mode`: "new", "replace", "alongside". (Legacy key)
   - **Common/Global Settings**:
     - `zfs_arc_max_gb`: Integer value for ARC max size (0 for auto).
     - `zfs_encryption_enabled`: Boolean.
     - `zfs_encryption_password`: String (handle with care).
     - `zfs_encryption_algorithm`: String (if encryption enabled).
     - `zfs_encryption_keyformat`: "passphrase" (if encryption enabled).
     - `zfs_encryption_keylocation`: "prompt" (if encryption enabled).
     - *(Note: Individual ZFS properties like compression, recordsize etc. are part of the `zfs_new_pool_command` for new pools. For existing pools, Calamares jobs would need to apply them to the `install_dataset` using `zfs set property=value dataset`)*

## Appendix A: Troubleshooting
   - Common issues and solutions (e.g., disk detection, invalid pool names, validation errors).

## Appendix B: ZFS Best Practices
   - Brief notes on ashift, redundancy, backups (not a full guide, but pointers).
---
This outline provides a comprehensive structure for documenting the ZFS configuration module.
