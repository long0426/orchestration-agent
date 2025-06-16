# =============================================================================
# agents/greeting_agent/agent.py
# =============================================================================
# 🎯 Purpose:
# A composite “orchestrator” agent that:
#     1) Discovers all registered A2A agents via DiscoveryClient
#     2) Invokes the TellTimeAgent to fetch the current time
#     3) Generates a 2–3 line poetic greeting referencing that time
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

# 🔍 Discovery client for finding other agents
from utilities.discovery import DiscoveryClient

# 🔗 Connector for interacting with other agents
from utilities.a2a.agent_connect import AgentConnector

# 📝 Instruction for the GreetingAgent
from .instruction import INSTRUCTION

# 🔧 FunctionTool for interacting with other agents
from google.adk.tools import FunctionTool

# 🔐 Load environment variables (like API keys) from a `.env` file. 
# This allows you to keep sensitive data out of your code
from dotenv import load_dotenv
load_dotenv()  # Load variables like GOOGLE_API_KEY into the system


# -----------------------------------------------------------------------------
# 🕒 GreetingAgent: Your AI agent that crafts a 2–3 line poetic greeting referencing that time
# -----------------------------------------------------------------------------

class GreetingAgent:
    """
        🧠 Orchestrator “meta-agent” that:
            - Provides two LLM tools: list_agents() and call_agent(...)
            - On a “greet me” request:
                1) Calls list_agents() to see which agents are up
                2) Calls call_agent("TellTimeAgent", "What is the current time?")
                3) Crafts a 2–3 line poetic greeting referencing that time
        """
    
    # This agent only supports plain text input/output
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 Initialize the GreetingAgent:
        - Creates the LLM agent (powered by Gemini)
        - Sets up session handling, memory, and a runner to execute tasks
        """
        self._agent = self._build_agent()  # Set up the Gemini agent
        self._user_id = "time_agent_user"  # Use a fixed user ID for simplicity

        # 🧠 The Runner is what actually manages the agent and its environment
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),  # For files (not used here)
            session_service=InMemorySessionService(),    # Keeps track of conversations
            memory_service=InMemoryMemoryService(),      # Optional: remembers past messages
        )

        # A helper client to discover what agents are registered
        self.discovery = DiscoveryClient()

        # Cache for created connectors so we reuse them
        self.connectors: dict[str, AgentConnector] = {}

    def _build_agent(self) -> LlmAgent:
        """
        ⚙️ Creates and returns a Gemini agent with basic settings.

        Returns:
            LlmAgent: An agent object from Google's ADK
        """

        # --- Tool 1: list_agents ---
        async def list_agents() -> list[dict]:
            """
            Fetch all AgentCard metadata from the registry,
            return as a list of plain dicts.
            """
            # Ask DiscoveryClient for all cards (returns Pydantic models)
            cards = await self.discovery.list_agent_cards()
            # Convert each card to a dict (dropping None fields)
            return [card.model_dump(exclude_none=True) for card in cards]
        
        # --- Tool 2: call_agent ---
        async def call_agent(agent_name: str, message: str) -> str:
            """
            Given an agent_name string and a user message,
            find that agent’s URL, send the task, and return its reply.
            """
            # Re-fetch registry each call to catch new agents dynamically
            cards = await self.discovery.list_agent_cards()

            # Try to match exactly by name or id (case-insensitive)
            matched = next(
                (c for c in cards
                 if c.name.lower() == agent_name.lower()
                 or getattr(c, "id", "").lower() == agent_name.lower()),
                None
            )

            # Fallback: substring match if no exact found
            if not matched:
                matched = next(
                    (c for c in cards if agent_name.lower() in c.name.lower()),
                    None
                )

            # If still nothing, error out
            if not matched:
                raise ValueError(f"Agent '{agent_name}' not found.")

            # Use Pydantic model’s name field as key
            key = matched.name
            # If we haven’t built a connector yet, create and cache one
            if key not in self.connectors:
                self.connectors[key] = AgentConnector(
                    name=matched.name,
                    base_url=matched.url
                )
            connector = self.connectors[key]

            # Use a single session per greeting agent run (could be improved)
            session_id = self.user_id

            # Delegate the task and wait for the full Task object
            task = await connector.send_task(message, session_id=session_id)

            # Pull the final agent reply out of the history
            if task.history and task.history[-1].parts:
                return task.history[-1].parts[0].text

            # If no reply, return empty string
            return ""

        # Wrap our Python functions into ADK FunctionTool objects
        list_agents_tool = FunctionTool(list_agents)
        call_agent_tool = FunctionTool(call_agent)

        # --- Build the agent ---
        return LlmAgent(
            model="gemini-1.5-flash-latest",         # Gemini model version
            name="greeting_agent",                  # Name of the agent
            description="Greetings the user",    # Description for metadata
            instruction=INSTRUCTION,  # System prompt
            tools=[list_agents, call_agent]  # Add our tools
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """
        Handle a user query and return a response string.
        """

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
            return ""

        # 📤 Extract and join all text responses into one string
        return "\n".join([p.text for p in last_event.content.parts if p.text])


    async def stream(self, query: str, session_id: str):
        """
        🌀 Simulates a "streaming" agent that returns a single reply.
        This is here just to demonstrate that streaming is possible.

        """
        yield {
            "is_task_complete": True,
            "content": f"Hello, how are you?"
        }
