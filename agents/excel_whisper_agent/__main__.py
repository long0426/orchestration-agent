# =============================================================================
# agents/excel_whisper_agent/__main__.py
# =============================================================================
# Purpose:
# This file starts the A2A-compatible agent server.
# It sets up environment, configures the task execution handler, agent card,
# and launches a Starlette-based web server for incoming agent tasks.
# =============================================================================

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os
import sys
import httpx
import click

# Import the agent logic and its executor
from .agent import ExcelWhisperAgent                # Defines the actual agent logic
from .agent_executor import ExcelWhisperAgentExecutor  # Bridges the agent with A2A server

# Import A2A SDK components to create a working agent server
from a2a.server.apps import A2AStarletteApplication  # Main application class based on Starlette
from a2a.server.request_handlers import DefaultRequestHandler  # Default logic for handling tasks
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore  # In-memory task manager and notifier
from a2a.types import AgentCard, AgentSkill, AgentCapabilities  # Agent metadata definitions

# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

@click.command()
@click.option("--host", default="localhost", help="Host to bind ExcelWhisperAgent server to")
@click.option("--port", default=10003, help="Port for ExcelWhisperAgent server")
def main(host: str, port: int):
    """
    🚀 Main function to start the ExcelWhisperAgent server.

    This function:
    1. Builds the agent card with capabilities and skills
    2. Sets up the A2A server infrastructure
    3. Starts the server using uvicorn
    """

    # 1) Build the agent card that describes this agent's capabilities
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="excel_whisper",
        name="Excel Analysis",
        description="讀取並解析 Excel 檔案內容，提供數據分析和摘要。",
        tags=["excel", "pandas", "spreadsheet", "data-analysis"],
        examples=["讀取我的Excel檔案", "分析這個試算表", "read /path/to/file.xlsx"]
    )

    def build_agent_card(host: str, port: int) -> AgentCard:
        """
        🏷️ Builds and returns the agent card that describes this agent's capabilities.
        """
        return AgentCard(
            name="Excel Whisper Agent",
            description="Reads and analyzes Excel files using pandas and AI",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=ExcelWhisperAgent.SUPPORTED_CONTENT_TYPES,    # Accepted input content types
            defaultOutputModes=ExcelWhisperAgent.SUPPORTED_CONTENT_TYPES,   # Returned output content types
            capabilities=capabilities,
            skills=[skill]
        )

    # 2) Check for required environment variables
    if not os.getenv('GOOGLE_API_KEY'):
        print("GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)

    # Create HTTP client (used for push notifications)
    client = httpx.AsyncClient()

    # Print a friendly banner so the user knows the server is starting
    print(f"\n🚀 Starting ExcelWhisperAgent on http://{host}:{port}/\n")

    # Set up the request handler for processing incoming tasks
    handler = DefaultRequestHandler(
        agent_executor=ExcelWhisperAgentExecutor(),  # Hook in our custom agent
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

if __name__ == "__main__":
    main()