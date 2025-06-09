# utilities/discovery.py
# =============================================================================
# 🎯 目的：
# 這是一個共用的工具模組，用於發現 Agent-to-Agent (A2A) 伺服器。
# 它會讀取代理 base URL 的註冊表（來自 JSON 檔案），並從標準 discovery 端點
# 取得每個代理的中繼資料（AgentCard）。
# 這讓任何 client 或 agent 都能動態得知可用代理。
# =============================================================================

import os                            # os 提供與作業系統互動的功能，如檔案路徑
import json                          # json 用於編碼與解碼 JSON 資料
import logging                       # logging 用於記錄警告/錯誤/資訊訊息
from typing import List             # List 是回傳列表時的型別提示

import httpx                         # httpx 是非同步 HTTP client，用於發送請求
from models.agent import AgentCard   # AgentCard 是 Pydantic 模型，代表代理的中繼資料

# 建立此模組專用的 logger；__name__ 代表模組名稱
logger = logging.getLogger(__name__)


class DiscoveryClient:
    """
    🔍 透過讀取 URL 註冊表檔案，並查詢每個 /.well-known/agent.json 端點，
    來發現 A2A 代理並取得 AgentCard。

    屬性：
        registry_file (str): 註冊 JSON 檔案的路徑（內容為 base URL 字串列表）。
        base_urls (List[str]): 載入的代理 base URL 列表。
    """

    def __init__(self, registry_file: str = None):
        """
        初始化 DiscoveryClient。

        參數：
            registry_file (str, optional): 註冊 JSON 檔案路徑。若為 None，
                則預設為本 utilities 資料夾下的 'agent_registry.json'。
        """
        # 若有自訂路徑則用之，否則組出預設路徑
        if registry_file:
            self.registry_file = registry_file
        else:
            # __file__ 是本模組檔案路徑；dirname 取其資料夾
            # join 組出與本腳本同層的 'agent_registry.json'
            self.registry_file = os.path.join(
                os.path.dirname(__file__),
                "agent_registry.json"
            )

        # 立即將註冊表檔案載入記憶體
        self.base_urls = self._load_registry()

    def _load_registry(self) -> List[str]:
        """
        載入並解析註冊 JSON 檔案，轉為 URL 列表。

        回傳：
            List[str]: 代理 base URL 列表，若錯誤則為空列表。
        """
        try:
            # 以讀取模式開啟 self.registry_file
            with open(self.registry_file, "r") as f:
                # 解析整個檔案為 JSON
                data = json.load(f)
            # 確保 JSON 是列表型態
            if not isinstance(data, list):
                raise ValueError("Registry file 必須是 URL 字串的 JSON 列表。")
            return data
        except FileNotFoundError:
            # 若檔案不存在，記錄警告並回傳空列表
            logger.warning(f"找不到 registry 檔案: {self.registry_file}")
            return []
        except (json.JSONDecodeError, ValueError) as e:
            # 若 JSON 格式錯誤或型別不符，記錄錯誤並回傳空列表
            logger.error(f"解析 registry 檔案錯誤: {e}")
            return []

    async def list_agent_cards(self) -> List[AgentCard]:
        """
        非同步地從每個註冊的 URL 取得 discovery 端點，
        並將回傳的 JSON 解析為 AgentCard 物件。

        回傳：
            List[AgentCard]: 成功取得的 agent card 列表。
        """
        cards: List[AgentCard] = []  # 準備一個空列表收集 AgentCard 實例

        # 建立新的 AsyncClient，並確保用完會關閉
        async with httpx.AsyncClient() as client:
            # 逐一處理註冊表中的每個 base URL
            for base in self.base_urls:
                # 正規化 URL（去除結尾斜線）並加 discovery 路徑
                url = base.rstrip("/") + "/.well-known/agent.json"
                try:
                    # 發送 GET 請求到 discovery 端點，設 5 秒 timeout
                    response = await client.get(url, timeout=5.0)
                    # 若回應狀態為 4xx/5xx 則拋出例外
                    response.raise_for_status()
                    # 將 JSON 回應轉為 AgentCard Pydantic 模型
                    card = AgentCard.model_validate(response.json())
                    # 加入有效的 AgentCard 到列表
                    cards.append(card)
                except Exception as e:
                    # 若有錯誤，記錄是哪個 URL 失敗及原因
                    logger.warning(f"發現代理失敗 {url}: {e}")
        # 回傳成功取得的 AgentCard 列表
        return cards
