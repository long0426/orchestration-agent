# =============================================================================
# models/json_rpc.py
# =============================================================================
# 目的：
# 此檔案定義 JSON-RPC 2.0 訊息的基礎類別與結構。
#
# JSON-RPC 是一種輕量級的遠端程序呼叫（RPC）協議，採用 JSON 編碼。
# 這些模型用於標準化代理在 Agent2Agent (A2A) 網路中發送與接收請求、
# 結果與錯誤的方式。
#
# 包含內容：
# - JSONRPCMessage：所有訊息的基礎模型
# - JSONRPCRequest：代理間的呼叫請求
# - JSONRPCResponse：請求的回覆（可能是結果或錯誤）
# - JSONRPCError：錯誤回應的結構
# - InternalError：預設的標準內部錯誤
# =============================================================================

# -----------------------------------------------------------------------------
# 匯入
# -----------------------------------------------------------------------------

from typing import Any, Literal               # 用於彈性型別與固定值
from uuid import uuid4                       # 產生唯一請求 ID
from pydantic import BaseModel, Field        # 建立強健、驗證過的資料模型


# -----------------------------------------------------------------------------
# JSONRPCMessage（基底類別）
# -----------------------------------------------------------------------------
# 所有 JSON-RPC 訊息都共用這些欄位。
# 這是請求與回應的共同父類別。
class JSONRPCMessage(BaseModel):
    # 必須指定協議版本，"2.0" 是唯一有效值。
    jsonrpc: Literal["2.0"] = "2.0"

    # 訊息 ID 用於對應請求與回應。
    # 若未提供，則自動產生唯一 ID。
    id: int | str | None = Field(default_factory=lambda: uuid4().hex)


# -----------------------------------------------------------------------------
# JSONRPCRequest
# -----------------------------------------------------------------------------
# JSON-RPC 請求，用於呼叫其他代理的方法。
# 這是你發送以執行某個動作的資料結構。
class JSONRPCRequest(JSONRPCMessage):
    # 欲呼叫的方法名稱（如 "tasks/send"）
    method: str

    # 方法的可選輸入參數（若不需要可省略）
    params: dict[str, Any] | None = None


# -----------------------------------------------------------------------------
# JSONRPCError
# -----------------------------------------------------------------------------
# 這是 JSON-RPC 回應中的標準錯誤物件。
# 當方法呼叫因錯誤失敗時會用到。
class JSONRPCError(BaseModel):
    # 數字型錯誤碼。建議使用標準碼（如 -32603 代表內部錯誤）。
    code: int

    # 人類可讀的錯誤訊息
    message: str

    # 可選的額外資訊，如堆疊追蹤或除錯資訊
    data: Any | None = None


# -----------------------------------------------------------------------------
# JSONRPCResponse
# -----------------------------------------------------------------------------
# JSON-RPC 回應，內容可能是結果或錯誤。
# `result` 與 `error` 只能有一個不為 None。
class JSONRPCResponse(JSONRPCMessage):
    # 方法呼叫成功時的回傳結果
    result: Any | None = None

    # 方法失敗時的錯誤物件
    error: JSONRPCError | None = None


# -----------------------------------------------------------------------------
# InternalError（JSONRPCError 子類別）
# -----------------------------------------------------------------------------
# 當代理遇到未預期例外時的預設錯誤。
# 遵循 JSON-RPC 標準內部錯誤碼（-32603）。
class InternalError(JSONRPCError):
    # 固定的內部錯誤碼
    code: int = -32603

    # 預設的錯誤訊息
    message: str = "Internal error"

    # 可選的除錯細節（如 traceback 或上下文資訊）
    data: Any | None = None
