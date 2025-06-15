# =============================================================================
# agents/host_agent/agent_connect.py
# =============================================================================
# 🎯 目的：
# 提供一個簡單的包裝器（`AgentConnector`），用於透過 A2AClient 向任何以 base URL 識別的遠端代理發送任務。
# 這讓 Orchestrator 不需關心底層 HTTP 細節與 HTTP client 設定。
# =============================================================================

import uuid                           # 標準函式庫，用於產生唯一 ID
import logging                        # 標準函式庫，用於彈性日誌紀錄

# 匯入自訂的 A2AClient，負責處理 JSON-RPC 任務請求
from client.client_bat import A2AClient
# 匯入 Task 模型，用於表示完整的任務回應
from models.task import Task

# 建立此模組專用的 logger
logger = logging.getLogger(__name__)


class AgentConnector:
    """
    🔗 連接到遠端 A2A 代理，並提供統一的方法來委派任務。

    屬性：
        name (str): 遠端代理的人類可讀識別名稱。
        client (A2AClient): 指向代理 URL 的 HTTP client。
    """

    def __init__(self, name: str, base_url: str):
        """
        初始化特定遠端代理的連接器。

        參數：
            name (str): 代理識別名稱（如 "TellTimeAgent"）。
            base_url (str): HTTP 端點（如 "http://localhost:10000"）。
        """
        # 儲存代理名稱，方便日誌與參考
        self.name = name
        # 建立綁定到代理 base URL 的 A2AClient
        self.client = A2AClient(url=base_url)
        # 記錄連接器已就緒
        logger.info(f"AgentConnector: initialized for {self.name} at {base_url}")

    async def send_task(self, message: str, session_id: str) -> Task:
        """
        向遠端代理發送文字任務，並回傳完整的 Task。

        參數：
            message (str): 想讓代理執行的內容（如："現在幾點？"）。
            session_id (str): 用於分組相關呼叫的會話識別碼。

        回傳：
            Task: 遠端代理回傳的完整 Task 物件（含歷史紀錄）。
        """
        # 產生唯一的任務 ID（使用 uuid4 的 hex）
        task_id = uuid.uuid4().hex
        # 建立符合 TaskSendParams 結構的 JSON-RPC 載荷
        payload = {
            "id": task_id,
            "sessionId": session_id,
            "message": {
                "role": "user",                # 表示這則訊息來自使用者
                "parts": [                       # 將文字包裝成 parts 列表
                    {"type": "text", "text": message}
                ]
            }
        }

        # 使用 A2AClient 非同步發送任務並等待回應
        task_result = await self.client.send_task(payload)
        # 記錄收到回應，方便除錯/追蹤
        logger.info(f"AgentConnector: received response from {self.name} for task {task_id}")
        # 回傳 Task Pydantic 模型，供 orchestrator 後續處理
        return task_result
