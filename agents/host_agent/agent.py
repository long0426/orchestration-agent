# =============================================================================
# agents/host_agent/agent.py
# =============================================================================
# 🎯 目的：
# 定義 HostAgent 的核心邏輯，使用 Google ADK 和 A2A SDK。
# =============================================================================

import json
import logging
import httpx
from typing import Dict

# Google ADK 匯入
from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.tools.function_tool import FunctionTool
from google.genai import types

# A2A SDK 匯入
from utilities.a2a.agent_connect import AgentConnector

# 本地匯入
from agents.host_agent.instruction import INSTRUCTION

# 設定日誌
logger = logging.getLogger(__name__)


class HostAgent:
    """
    🤖 Host Agent 負責協調和委派任務給子代理。
    使用 Google ADK 的 LLM 來理解用戶意圖並選擇適當的子代理。
    """

    # 定義支援的內容類型
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """初始化 HostAgent"""
        self._user_id = "host_agent_user"

        # 儲存已連接的代理
        self.connectors: Dict[str, AgentConnector] = {}

        # 檢查並印出已註冊的代理
        self._check_registered_agents()

        # 建立 LLM agent
        self._agent = self._build_agent()

        # 建立 Runner
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    async def _check_agent_connection(self, agent_data: dict) -> bool:
        """檢查單個代理的連線狀態"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{agent_data['url']}.well-known/agent.json")
                if response.status_code == 200:
                    return True
                else:
                    return False
        except Exception as e:
            logger.debug(f"Connection failed to {agent_data['name']}: {e}")
            return False

    def _check_registered_agents(self):
        """檢查並印出已註冊的代理連線狀態"""
        print("\n" + "="*60)
        print("🔍 檢查已註冊的代理連線狀態")
        print("="*60)

        try:
            with open("utilities/agent_registry.json", "r") as f:
                registry = json.load(f)

            agents = registry.get("agents", [])
            if not agents:
                print("❌ 沒有找到已註冊的代理")
                return

            print(f"📋 找到 {len(agents)} 個已註冊的代理：\n")

            # 同步檢查每個代理（簡化版本）
            for i, agent_data in enumerate(agents, 1):
                name = agent_data.get("name", "Unknown")
                url = agent_data.get("url", "Unknown")
                description = agent_data.get("description", "No description")

                print(f"{i}. 🤖 {name}")
                print(f"   📍 URL: {url}")
                print(f"   📝 描述: {description}")

                # 連線檢查：只要能取得有效的 agent card 就算成功
                try:
                    with httpx.Client(timeout=3.0) as client:
                        response = client.get(f"{url}.well-known/agent.json")
                        if response.status_code == 200:
                            agent_info = response.json()
                            # 驗證 agent card 的基本結構
                            if 'name' in agent_info:
                                print(f"   ✅ 連線狀態: 成功 (取得有效 Agent Card)")
                                print(f"   🏷️  實際名稱: {agent_info['name']}")
                                if 'version' in agent_info:
                                    print(f"   📦 版本: {agent_info['version']}")
                                if 'description' in agent_info:
                                    print(f"   � 描述: {agent_info['description']}")
                                if 'skills' in agent_info and agent_info['skills']:
                                    skills = [skill.get('name', 'Unknown') for skill in agent_info['skills']]
                                    print(f"   🛠️  技能: {', '.join(skills)}")
                            else:
                                print(f"   🟡 連線狀態: 取得回應但 Agent Card 格式無效")
                        else:
                            print(f"   ❌ 連線狀態: 失敗 (HTTP {response.status_code})")
                except Exception as e:
                    print(f"   ❌ 連線狀態: 失敗 ({str(e)[:50]}...)")

                print()  # 空行分隔

        except FileNotFoundError:
            print("❌ 找不到 utilities/agent_registry.json 檔案")
        except json.JSONDecodeError:
            print("❌ agent_registry.json 檔案格式錯誤")
        except Exception as e:
            print(f"❌ 檢查代理時發生錯誤: {e}")

        print("="*60 + "\n")

    def _build_agent(self) -> LlmAgent:
        """建立 Google ADK LlmAgent"""
        
        # 定義工具函數
        async def list_agents() -> str:
            """列出所有可用的代理"""
            print(f"🏠 HostAgent: list_agents called")

            # 從註冊表載入代理資訊
            try:
                with open("utilities/agent_registry.json", "r") as f:
                    registry = json.load(f)

                agents_info = []
                for agent_data in registry.get("agents", []):
                    name = agent_data.get("name", "Unknown")
                    description = agent_data.get("description", "No description")
                    url = agent_data.get("url", "Unknown")

                    # 檢查連線狀態：只要能取得 agent card 就算成功
                    try:
                        with httpx.Client(timeout=2.0) as client:
                            response = client.get(f"{url}.well-known/agent.json")
                            if response.status_code == 200:
                                # 嘗試解析 JSON 以確保是有效的 agent card
                                agent_card = response.json()
                                # 基本驗證：確保有必要的欄位
                                if 'name' in agent_card:
                                    status = "🟢 Online"
                                else:
                                    status = "🟡 Invalid Card"
                            else:
                                status = "🔴 Offline"
                    except:
                        status = "🔴 Offline"

                    agents_info.append(f"- {name} ({status}): {description}")

                result = "Available agents:\n" + "\n".join(agents_info)
                print(f"🏠 HostAgent: Available agents: {result}")
                return result

            except Exception as e:
                logger.error(f"Failed to load agent registry: {e}")
                return "Error: Could not load agent information"

        async def call_agent(agent_name: str, message: str) -> str:
            """呼叫指定的代理"""
            print(f"🏠 HostAgent: call_agent called with agent_name='{agent_name}', message='{message}'")
            
            try:
                # 從註冊表載入代理資訊
                with open("utilities/agent_registry.json", "r") as f:
                    registry = json.load(f)
                
                # 尋找匹配的代理
                matched = None
                for agent_data in registry.get("agents", []):
                    if agent_data.get("name", "").lower() == agent_name.lower():
                        matched = agent_data
                        break
                
                if not matched:
                    # 嘗試部分匹配
                    for agent_data in registry.get("agents", []):
                        if agent_name.lower() in agent_data.get("name", "").lower():
                            matched = agent_data
                            break
                
                if not matched:
                    return f"Agent '{agent_name}' not found."
                
                # 建立或重用連接器
                key = matched["name"]
                if key not in self.connectors:
                    print(f"🏠 HostAgent: Creating new connector for {matched['name']} at {matched['url']}")
                    self.connectors[key] = AgentConnector(
                        name=matched["name"],
                        base_url=matched["url"]
                    )
                
                connector = self.connectors[key]
                
                # 使用固定的 session_id
                session_id = self._user_id
                
                # 委派任務
                print(f"🏠 HostAgent: Calling {matched['name']} with message: '{message}'")
                task = await connector.send_task(message, session_id=session_id)
                print(f"🏠 HostAgent: Received task from {matched['name']}: {task}")
                
                # 提取回應 - 優先從 artifacts 提取
                if task.artifacts:
                    print(f"🏠 HostAgent: Found {len(task.artifacts)} artifacts")
                    for artifact in task.artifacts:
                        if artifact.name == 'current_result' and artifact.parts:
                            for part in artifact.parts:
                                if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                    result = part.root.text
                                    print(f"🏠 HostAgent: Extracted text from artifact: '{result}'")
                                    return result
                
                # 備用：從歷史中提取
                if task.history and len(task.history) > 1:
                    for message_obj in task.history:
                        if str(message_obj.role).lower() == 'agent' and message_obj.parts:
                            part = message_obj.parts[0]
                            if hasattr(part, 'root') and hasattr(part.root, 'text'):
                                result = part.root.text
                                print(f"🏠 HostAgent: Extracted text from history: '{result}'")
                                return result
                
                print(f"🏠 HostAgent: Could not extract response from task")
                return "No response received from agent"
                
            except Exception as e:
                logger.error(f"Error calling agent {agent_name}: {e}")
                return f"Error calling agent {agent_name}: {str(e)}"

        # 包裝工具函數
        list_agents_tool = FunctionTool(list_agents)
        call_agent_tool = FunctionTool(call_agent)

        # 建立 LlmAgent
        return LlmAgent(
            model="gemini-1.5-flash-latest",
            name="host_agent",
            description="Orchestrates tasks by delegating to child agents",
            instruction=INSTRUCTION,
            tools=[list_agents_tool, call_agent_tool]
        )

    async def invoke(self, query: str, session_id: str) -> str:
        """處理用戶查詢並返回回應"""
        print(f"🏠 HostAgent.invoke: Received query: '{query}' with session_id: '{session_id}'")
        
        # 取得或建立 session
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
                state={}
            )
        
        # 格式化用戶訊息
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )
        
        # 執行 agent
        last_event = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event
        
        # 提取回應
        if not last_event or not last_event.content or not last_event.content.parts:
            print(f"🏠 HostAgent.invoke: No valid response generated")
            return ""
        
        response = "\n".join([p.text for p in last_event.content.parts if p.text])
        print(f"🏠 HostAgent.invoke: Generated response: '{response}'")
        return response

    async def stream(self, query: str, session_id: str):
        """串流處理查詢"""
        print(f"🏠 HostAgent.stream: Processing query: '{query}' with session_id: '{session_id}'")
        
        # 使用 invoke 方法處理請求
        response = await self.invoke(query, session_id)
        
        yield {
            "is_task_complete": True,
            "content": response
        }
