#!/bin/bash

# Ensure the script is run as root
if [ "$EUID" -ne 0 ]; then
  echo "❌ Please run as root: sudo ./device_headless_wifi.sh"
  exit 1
fi

echo "=================================================="
echo "   Jetson Nano Pre-Login Wi-Fi & SSH Activator"
echo "=================================================="

# 1. Detect the active Wi-Fi connection
WIFI_SSID=$(nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2)

if [ -z "$WIFI_SSID" ]; then
    echo "❌ No active Wi-Fi connection detected."
    echo "Please connect to Wi-Fi manually once via monitor/serial first."
    exit 1
fi

echo "📡 Found active Wi-Fi: $WIFI_SSID"

# 2. Convert connection to a System-Wide connection
echo "🔐 Configuring '$WIFI_SSID' to start at boot without login..."

# Remove user-only permissions (makes it available to all users/system)
nmcli connection modify "$WIFI_SSID" connection.permissions ""

# Ensure the password (PSK) is stored in the config file, not the user keyring
nmcli connection modify "$WIFI_SSID" 802-11-wireless-security.psk-flags 0

# Set it to auto-connect with high priority
nmcli connection modify "$WIFI_SSID" connection.autoconnect yes
nmcli connection modify "$WIFI_SSID" connection.autoconnect-priority 10

# 3. Ensure SSH is enabled and starts after the network
echo "🖥 Optimizing SSH for headless boot..."
systemctl enable ssh

# Create a drop-in directory for ssh service override
mkdir -p /etc/systemd/system/ssh.service.d
cat <<EOF > /etc/systemd/system/ssh.service.d/wait-for-network.conf
[Unit]
After=network-online.target
Wants=network-online.target
EOF

# 4. Disable the GUI to save resources (Multi-user mode)
echo "📉 Disabling Desktop GUI (Setting to headless mode)..."
systemctl set-default multi-user.target

# 5. Apply changes
echo "🔄 Reloading configurations..."
systemctl daemon-reload
nmcli connection up "$WIFI_SSID"

echo ""
echo "✅ SUCCESS!"
echo "--------------------------------------------------"
echo "Your Jetson will now connect to '$WIFI_SSID'"
echo "immediately after the hardware finishes booting."
echo ""
echo "Next Step: Type 'sudo reboot' and try to SSH in"
echo "after 60 seconds without touching the keyboard."
echo "--------------------------------------------------"