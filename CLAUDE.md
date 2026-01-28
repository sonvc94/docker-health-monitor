# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Docker Compose health monitoring system that automatically restarts unhealthy containers, can auto-start stopped services, and sends notifications when container states change. It consists of a Python monitoring script that runs as a systemd service on Linux.

## Installation and Management

### Install as systemd service
```bash
sudo ./install_service.sh
```

This will:
- Install the monitor script to `/opt/docker-health-monitor/`
- Create config file at `/etc/docker-health-monitor/config.json`
- Install and enable the systemd service

### Uninstall service
```bash
sudo ./uninstall_service.sh
```

### Service management
```bash
# Check status
systemctl status docker-health-monitor

# View logs
journalctl -u docker-health-monitor -f

# Restart service
systemctl restart docker-health-monitor

# Stop service
systemctl stop docker-health-monitor
```

## Configuration

Configuration is stored in `/etc/docker-health-monitor/config.json` with these settings:

- `unhealthy_threshold`: Number of consecutive unhealthy checks before restarting (default: 3)
- `check_interval`: Seconds between health checks (default: 5)
- `auto_start_services`: Array of service names to auto-start if stopped (can be container name or compose service name)
- `log_max_size`: Maximum log file size in bytes before rotation (default: 10MB)
- `log_backup_count`: Number of backup logs to keep (default: 5)

The monitor script also writes logs to `/opt/docker-health-monitor/docker_health_monitor.log` with built-in rotation.

### Notifications Configuration

The monitor supports sending notifications to Slack and Telegram when container states change. Notifications are **disabled by default**.

**Notification structure in config.json:**
```json
{
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

**Enabling notifications:**
1. Set `notifications.enabled` to `true`
2. Configure at least one platform (Slack or Telegram)
3. Restart the service: `sudo systemctl restart docker-health-monitor`

**Slack setup:**
- Create a Slack App at https://api.slack.com/apps
- Add a Bot User with scopes: `chat:write`, `channels:read`, `groups:read`, `im:read`, `mpim:read`
- Install the app to your workspace and copy the **Bot User OAuth Token** (starts with `xoxb-`)
- Get the **Channel ID** where you want to send notifications:
  - Right-click on the channel → "Copy Link" → ID is in the URL (e.g., `/archives/C1234567890`)
  - Or use Slack API: `https://api.slack.com/methods/conversations.list`
- Copy the token to `slack.token` and channel ID to `slack.channel_id`
- Set `slack.enabled` to `true`
- Invite the bot to the channel: `/invite @YourBotName`

**Telegram setup:**
- Create a bot via @BotFather on Telegram
- Copy the bot token to `telegram.bot_token`
- Get your chat ID by messaging @userinfobot
- Copy your chat ID to `telegram.chat_id`
- Set `telegram.enabled` to `true`

**Notification triggers:**
Notifications are sent for **all** container state changes:
- Status changes (running ↔ exited ↔ paused, etc.)
- Health changes (healthy ↔ unhealthy ↔ starting)
- First time a container is detected

The notification includes:
- Container name
- Service name (from Compose labels)
- Project name (from Compose labels)
- State change details
- Timestamp

## Architecture

### Core Components

**DockerHealthMonitor class** (`docker_health_monitor.py:98-282`)
- Main monitoring loop that runs continuously
- Tracks consecutive unhealthy counts per container using `defaultdict`
- Only monitors containers with `com.docker.compose.project` label (Compose-managed containers)

**Health checking logic** (`docker_health_monitor.py:116-176`)
- Reads health status from container's `State.Health.Status` attribute
- Falls back to container running status if no healthcheck defined
- Increments unhealthy counter and restarts when threshold exceeded
- Resets counter when container becomes healthy

**Auto-start feature** (`docker_health_monitor.py:181-228`)
- Checks services specified in `auto_start_services` config
- Finds containers by container name OR `com.docker.compose.service` label
- Searches all containers (including stopped ones) using `containers.list(all=True)`
- Starts any stopped/exited containers matching the service names

**NotificationManager class** (`docker_health_monitor.py:117-211`)
- Manages notifications to Slack and Telegram
- Disabled by default, enabled via config
- Checks if `requests` library is available, disables notifications if missing
- Sends formatted notifications with container details and state changes

**State tracking** (`docker_health_monitor.py:266-327`)
- Tracks previous container states (status + health) in `previous_states` dict
- Detects all state changes between monitoring cycles
- Sends notifications when:
  - Container status changes (running ↔ exited ↔ paused)
  - Container health changes (healthy ↔ unhealthy ↔ starting)
  - First time seeing a container
- State changes trigger notifications to enabled platforms

### Container Discovery

The monitor uses Docker Python SDK (`docker.from_env()`) to communicate with the Docker daemon. It filters containers using Compose labels:
- `com.docker.compose.project`: Identifies Compose-managed containers
- `com.docker.compose.service`: Used for service name matching in auto-start

### Monitoring Flow

Each monitoring cycle:
1. Check and start any stopped services in `auto_start_services`
2. Get all running Compose containers
3. For each container:
   - Check current status and health
   - Compare with previous state
   - Send notification if state changed
   - Increment/decrement unhealthy counters
   - Restart if threshold exceeded
4. Sleep for `check_interval` seconds

## Development

### Dependencies
- Python 3
- docker Python package: `pip install docker` or `apt-get install python3-docker`
- requests Python package (optional, for notifications): `pip install requests` or `apt-get install python3-requests`

Note: The monitor will run without notifications if `requests` is not installed.

### Testing locally
Run the script directly (not as service) for testing:
```bash
python3 docker_health_monitor.py
```

### Health check requirements
Containers must have healthchecks defined in docker-compose.yml for proper monitoring. If no healthcheck is defined, the monitor falls back to checking if the container is running.
