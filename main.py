# -*- coding: utf-8 -*-
"""
预制舱钢结构力学分析 —— 应用入口
用法:
  python main.py                 # 启动桌面 GUI
  python main.py --api           # 同时后台启动 FastAPI(6006)
"""
import os
import sys

# 工程根入 path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def get_resource_path(relative_path):
    """资源绝对路径（兼容 PyInstaller）。"""
    try:
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS  # type: ignore
        else:
            base_path = _ROOT
    except Exception:
        base_path = _ROOT
    return os.path.join(base_path, relative_path)


def run_api_server():
    """后台起 FastAPI 服务（可选）。"""
    import uvicorn
    from api.fastapi_app import app
    config = uvicorn.Config(app, host="0.0.0.0", port=6006, log_level="warning")
    uvicorn.Server(config).run()


def main():
    import threading
    if "--api" in sys.argv:
        t = threading.Thread(target=run_api_server, daemon=True)
        t.start()

    from PyQt6.QtWidgets import QApplication
    from qfluentwidgets import FluentIcon
    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
