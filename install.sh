#!/bin/bash
#
# Docker Health Monitor - Quick Install Script
# Usage: curl -sSL https://raw.githubusercontent.com/sonvc94/docker-health-monitor/main/install.sh | bash
#

set -e

GITHUB_REPO="sonvc94/docker-health-monitor"
GITHUB_BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}"

echo "=== Docker Health Monitor - Quick Install ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run this script with sudo"
    exit 1
fi

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Downloading files to: $TEMP_DIR"

# Download required files
echo "Downloading installation files..."
curl -sSL "${BASE_URL}/docker_health_monitor.py" -o "${TEMP_DIR}/docker_health_monitor.py"
curl -sSL "${BASE_URL}/install_service.sh" -o "${TEMP_DIR}/install_service.sh"
curl -sSL "${BASE_URL}/config.json" -o "${TEMP_DIR}/config.json"
curl -sSL "${BASE_URL}/docker-health-monitor.service" -o "${TEMP_DIR}/docker-health-monitor.service"

# Make scripts executable
chmod +x "${TEMP_DIR}/install_service.sh"

# Change to temp directory and run installer
cd "${TEMP_DIR}"
echo "Running installation script..."
bash "${TEMP_DIR}/install_service.sh"

# Cleanup
cd /
rm -rf "${TEMP_DIR}"

echo ""
echo "=== Installation Complete ==="
echo "Docker Health Monitor has been installed and started!"
echo ""
echo "Next steps:"
echo "1. Edit configuration: sudo nano /etc/docker-health-monitor/config.json"
echo "2. Restart service: sudo systemctl restart docker-health-monitor"
echo "3. Check status: sudo systemctl status docker-health-monitor"
echo "4. View logs: sudo journalctl -u docker-health-monitor -f"
echo ""
echo "For more information, visit: https://github.com/${GITHUB_REPO}"
