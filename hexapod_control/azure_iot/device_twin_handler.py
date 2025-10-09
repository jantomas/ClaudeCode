"""Device Twin handler for configuration synchronization."""

import asyncio
from typing import Dict, Any, Optional, Callable
from loguru import logger

from azure_iot.device_client import AzureIoTClient
from utils.config_loader import get_config_loader


class DeviceTwinHandler:
    """
    Handles Azure IoT Device Twin synchronization.

    Manages desired properties from cloud and reports current state.
    """

    def __init__(
        self,
        iot_client: AzureIoTClient,
        config_loader=None
    ):
        """
        Initialize Device Twin handler.

        Args:
            iot_client: AzureIoTClient instance
            config_loader: ConfigLoader instance
        """
        self._iot_client = iot_client
        self._config_loader = config_loader or get_config_loader()

        # Load configuration
        azure_config = self._config_loader.get_azure_config()
        twin_config = azure_config.get('device_twin', {})

        self._update_interval = twin_config.get('update_interval', 300)
        self._desired_properties = twin_config.get('desired_properties', [])

        # Property change handlers
        self._property_handlers: Dict[str, Callable] = {}

        # Current state
        self._reported_properties: Dict[str, Any] = {}
        self._desired_values: Dict[str, Any] = {}

        # Background task
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None

        logger.info("DeviceTwinHandler initialized")

    def register_property_handler(self, property_name: str, handler: Callable):
        """
        Register handler for desired property changes.

        Args:
            property_name: Name of property to watch
            handler: Async callable(new_value)
        """
        self._property_handlers[property_name] = handler
        logger.info(f"Registered property handler for: {property_name}")

    async def update_reported_property(self, property_name: str, value: Any):
        """
        Update a reported property.

        Args:
            property_name: Property name
            value: Property value
        """
        self._reported_properties[property_name] = value

        # Send to IoT Hub
        patch = {property_name: value}
        success = await self._iot_client.update_reported_properties(patch)

        if success:
            logger.debug(f"Updated reported property: {property_name}={value}")
        else:
            logger.warning(f"Failed to update reported property: {property_name}")

    async def update_device_status(self, status: Dict[str, Any]):
        """
        Update device status in reported properties.

        Args:
            status: Status dictionary
        """
        await self.update_reported_property("device_status", status)

    async def sync_twin(self):
        """Synchronize device twin (get latest desired properties)."""
        twin = await self._iot_client.get_twin()

        if not twin:
            logger.warning("Failed to get device twin")
            return

        # Process desired properties
        desired = twin.get('desired', {})

        for prop_name in self._desired_properties:
            if prop_name in desired:
                new_value = desired[prop_name]
                old_value = self._desired_values.get(prop_name)

                if new_value != old_value:
                    logger.info(f"Desired property changed: {prop_name}={new_value}")
                    self._desired_values[prop_name] = new_value

                    # Call handler if registered
                    if prop_name in self._property_handlers:
                        try:
                            handler = self._property_handlers[prop_name]
                            await handler(new_value)
                        except Exception as e:
                            logger.error(
                                f"Error in property handler for {prop_name}: {e}"
                            )

        logger.debug("Device twin synchronized")

    async def start(self):
        """Start device twin synchronization."""
        if self._running:
            logger.warning("Device twin handler already running")
            return

        self._running = True

        # Initial sync
        await self.sync_twin()

        # Start background sync task
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("Device twin handler started")

    async def stop(self):
        """Stop device twin synchronization."""
        if not self._running:
            return

        logger.info("Stopping device twin handler")
        self._running = False

        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass

        logger.info("Device twin handler stopped")

    async def _sync_loop(self):
        """Background loop for periodic twin synchronization."""
        while self._running:
            try:
                await asyncio.sleep(self._update_interval)
                await self.sync_twin()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device twin sync loop: {e}")
                await asyncio.sleep(30.0)

    def get_desired_value(self, property_name: str, default: Any = None) -> Any:
        """
        Get desired property value.

        Args:
            property_name: Property name
            default: Default value if not found

        Returns:
            Property value or default
        """
        return self._desired_values.get(property_name, default)

    def get_reported_value(self, property_name: str, default: Any = None) -> Any:
        """
        Get reported property value.

        Args:
            property_name: Property name
            default: Default value if not found

        Returns:
            Property value or default
        """
        return self._reported_properties.get(property_name, default)
