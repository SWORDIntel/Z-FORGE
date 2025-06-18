#!/bin/bash
# iDRAC Configuration Script for PowerEdge R420

echo "PowerEdge R420 iDRAC Configuration Tool"
echo "======================================"
echo ""

# Check for root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root!"
    exit 1
fi

# Check for ipmitool
if ! command -v ipmitool &>/dev/null; then
    echo "ipmitool not found! Installing..."
    apt-get update
    apt-get install -y ipmitool
fi

# Function to configure iDRAC network
configure_idrac_network() {
    echo "Configuring iDRAC Network Settings"
    echo "=================================="

    # Get current settings
    echo "Current iDRAC Network Configuration:"
    ipmitool lan print 1

    echo ""
    echo "Select iDRAC Network Configuration:"
    echo "1. Use DHCP (recommended)"
    echo "2. Configure Static IP"

    read -p "Enter choice [1-2]: " network_choice

    if [ "$network_choice" == "1" ]; then
        echo "Setting iDRAC to use DHCP..."
        ipmitool lan set 1 ipsrc dhcp

    elif [ "$network_choice" == "2" ]; then
        read -p "Enter IP Address: " ip
        read -p "Enter Subnet Mask (e.g. 255.255.255.0): " netmask
        read -p "Enter Default Gateway: " gateway

        echo "Setting static IP configuration..."
        ipmitool lan set 1 ipsrc static
        ipmitool lan set 1 ipaddr $ip
        ipmitool lan set 1 netmask $netmask
        ipmitool lan set 1 defgw ipaddr $gateway
    fi

    # Show new configuration
    echo "New iDRAC Network Configuration:"
    ipmitool lan print 1
}

# Function to configure Serial Over LAN (SOL)
configure_sol() {
    echo "Configuring Serial Over LAN (SOL)"
    echo "================================="

    # Enable SOL
    echo "Enabling SOL..."
    ipmitool sol set enabled true
    ipmitool sol set force-encryption false
    ipmitool sol set privilege-level admin

    # Configure serial port
    echo "Configuring serial port for SOL..."
    ipmitool sol set baud-rate 115200

    # Set COM2 for SOL
    ipmitool raw 0x30 0x0 0x0 0x0 0x0 0x5

    # Show SOL configuration
    echo "SOL Configuration:"
    ipmitool sol info
}

# Function to configure iDRAC users
configure_users() {
    echo "Configuring iDRAC Users"
    echo "======================="

    # Show current users
    echo "Current iDRAC Users:"
    ipmitool user list 1

    echo "Do you want to configure the iDRAC root user?"
    echo "1. Yes, set password"
    echo "2. No, skip"

    read -p "Enter choice [1-2]: " user_choice

    if [ "$user_choice" == "1" ]; then
        read -s -p "Enter new password for root: " password
        echo ""
        read -s -p "Confirm password: " password2
        echo ""

        if [ "$password" != "$password2" ]; then
            echo "Passwords do not match!"
            return 1
        fi

        echo "Setting password for root user (ID 2)..."
        ipmitool user set password 2 $password
        ipmitool user enable 2

        # Set privileges
        ipmitool channel setaccess 1 2 link=on ipmi=on callin=on privilege=4

        echo "Root user configured"
    fi
}

# Function to configure iDRAC SNMP
configure_snmp() {
    echo "Configuring SNMP"
    echo "================"

    echo "Do you want to enable SNMP?"
    echo "1. Yes, enable SNMP"
    echo "2. No, skip"

    read -p "Enter choice [1-2]: " snmp_choice

    if [ "$snmp_choice" == "1" ]; then
        read -p "Enter SNMP community string: " community

        echo "Setting SNMP community string..."
        ipmitool raw 0x30 0x30 1 0xc0 0 0 1 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00

        # Install SNMP components
        apt-get install -y snmpd snmp

        # Configure SNMP
        cat > /etc/snmp/snmpd.conf << SNMPCONF
rocommunity $community localhost
rocommunity $community 192.168.0.0/16
sysLocation "Dell PowerEdge R420"
sysContact admin@example.com
SNMPCONF

        # Enable and start SNMP
        systemctl enable snmpd
        systemctl restart snmpd

        echo "SNMP configured with community string: $community"
    fi
}

# Main menu
while true; do
    echo ""
    echo "Dell PowerEdge R420 iDRAC Configuration Menu"
    echo "============================================"
    echo "1. Configure iDRAC Network Settings"
    echo "2. Configure Serial Over LAN (SOL)"
    echo "3. Configure iDRAC Users"
    echo "4. Configure SNMP"
    echo "5. Exit"

    read -p "Enter choice [1-5]: " menu_choice

    case $menu_choice in
        1) configure_idrac_network ;;
        2) configure_sol ;;
        3) configure_users ;;
        4) configure_snmp ;;
        5) break ;;
        *) echo "Invalid choice" ;;
    esac
done

echo "iDRAC configuration completed."
echo "Remember to reboot for all changes to take effect."
