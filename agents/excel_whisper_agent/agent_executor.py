# =============================================================================
# agents/excel_whisper_agent/agent_executor.py
# =============================================================================
# Purpose:
# This file defines the "executor" that acts as a bridge between the A2A server
# and the underlying ExcelWhisper agent. It listens to tasks and dispatches them to
# the agent, then sends back task updates and results through the event queue.
# =============================================================================

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

from .agent import ExcelWhisperAgent  # Imports the ExcelWhisperAgent class from the same directory

# Importing base classes from the A2A SDK to define agent behavior
from a2a.server.agent_execution import AgentExecutor  # Base class for defining agent task executor logic
from a2a.server.agent_execution import RequestContext  # Holds information about the incoming user query and context

# EventQueue is used to push updates back to the A2A server (e.g., task status, results)
from a2a.server.events.event_queue import EventQueue

# Importing event and status types for responding to client
from a2a.types import (
    TaskArtifactUpdateEvent,  # Event for sending result artifacts back to the client
    TaskStatusUpdateEvent,   # Event for sending status updates (e.g., working, completed)
    TaskStatus,              # Object that holds the current status of the task
    TaskState,               # Enum that defines states: working, completed, input_required, etc.
)

# Utility functions to create standardized message and artifact formats
from a2a.utils import (
    new_agent_text_message,  # Creates a message object from agent to client
    new_task,                # Creates a new task object from the initial message
    new_text_artifact        # Creates a textual result artifact
)

# -----------------------------------------------------------------------------
# ExcelWhisperAgentExecutor: Connects the agent logic to A2A server infrastructure
# -----------------------------------------------------------------------------

class ExcelWhisperAgentExecutor(AgentExecutor):  # Define a new executor by extending A2A's AgentExecutor
    """
    This class connects the ExcelWhisperAgent to the A2A server runtime. It implements
    the `execute` function to run tasks and push updates to the event queue.
    """

    def __init__(self):  # Constructor for the executor class
        self.agent = ExcelWhisperAgent()  # Creates an instance of the ExcelWhisperAgent for handling queries

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        # This method is called when a new task is received

        query = context.get_user_input()  # Extracts the actual text of the user's message
        task = context.current_task      # Gets the task object if it already exists

        print(f"📊 ExcelWhisperAgent: Received request")
        print(f"📊 ExcelWhisperAgent: Query: '{query}'")
        print(f"📊 ExcelWhisperAgent: Context message: {context.message}")
        print(f"📊 ExcelWhisperAgent: Current task: {task}")

        if not context.message:          # Ensure the message is not missing
            raise Exception('No message provided')  # Raise an error if something's wrong

        if not task:                     # If no existing task, this is a new interaction
            task = new_task(context.message)       # Create a new task based on the message
            print(f"📊 ExcelWhisperAgent: Created new task: {task}")
            await event_queue.enqueue_event(task)  # Wait for event to be queued

        # Use the agent to handle the query via async stream
        print(f"📊 ExcelWhisperAgent: Starting to process query with task.contextId: {task.contextId}")
        async for event in self.agent.stream(query, task.contextId):
            print(f"📊 ExcelWhisperAgent: Generated event: {event}")

            if event['is_task_complete']:  # If the task has been successfully completed
                print(f"📊 ExcelWhisperAgent: Task completed with content: '{event['content']}'")
                # Send the result artifact to the A2A server
                artifact = new_text_artifact(     # The result artifact
                    name='excel_analysis_result',      # Name of the artifact
                    description='Result of Excel analysis request to agent.',  # Description
                    text=event['content'],      # The actual result text
                )
                print(f"📊 ExcelWhisperAgent: Created artifact: {artifact}")

                # Send the artifact update event to the A2A server
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        taskId=task.id,                 # ID of the task
                        contextId=task.contextId,       # Context ID
                        artifact=artifact,              # The artifact containing the result
                        append=False,                   # Replace any existing artifacts
                        lastChunk=True,                 # This is the final chunk
                    )
                )

                # Send the task completion status to the A2A server
                status_event = TaskStatusUpdateEvent(
                    taskId=task.id,                 # ID of the task
                    contextId=task.contextId,       # Context ID
                    status=TaskStatus(state=TaskState.completed),  # Mark as completed
                    final=True,                     # This is the final status update
                )
                print(f"📊 ExcelWhisperAgent: Sending completion status: {status_event}")
                await event_queue.enqueue_event(status_event)

            elif event.get('require_user_input'):  # If the agent needs more information from user
                # Enqueue an input_required status with a message
                await event_queue.enqueue_event(
                    TaskStatusUpdateEvent(
                        taskId=task.id,                 # ID of the task
                        contextId=task.contextId,       # Context ID
                        status=TaskStatus(
                            state=TaskState.input_required,  # Set state as input_required
                            message=new_agent_text_message(  # Provide a message asking for input
                                event['content'],             # Message content
                                task.contextId,               # Context ID
                                task.id                       # Task ID
                            ),
                        ),
                        final=True,                     # Input_required is a final state until user responds
                    )
                )

            else:
                # Handle any other event types (e.g., progress updates)
                print(f"📊 ExcelWhisperAgent: Unhandled event type: {event}")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Optional method to cancel long-running tasks (not supported here)
        raise Exception('Cancel not supported')  # Raise error since this agent doesn't support canceling
