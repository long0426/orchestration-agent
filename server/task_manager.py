# =============================================================================
# server/task_manager.py
# =============================================================================
# 🎯 目的：
# 此檔案定義了在 Agent-to-Agent (A2A) 協議下如何管理任務。
#
# ✅ 包含：
# - 一個基礎抽象類別 `TaskManager`，規範必須實作的方法
# - 一個簡單的 `InMemoryTaskManager`，將任務暫存在記憶體中
#
# ❌ 不包含：
# - 取消任務功能
# - 推播通知或即時更新
# - 永久性儲存（如資料庫）
# =============================================================================


# -----------------------------------------------------------------------------
# 📚 標準 Python 匯入
# -----------------------------------------------------------------------------

from abc import ABC, abstractmethod        # 讓我們可以定義抽象基底類別（像介面）
from typing import Dict                    # Dict 是用來存放鍵值對的字典型別
import asyncio                             # 這裡用於鎖定，安全處理非同步操作


# -----------------------------------------------------------------------------
# 📦 專案匯入：請求與任務模型
# -----------------------------------------------------------------------------

from models.request import (
    SendTaskRequest, SendTaskResponse,    # 用於發送任務給代理
    GetTaskRequest, GetTaskResponse       # 用於查詢代理的任務資訊
)

from models.task import (
    Task, TaskSendParams, TaskQueryParams,  # 任務與輸入模型
    TaskStatus, TaskState, Message          # 任務狀態與歷史訊息物件
)


# -----------------------------------------------------------------------------
# 🧩 TaskManager（抽象基底類別）
# -----------------------------------------------------------------------------

class TaskManager(ABC):
    """
    🔧 這是一個基礎介面類別。

    所有 Task Manager 都必須實作這兩個 async 方法：
    - on_send_task()：接收並處理新任務
    - on_get_task()：查詢任務狀態或對話歷史

    這確保所有實作都遵循一致的結構。
    """

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """📥 此方法將處理新進來的任務。"""
        pass

    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """📤 此方法將根據任務 ID 回傳任務細節。"""
        pass


# -----------------------------------------------------------------------------
# 🧠 InMemoryTaskManager
# -----------------------------------------------------------------------------

class InMemoryTaskManager(TaskManager):
    """
    🧠 一個簡單、暫時的任務管理器，所有資料都存在記憶體（RAM）中。

    適合：
    - 展示、Demo
    - 本地開發
    - 單一會話互動

    ❗ 不適合正式環境：應用程式停止或重啟時資料會遺失。
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}   # 🗃️ 字典，key=任務ID，value=Task物件
        self.lock = asyncio.Lock()         # 🔐 非同步鎖，確保同時只有一個請求能修改資料

    # -------------------------------------------------------------------------
    # 💾 upsert_task: 在記憶體中建立或更新任務
    # -------------------------------------------------------------------------
    async def upsert_task(self, params: TaskSendParams) -> Task:
        """
        若任務不存在則建立新任務，若已存在則更新歷史紀錄。

        參數：
            params: TaskSendParams – 包含任務ID、會話ID與訊息

        回傳：
            Task – 新建立或已更新的任務
        """
        async with self.lock:
            task = self.tasks.get(params.id)  # 嘗試找出是否已有此ID的任務

            if task is None:
                # 若任務不存在，建立一個狀態為 "submitted" 的新任務
                task = Task(
                    id=params.id,
                    status=TaskStatus(state=TaskState.SUBMITTED),
                    history=[params.message]
                )
                self.tasks[params.id] = task
            else:
                # 若任務已存在，將新訊息加入歷史紀錄
                task.history.append(params.message)

            return task

    # -------------------------------------------------------------------------
    # 🚫 on_send_task: 必須由子類別實作
    # -------------------------------------------------------------------------
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """
        此方法在這裡故意不實作。
        像 `AgentTaskManager` 這樣的子類別應該要覆寫它。

        例外：
            NotImplementedError：如果直接呼叫會拋出此錯誤
        """
        raise NotImplementedError("on_send_task() 必須由子類別實作")

    # -------------------------------------------------------------------------
    # 📥 on_get_task: 依任務ID查詢任務
    # -------------------------------------------------------------------------
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        """
        依據任務ID查詢任務，並可選擇只回傳最近的訊息。

        參數：
            request: 一個帶有ID與可選歷史長度的 GetTaskRequest

        回傳：
            GetTaskResponse – 若找到則包含任務，否則回傳錯誤訊息
        """
        async with self.lock:
            query: TaskQueryParams = request.params
            task = self.tasks.get(query.id)

            if not task:
                # 若找不到任務，回傳結構化錯誤
                return GetTaskResponse(id=request.id, error={"message": "找不到任務"})

            # 可選：只顯示最近 N 筆訊息
            task_copy = task.model_copy()  # 複製一份，避免影響原始資料
            if query.historyLength is not None:
                task_copy.history = task_copy.history[-query.historyLength:]  # 取最後 N 筆訊息
            else:
                task_copy.history = task_copy.history

            return GetTaskResponse(id=request.id, result=task_copy)
