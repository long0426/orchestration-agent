# =============================================================================
# agents/host_agent/entry.py
# =============================================================================
# 🎯 目的：
# 啟動 OrchestratorAgent 作為 A2A 伺服器。
# 使用共用的 registry 檔案來發現所有子代理，
# 然後透過 A2A JSON-RPC 將路由委派給 OrchestratorAgent。
# =============================================================================

import asyncio                              # 內建，用於執行非同步協程
import logging                              # 標準 Python 日誌模組
import click                                # 用於建立 CLI 介面的函式庫

# 用於從本地 registry 發現遠端 A2A 代理的工具
from utilities.discovery import DiscoveryClient
# 共用的 A2A 伺服器實作（Starlette + JSON-RPC）
from server.server import A2AServer
# Pydantic 模型，用於定義代理中繼資料（AgentCard 等）
from models.agent import AgentCard, AgentCapabilities, AgentSkill
# Orchestrator 實作及其任務管理器
from agents.host_agent.orchestrator import (
    OrchestratorAgent,
    OrchestratorTaskManager
)

# 設定 root logger，顯示 INFO 級別訊息
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--host", default="localhost",
    help="要綁定 OrchestratorAgent 伺服器的主機"
)
@click.option(
    "--port", default=10002,
    help="OrchestratorAgent 伺服器的埠號"
)
@click.option(
    "--registry",
    default=None,
    help=(
        "列出子代理 URL 的 JSON 檔案路徑。"
        "預設為 utilities/agent_registry.json"
    )
)
def main(host: str, port: int, registry: str):
    """
    啟動 OrchestratorAgent A2A 伺服器的進入點。

    執行步驟：
    1. 從 registry JSON 檔案載入子代理 URL。
    2. 透過 `/.well-known/agent.json` 取得每個代理的中繼資料。
    3. 以發現到的 AgentCard 實例化 OrchestratorAgent。
    4. 用 OrchestratorTaskManager 包裝，提供 JSON-RPC 處理。
    5. 啟動 A2AServer 監聽進來的任務。
    """
    # 1) 從 registry 檔案發現所有已註冊的子代理
    discovery = DiscoveryClient(registry_file=registry)
    # 啟動時同步執行非同步發現
    agent_cards = asyncio.run(discovery.list_agent_cards())

    # 若 registry 中找不到代理則警告
    if not agent_cards:
        logger.warning(
            "在 registry 中找不到任何代理——orchestrator 將無法委派任務"
        )

    # 2) 定義 OrchestratorAgent 自身的中繼資料，供發現用
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="orchestrate",                          # 技能唯一識別碼
        name="Orchestrate Tasks",                  # 人類可讀名稱
        description=(
            "根據意圖（時間、問候等）將使用者請求路由到適當的子代理"
        ),
        tags=["routing", "orchestration"],       # 關鍵字，方便發現
        examples=[                                  # 使用者查詢範例
            "What is the time?",
            "Greet me",
            "Say hello based on time"
        ]
    )
    orchestrator_card = AgentCard(
        name="OrchestratorAgent",
        description="Delegates tasks to discovered child agents",
        url=f"http://{host}:{port}/",             # 公開端點
        version="1.0.0",
        defaultInputModes=["text"],                # 支援的輸入模式
        defaultOutputModes=["text"],               # 支援的輸出模式
        capabilities=capabilities,
        skills=[skill]
    )

    # 3) 實例化 OrchestratorAgent 及其 TaskManager
    orchestrator = OrchestratorAgent(agent_cards=agent_cards)
    task_manager = OrchestratorTaskManager(agent=orchestrator)

    # 4) 建立並啟動 A2A 伺服器
    server = A2AServer(
        host=host,
        port=port,
        agent_card=orchestrator_card,
        task_manager=task_manager
    )
    server.start()


if __name__ == "__main__":
    main()
