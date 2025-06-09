import pandas as pd
from pathlib import Path
import os


def read_excel(name: str, sheet_name: str) -> str:
    """讀取 Excel 文件內容並返回字符串形式的數據。

    Args:
        name: Excel 文件名
        sheet_name: 工作表名稱，如果為 None 則讀取所有工作表

    Returns:
        包含 Excel 內容的字符串，如果出錯則返回錯誤信息
    """
    print(f"(read_excel {name}, sheet={sheet_name})")
    try:
        file_path = name if name else os.getenv("FILE_PATH")
        if sheet_name is None:
            # 讀取所有工作表
            excel_file = pd.ExcelFile(file_path)
            result = []
            for sheet in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                result.append(f"\n工作表 '{sheet}':\n{df.to_string()}")
            return "\n".join(result)
        else:
            # 讀取指定工作表
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return df.to_string()
    except Exception as e:
        return f"讀取 Excel 文件時發生錯誤: {e}"