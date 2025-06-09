# =============================================================================
# agents/excel_whisper_agent/agent.py
# =============================================================================
# 🎯 目的：
# 本檔案定義一個簡單的 AI 代理 ExcelWhisperAgent。
# 它使用 Google ADK (Agent Development Kit) 與 Gemini 模型來讀取 Excel 檔案。
# =============================================================================


# -----------------------------------------------------------------------------
# 📦 內建與外部套件匯入
# -----------------------------------------------------------------------------
from google.adk.agents.llm_agent import LlmAgent

# 📚 ADK 服務：session、記憶體、檔案 artifact
from google.adk.sessions import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService

# 🏃 Runner 負責串接 agent、session、記憶體與檔案，形成完整系統
from google.adk.runners import Runner

# 🧾 Gemini 相容型別，用於格式化輸入/輸出訊息
from google.genai import types

from .tools import read_excel

# 🔐 載入環境變數（如 API 金鑰）
from dotenv import load_dotenv
load_dotenv()  # 將 GOOGLE_API_KEY 等變數載入系統
# 這樣可避免將敏感資料寫死在程式碼中。


# -----------------------------------------------------------------------------
# 🕒 ExcelWhisperAgent：你的 Excel 解析專家代理
# -----------------------------------------------------------------------------

class ExcelWhisperAgent:
    """
    ExcelWhisperAgent：接收 Excel 檔案路徑，讀取並解析內容，回傳摘要。
    支援 .xlsx/.xls 檔案，回傳前幾行資料與欄位資訊。
    """
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        """
        👷 初始化 ExcelWhisperAgent：
        - 建立 LLM 代理（由 Gemini 提供）
        - 設定 session 處理、記憶體與 runner 以執行任務
        """
        self._agent = self._build_agent()  # 設定 Gemini 代理
        self._user_id = "excel_whisper_agent_user"  # 固定 user ID，簡化 session

        # 🧠 Runner 實際管理 agent 與其執行環境
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),  # 處理檔案（本例未用）
            session_service=InMemorySessionService(),    # 管理對話 session
            memory_service=InMemoryMemoryService(),      # 可選：記憶過往訊息
        )

    def _build_agent(self) -> LlmAgent:
        """
        ⚙️ 建立並回傳一個基本設定的 Gemini 代理。

        回傳：
            LlmAgent: 來自 Google ADK 的代理物件
        """
        return LlmAgent(
            model="gemini-1.5-flash-latest",         # Gemini 模型版本
            name="excel_whisper_agent",                  # 代理名稱
            description="你是個Excel專家，可以幫助使用者處理Excel文件",    # metadata 描述
            instruction="""
                1. 你是一個Excel專家，可以幫助使用者處理Excel文件。
                2. 你可以讀取Excel檔案名稱，並且讀取Excel檔案的內容。
                3. 你可以讀取工作表名稱。
                4. 如果沒有提供路徑檔名，則使用環境變數FILE_PATH的值為路徑。
                5. 如果沒有提供工作表名稱，則讀取"工作表1"。
            """,
            tools=[
                read_excel,
            ],
        )

    async def invoke(self, file_path: str, session_id: str) -> str:
        """
        代理主要入口：
        參數：
            file_path (str): Excel 檔案路徑（如 "data/test.xlsx"）
            session_id (str): 用於分組訊息的 session 識別碼
        回傳：
            str: 代理回覆內容
        """
        # 🔁 嘗試重用現有 session，若無則新建
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
                state={}  # 可選：session 狀態字典
            )

        # 📨 將使用者訊息格式化為 Gemini 模型期望的格式
        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=file_path)]
        )

        # 🚀 執行代理，收集最後一個事件
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

    async def stream(self, query: str, session_id: str):
        """
        🌀 範例：模擬「串流」代理，回傳單一回覆。
        這裡僅示範串流機制。

        產生：
            dict: 回應 payload，表示任務完成並給出時間
        """
        yield {
            "is_task_complete": True,
            "content": "模擬「串流」代理"
        }