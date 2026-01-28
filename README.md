# Docker Health Monitor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ansible-green.svg)](https://www.docker.com/)

A Python-based health monitoring system for Docker Compose services that automatically restarts unhealthy containers and sends notifications when container states change.

## Features

- **Health Monitoring**: Continuously monitors Docker Compose container health
- **Auto-Restart**: Automatically restarts containers that fail health checks
- **Auto-Start**: Optionally auto-start specific stopped services
- **Notifications**: Send alerts to **Slack** and **Telegram** when containers change state
- **State Tracking**: Tracks all container state transitions (status and health changes)
- **Configurable**: Flexible configuration via JSON file
- **Systemd Service**: Runs as a Linux system service with auto-restart

## Requirements

- Linux system with systemd
- Python 3.6+
- Docker Engine
- Docker Compose
- python3-docker package
- python3-requests package (for notifications)

## Quick Install

Install directly from GitHub with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/sonvc94/docker-health-monitor/main/install.sh | sudo bash
```

This will:
- Download all required files
- Install the monitor script to `/opt/docker-health-monitor/`
- Create configuration at `/etc/docker-health-monitor/config.json`
- Install and enable the systemd service
- Start the service immediately

## Manual Install

1. Clone the repository:
```bash
git clone https://github.com/sonvc94/docker-health-monitor.git
cd docker-health-monitor
```

2. Run the installation script:
```bash
sudo ./install_service.sh
```

## Configuration

Edit the configuration file at `/etc/docker-health-monitor/config.json`:

```json
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
      "token": "xoxb-your-bot-token",
      "channel_id": "C1234567890"
    },
    "telegram": {
      "enabled": false,
      "bot_token": "YOUR_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID"
    }
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `unhealthy_threshold` | int | 3 | Number of consecutive unhealthy checks before restart |
| `check_interval` | int | 5 | Seconds between health checks |
| `auto_start_services` | array | [] | Service names to auto-start if stopped |
| `log_max_size` | int | 10485760 | Max log file size in bytes (10MB) |
| `log_backup_count` | int | 5 | Number of backup logs to keep |
| `notifications.enabled` | bool | false | Enable/disable all notifications |
| `notifications.slack.enabled` | bool | false | Enable Slack notifications |
| `notifications.slack.token` | string | "" | Slack Bot User OAuth Token |
| `notifications.slack.channel_id` | string | "" | Slack Channel ID |
| `notifications.telegram.enabled` | bool | false | Enable Telegram notifications |
| `notifications.telegram.bot_token` | string | "" | Telegram Bot Token |
| `notifications.telegram.chat_id` | string | "" | Telegram Chat ID |

## Notifications

### Slack Setup

1. **Create a Slack App**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app and select workspace

2. **Configure Bot Permissions**
   - Navigate to "OAuth & Permissions"
   - Add Bot Token Scopes:
     - `chat:write`
     - `channels:read`
     - `groups:read`
     - `im:read`
     - `mpim:read`

3. **Install App**
   - Click "Install to Workspace"
   - Copy the **Bot User OAuth Token** (starts with `xoxb-`)

4. **Get Channel ID**
   - Right-click the channel in Slack → "Copy Link"
   - Extract Channel ID from URL (e.g., `C1234567890` from `https://workspace.slack.com/archives/C1234567890`)

5. **Invite Bot to Channel**
   - In the channel, run: `/invite @YourBotName`

6. **Update Configuration**
   ```json
   {
     "notifications": {
       "enabled": true,
       "slack": {
         "enabled": true,
         "token": "xoxb-your-token-here",
         "channel_id": "C1234567890"
       }
     }
   }
   ```

### Telegram Setup

1. **Create a Bot**
   - Message @BotFather on Telegram
   - Send `/newbot` and follow instructions
   - Copy the bot token

2. **Get Your Chat ID**
   - Message @userinfobot
   - Copy your chat ID

3. **Start the Bot**
   - Open Telegram
   - Search for your bot
   - Send `/start` command

4. **Update Configuration**
   ```json
   {
     "notifications": {
       "enabled": true,
       "telegram": {
         "enabled": true,
         "bot_token": "123456789:ABCdefGhIjKlMnOpQrStUvWx",
         "chat_id": "123456789"
       }
     }
   }
   ```

### Notification Triggers

Notifications are sent for **all** container state changes:
- Container status changes (running ↔ exited ↔ paused)
- Container health changes (healthy ↔ unhealthy ↔ starting)
- First time a container is detected

Each notification includes:
- Container name
- Service name (from Docker Compose labels)
- Project name (from Docker Compose labels)
- State change details
- Timestamp

## Usage

### Systemd Service Management

```bash
# Check service status
sudo systemctl status docker-health-monitor

# View live logs
sudo journalctl -u docker-health-monitor -f

# Restart service
sudo systemctl restart docker-health-monitor

# Stop service
sudo systemctl stop docker-health-monitor

# Start service
sudo systemctl start docker-health-monitor

# Enable service on boot
sudo systemctl enable docker-health-monitor

# Disable service
sudo systemctl disable docker-health-monitor
```

### Log Files

Service logs are also written to:
```
/opt/docker-health-monitor/docker_health_monitor.log
```

### Reload Configuration

After editing the configuration file:

```bash
sudo systemctl restart docker-health-monitor
```

## Example Docker Compose

Here's an example `docker-compose.yml` with health checks:

```yaml
services:
  web:
    image: nginx:latest
    container_name: nginx-server
    ports:
      - "80:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  api:
    image: myapi:latest
    container_name: api-server
    ports:
      - "8080:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
```

## Auto-Start Services

To automatically start specific services when they stop:

```json
{
  "auto_start_services": [
    "nginx-server",
    "api-server"
  ]
}
```

Services can be specified by:
- Container name (e.g., `nginx-server`)
- Compose service name (e.g., `web`)

## Development

### Local Testing

Run the script directly without installing:

```bash
python3 docker_health_monitor.py
```

### Dependencies

Install Python dependencies:

```bash
# Using apt (Debian/Ubuntu)
sudo apt-get install python3-docker python3-requests

# Using pip
pip3 install docker requests
```

## Troubleshooting

### Service Not Starting

Check logs for errors:
```bash
sudo journalctl -u docker-health-monitor -n 50
```

### Notifications Not Working

1. Verify libraries are installed:
```bash
python3 -c "import requests"
```

2. Check configuration:
```bash
sudo cat /etc/docker-health-monitor/config.json
```

3. Restart service:
```bash
sudo systemctl restart docker-health-monitor
```

### Containers Not Being Monitored

Ensure containers:
- Have the `com.docker.compose.project` label (automatically added by Docker Compose)
- Are running (the monitor only checks running containers)
- Have health checks defined (optional, but recommended)

## Uninstall

Remove the service completely:

```bash
sudo ./uninstall_service.sh
```

This will:
- Stop and disable the service
- Remove systemd service file
- Delete installation directory
- Remove configuration directory

## Architecture

For detailed architecture information, see [CLAUDE.md](https://github.com/sonvc94/docker-health-monitor/blob/main/CLAUDE.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the [GitHub Issues](https://github.com/sonvc94/docker-health-monitor/issues).

## Author

Created by [@sonvc94](https://github.com/sonvc94)

---

**Note**: This tool is provided as-is and comes with no warranty. Always test thoroughly before using in production environments.
