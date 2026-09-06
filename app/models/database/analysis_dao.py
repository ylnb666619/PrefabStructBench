# -*- coding: utf-8 -*-
"""
analysis_dao —— 力学分析记录数据访问（analysis_results 表）
供 GUI / API / 仪表盘统一读写。
"""
import json
import datetime

from app.models.database.base_db import BaseDB


class AnalysisDAO:
    def __init__(self):
        self.db = BaseDB()

    # ---- 写入 ----
    def add_analysis(self, component_type, component_name, section_info, steel,
                     params_dict=None, ratios_dict=None, control_ratio=None,
                     verdict=None, optimize_dict=None):
        """插入一条分析记录，返回自增 id。"""
        sql = ("INSERT INTO analysis_results "
               "(component_type, component_name, section_info, steel, "
               "params_json, ratios_json, control_ratio, verdict, optimize_json) "
               "VALUES (?,?,?,?,?,?,?,?,?)")
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute(sql, (
                str(component_type), str(component_name), str(section_info),
                str(steel),
                json.dumps(params_dict or {}, ensure_ascii=False),
                json.dumps(ratios_dict or {}, ensure_ascii=False),
                float(control_ratio) if control_ratio is not None else None,
                str(verdict or ""),
                json.dumps(optimize_dict or {}, ensure_ascii=False),
            ))
            self.db.conn.commit()
            return cur.lastrowid

    # ---- 查询 ----
    @staticmethod
    def _row_to_dict(row):
        return {
            "id": row[0],
            "component_type": row[1],
            "component_name": row[2],
            "section_info": row[3],
            "steel": row[4],
            "params": json.loads(row[5]) if row[5] else {},
            "ratios": json.loads(row[6]) if row[6] else {},
            "control_ratio": row[7],
            "verdict": row[8],
            "optimize": json.loads(row[9]) if row[9] else {},
            "timestamp": row[10],
        }

    def get_by_id(self, analysis_id):
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute("SELECT * FROM analysis_results WHERE id = ?", (analysis_id,))
            row = cur.fetchone()
            return self._row_to_dict(row) if row else None

    def fetch_all(self, page=1, page_size=10, component_type=None):
        """分页查询，按时间倒序。返回 (rows, total)。"""
        where = ""
        args = []
        if component_type:
            where = " WHERE component_type = ?"
            args.append(component_type)
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM analysis_results" + where, args)
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT * FROM analysis_results" + where +
                " ORDER BY id DESC LIMIT ? OFFSET ?",
                args + [page_size, (page - 1) * page_size],
            )
            rows = [self._row_to_dict(r) for r in cur.fetchall()]
            return rows, total

    def fetch_recent(self, limit=50):
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute("SELECT * FROM analysis_results ORDER BY id DESC LIMIT ?", (limit,))
            return [self._row_to_dict(r) for r in cur.fetchall()]

    def delete_by_id(self, analysis_id):
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute("DELETE FROM analysis_results WHERE id = ?", (analysis_id,))
            self.db.conn.commit()

    # ---- 仪表盘统计 ----
    def dashboard_stats(self, month=None):
        """返回仪表盘统计：总数/不合格/类型分布/近30日趋势。"""
        month = month or datetime.date.today().strftime("%Y-%m")
        stats = {"total": 0, "fail": 0, "by_type": {}, "trend": {}}
        with self.db.lock:
            cur = self.db.conn.cursor()
            cur.execute("SELECT COUNT(*) FROM analysis_results")
            stats["total"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM analysis_results WHERE verdict='不合格'")
            stats["fail"] = cur.fetchone()[0]
            cur.execute("SELECT component_type, COUNT(*) FROM analysis_results "
                        "GROUP BY component_type")
            stats["by_type"] = dict(cur.fetchall())
            # 近 30 日趋势（按天）
            cur.execute(
                "SELECT substr(timestamp,1,10) d, COUNT(*) FROM analysis_results "
                "GROUP BY d ORDER BY d DESC LIMIT 30")
            stats["trend"] = dict(reversed(cur.fetchall()))
        stats["month_total"] = 0
        return stats
