#!/bin/bash
# iDRAC Configuration Script for PowerEdge R730xd

# Text formatting
BOLD=$(tput bold)
NORMAL=$(tput sgr0)
GREEN=$(tput setaf 2)
BLUE=$(tput setaf 4)
RED=$(tput setaf 1)

echo "${BOLD}${BLUE}Dell PowerEdge R730xd iDRAC Configuration Tool${NORMAL}"
echo "=============================================="
echo ""

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "${RED}This script must be run as root!${NORMAL}"
    exit 1
fi

# Check for required tools
if ! command -v ipmitool &>/dev/null; then
    echo "ipmitool not found. Installing required packages..."
    apt-get update
    apt-get install -y ipmitool openipmi
fi

# Function to configure network settings
configure_network() {
    echo "${BOLD}${BLUE}iDRAC Network Configuration${NORMAL}"
    echo "------------------------------"
    
    # Show current configuration
    echo "Current network configuration:"
    ipmitool lan print 1
    
    echo ""
    echo "Select configuration method:"
    echo "1. Use DHCP"
    echo "2. Configure static IP"
    echo "3. Skip network configuration"
    
    read -r -p "Enter choice [1-3]: " net_choice
    
    case $net_choice in
        1)
            echo "Configuring iDRAC to use DHCP..."
            ipmitool lan set 1 ipsrc dhcp
            ;;
        2)
            echo "Enter static IP configuration:"
            read -r -p "IP Address: " ip_addr
            read -r -p "Subnet Mask (e.g. 255.255.255.0): " subnet
            read -r -p "Default Gateway: " gateway
            
            # Validate inputs
            if [[ ! $ip_addr =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                echo "${RED}Invalid IP address format${NORMAL}"
                return 1
            fi
            
            # Set static network configuration
            echo "Applying static network configuration..."
            ipmitool lan set 1 ipsrc static
            ipmitool lan set 1 ipaddr "$ip_addr"
            ipmitool lan set 1 netmask "$subnet"
            ipmitool lan set 1 defgw ipaddr "$gateway"
            ;;
        3)
            echo "Skipping network configuration."
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            return 1
            ;;
    esac
    
    # Display new configuration
    echo ""
    echo "Updated network configuration:"
    ipmitool lan print 1
    
    return 0
}

# Function to configure user accounts
configure_users() {
    echo "${BOLD}${BLUE}iDRAC User Configuration${NORMAL}"
    echo "---------------------------"
    
    # Show current users
    echo "Current user list:"
    ipmitool user list 1
    
    echo ""
    echo "Select user action:"
    echo "1. Configure root user (ID 2)"
    echo "2. Add new admin user"
    echo "3. Skip user configuration"
    
    read -r -p "Enter choice [1-3]: " user_choice
    
    case $user_choice in
        1)
            echo "Configuring root user (ID 2)..."
            read -r -s -p "Enter new password for root: " root_pass
            echo ""
            read -r -s -p "Confirm password: " root_pass_confirm
            echo ""
            
            if [ "$root_pass" != "$root_pass_confirm" ]; then
                echo "${RED}Passwords do not match${NORMAL}"
                return 1
            fi
            
            # Set root password
            ipmitool user set password 2 "$root_pass"
            
            # Enable user and set privileges
            ipmitool user enable 2
            ipmitool channel setaccess 1 2 link=on ipmi=on callin=on privilege=4
            
            echo "${GREEN}Root user configured successfully${NORMAL}"
            ;;
        2)
            echo "Adding new admin user..."
            
            # Find available user ID
            for user_id in {3..10}; do
                user_name=$(ipmitool user list 1 | grep "^$user_id" | awk '{print $2}')
                if [ "$user_name" == "" ]; then
                    break
                fi
            done
            
            if [ "$user_id" -gt 10 ]; then
                echo "${RED}No available user slots${NORMAL}"
                return 1
            fi
            
            # Get user information
            read -r -p "Enter username: " new_user
            read -r -s -p "Enter password: " new_pass
            echo ""
            read -r -s -p "Confirm password: " new_pass_confirm
            echo ""
            
            if [ "$new_pass" != "$new_pass_confirm" ]; then
                echo "${RED}Passwords do not match${NORMAL}"
                return 1
            fi
            
            # Create and configure user
            ipmitool user set name "$user_id" "$new_user"
            ipmitool user set password "$user_id" "$new_pass"
            ipmitool user enable "$user_id"
            ipmitool channel setaccess 1 "$user_id" link=on ipmi=on callin=on privilege=4
            
            echo "${GREEN}User $new_user added with ID $user_id${NORMAL}"
            ;;
        3)
            echo "Skipping user configuration."
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            return 1
            ;;
    esac
    
    return 0
}

# Function to configure serial over LAN
configure_sol() {
    echo "${BOLD}${BLUE}Serial Over LAN (SOL) Configuration${NORMAL}"
    echo "------------------------------------"
    
    # Show current SOL configuration
    echo "Current SOL configuration:"
    ipmitool sol info 1
    
    echo ""
    echo "Configure Serial Over LAN?"
    echo "1. Enable SOL"
    echo "2. Disable SOL"
    echo "3. Skip SOL configuration"
    
    read -r -p "Enter choice [1-3]: " sol_choice
    
    case $sol_choice in
        1)
            echo "Enabling Serial Over LAN..."
            
            # Configure SOL
            ipmitool sol set enabled true 1
            ipmitool sol set force-encryption false 1
            ipmitool sol set privilege-level admin 1
            ipmitool sol set character-accumulate-level 5 1
            ipmitool sol set character-send-threshold 1 1
            ipmitool sol set retry-count 7 1
            ipmitool sol set retry-interval 10 1
            ipmitool sol set non-volatile-bit-rate 115.2 1
            ipmitool sol set volatile-bit-rate 115.2 1
            
            echo "${GREEN}SOL enabled successfully${NORMAL}"
            ;;
        2)
            echo "Disabling Serial Over LAN..."
            ipmitool sol set enabled false 1
            echo "${GREEN}SOL disabled${NORMAL}"
            ;;
        3)
            echo "Skipping SOL configuration."
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            return 1
            ;;
    esac
    
    # Display updated SOL configuration
    echo ""
    echo "Updated SOL configuration:"
    ipmitool sol info 1
    
    # Configure BIOS/UEFI for SOL
    echo ""
    echo "Do you want to configure BIOS for SOL support?"
    echo "This will set COM2 as the serial port for BIOS redirection"
    echo "1. Yes, configure BIOS"
    echo "2. Skip BIOS configuration"
    
    read -r -p "Enter choice [1-2]: " bios_choice
    
    if [ "$bios_choice" == "1" ]; then
        echo "Configuring BIOS for SOL..."
        
        # Set BIOS serial port for redirection
        ipmitool raw 0x30 0x70 0x0c 0x00 0x04 0x00 0x01 0x00 # Enable Serial Port for COM2
        ipmitool raw 0x30 0x70 0x0c 0x00 0x05 0x00 0x01 0x00 # Enable Serial Redirection
        
        echo "${GREEN}BIOS configured for SOL. Changes will take effect after next reboot.${NORMAL}"
    fi
    
    return 0
}

# Function to configure SNMP settings
configure_snmp() {
    echo "${BOLD}${BLUE}SNMP Configuration${NORMAL}"
    echo "-------------------"
    
    echo "Configure SNMP for iDRAC?"
    echo "1. Configure SNMP"
    echo "2. Skip SNMP configuration"
    
    read -r -p "Enter choice [1-2]: " snmp_choice
    
    if [ "$snmp_choice" == "1" ]; then
        read -r -p "Enter SNMP community string: " snmp_string
        
        # Configure SNMP
        ipmitool raw 0x30 0x30 0x01 0x00 0x"$snmp_string"
        
        echo "${GREEN}SNMP configured with community string: $snmp_string${NORMAL}"
        
        # Install SNMP packages on host system
        echo "Do you want to install and configure SNMP on the host system?"
        echo "1. Yes, install and configure SNMP"
        echo "2. Skip host SNMP configuration"
        
        read -r -p "Enter choice [1-2]: " host_snmp
        
        if [ "$host_snmp" == "1" ]; then
            apt-get update
            apt-get install -y snmpd snmp
            
            # Create SNMP configuration
            cat > /etc/snmp/snmpd.conf << SNMPCONF
# SNMP configuration for Dell PowerEdge R730xd
rocommunity $snmp_string localhost
rocommunity $snmp_string 127.0.0.1
sysLocation DataCenter
sysContact admin@example.com

# Required for SNMP monitoring
view systemview included .1.3.6.1.2.1.1
view systemview included .1.3.6.1.2.1.25.1
includeAllDisks 10%
SNMPCONF
            
            # Restart SNMP service
            systemctl restart snmpd
            systemctl enable snmpd
            
            echo "${GREEN}SNMP installed and configured on host system${NORMAL}"
        fi
    else
        echo "Skipping SNMP configuration."
    fi
    
    return 0
}

# Function to configure iDRAC system settings
configure_system() {
    echo "${BOLD}${BLUE}iDRAC System Configuration${NORMAL}"
    echo "-----------------------------"
    
    echo "Configure system timezone?"
    echo "1. Yes, configure timezone"
    echo "2. Skip timezone configuration"
    
    read -r -p "Enter choice [1-2]: " tz_choice
    
    if [ "$tz_choice" == "1" ]; then
        # Set timezone to UTC by default
        ipmitool raw 0x30 0x60 0x00 0x00 0x04 0x00 0x00 0x00 0x00
        echo "${GREEN}Timezone set to UTC${NORMAL}"
    fi
    
    echo ""
    echo "Configure system hostname in iDRAC?"
    echo "1. Yes, set hostname"
    echo "2. Skip hostname configuration"
    
    read -r -p "Enter choice [1-2]: " host_choice
    
    if [ "$host_choice" == "1" ]; then
        read -r -p "Enter hostname: " hostname
        
        # Set hostname in iDRAC
        ipmitool mc set hostname "$hostname"
        echo "${GREEN}Hostname set to $hostname${NORMAL}"
    fi
    
    return 0
}

# Function to configure power settings
configure_power() {
    echo "${BOLD}${BLUE}Power Management Configuration${NORMAL}"
    echo "-------------------------------"
    
    echo "Configure power profile?"
    echo "1. Maximum Performance"
    echo "2. Balanced"
    echo "3. Power Saving"
    echo "4. Skip power configuration"
    
    read -r -p "Enter choice [1-4]: " power_choice
    
    case $power_choice in
        1)
            echo "Setting power profile to Maximum Performance..."
            ipmitool raw 0x30 0xce 0x00 0x00 0x05 0x00 0x00 0x00 # Set to Performance
            echo "${GREEN}Power profile set to Maximum Performance${NORMAL}"
            ;;
        2)
            echo "Setting power profile to Balanced..."
            ipmitool raw 0x30 0xce 0x00 0x00 0x00 0x00 0x00 0x00 # Set to Balanced
            echo "${GREEN}Power profile set to Balanced${NORMAL}"
            ;;
        3)
            echo "Setting power profile to Power Saving..."
            ipmitool raw 0x30 0xce 0x00 0x00 0x01 0x00 0x00 0x00 # Set to Power Saving
            echo "${GREEN}Power profile set to Power Saving${NORMAL}"
            ;;
        4)
            echo "Skipping power configuration."
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            return 1
            ;;
    esac
    
    return 0
}

# Function to configure system event log
configure_sel() {
    echo "${BOLD}${BLUE}System Event Log Configuration${NORMAL}"
    echo "--------------------------------"
    
    # Show current SEL
    echo "Current System Event Log status:"
    ipmitool sel info
    
    echo ""
    echo "System Event Log Actions:"
    echo "1. Clear System Event Log"
    echo "2. Configure SEL policy"
    echo "3. Skip SEL configuration"
    
    read -r -p "Enter choice [1-3]: " sel_choice
    
    case $sel_choice in
        1)
            echo "Clearing System Event Log..."
            ipmitool sel clear
            echo "${GREEN}System Event Log cleared${NORMAL}"
            ;;
        2)
            echo "Select SEL policy:"
            echo "1. Circular (overwrite oldest entries when full)"
            echo "2. Stop when full"
            
            read -r -p "Enter choice [1-2]: " policy_choice
            
            if [ "$policy_choice" == "1" ]; then
                ipmitool raw 0x0a 0x40 0x01 0x00 # Set to circular buffer
                echo "${GREEN}SEL policy set to circular${NORMAL}"
            elif [ "$policy_choice" == "2" ]; then
                ipmitool raw 0x0a 0x40 0x01 0x01 # Set to stop when full
                echo "${GREEN}SEL policy set to stop when full${NORMAL}"
            else
                echo "${RED}Invalid choice${NORMAL}"
                return 1
            fi
            ;;
        3)
            echo "Skipping SEL configuration."
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            return 1
            ;;
    esac
    
    return 0
}

# Main menu
while true; do
    echo ""
    echo "${BOLD}${BLUE}Dell PowerEdge R730xd iDRAC Configuration Menu${NORMAL}"
    echo "==========================================="
    echo "1. Configure Network Settings"
    echo "2. Configure User Accounts"
    echo "3. Configure Serial Over LAN (SOL)"
    echo "4. Configure SNMP"
    echo "5. Configure iDRAC System Settings"
    echo "6. Configure Power Management"
    echo "7. Configure System Event Log"
    echo "8. Show Current Configuration"
    echo "9. Exit"
    echo ""
    
    read -r -p "Enter choice [1-9]: " main_choice
    echo ""
    
    case $main_choice in
        1) configure_network ;;
        2) configure_users ;;
        3) configure_sol ;;
        4) configure_snmp ;;
        5) configure_system ;;
        6) configure_power ;;
        7) configure_sel ;;
        8)
            echo "${BOLD}Current iDRAC Configuration:${NORMAL}"
            echo "------------------------"
            echo "${BLUE}Network Settings:${NORMAL}"
            ipmitool lan print 1 | grep -E "IP Address|MAC Address|Subnet Mask|Default Gateway"
            echo ""
            echo "${BLUE}User Accounts:${NORMAL}"
            ipmitool user list 1
            echo ""
            echo "${BLUE}Serial Over LAN:${NORMAL}"
            ipmitool sol info
            echo ""
            echo "${BLUE}System Information:${NORMAL}"
            ipmitool mc info
            ;;
        9)
            echo "Exiting iDRAC configuration tool."
            exit 0
            ;;
        *)
            echo "${RED}Invalid choice${NORMAL}"
            ;;
    esac
done
