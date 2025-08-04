# 1) Remove the unsupported 'splash' key (silences the warning)
sudo sed -i '/^[[:space:]]*splash[[:space:]]*$/d' /boot/efi/loader/loader.conf

# 2) Clear any temp artifacts and staging dirs from earlier runs
sudo rm -f /boot/efi/EFI/BOOT/.#BOOTX64.EFI* /boot/efi/EFI/BOOT/.BOOTX64.* 2>/dev/null || true
sudo umount /boot/efi/EFI/BOOT 2>/dev/null || true
sudo rm -rf /root/esp-boot-staging.* 2>/dev/null || true

# 3) Lock in the working state so the postinst won’t rerun unexpectedly
sudo apt-mark hold systemd-boot

# 4) Optional (Proxmox): sync ESPs if tool exists
command -v proxmox-boot-tool >/dev/null 2>&1 && sudo proxmox-boot-tool refresh || true

# 5) Final package health check
dpkg -l | awk '$2=="systemd-boot"{print $1,$2,$3}'
dpkg --audit || true

