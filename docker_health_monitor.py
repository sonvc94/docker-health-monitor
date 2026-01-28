#!/usr/bin/env python3
"""
Docker Compose Health Monitor
Monitors Docker Compose service health and automatically restarts unhealthy services.
Also auto-starts stopped services by name.
"""

import time
import logging
import os
import json
from collections import defaultdict
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Get script directory for log file placement
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = "/etc/docker-health-monitor/config.json"


def load_config():
    """
    Load configuration from JSON file.
    Returns default values if file is missing or invalid.

    Returns:
        dict: Configuration dictionary
    """
    defaults = {
        "unhealthy_threshold": 3,
        "check_interval": 5,
        "auto_start_services": [],
        "log_max_size": 10 * 1024 * 1024,
        "log_backup_count": 5,
        "notifications": {
            "enabled": False,
            "slack": {
                "enabled": False,
                "token": "",
                "channel_id": ""
            },
            "telegram": {
                "enabled": False,
                "bot_token": "",
                "chat_id": ""
            }
        }
    } 

    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"Config file not found: {CONFIG_FILE}, using defaults")
        return defaults

    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with defaults to ensure all keys exist
            for key, value in defaults.items():
                if key not in config:
                    config[key] = value
            logger.info(f"Loaded config from: {CONFIG_FILE}")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}, using defaults")
        return defaults
    except Exception as e:
        logger.error(f"Error loading config: {e}, using defaults")
        return defaults

try:
    import docker
except ImportError:
    print("Error: docker-py not installed. Run: pip install docker")
    exit(1)

try:
    import requests
except ImportError:
    print("Warning: requests not installed. Notifications will be disabled.")
    requests = None


# Configure logging with built-in rotation
LOG_FILE = os.path.join(SCRIPT_DIR, 'docker_health_monitor.log')

# Initialize logger (will be reconfigured after loading config)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Temporary handlers until config is loaded
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)


def configure_logging(log_max_size, log_backup_count):
    """Configure logging with rotation parameters from config."""
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler with rotation
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=log_max_size,
        backupCount=log_backup_count
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)


class NotificationManager:
    """Manage notifications to Slack and Telegram."""

    def __init__(self, config):
        """
        Initialize notification manager with configuration.

        Args:
            config: Notifications configuration dictionary
        """
        # Check if requests library is available
        if requests is None:
            self.enabled = False
            logger.warning("Requests library not available, notifications disabled")
            return

        self.enabled = config.get("enabled", False)
        self.slack_config = config.get("slack", {})
        self.telegram_config = config.get("telegram", {})

    def send_notification(self, title, message):
        """
        Send notification to all enabled platforms.

        Args:
            title: Notification title
            message: Notification message
        """
        if not self.enabled:
            return

        # Send to Slack if enabled
        if self.slack_config.get("enabled", False):
            self._send_slack(title, message)

        # Send to Telegram if enabled
        if self.telegram_config.get("enabled", False):
            self._send_telegram(title, message)

    def _send_slack(self, title, message):
        """
        Send notification to Slack via Web API.

        Args:
            title: Notification title
            message: Notification message
        """
        token = self.slack_config.get("token", "")
        channel_id = self.slack_config.get("channel_id", "")

        if not token:
            logger.warning("Slack token not configured")
            return

        if not channel_id:
            logger.warning("Slack channel ID not configured")
            return

        # Determine color based on message content
        color = "danger" if "unhealthy" in message.lower() or "stopped" in message.lower() else "good"

        # Format message using blocks for better formatting
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": message
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Docker Health Monitor | <!date^{int(datetime.now().timestamp())}^{{date_short_pretty}} {{time_secs}}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}>"
                    }
                ]
            }
        ]

        payload = {
            "channel": channel_id,
            "blocks": blocks,
            "text": f"{title}: {message}"  # Fallback text for notifications
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post("https://slack.com/api/chat.postMessage",
                                   json=payload,
                                   headers=headers,
                                   timeout=10)
            response_data = response.json()

            if not response_data.get("ok"):
                logger.error(f"Failed to send Slack notification: {response_data.get('error')}")
            else:
                logger.info("Slack notification sent successfully")
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")

    def _send_telegram(self, title, message):
        """
        Send notification to Telegram via bot API.

        Args:
            title: Notification title
            message: Notification message
        """
        bot_token = self.telegram_config.get("bot_token", "")
        chat_id = self.telegram_config.get("chat_id", "")

        if not bot_token or not chat_id:
            logger.warning("Telegram bot token or chat ID not configured")
            return

        # Format message with Markdown
        formatted_message = f"*{title}*\n\n{message}"
        formatted_message = formatted_message.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": formatted_message,
            "parse_mode": "MarkdownV2"
        }

        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to send Telegram notification: {response.status_code} - {response.text}")
            else:
                logger.info("Telegram notification sent successfully")
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")


class DockerHealthMonitor:
    """Monitor Docker container health and restart unhealthy services."""

    def __init__(self, unhealthy_threshold=3, check_interval=5, auto_start_services=None, notification_config=None):
        """
        Initialize the health monitor.

        Args:
            unhealthy_threshold: Number of consecutive unhealthy checks before restart
            check_interval: Seconds between health checks
            auto_start_services: List of service names to auto-start if stopped
            notification_config: Notification configuration dictionary
        """
        self.unhealthy_threshold = unhealthy_threshold
        self.check_interval = check_interval
        self.auto_start_services = auto_start_services or []
        self.unhealthy_counts = defaultdict(int)
        self.client = docker.from_env()
        self.notification_manager = NotificationManager(notification_config or {})
        self.previous_states = {}  # Track previous container states

    def get_container_health(self, container):
        """
        Get the health status of a container.

        Args:
            container: Docker container object

        Returns:
            str: Health status ('healthy', 'unhealthy', 'starting', or 'none')
        """
        status = container.attrs.get('State', {}).get('Health', {}).get('Status')
        if status:
            return status
        # Fallback to container status if no healthcheck defined
        container_status = container.status
        if container_status == 'running':
            return 'healthy'
        return 'unhealthy'

    def get_container_state_key(self, container):
        """
        Get a unique key for tracking container state.

        Args:
            container: Docker container object

        Returns:
            str: Unique key for container
        """
        return f"{container.name}"

    def check_and_notify_state_change(self, container, current_status, current_health):
        """
        Check if container state changed and send notification.

        Args:
            container: Docker container object
            current_status: Current container status (running, exited, etc.)
            current_health: Current health status (healthy, unhealthy, starting)
        """
        container_key = self.get_container_state_key(container)
        previous_state = self.previous_states.get(container_key, {})

        prev_status = previous_state.get("status")
        prev_health = previous_state.get("health")

        # Check for state changes
        state_changed = False
        change_message = ""

        # Check status change (running <-> exited, etc.)
        if prev_status != current_status and prev_status is not None:
            state_changed = True
            change_message = f"Container status changed from `{prev_status}` to `{current_status}`"

        # Check health change
        elif prev_health != current_health and prev_health is not None:
            state_changed = True
            change_message = f"Container health changed from `{prev_health}` to `{current_health}`"

        # First time seeing this container
        elif prev_status is None:
            change_message = f"Container started monitoring with status: `{current_status}`, health: `{current_health}`"

        # Update previous state
        self.previous_states[container_key] = {
            "status": current_status,
            "health": current_health
        }

        # Send notification if state changed or first time
        if state_changed and change_message:
            container_name = container.name
            labels = container.attrs.get('Config', {}).get('Labels', {})
            service_name = labels.get('com.docker.compose.service', 'N/A')
            project_name = labels.get('com.docker.compose.project', 'N/A')

            message = (
                f"Container: *{container_name}*\n"
                f"Service: {service_name}\n"
                f"Project: {project_name}\n"
                f"{change_message}"
            )

            # Determine notification title based on state
            if current_status == "exited" or current_health == "unhealthy":
                title = "🚨 Container Issue Detected"
            elif current_status == "running" and current_health == "healthy":
                title = "✅ Container Recovered"
            else:
                title = "ℹ️ Container State Changed"

            self.notification_manager.send_notification(title, message)

    def restart_container(self, container):
        """
        Restart a container and log the action.

        Args:
            container: Docker container object to restart
        """
        container_name = container.name
        logger.warning(f"Restarting container: {container_name}")
        try:
            container.restart()
            logger.info(f"Successfully restarted container: {container_name}")
        except Exception as e:
            logger.error(f"Failed to restart container {container_name}: {e}")

    def check_and_restart_unhealthy(self, container):
        """
        Check container health and restart if threshold exceeded.

        Args:
            container: Docker container object to check
        """
        container_name = container.name
        container_status = container.status
        health_status = self.get_container_health(container)

        # Check for state changes and send notifications
        self.check_and_notify_state_change(container, container_status, health_status)

        logger.info(f"Container '{container_name}' health status: {health_status}")

        if health_status == 'healthy':
            if self.unhealthy_counts[container_name] > 0:
                logger.info(f"Container '{container_name}' recovered after {self.unhealthy_counts[container_name]} unhealthy checks")
            self.unhealthy_counts[container_name] = 0

        elif health_status == 'unhealthy':
            self.unhealthy_counts[container_name] += 1
            logger.warning(
                f"Container '{container_name}' is unhealthy "
                f"({self.unhealthy_counts[container_name]}/{self.unhealthy_threshold})"
            )

            if self.unhealthy_counts[container_name] >= self.unhealthy_threshold:
                self.restart_container(container)
                self.unhealthy_counts[container_name] = 0

        elif health_status == 'starting':
            logger.info(f"Container '{container_name}' is starting...")

    def check_and_start_stopped_services(self):
        """
        Check configured services and start them if they are stopped.
        Services can be specified by container name or service name.
        """
        if not self.auto_start_services:
            return

        # Get all containers (including stopped ones)
        all_containers = self.client.containers.list(all=True)

        for service_name in self.auto_start_services:
            container = None
            found_by = None

            # Search for container by name or service label
            for c in all_containers:
                labels = c.attrs.get('Config', {}).get('Labels', {})

                # Check by container name
                if c.name == service_name:
                    container = c
                    found_by = 'name'
                    break

                # Check by compose service name
                if labels.get('com.docker.compose.service') == service_name:
                    container = c
                    found_by = 'service'
                    break

            if container is None:
                logger.warning(f"Service '{service_name}' not found (checked all containers)")
                continue

            # Check container status
            status = container.status
            if status == 'running':
                logger.debug(f"Service '{service_name}' is running (found by {found_by})")
            else:
                logger.warning(
                    f"Service '{service_name}' is {status} (found by {found_by}), starting..."
                )
                try:
                    container.start()
                    logger.info(f"Successfully started service '{service_name}'")
                except Exception as e:
                    logger.error(f"Failed to start service '{service_name}': {e}")

    def get_compose_containers(self):
        """
        Get all containers managed by docker-compose.

        Returns:
            list: List of Docker container objects
        """
        # Get all running containers
        containers = self.client.containers.list(all=False)

        # Filter containers that are part of a compose project
        # (have com.docker.compose.project label)
        compose_containers = []
        for container in containers:
            labels = container.attrs.get('Config', {}).get('Labels', {})
            if 'com.docker.compose.project' in labels:
                compose_containers.append(container)

        return compose_containers

    def run(self):
        """Run the health monitor loop."""
        logger.info(f"Starting Docker Health Monitor (threshold: {self.unhealthy_threshold}, interval: {self.check_interval}s)")

        if self.auto_start_services:
            logger.info(f"Auto-start enabled for services: {', '.join(self.auto_start_services)}")

        try:
            while True:
                try:
                    # Check and start stopped services first
                    self.check_and_start_stopped_services()

                    # Then monitor health of running containers
                    containers = self.get_compose_containers()

                    if not containers:
                        logger.warning("No Docker Compose containers found running")
                    else:
                        logger.info(f"Monitoring {len(containers)} Docker Compose container(s)")
                        for container in containers:
                            self.check_and_restart_unhealthy(container)

                except docker.errors.APIError as e:
                    logger.error(f"Docker API error: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            logger.info("Health monitor stopped by user")


def main():
    """Main entry point."""
    # Load configuration from file
    config = load_config()

    # Reconfigure logging with config values
    configure_logging(config["log_max_size"], config["log_backup_count"])

    # Log loaded configuration
    logger.info(f"Configuration loaded: threshold={config['unhealthy_threshold']}, "
                f"interval={config['check_interval']}s, "
                f"auto_start={config['auto_start_services']}")

    # Log notification configuration
    notifications_config = config.get("notifications", {})
    if notifications_config.get("enabled", False):
        enabled_platforms = []
        if notifications_config.get("slack", {}).get("enabled", False):
            enabled_platforms.append("Slack")
        if notifications_config.get("telegram", {}).get("enabled", False):
            enabled_platforms.append("Telegram")
        logger.info(f"Notifications enabled for: {', '.join(enabled_platforms)}")
    else:
        logger.info("Notifications disabled")

    monitor = DockerHealthMonitor(
        unhealthy_threshold=config["unhealthy_threshold"],
        check_interval=config["check_interval"],
        auto_start_services=config["auto_start_services"],
        notification_config=notifications_config
    )

    monitor.run()


if __name__ == "__main__":
    main()
