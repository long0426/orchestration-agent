# =============================================================================
# agents/host_agent/orchestrator.py
# =============================================================================
# 🎯 目的：
# 定義 OrchestratorAgent，該代理使用 Gemini LLM 解讀使用者查詢，
# 並將其委派給啟動時發現的任意子 A2A 代理。
# 也定義 OrchestratorTaskManager，透過 JSON-RPC 對外暴露這套邏輯。
# =============================================================================

import os                           # 標準函式庫，用於與作業系統互動
import uuid                         # 產生唯一識別碼（如 session ID）
import logging                      # 標準函式庫，用於彈性日誌紀錄
from dotenv import load_dotenv      # 載入 .env 檔案中的環境變數

# 載入 .env 檔案，讓如 GOOGLE_API_KEY 等環境變數可供 ADK client 使用
load_dotenv()

# -----------------------------------------------------------------------------
# Google ADK / Gemini 匯入
# -----------------------------------------------------------------------------
from google.adk.agents.llm_agent import LlmAgent
# LlmAgent：定義 Gemini AI 代理的核心類別

from google.adk.sessions import InMemorySessionService
# InMemorySessionService：將 session 狀態存於記憶體（適合 demo）

from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
# InMemoryMemoryService：可選的對話記憶體，存於 RAM

from google.adk.artifacts import InMemoryArtifactService
# InMemoryArtifactService：處理檔案/二進位物件（本例未用）

from google.adk.runners import Runner
# Runner：整合 agent、session、記憶體、工具調用

from google.adk.agents.readonly_context import ReadonlyContext
# ReadonlyContext：傳給 system prompt function 以讀取上下文

from google.adk.tools.tool_context import ToolContext
# ToolContext：傳給工具函式，提供狀態與操作

from google.genai import types           
# types.Content & types.Part：用於包裝 LLM 的使用者訊息

# -----------------------------------------------------------------------------
# A2A 伺服器端基礎設施
# -----------------------------------------------------------------------------
from server.task_manager import InMemoryTaskManager
# InMemoryTaskManager：提供記憶體型任務儲存與鎖定的基底類別

from models.request import SendTaskRequest, SendTaskResponse
# 進來的任務請求與回應的資料模型

from models.task import Message, TaskStatus, TaskState, TextPart
# Message：封裝角色+內容；TaskStatus/State：狀態列舉；TextPart：文字內容

# -----------------------------------------------------------------------------
# 連接子 A2A 代理的包裝器
# -----------------------------------------------------------------------------
from agents.host_agent.agent_connect import AgentConnector
# AgentConnector：A2AClient 的輕量包裝器，用於呼叫其他代理

from models.agent import AgentCard
# AgentCard：代理發現結果的中繼資料結構

# 設定模組層級 logger，方便 debug/info 訊息
logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """
    🤖 使用 Gemini LLM 路由進來的使用者查詢，
    透過工具呼叫任何已發現的子 A2A 代理。
    """

    # 定義支援的輸入/輸出 MIME 類型
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, agent_cards: list[AgentCard]):
        # 為每個發現到的 AgentCard 建立一個 AgentConnector
        # agent_cards 是 discovery 回傳的 AgentCard 物件列表
        self.connectors = {
            card.name: AgentConnector(card.name, card.url)
            for card in agent_cards
        }

        # 建立內部 LLM agent，帶入自訂工具與指令
        self._agent = self._build_agent()

        # 靜態 user ID，用於跨呼叫 session 追蹤
        self._user_id = "orchestrator_user"

        # Runner 整合 session、記憶體、artifact，並處理 agent.run()
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )

    def _build_agent(self) -> LlmAgent:
        """
        建立 Gemini LlmAgent，包含：
        - 模型名稱
        - 代理名稱/描述
        - 系統指令 callback
        - 可用工具函式
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",    # 指定 Gemini 模型版本
            name="orchestrator_agent",          # 代理的人類識別名稱
            description="Delegates user queries to child A2A agents based on intent.",
            instruction=self._root_instruction,  # 提供 system prompt 的函式
            tools=[
                self._list_agents,               # 工具1：列出可用子代理
                self._delegate_task             # 工具2：呼叫子代理
            ],
        )

    def _root_instruction(self, context: ReadonlyContext) -> str:
        """
        系統提示函式：回傳給 LLM 的指令文字，
        包含可用工具與子代理列表。
        """
        # 建立代理名稱的條列清單
        agent_list = "\n".join(f"- {name}" for name in self.connectors)
        return (
            "You are an orchestrator with two tools:\n"
            "1) list_agents() -> list available child agents\n"
            "2) delegate_task(agent_name, message) -> call that agent\n"
            "Use these tools to satisfy the user. Do not hallucinate.\n"
            "Available agents:\n" + agent_list
        )

    def _list_agents(self) -> list[str]:
        """
        工具函式：回傳目前已註冊的子代理名稱列表。
        LLM 想查詢可用代理時會呼叫。
        """
        return list(self.connectors.keys())

    async def _delegate_task(
        self,
        agent_name: str,
        message: str,
        tool_context: ToolContext
    ) -> str:
        """
        工具函式：將 `message` 轉發給指定的子代理
        （透過 AgentConnector），等待回應並回傳最後一則回覆文字。
        """
        # 驗證 agent_name 是否存在
        if agent_name not in self.connectors:
            raise ValueError(f"Unknown agent: {agent_name}")
        connector = self.connectors[agent_name]

        # 確保 session_id 可跨工具呼叫持續存在（透過 tool_context.state）
        state = tool_context.state
        if "session_id" not in state:
            state["session_id"] = str(uuid.uuid4())
        session_id = state["session_id"]

        # 非同步委派任務並等待 Task 結果
        child_task = await connector.send_task(message, session_id)

        # 從最後一則歷史訊息擷取文字（若有）
        if child_task.history and len(child_task.history) > 1:
            return child_task.history[-1].parts[0].text
        return ""

    async def invoke(self, query: str, session_id: str) -> str:
        """
        主要入口：接收使用者查詢與 session_id，
        建立或取得 session，包裝查詢給 LLM，
        執行 Runner（啟用工具），並回傳最終文字。
        註：2025/5/28 更新
        變更摘要：
        1. Agent 的 invoke 方法改為 async
        2. 所有 async 呼叫（get_session, create_session, run_async）
            都在 invoke 內 await
        3. task manager 的 on_send_task 也改為 await invoke

        原因：get_session 與 create_session 在新版 Google ADK 已改為 async，
        舊版為同步。詳見 Google ADK 近期異動：
        https://github.com/google/adk-python/commit/1804ca39a678433293158ec066d44c30eeb8e23b

        """
        # 嘗試重用現有 session
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id
        )
        # 若找不到則新建
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                session_id=session_id,
                state={}
            )

        # 將使用者查詢包裝成 types.Content 訊息
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=query)]
        )

        # 🚀 使用 Runner 執行 agent，收集最後一個事件
        last_event = None
        async for event in self._runner.run_async(
            user_id=self._user_id,
            session_id=session.id,
            new_message=content
        ):
            last_event = event

        # 🧹 若出錯則回傳空字串
        if not last_event or not last_event.content or not last_event.content.parts:
            return ""

        # 📤 擷取所有文字回應並合併成一個字串
        return "\n".join([p.text for p in last_event.content.parts if p.text])


class OrchestratorTaskManager(InMemoryTaskManager):
    """
    🪄 TaskManager 包裝器：將 OrchestratorAgent.invoke() 透過
    A2A JSON-RPC `tasks/send` 端點對外暴露，並處理記憶體儲存與回應格式化。
    """
    def __init__(self, agent: OrchestratorAgent):
        super().__init__()       # 初始化基底記憶體儲存
        self.agent = agent       # 儲存 orchestrator 邏輯

    def _get_user_text(self, request: SendTaskRequest) -> str:
        """
        輔助函式：從請求物件中擷取使用者原始輸入文字。
        """
        return request.params.message.parts[0].text

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """
        當 A2A 伺服器收到新任務時呼叫：
        1. 儲存進來的使用者訊息
        2. 呼叫 OrchestratorAgent 取得回應
        3. 將回應加入歷史並標記為已完成
        4. 回傳包含完整 Task 的 SendTaskResponse
        """
        logger.info(f"OrchestratorTaskManager received task {request.params.id}")

        # 步驟 1：儲存初始訊息
        task = await self.upsert_task(request.params)

        # 步驟 2：執行 orchestrator 邏輯
        user_text = self._get_user_text(request)
        response_text = await self.agent.invoke(user_text, request.params.sessionId)

        # 步驟 3：將 LLM 輸出包裝成 Message
        reply = Message(role="agent", parts=[TextPart(text=response_text)])
        async with self.lock:
            task.status = TaskStatus(state=TaskState.COMPLETED)
            task.history.append(reply)

        # 步驟 4：回傳結構化回應
        return SendTaskResponse(id=request.id, result=task)
