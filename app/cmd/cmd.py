# =============================================================================
# cmd.py
# =============================================================================
# Purpose:
# This file is a command-line interface (CLI) that lets users interact with
# the TellTimeAgent running on an A2A server.
#
# It sends simple text messages (like "What time is it?") to the agent,
# waits for a response, and displays it in the terminal.
#
# This version supports:
# - basic task sending via A2AClient
# - session reuse
# - optional task history printing
# =============================================================================

import asyncclick as click        # click is a CLI tool; asyncclick supports async functions
import asyncio                    # Built-in Python module to run async event loops
from uuid import uuid4            # Used to generate unique task and session IDs
import httpx                      # Async HTTP client
import json                       # 用於 JSON 格式化

# Import the A2A SDK client and related types
from a2a.client import A2AClient
from a2a.types import (
    SendMessageRequest,
    MessageSendParams,
    Task,
    TaskState
)

# Import the Task model so we can handle and parse responses from the agent
from models.task import Task


# -----------------------------------------------------------------------------
# @click.command(): Turns the function below into a command-line command
# -----------------------------------------------------------------------------
@click.command()
@click.option("--agent", default="http://localhost:10002", help="Base URL of the A2A agent server")
# ^ This defines the --agent option. It's a string with a default of localhost:10002
# ^ Used to point to the running agent server (adjust if server runs elsewhere)

@click.option("--session", default=0, help="Session ID (use 0 to generate a new one)")
# ^ This defines the --session option. A session groups multiple tasks together.
# ^ If user passes 0, we generate a random session ID using uuid4.

@click.option("--history", is_flag=True, help="Print full task history after receiving a response")
# ^ This defines a --history flag (boolean). If passed, full conversation history is shown.

async def cli(agent: str, session: str, history: bool):
    """
    CLI to send user messages to an A2A agent and display the response.

    Args:
        agent (str): The base URL of the A2A agent server (e.g., http://localhost:10002)
        session (str): Either a string session ID or 0 to generate one
        history (bool): If true, prints the full task history
    """

    # Initialize the client by providing the full POST endpoint for sending tasks
    async with httpx.AsyncClient() as httpx_client:
        client = A2AClient(url=f"{agent}", httpx_client=httpx_client)

        # Generate a new session ID if not provided (user passed 0)
        session_id = uuid4().hex if str(session) == "0" else str(session)

        # Start the main input loop
        while True:
            # Prompt user for input
            prompt = click.prompt("\nWhat do you want to send to the agent? (type ':q' or 'quit' to exit)")

            # Exit loop if user types ':q' or 'quit'
            if prompt.strip().lower() in [":q", "quit"]:
                break

            # Construct the payload using the expected JSON-RPC task format
            payload = {
                "message": {
                    "role": "user",  # The message is from the user
                    "parts": [{"kind": "text", "text": prompt}],  # Wrap user input in a text part
                    "messageId": uuid4().hex  # Generate a new unique message ID
                }
            }

            try:
                # Send the message to the agent and get a structured Task response
                request = SendMessageRequest(
                    id=uuid4().hex,  # 添加必需的 id 字段
                    params=MessageSendParams(**payload)
                )
                result = await client.send_message(request)
                print("\n📤 收到的回應：")
                print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
                
                # 檢查是否為錯誤響應
                if hasattr(result, 'error'):
                    print(f"\n❌ 代理返回錯誤: {result.error.message}")
                    continue
                
                # 處理成功響應
                response_data = result.model_dump()['result']
                print(f"\n📝 任務 ID: {response_data['id']}")
                print(f"📝 任務狀態: {response_data['status']['state']}")
                
                # 從 artifacts 中提取時間信息
                answer = []
                if response_data['artifacts'] and len(response_data['artifacts']) > 0:
                    for artifact in response_data['artifacts']:
                        if artifact['name'] == 'current_result' and artifact['parts']:
                            for part in artifact['parts']:
                                if part['kind'] == 'text':
                                    answer.append(part['text'])

                # Check if the agent responded (expecting at least 2 messages: user + agent)
                if response_data['history']:
                    reply = response_data['history'][-1]  # Last message is usually from the agent
                    print("\nAgent says:", "".join(answer))  # Print agent's text reply
                else:
                    print("\nNo response received.")

                # If --history flag was set, show the entire conversation history
                if history:
                    print("\n========= Conversation History =========")
                    for msg in response_data['history']:
                        print(f"[{msg['role']}] {msg['parts'][0]['text']}")  # Show each message in sequence

            except Exception as e:
                import traceback
                traceback.print_exc()
                # Catch and print any errors (e.g., server not running, invalid response)
                print(f"\n❌ Error while sending task: {e}")


# -----------------------------------------------------------------------------
# Entrypoint: This ensures the CLI only runs when executing `python cmd.py`
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Run the async `cli()` function inside the event loop
    asyncio.run(cli())
