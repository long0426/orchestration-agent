# =============================================================================
# cmd.py
# =============================================================================
# Purpose:
# This file is a command-line interface (CLI) that lets users interact with
# the HostAgent running on an A2A server.
#
# It sends simple text messages to the HostAgent, which orchestrates tasks
# by delegating them to specialized child agents (TellTimeAgent, GreetingAgent,
# ExcelWhisperAgent, etc.).
#
# This version supports:
# - basic task sending via A2AClient to HostAgent
# - session reuse
# - optional task history printing
# - improved response handling for orchestrated tasks
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
    MessageSendParams
)


# -----------------------------------------------------------------------------
# @click.command(): Turns the function below into a command-line command
# -----------------------------------------------------------------------------
@click.command()
@click.option("--agent", default="http://localhost:10000", help="Base URL of the HostAgent server")
# ^ This defines the --agent option. It's a string with a default of localhost:10000 (HostAgent)
# ^ Used to point to the running HostAgent server which orchestrates child agents

@click.option("--session", default=0, help="Session ID (use 0 to generate a new one)")
# ^ This defines the --session option. A session groups multiple tasks together.
# ^ If user passes 0, we generate a random session ID using uuid4.

@click.option("--history", is_flag=True, help="Print full task history after receiving a response")
# ^ This defines a --history flag (boolean). If passed, full conversation history is shown.

async def cli(agent: str, session: str, history: bool):
    """
    CLI to send user messages to the HostAgent and display orchestrated responses.

    The HostAgent will automatically delegate tasks to appropriate child agents
    (TellTimeAgent, GreetingAgent, ExcelWhisperAgent, etc.) based on user input.

    Args:
        agent (str): The base URL of the HostAgent server (e.g., http://localhost:10000)
        session (str): Either a string session ID or 0 to generate one
        history (bool): If true, prints the full task history
    """

    # Initialize the client with proper timeout settings
    timeout = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s connect
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        client = A2AClient(url=f"{agent}", httpx_client=httpx_client)

        # Generate a new session ID if not provided (user passed 0)
        session_id = uuid4().hex if str(session) == "0" else str(session)
        print(f"🔗 使用 Session ID: {session_id}")

        # Test connection to HostAgent
        print(f"🔍 測試連接到 HostAgent ({agent})...")
        try:
            response = await httpx_client.get(f"{agent}/.well-known/agent.json")
            if response.status_code == 200:
                agent_info = response.json()
                print(f"✅ 連接成功！代理: {agent_info.get('name', 'Unknown')}")
            else:
                print(f"⚠️  連接異常，HTTP 狀態: {response.status_code}")
        except Exception as e:
            print(f"❌ 連接測試失敗: {e}")
            print("   請確認 HostAgent 是否正在運行")
            return

        # Start the main input loop
        while True:
            # Prompt user for input
            prompt = click.prompt("\n🤖 請輸入您的請求 (HostAgent 會自動委派給適當的子代理)，或輸入 ':q' / 'quit' 退出")

            # Exit loop if user types ':q' or 'quit'
            if prompt.strip().lower() in [":q", "quit"]:
                print("👋 再見！")
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
                print(f"📤 正在發送請求到 HostAgent...")
                # Send the message to the agent and get a structured Task response
                request = SendMessageRequest(
                    id=uuid4().hex,
                    params=MessageSendParams(**payload)
                )
                result = await client.send_message(request)

                # 檢查是否為錯誤響應
                if hasattr(result, 'error'):
                    print(f"\n❌ HostAgent 返回錯誤: {result.error.message}")
                    continue

                # 處理成功響應
                response_data = result.model_dump()['result']
                print(f"\n📝 任務 ID: {response_data['id']}")
                print(f"📝 任務狀態: {response_data['status']['state']}")

                # 從 artifacts 中提取 HostAgent 的回應
                agent_response = ""
                if response_data.get('artifacts') and len(response_data['artifacts']) > 0:
                    for artifact in response_data['artifacts']:
                        if artifact['name'] == 'current_result' and artifact.get('parts'):
                            for part in artifact['parts']:
                                if part.get('kind') == 'text':
                                    agent_response += part['text']

                # 顯示 HostAgent 的回應
                if agent_response:
                    print(f"\n🏠 HostAgent 回應: {agent_response}")
                else:
                    print("\n⚠️  未收到有效回應")

                # 如果用戶要求顯示完整歷史記錄
                if history and response_data.get('history'):
                    print(f"\n📚 完整對話歷史 ({len(response_data['history'])} 條訊息):")
                    for i, msg in enumerate(response_data['history']):
                        role = msg.get('role', 'unknown')
                        parts = msg.get('parts', [])
                        content = ""
                        for part in parts:
                            if part.get('kind') == 'text':
                                content += part.get('text', '')
                        print(f"  {i+1}. [{role}]: {content}")

                # 顯示詳細的 JSON 回應（可選）
                if history:
                    print("\n🔍 詳細回應資料：")
                    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))

            except httpx.ConnectError as e:
                print(f"\n❌ 無法連接到 HostAgent ({agent})")
                print("   請確認 HostAgent 是否正在運行")
                print("   啟動指令: python3 -m agents.host_agent --host=localhost --port=10000")
                print(f"   詳細錯誤: {e}")
            except httpx.TimeoutException as e:
                print(f"\n⏰ 請求超時，HostAgent 可能正在處理複雜任務")
                print(f"   詳細錯誤: {e}")
            except httpx.HTTPStatusError as e:
                print(f"\n❌ HTTP 錯誤: {e.response.status_code}")
                print(f"   回應內容: {e.response.text[:200]}...")
                if history:
                    print(f"   完整錯誤: {e}")
            except httpx.RequestError as e:
                print(f"\n❌ 請求錯誤: {e}")
                print("   這可能是網路連線問題或 HostAgent 回應格式問題")
            except Exception as e:
                print(f"\n❌ 發送請求時發生錯誤: {e}")
                print(f"   錯誤類型: {type(e).__name__}")
                if history:  # 只在 debug 模式下顯示詳細錯誤
                    import traceback
                    traceback.print_exc()


# -----------------------------------------------------------------------------
# Entrypoint: This ensures the CLI only runs when executing `python cmd.py`
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    # Run the async `cli()` function inside the event loop
    asyncio.run(cli())
