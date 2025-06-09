# =============================================================================
# server.py
# =============================================================================
# 📌 目的：
# 此檔案定義了一個非常簡單的 A2A（代理對代理）伺服器。
# 支援：
# - 通過 POST（"/"）接收任務請求
# - 讓客戶端通過 GET（"/.well-known/agent.json"）發現代理的詳細資訊
# 注意：本版本不支援串流或推播通知。
# =============================================================================


# -----------------------------------------------------------------------------
# 🧱 必要匯入
# -----------------------------------------------------------------------------

# 🌐 FastAPI 是 Starlette 的超集，支援自動產生 Swagger UI
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# 📦 匯入自訂的模型與邏輯
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.agent import AgentCard                      # 描述代理的身份與技能
from models.request import A2ARequest, SendTaskRequest  # 任務請求的模型
from models.json_rpc import JSONRPCResponse, InternalError  # JSON-RPC 工具，用於結構化訊息
from . import task_manager              # 實際的任務處理邏輯（Gemini agent）

# 🛠️ 一般工具
import json                                              # 用於列印請求內容（除錯用）
import logging                                           # 用於記錄錯誤與資訊訊息
logger = logging.getLogger(__name__)                     # 設定本檔案的 logger

# 🕒 匯入 datetime 以便序列化
from datetime import datetime

# 📦 編碼器，協助將 datetime 等複雜資料轉為 JSON
from fastapi.encoders import jsonable_encoder


# -----------------------------------------------------------------------------
# 🔧 datetime 序列化器
# -----------------------------------------------------------------------------
def json_serializer(obj):
    """
    此函式可將 Python 的 datetime 物件轉為 ISO 字串。
    若遇到無法處理的型別會拋出錯誤。
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


# -----------------------------------------------------------------------------
# 🚀 A2AServer 類別：核心伺服器邏輯
# -----------------------------------------------------------------------------
class A2AServer:
    def __init__(self, host="0.0.0.0", port=5000, agent_card: AgentCard = None, task_manager=None):
        """
        🔧 A2AServer 建構子

        參數：
            host: 綁定伺服器的 IP 位址（預設為所有介面）
            port: 監聽的埠號（預設為 5000）
            agent_card: 描述代理的中繼資料（名稱、技能、能力）
            task_manager: 處理任務的邏輯（這裡用 Gemini agent）
        """
        self.host = host
        self.port = port
        self.agent_card = agent_card
        self.task_manager = task_manager

        # 🌐 FastAPI app 初始化
        self.app = FastAPI()

        # 用 decorator 註冊 handler
        self._register_routes()

    def _register_routes(self):
        app = self.app
        server = self  # 為了在 handler 裡存取 self

        @app.post("/")
        async def handle_request(request: Request):
            """
            處理發送到根路徑（"/"）的任務請求。
            - 解析進來的 JSON
            - 驗證 JSON-RPC 訊息
            - 對於支援的任務型別，交由 task manager 處理
            - 回傳結果或錯誤
            """
            try:
                body = await request.json()
                print("\n🔍 收到的 JSON:", json.dumps(body, indent=2))
                json_rpc = A2ARequest.validate_python(body)
                if isinstance(json_rpc, SendTaskRequest):
                    result = await server.task_manager.on_send_task(json_rpc)
                else:
                    raise ValueError(f"不支援的 A2A 方法: {type(json_rpc)}")
                return server._create_response(result)
            except Exception as e:
                logger.error(f"例外狀況: {e}")
                return JSONResponse(
                    JSONRPCResponse(id=None, error=InternalError(message=str(e))).model_dump(),
                    status_code=400
                )

        @app.get("/.well-known/agent.json")
        async def get_agent_card():
            """
            代理發現端點（GET /.well-known/agent.json）
            回傳：代理中繼資料（字典格式）
            """
            return JSONResponse(server.agent_card.model_dump(exclude_none=True))

    # -----------------------------------------------------------------------------
    # 🧾 _create_response(): 將結果物件轉為 JSONResponse
    # -----------------------------------------------------------------------------
    def _create_response(self, result):
        """
        將 JSONRPCResponse 物件轉為 JSON HTTP 回應。

        參數：
            result: 回應物件（必須為 JSONRPCResponse）

        回傳：
            JSONResponse: Starlette 相容的 HTTP 回應，內容為 JSON
        """
        if isinstance(result, JSONRPCResponse):
            return JSONResponse(content=jsonable_encoder(result.model_dump(exclude_none=True)))
        else:
            raise ValueError("回應型別無效")

    # -----------------------------------------------------------------------------
    # ▶️ start(): 使用 uvicorn 啟動網頁伺服器
    # -----------------------------------------------------------------------------
    def start(self):
        """
        使用 uvicorn（ASGI 網頁伺服器）啟動 A2A 伺服器。
        此函式會阻塞並永久運行伺服器。
        """
        if not self.agent_card or not self.task_manager:
            raise ValueError("Agent card 和 task manager 為必填")
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)
