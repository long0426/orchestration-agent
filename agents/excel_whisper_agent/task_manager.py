import logging
from server.task_manager import InMemoryTaskManager
from models.task import Message, TaskStatus, TaskState, TextPart
from models.request import SendTaskRequest, SendTaskResponse

logger = logging.getLogger(__name__)

class ExcelWhisperTaskManager(InMemoryTaskManager):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent

    def _get_user_text(self, request: SendTaskRequest) -> str:
        return request.params.message.parts[0].text

    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        logger.info(f"ExcelWhisperTaskManager received task {request.params.id}")
        # 1. 建立或更新 Task
        task = await self.upsert_task(request.params)
        # 2. 取得使用者輸入
        user_text = self._get_user_text(request)
        # 3. 呼叫 agent 處理
        response_text = await self.agent.invoke(user_text, request.params.sessionId)
        # 4. 包裝回覆
        reply = Message(role="agent", parts=[TextPart(text=response_text)])
        # 5. 更新狀態與歷史
        async with self.lock:
            task.status = TaskStatus(state=TaskState.COMPLETED)
            task.history.append(reply)
        # 6. 回傳結果
        return SendTaskResponse(id=request.id, result=task) 