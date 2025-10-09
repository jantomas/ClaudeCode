"""Adaptive telemetry sender for energy-efficient data transmission."""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from collections import deque
from loguru import logger

from azure_iot.device_client import AzureIoTClient
from utils.config_loader import get_config_loader


@dataclass
class TelemetryMessage:
    """Telemetry message with priority."""
    data: Dict[str, Any]
    priority: int  # 1=highest, 5=lowest
    timestamp: datetime
    message_type: str


class TelemetrySender:
    """
    Adaptive telemetry sender with priority queuing.

    Adjusts transmission rate based on battery level and connection quality.
    Buffers messages when offline and syncs when connection restored.
    """

    def __init__(
        self,
        iot_client: AzureIoTClient,
        config_loader=None
    ):
        """
        Initialize telemetry sender.

        Args:
            iot_client: AzureIoTClient instance
            config_loader: ConfigLoader instance
        """
        self._iot_client = iot_client
        self._config_loader = config_loader or get_config_loader()

        # Load telemetry configuration
        behavior_config = self._config_loader.get_behavior_config()
        self._telemetry_config = behavior_config['telemetry']

        # Transmission intervals
        self._base_interval = self._telemetry_config['lorawan']['base_interval']
        self._active_interval = self._telemetry_config['lorawan']['active_interval']
        self._current_interval = self._base_interval

        # Adaptive transmission
        self._adaptive_enabled = self._telemetry_config['lorawan']['adaptive']['enabled']
        self._low_battery_interval = self._telemetry_config['lorawan']['adaptive']['low_battery_interval']
        self._critical_battery_interval = self._telemetry_config['lorawan']['adaptive']['critical_battery_interval']

        # Message queue with priority
        self._message_queue: deque[TelemetryMessage] = deque(maxlen=1000)
        self._running = False
        self._sender_task: Optional[asyncio.Task] = None

        # Statistics
        self._messages_sent = 0
        self._messages_failed = 0
        self._last_send_time: Optional[datetime] = None

        logger.info("TelemetrySender initialized")

    def queue_telemetry(
        self,
        data: Dict[str, Any],
        message_type: str = "general",
        priority: int = 3
    ):
        """
        Queue telemetry message for sending.

        Args:
            data: Telemetry data
            message_type: Type of message
            priority: Priority level (1=highest, 5=lowest)
        """
        message = TelemetryMessage(
            data=data,
            priority=priority,
            timestamp=datetime.now(),
            message_type=message_type
        )

        # Insert into queue based on priority
        # Higher priority (lower number) goes first
        inserted = False
        for i, existing_msg in enumerate(self._message_queue):
            if message.priority < existing_msg.priority:
                # Insert before this message
                temp_queue = list(self._message_queue)
                temp_queue.insert(i, message)
                self._message_queue = deque(temp_queue, maxlen=1000)
                inserted = True
                break

        if not inserted:
            self._message_queue.append(message)

        logger.debug(
            f"Queued {message_type} telemetry (priority={priority}, "
            f"queue_size={len(self._message_queue)})"
        )

    def queue_position_update(self, latitude: float, longitude: float, altitude: float = 0.0):
        """Queue position update."""
        self.queue_telemetry(
            {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "timestamp": datetime.now().isoformat()
            },
            message_type="position",
            priority=2
        )

    def queue_orientation_update(self, roll: float, pitch: float, yaw: float):
        """Queue orientation update."""
        self.queue_telemetry(
            {
                "roll": roll,
                "pitch": pitch,
                "yaw": yaw,
                "timestamp": datetime.now().isoformat()
            },
            message_type="orientation",
            priority=3
        )

    def queue_battery_status(self, voltage: float, percentage: float, current: float = 0.0):
        """Queue battery status."""
        priority = 1 if percentage < 20.0 else 2
        self.queue_telemetry(
            {
                "voltage": voltage,
                "percentage": percentage,
                "current": current,
                "timestamp": datetime.now().isoformat()
            },
            message_type="battery",
            priority=priority
        )

    def queue_system_health(self, status: Dict[str, Any]):
        """Queue system health status."""
        self.queue_telemetry(
            status,
            message_type="health",
            priority=4
        )

    def queue_emergency_event(self, event: str, details: Dict[str, Any]):
        """Queue emergency event (highest priority)."""
        self.queue_telemetry(
            {
                "event": event,
                "details": details,
                "timestamp": datetime.now().isoformat()
            },
            message_type="emergency",
            priority=1
        )

    def set_battery_level(self, percentage: float):
        """
        Update battery level and adjust transmission interval.

        Args:
            percentage: Battery percentage (0-100)
        """
        if not self._adaptive_enabled:
            return

        if percentage < 10.0:
            # Critical battery - slowest transmission
            self._current_interval = self._critical_battery_interval
            logger.warning(f"Battery critical ({percentage}%), reducing telemetry rate")
        elif percentage < 30.0:
            # Low battery - reduced transmission
            self._current_interval = self._low_battery_interval
            logger.info(f"Battery low ({percentage}%), reducing telemetry rate")
        else:
            # Normal transmission
            self._current_interval = self._base_interval

    def set_active_mode(self, active: bool):
        """
        Set active mode (increases transmission rate).

        Args:
            active: True if actively moving
        """
        if active:
            self._current_interval = self._active_interval
            logger.debug("Active mode: Increased telemetry rate")
        else:
            self._current_interval = self._base_interval
            logger.debug("Idle mode: Normal telemetry rate")

    async def start(self):
        """Start telemetry sender background task."""
        if self._running:
            logger.warning("Telemetry sender already running")
            return

        self._running = True
        self._sender_task = asyncio.create_task(self._sender_loop())
        logger.info("Telemetry sender started")

    async def stop(self):
        """Stop telemetry sender."""
        if not self._running:
            return

        logger.info("Stopping telemetry sender")
        self._running = False

        if self._sender_task:
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass

        logger.info("Telemetry sender stopped")

    async def _sender_loop(self):
        """Background loop for sending telemetry."""
        while self._running:
            try:
                # Wait for interval
                await asyncio.sleep(self._current_interval)

                # Send queued messages
                await self._send_queued_messages()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in telemetry sender loop: {e}")
                await asyncio.sleep(5.0)  # Wait before retry

    async def _send_queued_messages(self):
        """Send queued telemetry messages."""
        if not self._message_queue:
            return

        # Send highest priority messages first
        messages_to_send = []
        max_batch_size = 10

        while len(messages_to_send) < max_batch_size and self._message_queue:
            messages_to_send.append(self._message_queue.popleft())

        logger.debug(f"Sending {len(messages_to_send)} telemetry messages")

        for message in messages_to_send:
            success = await self._send_message(message)

            if success:
                self._messages_sent += 1
                self._last_send_time = datetime.now()
            else:
                self._messages_failed += 1

                # Re-queue if failed (unless too old)
                age = (datetime.now() - message.timestamp).total_seconds()
                if age < 3600:  # Re-queue if less than 1 hour old
                    self._message_queue.append(message)
                else:
                    logger.warning(f"Dropping stale message (age={age}s)")

    async def _send_message(self, message: TelemetryMessage) -> bool:
        """
        Send a single telemetry message.

        Args:
            message: TelemetryMessage to send

        Returns:
            True if successful
        """
        try:
            # Add metadata
            telemetry_data = {
                **message.data,
                "message_type": message.message_type,
                "priority": message.priority,
                "queued_at": message.timestamp.isoformat(),
                "sent_at": datetime.now().isoformat()
            }

            # Send via IoT client
            success = await self._iot_client.send_telemetry(
                telemetry_data,
                properties={"messageType": message.message_type}
            )

            if success:
                logger.debug(f"Sent {message.message_type} telemetry")
            else:
                logger.warning(f"Failed to send {message.message_type} telemetry")

            return success

        except Exception as e:
            logger.error(f"Error sending telemetry: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get telemetry statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "messages_sent": self._messages_sent,
            "messages_failed": self._messages_failed,
            "queue_size": len(self._message_queue),
            "current_interval": self._current_interval,
            "last_send_time": self._last_send_time.isoformat() if self._last_send_time else None,
            "is_running": self._running
        }

    def clear_queue(self):
        """Clear all queued messages."""
        count = len(self._message_queue)
        self._message_queue.clear()
        logger.info(f"Cleared {count} queued telemetry messages")
