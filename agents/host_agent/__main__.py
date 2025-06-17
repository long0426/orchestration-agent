# =============================================================================
# agents/host_agent/__main__.py
# =============================================================================
# 🎯 目的：
# 啟動 HostAgent 作為 A2A 伺服器。
# 使用 Google ADK 和 A2A SDK。
# =============================================================================

import os
import sys
import logging
import click
import httpx
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# A2A SDK 匯入
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

# HostAgent 相關匯入
from agents.host_agent.agent_executor import HostAgentExecutor
from agents.host_agent.agent import HostAgent

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--host", default="localhost",
    help="要綁定 HostAgent 伺服器的主機"
)
@click.option(
    "--port", default=10000,
    help="HostAgent 伺服器的埠號"
)
def main(host: str, port: int):
    """
    啟動 HostAgent A2A 伺服器的進入點。
    
    執行步驟：
    1. 定義 HostAgent 的中繼資料
    2. 實例化 HostAgentExecutor
    3. 建立並啟動 A2A 伺服器
    """
    
    # 1) 定義 HostAgent 自身的中繼資料
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="orchestrate",
        name="OrchestrateAgent",
        description=(
            "根據意圖將使用者請求路由到適當的子代理，"
            "支援時間查詢、問候語生成、Excel檔案分析等功能"
        ),
        tags=["routing", "orchestration", "delegation", "excel", "time", "greeting"],
        examples=[
            "What is the time?",
            "Greet me",
            "Say hello based on time",
            "Tell me the current time",
            "Generate a greeting",
            "讀取我的Excel檔案",
            "分析這個試算表",
            "給我Excel檔案的內容摘要",
            "read /path/to/file.xlsx"
        ]
    )
    
    agent_card = AgentCard(
        name="Host Agent",
        description="Orchestrates tasks by delegating to specialized child agents",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=HostAgent.SUPPORTED_CONTENT_TYPES,
        defaultOutputModes=HostAgent.SUPPORTED_CONTENT_TYPES,
        capabilities=capabilities,
        skills=[skill]
    )
    
    # 2) 檢查必要的環境變數
    if not os.getenv('GOOGLE_API_KEY'):
        print("GOOGLE_API_KEY environment variable not set.")
        sys.exit(1)

    # 3) 建立 HTTP 客戶端
    client = httpx.AsyncClient()

    # 4) 友善的啟動訊息
    print(f"\n🚀 Starting HostAgent on http://{host}:{port}/\n")

    # 5) 設定請求處理器
    handler = DefaultRequestHandler(
        agent_executor=HostAgentExecutor(),
        task_store=InMemoryTaskStore(),
        push_notifier=InMemoryPushNotifier(client),
    )

    # 6) 設定 A2A 伺服器應用程式
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=handler,
    )

    # 7) 啟動伺服器
    import uvicorn
    uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
    main()
