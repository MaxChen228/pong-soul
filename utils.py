# utils.py
import sys
import os

def resource_path(relative_path):
    """
    取得資源的絕對路徑，適用於開發環境和 PyInstaller 打包後的環境。
    """
    try:
        # PyInstaller 建立一個暫存資料夾並將路徑儲存在 _MEIPASS
        # sys._MEIPASS 在開發環境執行時不存在，會觸發 Except
        base_path = sys._MEIPASS
    except Exception:
        # 如果不是在 PyInstaller 打包的環境中執行，則使用普通的路徑
        # os.path.abspath(".") 會取得目前工作目錄 (通常是專案根目錄)
        base_path = os.path.abspath(".")

    # 將基礎路徑和相對路徑結合，形成絕對路徑
    return os.path.join(base_path, relative_path)