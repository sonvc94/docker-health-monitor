#!/bin/bash
# Uninstallation script for Docker Health Monitor service

set -e

INSTALL_DIR="/opt/docker-health-monitor"
SERVICE_FILE="/etc/systemd/system/docker-health-monitor.service"

echo "=== Docker Health Monitor Service Uninstallation ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run this script with sudo"
    exit 1
fi

# Stop and disable service
echo "Stopping service..."
systemctl stop docker-health-monitor.service 2>/dev/null || true

echo "Disabling service..."
systemctl disable docker-health-monitor.service 2>/dev/null || true

# Remove service file
echo "Removing systemd service file..."
rm -f "$SERVICE_FILE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Remove installation directory
echo "Removing installation directory..."
rm -rf "$INSTALL_DIR"

# Remove config directory
echo "Removing config directory..."
rm -rf /etc/docker-health-monitor

echo ""
echo "=== Uninstallation Complete ==="
echo "Service has been removed from your system."
