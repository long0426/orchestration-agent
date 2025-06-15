# =============================================================================
# client/client.py
# =============================================================================
# 目的：
# 此檔案定義了一個可重複使用、非同步的 Python client，用於與 Agent2Agent (A2A) 伺服器互動。
#
# 支援：
# - 發送任務並接收回應
# - 查詢任務狀態或歷史
# -（本簡化版不支援串流與取消功能）
# =============================================================================

# -----------------------------------------------------------------------------
# 匯入
# -----------------------------------------------------------------------------

import json
from uuid import uuid4                                 # 用於編碼/解碼 JSON 資料
import httpx                                # 非同步 HTTP client，用於發送網路請求
from httpx_sse import connect_sse           # httpx 的 SSE 擴充（目前未用）
from typing import Any                      # 型別提示，增加彈性

# 匯入支援的請求型別
from models.request import SendTaskRequest, GetTaskRequest  # 已移除 CancelTaskRequest

# JSON-RPC 2.0 的基礎請求格式
from models.json_rpc import JSONRPCRequest

# 任務結果與代理身份的模型
from models.task import Task, TaskSendParams
from models.agent import AgentCard


# -----------------------------------------------------------------------------
# 自訂錯誤類別
# -----------------------------------------------------------------------------

class A2AClientHTTPError(Exception):
    """當 HTTP 請求失敗（如伺服器回應異常）時拋出"""
    pass

class A2AClientJSONError(Exception):
    """當回應不是有效的 JSON 時拋出"""
    pass


# -----------------------------------------------------------------------------
# A2AClient：與 A2A 代理溝通的主要介面
# -----------------------------------------------------------------------------

class A2AClient:
    def __init__(self, agent_card: AgentCard = None, url: str = None):
        """
        使用 agent card 或直接 URL 初始化 client。
        兩者必須擇一提供。
        """
        if agent_card:
            self.url = agent_card.url
        elif url:
            self.url = url
        else:
            raise ValueError("必須提供 agent_card 或 url 其中之一")


    # -------------------------------------------------------------------------
    # send_task：發送新任務給代理
    # -------------------------------------------------------------------------
    async def send_task(self, payload: dict[str, Any]) -> Task:

        request = SendTaskRequest(
            id=uuid4().hex,
            params=TaskSendParams(**payload)  # ✅ 正確包裝成模型
        )

        print("\n📤 發送 JSON-RPC 請求：")
        print(json.dumps(request.model_dump(), indent=2))

        response = await self._send_request(request)
        return Task(**response["result"])  # ✅ 只取 'result' 欄位



    # -------------------------------------------------------------------------
    # get_task：查詢先前發送任務的狀態或歷史
    # -------------------------------------------------------------------------
    async def get_task(self, payload: dict[str, Any]) -> Task:
        request = GetTaskRequest(params=payload)
        response = await self._send_request(request)
        return Task(**response["result"])



    # -------------------------------------------------------------------------
    # _send_request：內部輔助函式，發送 JSON-RPC 請求
    # -------------------------------------------------------------------------
    async def _send_request(self, request: JSONRPCRequest) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.url,
                    json=request.model_dump(),  # 將 Pydantic 模型轉為 JSON
                    timeout=30
                )
                response.raise_for_status()     # 若狀態碼為 4xx/5xx 則拋出錯誤
                return response.json()          # 回傳解析後的 dict

            except httpx.HTTPStatusError as e:
                raise A2AClientHTTPError(e.response.status_code, str(e)) from e

            except json.JSONDecodeError as e:
                raise A2AClientJSONError(str(e)) from e
