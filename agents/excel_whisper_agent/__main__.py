import logging
import click
from server.server import A2AServer
from models.agent import AgentCard, AgentCapabilities, AgentSkill
from agents.excel_whisper_agent.agent import ExcelWhisperAgent
from agents.excel_whisper_agent.task_manager import ExcelWhisperTaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@click.command()
@click.option("--host", default="localhost", help="Host to bind ExcelWhisperAgent server to")
@click.option("--port", default=10003, help="Port for ExcelWhisperAgent server")
def main(host: str, port: int):
    capabilities = AgentCapabilities(streaming=False)
    skill = AgentSkill(
        id="excel_whisper",
        name="Excel Whisper",
        description="讀取並解析 Excel 檔案內容，回傳解析結果。",
        tags=["excel", "pandas", "spreadsheet"],
        examples=["read /path/to/file.xlsx"]
    )
    agent_card = AgentCard(
        name="ExcelWhisperAgent",
        description="Reads and summarizes Excel files using pandas.",
        url=f"http://{host}:{port}/",
        version="1.0.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill]
    )
    agent = ExcelWhisperAgent()
    task_manager = ExcelWhisperTaskManager(agent=agent)
    server = A2AServer(
        host=host,
        port=port,
        agent_card=agent_card,
        task_manager=task_manager
    )
    server.start()

if __name__ == "__main__":
    main() 