# orchestration-agent

## 專案簡介

`orchestration-agent` 是一個基於 Google A2A 協議的多代理協作平台，支援自動發現、註冊並協調多個智能代理。系統採用 **HostAgent** 作為主控代理，根據使用者意圖自動路由請求至最合適的子代理，並整合多代理的能力，提升任務處理的彈性與智能化。適用於需要多任務協同、智能分流、或跨領域 AI 能力整合的應用場景。

---

## 主要功能

- **智能任務路由**：HostAgent 使用 Google ADK 的 LLM 分析使用者意圖，自動委派任務給最適合的子代理
- **代理自動發現**：透過 `DiscoveryClient` 從註冊表自動載入所有可用代理，並查詢其能力描述（AgentCard）
- **多樣化子代理**：
  - `GreetingAgent`：根據當前時間生成個人化問候語
  - `TellTimeAgent`：提供當前時間資訊
  - `ExcelWhisperAgent`：使用 pandas 處理 Excel 檔案分析
- **標準化通訊協定**：所有代理均支援 Google A2A Protocol 和 JSON-RPC over HTTP
- **會話管理**：支援 InMemory session/memory/artifact 管理，便於開發和測試
- **MCP 整合**：支援 Model Context Protocol (MCP) 整合，可擴展至 taskmaster-ai 等工具

---

## 技術架構

### 核心組件
- **HostAgent**：主控代理，負責任務路由和協調
- **子代理群**：專門化的功能代理（Greeting、TellTime、ExcelWhisper）
- **DiscoveryClient**：代理發現和註冊管理
- **AgentConnector**：代理間通訊的封裝層
- **A2AStarletteApplication**：基於 Starlette 的 A2A 伺服器

### 資料模型
- **AgentCard**：代理能力描述和中繼資料
- **Task**：任務執行單位，包含狀態和歷史
- **Message**：任務中的訊息，支援多種內容類型
- **AgentSkill & AgentCapabilities**：代理技能和能力定義

### 技術棧
- **Python 3.13+**：主要開發語言
- **Google ADK**：Google Agent Development Kit，提供 LLM 代理能力
- **A2A SDK**：Google Agent-to-Agent 通訊協定實作
- **Starlette/FastAPI**：非同步 Web 框架
- **Pydantic**：資料驗證和序列化
- **httpx**：非同步 HTTP 客戶端
- **pandas & openpyxl**：Excel 檔案處理

---

## 安裝與環境建置

### 1. 環境需求
- **Python 3.13+**
- **Google API Key**：用於 Google ADK 的 LLM 功能

### 2. 安裝依賴套件
使用 uv（推薦）或 pip 安裝：
```bash
# 使用 uv（推薦）
uv sync

# 或使用 pip
pip install -e .
```

### 3. 環境變數設定
建立 `.env` 檔案並設定必要的環境變數：
```bash
# Google API 金鑰（必要）
GOOGLE_API_KEY=your_google_api_key_here

# 可選：其他設定
LOG_LEVEL=INFO
```

---

## 啟動方式

### 1. 啟動 HostAgent（主控代理）

```bash
python3 -m agents.host_agent --host=localhost --port=10000
```

### 2. 啟動子代理

在不同的終端視窗中啟動各個子代理：

#### GreetingAgent（問候代理）
```bash
python3 -m agents.greeting_agent --host=localhost --port=10001
```

#### TellTimeAgent（時間代理）
```bash
python3 -m agents.tell_time_agent --host=localhost --port=10002
```

#### ExcelWhisperAgent（Excel 處理代理）
```bash
python3 -m agents.excel_whisper_agent --host=localhost --port=10003
```

### 3. 代理註冊

系統會自動從 `utilities/a2a/agent_registry.json` 讀取代理註冊資訊：
```json
{
  "agents": [
    {
      "name": "Greeting Agent",
      "description": "根據時間生成個人化問候語",
      "url": "http://localhost:10001"
    },
    {
      "name": "Tell Time Agent",
      "description": "提供當前時間資訊",
      "url": "http://localhost:10002"
    },
    {
      "name": "Excel Whisper Agent",
      "description": "處理和分析 Excel 檔案",
      "url": "http://localhost:10003"
    }
  ]
}
```

---

## 使用方式

### 1. 透過 CLI 工具（推薦）

使用內建的命令列工具與 HostAgent 互動：
```bash
python3 -m app.cmd.cmd --agent http://localhost:10000
```

CLI 工具功能：
- **智能路由**：輸入任何問題，HostAgent 會自動選擇合適的子代理處理
- **會話管理**：支援多輪對話，保持上下文
- **錯誤處理**：友善的錯誤訊息和連線狀態檢查

#### 使用範例：
```bash
# 啟動 CLI
python3 -m app.cmd.cmd --agent http://localhost:10000

# 範例互動
🤖 請輸入您的請求: 現在幾點？
🏠 HostAgent 回應: 現在是 2024年12月17日 下午2:30

🤖 請輸入您的請求: 早安
🏠 HostAgent 回應: 午安！希望您今天過得愉快！

🤖 請輸入您的請求: 分析這個 Excel 檔案 /path/to/data.xlsx
🏠 HostAgent 回應: [Excel 分析結果...]
```

### 2. 透過 Python A2A Client

直接使用 A2A SDK 進行程式化互動：
```python
import asyncio
from a2a.client import A2AClient
from a2a.types import SendMessageRequest, MessageSendParams
from uuid import uuid4

async def main():
    # 建立客戶端連接到 HostAgent
    client = A2AClient(url="http://localhost:10000")

    # 建構訊息
    request = SendMessageRequest(
        id=uuid4().hex,
        params=MessageSendParams(
            message={
                "role": "user",
                "parts": [{"kind": "text", "text": "現在幾點？"}],
                "messageId": uuid4().hex
            }
        )
    )

    # 發送請求並取得回應
    result = await client.send_message(request)
    print(f"回應: {result}")

# 執行
asyncio.run(main())
```

### 3. 直接 HTTP API 呼叫

所有代理都支援標準的 HTTP JSON-RPC API：
```bash
# 查詢代理資訊
curl http://localhost:10000/.well-known/agent.json

# 發送任務（JSON-RPC 格式）
curl -X POST http://localhost:10000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "sendMessage",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Hello"}],
        "messageId": "unique-id"
      }
    },
    "id": "request-id"
  }'
```

---

## 專案結構

```
orchestration-agent/
├── agents/                     # 代理實作
│   ├── host_agent/            # 主控代理（HostAgent）
│   ├── greeting_agent/        # 問候代理
│   ├── tell_time_agent/       # 時間代理
│   └── excel_whisper_agent/   # Excel 處理代理
├── app/
│   └── cmd/                   # CLI 工具
├── client/                    # A2A 客戶端實作
├── models/                    # 資料模型定義
│   ├── agent.py              # AgentCard, AgentSkill 等
│   ├── task.py               # Task, Message 等
│   └── json_rpc.py           # JSON-RPC 協議模型
├── server/                    # 伺服器相關（舊版，已整合至 agents）
├── utilities/                 # 工具模組
│   ├── a2a/                  # A2A 相關工具
│   │   ├── agent_discovery.py # 代理發現
│   │   ├── agent_connect.py   # 代理連接
│   │   └── agent_registry.json # 代理註冊表
│   └── mcp/                  # MCP 整合工具
├── .taskmaster/              # TaskMaster AI 整合
│   └── docs/prd.txt         # 產品需求文件
└── pyproject.toml           # 專案依賴和設定
```

---

## 開發指南

### 新增自訂代理

1. **建立代理目錄**：在 `agents/` 下建立新目錄
2. **實作代理邏輯**：參考現有代理的結構
   - `agent.py`：核心代理邏輯（使用 Google ADK）
   - `agent_executor.py`：A2A 執行器
   - `__main__.py`：啟動入口點
3. **註冊代理**：在 `utilities/a2a/agent_registry.json` 中新增代理資訊
4. **測試**：啟動代理並透過 HostAgent 測試

### 代理開發模式

所有代理都遵循統一的架構模式：
- **Google ADK 整合**：使用 `LlmAgent` 提供 AI 能力
- **A2A 協議支援**：透過 `A2AStarletteApplication` 提供標準 API
- **會話管理**：使用 `InMemorySessionService` 等服務
- **工具整合**：可透過 `FunctionTool` 擴展功能

### MCP 整合

專案支援 Model Context Protocol (MCP) 整合：
- **TaskMaster AI**：可整合 taskmaster-ai MCP 工具
- **Azure OpenAI**：支援 GPT-4o 等模型
- **擴展性**：可輕鬆整合其他 MCP 工具

---

## 故障排除

### 常見問題

1. **代理無法啟動**
   - 檢查 `GOOGLE_API_KEY` 環境變數是否設定
   - 確認 Python 版本為 3.13+
   - 檢查埠號是否被佔用

2. **HostAgent 找不到子代理**
   - 確認子代理已啟動並正在運行
   - 檢查 `agent_registry.json` 中的 URL 是否正確
   - 測試代理的 `/.well-known/agent.json` 端點

3. **CLI 工具連線失敗**
   - 確認 HostAgent 正在 `http://localhost:10000` 運行
   - 檢查防火牆設定
   - 查看代理日誌輸出

### 除錯技巧

- 使用 `--history` 參數查看完整對話歷史
- 檢查各代理的日誌輸出
- 使用 `curl` 測試 API 端點
- 查看 `.well-known/agent.json` 確認代理狀態

---

## 參考資源

- **Google ADK 文件**：Agent Development Kit 官方文件
- **A2A 協議規範**：Google Agent-to-Agent Protocol
- **專案 PRD**：`.taskmaster/docs/prd.txt`
- **範例程式碼**：各 `agents/` 目錄下的實作

---

## 授權與致謝

本專案基於以下開源技術構建：
- Google ADK & A2A Protocol
- Starlette/FastAPI Web 框架
- Pydantic 資料驗證
- pandas & openpyxl Excel 處理

如需更多協助或有任何問題，歡迎查看原始碼註解或提出 Issue！
