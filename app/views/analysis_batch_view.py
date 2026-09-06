# -*- coding: utf-8 -*-
"""
analysis_batch_view —— 页面「批量分析」：多工况批量验算 + 优化
每行一条工况 JSON，如：
  {"kind":"beam","Mx":15,"V":25,"grade":"22#"}
  {"kind":"column","N":60,"Mx":8,"My":3,"width":100,"thick":4,"height":2850}
  {"kind":"truss","N":1000,"l0":1820}
"""
import json
import os
import sys

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QTextEdit)
from qfluentwidgets import (PrimaryPushButton, PushButton, TitleLabel,
                            BodyLabel, ElevatedCardWidget, InfoBar)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from app.models.analysis_model import AnalysisModel
from app.models.event_bus import EventBus

KIND_CN = {"beam": "底座底框横梁", "column": "墙体立柱", "truss": "屋顶桁架杆件"}


class AnalysisBatchView(QWidget):
    def __init__(self):
        super().__init__()
        self.model = AnalysisModel()
        self.event_bus = EventBus.get_instance()
        self._build_ui()
        self._bind()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(TitleLabel("批量分析 · 多工况验算"))

        card = ElevatedCardWidget()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 16, 16, 16)
        cl.addWidget(BodyLabel("工况列表（每行一条 JSON，示例见注释/下方）："))
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            '{"kind":"beam","Mx":15,"V":25,"grade":"22#"}\n'
            '{"kind":"column","N":60,"Mx":8,"My":3,"width":100,"thick":4,"height":2850}\n'
            '{"kind":"truss","N":1000,"l0":1820}')
        self.input_edit.setFixedHeight(120)
        cl.addWidget(self.input_edit)

        bar = QHBoxLayout()
        self.run_btn = PrimaryPushButton("批量验算")
        self.example_btn = PushButton("填入示例")
        bar.addWidget(self.run_btn)
        bar.addWidget(self.example_btn)
        bar.addStretch(1)
        cl.addLayout(bar)
        lay.addWidget(card)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["构件", "截面", "钢材", "控制应力比", "判定", "参数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table)
        lay.addStretch(1)

    def _bind(self):
        self.run_btn.clicked.connect(self.run_batch)
        self.example_btn.clicked.connect(self.fill_example)
        self.model.batch_done.connect(self.show_results)

    def fill_example(self):
        self.input_edit.setPlainText(
            '{"kind":"beam","Mx":40,"V":50,"grade":"22#"}\n'
            '{"kind":"column","N":120,"Mx":18,"My":6,"width":120,"thick":5,"height":3000}\n'
            '{"kind":"truss","N":600,"l0":1820}\n'
            '{"kind":"column","N":200,"Mx":25,"My":10,"width":100,"thick":4,"height":2850}')

    def _parse_items(self):
        items = []
        for ln in self.input_edit.toPlainText().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            try:
                d = json.loads(ln)
            except Exception as exc:
                InfoBar.error("解析失败", "%s" % exc, parent=self)
                continue
            kind = str(d.get("kind", "")).lower()
            params = {k: v for k, v in d.items() if k not in ("kind", "steel")}
            items.append({"kind": kind, "params": params,
                          "steel": str(d.get("steel", "Q355B"))})
        return items

    def run_batch(self):
        items = self._parse_items()
        if not items:
            InfoBar.warning("批量", "没有可用的工况行", parent=self)
            return
        self.run_btn.setEnabled(False)
        self.model.start_batch(items)

    def show_results(self, results):
        self.table.setRowCount(len(results))
        for i, r in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(KIND_CN.get(r.get("kind"), r.get("kind"))))
            self.table.setItem(i, 1, QTableWidgetItem(r.get("section", "")))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("steel", "")))
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("control_ratio", ""))))
            self.table.setItem(i, 4, QTableWidgetItem(r.get("verdict", "")))
            self.table.setItem(i, 5, QTableWidgetItem(json.dumps(r.get("params", {}), ensure_ascii=False)))
            self._save(r)
        self.run_btn.setEnabled(True)
        InfoBar.success("批量", "完成 %d 条工况验算" % len(results), parent=self)
        self.event_bus.inference_data_saved.emit()

    def _save(self, r):
        try:
            from app.models.database.analysis_dao import AnalysisDAO
            AnalysisDAO().add_analysis(
                component_type=r.get("kind", ""), component_name=r.get("name", ""),
                section_info=r.get("section", ""), steel=r.get("steel", ""),
                params_dict=r.get("params", {}), ratios_dict=r.get("ratios", {}),
                control_ratio=r.get("control_ratio"), verdict=r.get("verdict", ""))
        except Exception:
            pass
