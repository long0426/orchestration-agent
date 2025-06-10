# orchestration-agent

## 專案簡介

`orchestration-agent` 是一個多代理協作平台，支援自動發現、註冊並協調多個 A2A（Agent-to-Agent）智能代理。其核心目標是根據使用者意圖，將請求自動路由至最合適的子代理，並整合多代理的能力，提升任務處理的彈性與智能化。適用於需要多任務協同、智能分流、或跨領域 AI 能力整合的應用場景。

---

## 主要功能

- **代理自動發現與註冊**：可從註冊表自動載入所有可用代理，並查詢其能力描述（AgentCard）。
- **任務路由與委派**：主 OrchestratorAgent 會根據使用者查詢內容，判斷意圖並將任務委派給最合適的子代理。
- **多種子代理**：
  - `GreetingAgent`：根據時間問候
  - `TellTimeAgent`：回報當前時間
  - `ExcelWhisperAgent`：用 pandas 處理 Excel 檔案
- **JSON-RPC 與 HTTP API**：所有代理均支援標準 JSON-RPC 通訊協定，便於擴充與整合。
- **記憶體與 session 管理**：支援 InMemory session/memory/artifact，方便 demo 與測試。

---

## 架構與技術

- **系統組件**：OrchestratorAgent（主控）、多個子代理、DiscoveryClient（代理發現）、A2AServer（API 伺服器）、TaskManager（任務管理）
- **資料模型**：AgentCard、Task、Message、Session（皆為 Pydantic 定義）
- **API 與整合**：所有代理均支援 JSON-RPC over HTTP，並有標準發現端點（/.well-known/agent.json）
- **A2A 協議**：Agent 之間溝通符合 Google A2A Protocol
- **基礎設施需求**：Python 3.13+，依賴 FastAPI、httpx、pydantic、google-adk、uvicorn、pandas、openpyxl 等

---

## 安裝與環境建置

1. **安裝 Python 3.13+**
2. **安裝依賴套件**
   ```bash
   pip install -r requirements.txt
   ```
   或根據 `pyproject.toml` 安裝 Poetry/uv 等管理工具

3. **設定環境變數**
   - 建議建立 `.env` 檔案，設定 Google API 金鑰等敏感資訊

---

## 啟動方式

### 啟動 OrchestratorAgent（主控代理）

```bash
python3 -m agents.host_agent.entry --host=localhost --port=10000 --registry=utilities/agent_registry.json
```

### 啟動子代理

#### GreetingAgent
```bash
python3 -m agents.greeting_agent --host=localhost --port=10001
```

#### TellTimeAgent
```bash
python3 -m agents.tell_time_agent --host=localhost --port=10002
```

#### ExcelWhisperAgent
```bash
python3 -m agents.excel_whisper_agent --host=localhost --port=10003
```

### 註冊子代理

編輯 `utilities/agent_registry.json`，加入各子代理的 URL，例如：
```json
[
    "http://localhost:10001",
    "http://localhost:10002",
    "http://localhost:10003"
]
```

---

## 如何互動

### 1. 透過 CLI 工具

以 TellTimeAgent 為例：
```bash
python3 app/cmd/cmd.py --agent http://localhost:10000
```
你可以直接輸入問題（如 "What time is it?"），或對 ExcelWhisperAgent 輸入 `read /path/to/file.xlsx`。

### 2. 透過 Python client

可參考 `client/client.py`，使用 `A2AClient` 發送任務：
```python
from client.client import A2AClient
import asyncio

async def main():
    client = A2AClient(url="http://localhost:10004")
    payload = {
        "id": "your-task-id",
        "sessionId": "your-session-id",
        "message": {
            "role": "user",
            "parts": [{"type": "text", "text": "read /path/to/file.xlsx"}]
        }
    }
    result = await client.send_task(payload)
    print(result)

asyncio.run(main())
```

---

## 進階說明

- **自訂/擴充代理**：可於 `agents/` 目錄下新增自訂代理，並於 registry 註冊即可自動被 OrchestratorAgent 發現與路由。
- **API/協議細節**：請參考 `models/`、`server/`、`client/` 目錄下的程式碼與註解。
- **PRD/架構說明**：詳見 `.taskmaster/docs/prd.txt`。

---

## 參考與致謝

- Google ADK、Google A2A 協議
- OpenAI 多代理協作架構
- pandas、openpyxl 等開源套件

---

如需更多協助，請參考各 agent 目錄下的原始碼與註解，或直接提問！
