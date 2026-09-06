# app/models/database/base_db.py
# 数据库管理：线程安全单例，内嵌建表（不依赖外部 resources/sql）
import sqlite3
import threading
import os
import sys

try:
    from main import get_resource_path
except ImportError:
    def get_resource_path(relative_path):
        try:
            if hasattr(sys, '_MEIPASS'):
                base_path = sys._MEIPASS  # type: ignore
            else:
                base_path = os.path.abspath(os.path.dirname(os.path.dirname(
                    os.path.dirname(os.path.dirname(__file__)))))
        except Exception:
            base_path = os.path.abspath(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(__file__)))))
        return os.path.join(base_path, relative_path)


# ============================================================================
# 内嵌建表脚本（改造后：力学分析记录 + 用户/计费）
# ============================================================================
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE,
    name TEXT,
    email TEXT,
    balance REAL DEFAULT 0.0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_pricing (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT UNIQUE,
    price_per_call REAL DEFAULT 0.0,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    token TEXT,
    model_name TEXT,
    endpoint TEXT,
    image_count INTEGER DEFAULT 1,
    cost REAL DEFAULT 0.0,
    status TEXT,
    inference_result_id INTEGER,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recharge_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    balance_before REAL,
    balance_after REAL,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 力学分析记录
CREATE TABLE IF NOT EXISTS analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_type TEXT,
    component_name TEXT,
    section_info TEXT,
    steel TEXT,
    params_json TEXT,
    ratios_json TEXT,
    control_ratio REAL,
    verdict TEXT,
    optimize_json TEXT,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analysis_time ON analysis_results(timestamp);
"""


class BaseDB:
    """
    数据库管理抽象基类，单例模式保证线程安全。
    """
    _db_instance = None
    _lock = threading.Lock()

    def __init__(self):
        if not hasattr(self, 'conn'):
            with BaseDB._lock:
                if BaseDB._db_instance is None:
                    BaseDB._db_instance = self._create_db_connection()
                self.conn, self.lock = BaseDB._db_instance

    def _create_db_connection(self):
        user_home = os.path.expanduser("~")
        app_data_dir = os.path.join(user_home, "SteelDefect", "data")
        os.makedirs(app_data_dir, exist_ok=True)

        db_path = os.path.join(app_data_dir, 'database.db')
        print(f"[INFO] 数据库路径: {db_path}")

        conn = sqlite3.connect(db_path, check_same_thread=False)
        lock = threading.Lock()
        self._create_tables(conn)
        return conn, lock

    def _create_tables(self, conn):
        cursor = conn.cursor()
        cursor.executescript(_SCHEMA)
        conn.commit()
