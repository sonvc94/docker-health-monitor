#!/bin/bash
# Installation script for Docker Health Monitor as a systemd service

set -e

INSTALL_DIR="/opt/docker-health-monitor"
SERVICE_FILE="/etc/systemd/system/docker-health-monitor.service"

echo "=== Docker Health Monitor Service Installation ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run this script with sudo"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Create config directory
CONFIG_DIR="/etc/docker-health-monitor"
echo "Creating config directory: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# Copy monitor script
echo "Copying monitor script..."
cp docker_health_monitor.py "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/docker_health_monitor.py"

# Copy config file
if [ -f "config.json" ]; then
    echo "Copying config file..."
    cp config.json "$CONFIG_DIR/"
    chmod 644 "$CONFIG_DIR/config.json"
else
    echo "Warning: config.json not found, creating default config..."
    cat > "$CONFIG_DIR/config.json" << 'EOF'
{
  "unhealthy_threshold": 3,
  "check_interval": 5,
  "auto_start_services": [],
  "log_max_size": 10485760,
  "log_backup_count": 5,
  "notifications": {
    "enabled": false,
    "slack": {
      "enabled": false,
      "token": "",
      "channel_id": ""
    },
    "telegram": {
      "enabled": false,
      "bot_token": "",
      "chat_id": ""
    }
  }
}
EOF
    chmod 644 "$CONFIG_DIR/config.json"
fi

# Check if python3-docker is installed
echo "Checking python3-docker installation..."
if ! python3 -c "import docker" 2>/dev/null; then
    echo ""
    echo "ERROR: python3-docker is not installed!"
    echo ""
    echo "Please install it first using one of these methods:"
    echo ""
    echo "  Option 1 - Using apt (recommended for Debian/Ubuntu):"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install -y python3-docker"
    echo ""
    echo "  Option 2 - Using pip:"
    echo "    pip3 install docker"
    echo ""
    exit 1
fi
echo "python3-docker is installed."

# Check if python3-requests is installed
echo "Checking python3-requests installation..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo ""
    echo "WARNING: python3-requests is not installed!"
    echo ""
    echo "Notifications require requests library. Please install it using one of these methods:"
    echo ""
    echo "  Option 1 - Using apt (recommended for Debian/Ubuntu):"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install -y python3-requests"
    echo ""
    echo "  Option 2 - Using pip:"
    echo "    pip3 install requests"
    echo ""
    echo "The monitor will run without notifications if requests is not installed."
fi
echo "python3-requests check complete."

# Copy service file
echo "Installing systemd service..."
cp docker-health-monitor.service "$SERVICE_FILE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service
echo "Enabling service to start on boot..."
systemctl enable docker-health-monitor.service

# Start service
echo "Starting service..."
systemctl start docker-health-monitor.service

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Service management commands:"
echo "  Check status:  systemctl status docker-health-monitor"
echo "  View logs:     journalctl -u docker-health-monitor -f"
echo "  Restart:       systemctl restart docker-health-monitor"
echo "  Stop:          systemctl stop docker-health-monitor"
echo "  Disable:       systemctl disable docker-health-monitor"
echo ""
echo "Log file also available at: $INSTALL_DIR/docker_health_monitor.log"
