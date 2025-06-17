# =============================================================================
# agents/excel_whisper_agent/agent.py
# =============================================================================
# 🎯 Purpose:
# This file defines a simple AI agent called ExcelWhisperAgent.
# It uses Google's ADK (Agent Development Kit) and Gemini model to read and analyze Excel files.
# =============================================================================


# -----------------------------------------------------------------------------
# 📦 Built-in & External Library Imports
# -----------------------------------------------------------------------------

# 🧠 Gemini-based AI agent provided by Google's ADK
from google.adk.agents.llm_agent import LlmAgent

# 📚 ADK services for session, memory, and file-like "artifacts"
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService

# 🏃 The "Runner" connects the agent, session, memory, and files into a complete system
from google.adk.runners import Runner

# 🧾 Gemini-compatible types for formatting input/output messages
from google.genai import types

# 🔐 Load environment variables (like API keys) from a `.env` file
from dotenv import load_dotenv
load_dotenv()  # Load variables like GOOGLE_API_KEY into the system
# This allows you to keep sensitive data out of your code.

from .tools import read_excel
from .instruction import INSTRUCTION


# -----------------------------------------------------------------------------
# 📊 ExcelWhisperAgent: Your Excel analysis expert agent
# -----------------------------------------------------------------------------

class ExcelWhisperAgent:
    # This agent only supports plain text input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 Initialize the ExcelWhisperAgent:
        - Creates the LLM agent (powered by Gemini)
        - Sets up session handling, memory, and a runner to execute tasks
        """
        self._agent = self._build_agent()  # Set up the Gemini agent
        self._user_id = "excel_whisper_agent_user"  # Use a fixed user ID for simplicity

        # 🧠 The Runner is what actually manages the agent and its environment
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),  # For files (not used here)
            session_service=InMemorySessionService(),    # Keeps track of conversations
            memory_service=InMemoryMemoryService(),      # Optional: remembers past messages
        )

    def _build_agent(self) -> LlmAgent:
        """
        ⚙️ Creates and returns a Gemini agent with basic settings.

        Returns:
            LlmAgent: An agent object from Google's ADK
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",         # Gemini model version
            name="excel_whisper_agent",              # Name of the agent
            description="Excel analysis expert that can read and analyze Excel files",    # Description for metadata
            instruction=INSTRUCTION,                 # System prompt
            tools=[
                read_excel,
            ],
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        📥 Handle a user query and return a response string.
        Note - function updated 28 May 2025
        Summary of changes:
        1. Agent's invoke method is made async
        2. All async calls (get_session, create_session, run_async)
            are awaited inside invoke method
        3. task manager's on_send_task updated to await the invoke call

        Reason - get_session and create_session are async in the
        "Current" Google ADK version and were synchronous earlier
        when this lecture was recorded. This is due to a recent change
        in the Google ADK code
        https://github.com/google/adk-python/commit/1804ca39a678433293158ec066d44c30eeb8e23b

        Args:
            query (str): What the user said (e.g., "read my excel file")
            session_id (str): Helps group messages into a session

        Returns:
            str: Agent's reply (usually Excel analysis results)
        """

        print(f"📊 ExcelWhisperAgent.invoke: Received query: '{query}' with session_id: '{session_id}'")

        # 🔁 Try to reuse an existing session (or create one if needed)
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id
        )

        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={}  # Optional dictionary to hold session state
            )

        # 📨 Format the user message in a way the Gemini model expects
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # 🚀 Run the agent using the Runner and collect the last event
        last_event = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        # 🧹 Fallback: return empty string if something went wrong
        if not last_event or not last_event.content or not last_event.content.parts:
            print(f"📊 ExcelWhisperAgent.invoke: No valid response generated")
            return ""

        # 📤 Extract and join all text responses into one string
        response = "\n".join([p.text for p in last_event.content.parts if p.text])
        print(f"📊 ExcelWhisperAgent.invoke: Generated response: '{response}'")
        return response

    async def stream(self, query: str, session_id: str):
        """
        🌀 Simulates a "streaming" agent that processes Excel files.
        This is here just to demonstrate that streaming is possible.

        Yields:
            dict: Response payload that says the task is complete and gives the Excel analysis
        """
        print(f"📊 ExcelWhisperAgent.stream: Processing query: '{query}' with session_id: '{session_id}'")

        # Get the actual response from the agent
        response_content = await self.invoke(query, session_id)

        response = {
            "is_task_complete": True,
            "content": response_content
        }
        print(f"📊 ExcelWhisperAgent.stream: Yielding response: {response}")
        yield response