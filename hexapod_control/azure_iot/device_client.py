"""Azure IoT Hub device client for hexapod."""

import asyncio
from typing import Optional, Callable, Dict, Any
from loguru import logger

try:
    from azure.iot.device.aio import IoTHubDeviceClient
    from azure.iot.device import Message, MethodResponse
    AZURE_IOT_AVAILABLE = True
except ImportError:
    AZURE_IOT_AVAILABLE = False
    logger.warning(
        "Azure IoT SDK not available. Install with: pip install azure-iot-device"
    )

from utils.config_loader import get_config_loader


class AzureIoTClient:
    """
    Azure IoT Hub device client.

    Handles connection, telemetry, C2D messages, and direct methods.
    """

    def __init__(self, config_loader=None, mock_mode: bool = False):
        """
        Initialize Azure IoT client.

        Args:
            config_loader: ConfigLoader instance
            mock_mode: If True, simulate connection (for development)
        """
        self._config_loader = config_loader or get_config_loader()
        self._mock_mode = mock_mode or not AZURE_IOT_AVAILABLE
        self._client: Optional[IoTHubDeviceClient] = None
        self._connected = False

        # Load Azure configuration
        try:
            azure_config = self._config_loader.get_azure_config()
            self._connection_string = azure_config['azure_iot']['connection_string']
            self._protocol = azure_config['azure_iot'].get('protocol', 'MQTT')
            self._keep_alive = azure_config['azure_iot'].get('keep_alive', 60)

            # Check if mock mode is configured
            dev_config = azure_config.get('development', {})
            if dev_config.get('mock_connection', False):
                self._mock_mode = True

        except Exception as e:
            logger.error(f"Failed to load Azure configuration: {e}")
            self._mock_mode = True
            self._connection_string = ""

        # Message handlers
        self._message_handlers: Dict[str, Callable] = {}
        self._method_handlers: Dict[str, Callable] = {}

        if self._mock_mode:
            logger.info("AzureIoTClient initialized in MOCK mode")
        else:
            logger.info("AzureIoTClient initialized")

    async def connect(self) -> bool:
        """
        Connect to Azure IoT Hub.

        Returns:
            True if successful
        """
        if self._connected:
            logger.warning("Already connected to Azure IoT Hub")
            return True

        if self._mock_mode:
            logger.info("Mock mode: Simulating Azure IoT Hub connection")
            self._connected = True
            return True

        if not self._connection_string:
            logger.error("No connection string configured")
            return False

        try:
            # Create device client
            self._client = IoTHubDeviceClient.create_from_connection_string(
                self._connection_string
            )

            # Set connection parameters
            self._client.keep_alive = self._keep_alive

            # Connect
            await self._client.connect()

            self._connected = True
            logger.info("Connected to Azure IoT Hub")

            # Set up handlers
            await self._setup_handlers()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Azure IoT Hub: {e}")
            return False

    async def _setup_handlers(self):
        """Setup message and method handlers."""
        if self._mock_mode or not self._client:
            return

        # Set up C2D message handler
        self._client.on_message_received = self._handle_c2d_message

        # Set up method request handler
        self._client.on_method_request_received = self._handle_method_request

    async def _handle_c2d_message(self, message):
        """Handle cloud-to-device message."""
        logger.info(f"Received C2D message: {message.data.decode('utf-8')}")

        try:
            # Extract command from message properties
            command = message.custom_properties.get('command', 'unknown')

            # Call registered handler if exists
            if command in self._message_handlers:
                handler = self._message_handlers[command]
                await handler(message.data.decode('utf-8'))
            else:
                logger.warning(f"No handler registered for command: {command}")

        except Exception as e:
            logger.error(f"Error handling C2D message: {e}")

    async def _handle_method_request(self, method_request):
        """Handle direct method invocation."""
        logger.info(f"Received method request: {method_request.name}")

        try:
            # Call registered method handler
            if method_request.name in self._method_handlers:
                handler = self._method_handlers[method_request.name]
                result = await handler(method_request.payload)

                # Send response
                response = MethodResponse.create_from_method_request(
                    method_request,
                    status=200,
                    payload=result
                )
            else:
                logger.warning(f"No handler for method: {method_request.name}")
                response = MethodResponse.create_from_method_request(
                    method_request,
                    status=404,
                    payload={"error": f"Method {method_request.name} not found"}
                )

            await self._client.send_method_response(response)

        except Exception as e:
            logger.error(f"Error handling method request: {e}")

            # Send error response
            response = MethodResponse.create_from_method_request(
                method_request,
                status=500,
                payload={"error": str(e)}
            )
            await self._client.send_method_response(response)

    def register_message_handler(self, command: str, handler: Callable):
        """
        Register handler for C2D message command.

        Args:
            command: Command name
            handler: Async callable(message_data)
        """
        self._message_handlers[command] = handler
        logger.info(f"Registered C2D message handler for: {command}")

    def register_method_handler(self, method_name: str, handler: Callable):
        """
        Register handler for direct method.

        Args:
            method_name: Method name
            handler: Async callable(payload) -> result
        """
        self._method_handlers[method_name] = handler
        logger.info(f"Registered method handler for: {method_name}")

    async def send_telemetry(
        self,
        data: Dict[str, Any],
        properties: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send telemetry message to IoT Hub.

        Args:
            data: Telemetry data (will be JSON serialized)
            properties: Optional message properties

        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected to Azure IoT Hub")
            return False

        if self._mock_mode:
            logger.debug(f"Mock: Sending telemetry: {data}")
            return True

        try:
            import json

            # Create message
            message = Message(json.dumps(data))
            message.content_type = "application/json"
            message.content_encoding = "utf-8"

            # Add custom properties
            if properties:
                for key, value in properties.items():
                    message.custom_properties[key] = value

            # Send message
            await self._client.send_message(message)
            logger.debug("Telemetry sent successfully")

            return True

        except Exception as e:
            logger.error(f"Failed to send telemetry: {e}")
            return False

    async def update_reported_properties(self, properties: Dict[str, Any]) -> bool:
        """
        Update device twin reported properties.

        Args:
            properties: Properties to report

        Returns:
            True if successful
        """
        if not self._connected:
            logger.error("Not connected to Azure IoT Hub")
            return False

        if self._mock_mode:
            logger.debug(f"Mock: Updating reported properties: {properties}")
            return True

        try:
            twin_patch = self._client.patch_twin_reported_properties(properties)
            await twin_patch
            logger.info("Reported properties updated")
            return True

        except Exception as e:
            logger.error(f"Failed to update reported properties: {e}")
            return False

    async def get_twin(self) -> Optional[Dict[str, Any]]:
        """
        Get current device twin.

        Returns:
            Device twin data or None
        """
        if not self._connected:
            logger.error("Not connected to Azure IoT Hub")
            return None

        if self._mock_mode:
            logger.debug("Mock: Getting device twin")
            return {
                "desired": {"gait_mode": "tripod", "max_speed": 1.0},
                "reported": {"status": "operational"}
            }

        try:
            twin = await self._client.get_twin()
            return twin

        except Exception as e:
            logger.error(f"Failed to get device twin: {e}")
            return None

    async def disconnect(self):
        """Disconnect from Azure IoT Hub."""
        if not self._connected:
            return

        logger.info("Disconnecting from Azure IoT Hub")

        if self._mock_mode:
            self._connected = False
            return

        try:
            if self._client:
                await self._client.disconnect()
            self._connected = False
            logger.info("Disconnected from Azure IoT Hub")

        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

    def is_connected(self) -> bool:
        """Check if connected to IoT Hub."""
        return self._connected

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
