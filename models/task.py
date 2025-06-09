# =============================================================================
# models/task.py
# =============================================================================
# 目的：
# 此模組定義 Agent2Agent 協議中**任務相關的模型**。
#
# 這些模型代表：
# - 任務的結構（`Task`）
# - 任務的狀態（`TaskStatus`, `TaskState`）
# - 任務過程中的訊息（`Message`, `TextPart`）
# - 發送、查詢、取消任務時所用的參數
# =============================================================================

# -----------------------------------------------------------------------------
# 匯入
# -----------------------------------------------------------------------------

from enum import Enum                          # 用於建立固定值常數（如任務狀態）
from uuid import uuid4                         # 產生唯一識別碼
from pydantic import BaseModel, Field          # Pydantic 用於結構化資料驗證
from typing import Any, Literal, List          # 型別提示，增加彈性與結構
from datetime import datetime                  # 儲存時間戳記


# -----------------------------------------------------------------------------
# 訊息片段：目前僅支援純文字
# -----------------------------------------------------------------------------

# 代表訊息的一個片段，目前僅允許純文字
class TextPart(BaseModel):
    type: Literal["text"] = "text"  # 固定值欄位，標示為 "text" 類型
    text: str                       # 實際的文字內容（如："現在幾點？"）

# 別名：目前 "Part" 等同於 TextPart（方便未來重構）
Part = TextPart


# -----------------------------------------------------------------------------
# Message：任務歷史中的一則訊息
# -----------------------------------------------------------------------------

# 任務中的一則訊息，可能來自使用者或代理
class Message(BaseModel):
    role: Literal["user", "agent"]  # 訊息發送者："user" 或 "agent"
    parts: List[Part]               # 一則訊息可包含多個片段（如多行文字）


# -----------------------------------------------------------------------------
# TaskStatus：描述任務在某一時刻的狀態
# -----------------------------------------------------------------------------

class TaskStatus(BaseModel):
    state: str  # 狀態字串，如 "submitted"、"working" 等（由 TaskState 定義）
    
    # 自動記錄狀態建立的時間
    timestamp: datetime = Field(default_factory=datetime.now)


# -----------------------------------------------------------------------------
# Task：Agent2Agent 協議中的核心任務單位
# -----------------------------------------------------------------------------

class Task(BaseModel):
    id: str                    # 任務的唯一識別碼（可由客戶端或代理產生）
    status: TaskStatus         # 任務目前的狀態
    history: List[Message]     # 任務的對話歷史（使用者說了什麼、代理如何回覆）


# -----------------------------------------------------------------------------
# API 請求參數模型
# -----------------------------------------------------------------------------

# 用於識別任務，例如取消或查詢時
class TaskIdParams(BaseModel):
    id: str                                # 任務 ID
    metadata: dict[str, Any] | None = None # 可選的額外中繼資料（如提交者）


# 擴充 TaskIdParams，加入可選的歷史長度
# 查詢任務時可控制回傳多少歷史訊息
class TaskQueryParams(TaskIdParams):
    historyLength: int | None = None       # 限制回傳任務歷史訊息的數量


# 發送新任務給代理所需的參數
class TaskSendParams(BaseModel):
    id: str                                # 任務 ID（通常由客戶端產生）
    
    # 用於分組相關任務的會話 ID（若未提供則自動產生）
    sessionId: str = Field(default_factory=lambda: uuid4().hex)

    message: Message                       # 啟動任務的訊息
    historyLength: int | None = None       # 可選的歷史長度
    metadata: dict[str, Any] | None = None # 可選的額外資訊（如使用者角色、優先權）


# -----------------------------------------------------------------------------
# TaskState：預設任務生命週期狀態的列舉
# -----------------------------------------------------------------------------

# Enum 提供受控的任務狀態字彙
class TaskState(str, Enum):
    SUBMITTED = "submitted"              # 任務已收到
    WORKING = "working"                  # 任務進行中
    INPUT_REQUIRED = "input-required"    # 代理等待更多輸入
    COMPLETED = "completed"             # 任務已完成
    CANCELED = "canceled"               # 任務被使用者或系統取消
    FAILED = "failed"                   # 發生錯誤
    UNKNOWN = "unknown"                 # 未定義或無法識別的狀態