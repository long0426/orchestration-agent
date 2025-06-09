# =============================================================================
# models/request.py
# =============================================================================
# 目的：
# 此模組定義 A2A（Agent2Agent）協議中使用的結構化請求模型。
#
# 這些模型代表代理可能發送或接收的各種請求，
# 例如發送任務或查詢任務。每個請求都遵循 JSON-RPC 2.0 格式。
#
# 也包含一個稱為 `A2ARequest` 的判別聯集（discriminated union），
# 可根據 `method` 欄位自動識別與解析請求型別。
#
# 包含模型：
# - SendTaskRequest
# - GetTaskRequest
# - A2ARequest（判別聯集）
# - SendTaskResponse
# - GetTaskResponse
#
# 注意：CancelTaskRequest 若未來支援取消功能會再加入。
# =============================================================================

# -----------------------------------------------------------------------------
# 匯入
# -----------------------------------------------------------------------------

from typing import Annotated, Union, Literal       # 型別註解與判別聯集用
from pydantic import Field                         # Pydantic 欄位設定
from pydantic.type_adapter import TypeAdapter      # 執行時判別聯集解析

# JSON-RPC 請求與回應的基礎模型
from models.json_rpc import JSONRPCRequest, JSONRPCResponse

# 任務相關的參數與回傳模型
from models.task import Task, TaskSendParams
from models.task import TaskQueryParams


# -----------------------------------------------------------------------------
# SendTaskRequest：用於發送新任務給代理
# -----------------------------------------------------------------------------

class SendTaskRequest(JSONRPCRequest):
    method: Literal["tasks/send"] = "tasks/send"    # 必須為指定方法字串
    params: TaskSendParams                          # 任務建立參數


# -----------------------------------------------------------------------------
# GetTaskRequest：用於查詢任務狀態或歷史
# -----------------------------------------------------------------------------

class GetTaskRequest(JSONRPCRequest):
    method: Literal["tasks/get"] = "tasks/get"      # 必須為指定方法字串
    params: TaskQueryParams                         # 任務 ID 與可選歷史長度


# -----------------------------------------------------------------------------
# A2ARequest：支援的請求型別判別聯集
# -----------------------------------------------------------------------------
# 允許根據 `method` 欄位自動解析請求型別。

A2ARequest = TypeAdapter(
    Annotated[
        Union[
            SendTaskRequest,
            GetTaskRequest,
            # CancelTaskRequest 若未來支援可加入
        ],
        Field(discriminator="method")
    ]
)


# -----------------------------------------------------------------------------
# SendTaskResponse："tasks/send" 請求的回應模型
# -----------------------------------------------------------------------------

class SendTaskResponse(JSONRPCResponse):
    result: Task | None = None                      # 代理回傳的任務


# -----------------------------------------------------------------------------
# GetTaskResponse："tasks/get" 請求的回應模型
# -----------------------------------------------------------------------------

class GetTaskResponse(JSONRPCResponse):
    result: Task | None = None                      # 查詢到的任務，若無則為 None
