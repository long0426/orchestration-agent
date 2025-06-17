# =============================================================================
# agents/greeting_agent/__main__.py
# =============================================================================
# Purpose:
# This file starts the A2A-compatible agent server.
# It sets up environment, configures the task execution handler, agent card,
# and launches a Starlette-based web server for incoming agent tasks.
# =============================================================================

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import os                      # Provides access to environment variables
import sys                     # Used for exiting if setup is incomplete

import click                   # Helps define command-line interface for running the server
import httpx                   # HTTP client used for async push notifications
from dotenv import load_dotenv  # Loads .env file for environment variables

# Import the agent logic and its executor
from .agent import GreetingAgent                # Defines the actual agent logic
from .agent_executor import GreetingAgentExecutor  # Bridges the agent with A2A server

# Import A2A SDK components to create a working agent server
from a2a.server.apps import A2AStarletteApplication  # Main application class based on Starlette
from a2a.server.request_handlers import DefaultRequestHandler  # Default logic for handling tasks
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore  # In-memory task manager and notifier
from a2a.types import AgentCard, AgentSkill, AgentCapabilities  # Agent metadata definitions

# -----------------------------------------------------------------------------
# Load environment variables from .env file if present
# -----------------------------------------------------------------------------
load_dotenv()

# -----------------------------------------------------------------------------
# Main entry point to launch the agent server
# -----------------------------------------------------------------------------
@click.command()
@click.option('--host', 'host', default='localhost')     # Host where the agent will listen (default: localhost)
@click.option('--port', 'port', default=10001)            # Port where the agent will listen (default: 10000)
def main(host: str, port: int):
    """
    Launches the GreetingAgent A2A server.

    Args:
        host (str): Hostname or IP to bind to (default: localhost)
        port (int): TCP port to listen on (default: 10001)
    """
    # Check if the required API key is set in environment
    if not os.getenv('GOOGLE_API_KEY'):
        print("GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)  # Exit the program if API key is missing

    # Create HTTP client (used for push notifications)
    client = httpx.AsyncClient()

    # Print a friendly banner so the user knows the server is starting
    print(f"\n🚀 Starting GreetingAgent on http://{host}:{port}/\n")

    # Set up the request handler for processing incoming tasks
    handler = DefaultRequestHandler(
        agent_executor=GreetingAgentExecutor(),  # Hook in our custom agent
        task_store=InMemoryTaskStore(),          # Use in-memory store to manage task state
        push_notifier=InMemoryPushNotifier(client),  # Enable server push updates (e.g., via webhook)
    )

    # Set up the A2A server application using agent card and handler
    server = A2AStarletteApplication(
        agent_card=build_agent_card(host, port),  # Provide agent capabilities and skills
        http_handler=handler,                     # Attach the request handler
    )

    # Start the server using uvicorn async server
    import uvicorn
    uvicorn.run(server.build(), host=host, port=port)

# -----------------------------------------------------------------------------
# Defines the metadata card for this agent
# -----------------------------------------------------------------------------
def build_agent_card(host: str, port: int) -> AgentCard:
    return AgentCard(
        name="Greeting Agent",                                      # Human-readable name of the agent
        description="Greetings the user.",               # Short description
        url=f"http://{host}:{port}/",                               # Full URL where the agent is reachable
        version="1.0.0",                                            # Version of the agent
        capabilities=AgentCapabilities(streaming=True, pushNotifications=True),  # Supported features
        defaultInputModes=GreetingAgent.SUPPORTED_CONTENT_TYPES,    # Accepted input content types
        defaultOutputModes=GreetingAgent.SUPPORTED_CONTENT_TYPES,   # Returned output content types
        skills=[                                                     # Skills this agent supports (currently one)
            AgentSkill(
                id="greeting",                                     # Unique ID for the skill
                name="Greeting",                           # Display name
                description="Greetings the user.",
                tags=["greeting"],                             # Useful tags for search/filtering
                examples=["Hello", "Hi", "Greet me"],  # Example user prompts
            )
        ],
    )

# -----------------------------------------------------------------------------
# This ensures the server starts when you run `python3 -m agents.greeting_agent
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    main()
