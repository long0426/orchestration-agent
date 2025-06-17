# =============================================================================
# utilities/a2a/agent_connect.py
# =============================================================================
# 🎯 Purpose:
# Provides a simple wrapper (`AgentConnector`) around the A2AClient to send tasks
# to any remote agent identified by a base URL. This decouples the Orchestrator
# from low-level HTTP details and HTTP client setup.
# =============================================================================

import uuid                           # Standard library for generating unique IDs
import logging                        # Standard library for configurable logging
import httpx                          # HTTP client

# Import the official A2A SDK client which handles JSON-RPC task requests
from a2a.client import A2AClient
from a2a.types import (
    SendMessageRequest,             # For sending messages
    MessageSendParams,              # Structure to hold message content
    SendMessageSuccessResponse,     # Represents a successful response from the agent
    Task,                           # Task object representing the agent's work unit
)

# Create a logger for this module using its namespace
logger = logging.getLogger(__name__)


class AgentConnector:
    """
    🔗 Connects to a remote A2A agent and provides a uniform method to delegate tasks.

    Attributes:
        name (str): Human-readable identifier of the remote agent.
        client (A2AClient): HTTP client pointing at the agent's URL.
        httpx_client (httpx.AsyncClient): HTTP client instance.
    """

    def __init__(self, name: str, base_url: str):
        """
        Initialize the connector for a specific remote agent.

        Args:
            name (str): Identifier for the agent (e.g., "TellTime Agent").
            base_url (str): The HTTP endpoint (e.g., "http://localhost:10000").
        """
        # Store the agent’s name for logging and reference
        self.name = name
        # Create HTTP client instance
        self.httpx_client = httpx.AsyncClient()
        # Instantiate an A2AClient bound to the agent’s base URL with httpx_client
        self.client = A2AClient(url=base_url, httpx_client=self.httpx_client)
        # Log that the connector is ready for use
        logger.info(f"AgentConnector: initialized for {self.name} at {base_url}")

    async def send_task(self, message: str, session_id: str) -> Task:
        """
        Send a text task to the remote agent and return its completed Task.

        Args:
            message (str): What you want the agent to do (e.g., "What time is it?").
            session_id (str): Session identifier to group related calls (currently not used by A2A SDK).

        Returns:
            Task: The full Task object (including history) from the remote agent.
        """
        # Generate a unique ID for this message using uuid4, hex form
        message_id = uuid.uuid4().hex

        # Build the message payload in the expected A2A format
        message_payload = {
            "role": "user",                # Indicates this message is from the user
            "parts": [{"kind": "text", "text": message}],  # The actual message content
            "messageId": message_id,       # Unique message ID for tracking
        }

        # Create the request using the official A2A SDK types
        request = SendMessageRequest(
            id=uuid.uuid4().hex,  # Request ID
            params=MessageSendParams(message=message_payload)
        )

        # Log the outgoing request
        logger.info(f"AgentConnector: Sending request to {self.name}")
        logger.info(f"Request message: {message}")
        logger.info(f"Request payload: {message_payload}")

        # Use the A2AClient to send the message asynchronously and await the response
        result = await self.client.send_message(request)

        # Log the raw response
        logger.info(f"AgentConnector: Raw response from {self.name}: {result}")

        # Extract the Task from the response
        if isinstance(result.root, SendMessageSuccessResponse):
            task = result.root.result
            # Log the task details
            logger.info(f"AgentConnector: Task from {self.name} - ID: {task.id}, Status: {task.status}")
            if task.history:
                logger.info(f"AgentConnector: Task history length: {len(task.history)}")
                for i, msg in enumerate(task.history):
                    logger.info(f"AgentConnector: History[{i}] - Role: {msg.role}, Parts: {len(msg.parts) if msg.parts else 0}")
                    if msg.parts:
                        for j, part in enumerate(msg.parts):
                            logger.info(f"AgentConnector: History[{i}].Parts[{j}]: {part}")
            return task
        else:
            # Handle error case
            logger.error(f"AgentConnector: Error response from {self.name}: {result}")
            raise RuntimeError(f"Failed to send message to {self.name}: {result}")

    async def close(self):
        """
        Close the HTTP client to clean up resources.
        """
        await self.httpx_client.aclose()
