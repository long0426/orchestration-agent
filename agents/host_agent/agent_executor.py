# =============================================================================
# agents/host_agent/agent_executor.py
# =============================================================================
# 🎯 目的：
# 處理 A2A 請求並執行 HostAgent 邏輯。
# 遵循 greeting_agent 的結構模式。
# =============================================================================

import logging

# 本地匯入
from .agent import HostAgent

# A2A SDK 匯入 - 基礎類別和上下文
from a2a.server.agent_execution import AgentExecutor
from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue

# A2A SDK 匯入 - 事件和狀態類型
from a2a.types import (
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
)

# A2A SDK 匯入 - 工具函數
from a2a.utils import new_task, new_text_artifact

# 設定日誌
logger = logging.getLogger(__name__)


class HostAgentExecutor(AgentExecutor):
    """
    🎯 HostAgent 的執行器，處理 A2A 請求並管理任務生命週期。
    繼承自 AgentExecutor 以提供 A2A SDK 標準功能。
    """

    def __init__(self):
        """初始化執行器"""
        self.agent = HostAgent()
        logger.info("HostAgentExecutor initialized")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        執行 A2A 任務請求的主要方法。
        
        Args:
            context: 請求上下文，包含用戶輸入和任務資訊
            event_queue: 事件佇列，用於發送回應事件
        """
        
        query = context.get_user_input()  # 提取用戶輸入
        task = context.current_task      # 取得當前任務
        
        print(f"🏠 HostAgentExecutor: Received request")
        print(f"🏠 HostAgentExecutor: Query: '{query}'")
        print(f"🏠 HostAgentExecutor: Context message: {context.message}")
        print(f"🏠 HostAgentExecutor: Current task: {task}")
        
        if not context.message:
            raise Exception('No message provided')
        
        if not task:
            task = new_task(context.message)
            print(f"🏠 HostAgentExecutor: Created new task: {task}")
            await event_queue.enqueue_event(task)
        
        # 使用 agent 處理查詢
        print(f"🏠 HostAgentExecutor: Starting to process query with task.contextId: {task.contextId}")
        async for event in self.agent.stream(query, task.contextId):
            print(f"🏠 HostAgentExecutor: Generated event: {event}")
            
            if event['is_task_complete']:
                print(f"🏠 HostAgentExecutor: Task completed with content: '{event['content']}'")
                
                # 建立結果 artifact
                artifact = new_text_artifact(
                    name='current_result',
                    description='Result of request to HostAgent.',
                    text=event['content'],
                )
                print(f"🏠 HostAgentExecutor: Created artifact: {artifact}")
                
                # 發送 artifact 更新事件
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        taskId=task.id,
                        contextId=task.contextId,
                        artifact=artifact,
                        append=False,
                        lastChunk=True,
                    )
                )
                
                # 發送任務完成狀態
                status_event = TaskStatusUpdateEvent(
                    taskId=task.id,
                    contextId=task.contextId,
                    status=TaskStatus(state=TaskState.completed),
                    final=True,
                )
                print(f"🏠 HostAgentExecutor: Sending completion status: {status_event}")
                await event_queue.enqueue_event(status_event)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """取消任務的方法（目前不支援）"""
        raise Exception('Cancel not supported')
