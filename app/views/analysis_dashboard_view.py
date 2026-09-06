# -*- coding: utf-8 -*-
"""
analysis_dashboard_view —— 页面「仪表盘」：分析统计概览
（替换原缺陷检测仪表盘；统计来源 = analysis_results）
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from qfluentwidgets import (TitleLabel, BodyLabel, CaptionLabel, ElevatedCardWidget,
                            SmoothScrollArea, InfoBar)

from app.models.database.analysis_dao import AnalysisDAO
from app.models.event_bus import EventBus

KIND_CN = {"beam": "底座横梁", "column": "墙体立柱", "truss": "桁架杆件"}


class AnalysisDashboardView(QWidget):
    def __init__(self):
        super().__init__()
        self.dao = AnalysisDAO()
        self.event_bus = EventBus.get_instance()
        self._build_ui()
        self.event_bus.inference_data_saved.connect(self.refresh)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(TitleLabel("数据概览 · 力学分析统计"))

        # 统计卡
        card_row = QHBoxLayout()
        self.total_card = self._stat_card("分析总数", "0")
        self.fail_card = self._stat_card("不合格数", "0")
        self.type_card = self._stat_card("构件类型", "-")
        card_row.addWidget(self.total_card)
        card_row.addWidget(self.fail_card)
        card_row.addWidget(self.type_card)
        card_row.addStretch(1)
        lay.addLayout(card_row)

        # 类型分布表
        self.type_table = QTableWidget(0, 2)
        self.type_table.setHorizontalHeaderLabels(["构件类型", "分析次数"])
        self.type_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(BodyLabel("构件类型分布"))
        lay.addWidget(self.type_table)

        # 近30日趋势表
        self.trend_table = QTableWidget(0, 2)
        self.trend_table.setHorizontalHeaderLabels(["日期", "分析次数"])
        self.trend_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(BodyLabel("近 30 日趋势"))
        lay.addWidget(self.trend_table)
        lay.addStretch(1)

    def _stat_card(self, title, value):
        card = ElevatedCardWidget()
        cl = QVBoxLayout(card)
        cl.addWidget(CaptionLabel(title))
        self._value_labels = getattr(self, "_value_labels", {})
        lbl = TitleLabel(value)
        self._value_labels[title] = lbl
        cl.addWidget(lbl)
        return card

    def refresh(self):
        stats = self.dao.dashboard_stats()
        self._value_labels.get("分析总数", None)
        total_lbl = self._value_labels.get("分析总数")
        fail_lbl = self._value_labels.get("不合格数")
        type_lbl = self._value_labels.get("构件类型")
        if total_lbl:
            total_lbl.setText(str(stats.get("total", 0)))
        if fail_lbl:
            fail_lbl.setText(str(stats.get("fail", 0)))
        if type_lbl:
            type_lbl.setText(str(len(stats.get("by_type", {}))))

        by_type = stats.get("by_type", {})
        self.type_table.setRowCount(len(by_type))
        for i, (k, v) in enumerate(sorted(by_type.items())):
            self.type_table.setItem(i, 0, QTableWidgetItem(KIND_CN.get(k, k)))
            self.type_table.setItem(i, 1, QTableWidgetItem(str(v)))

        trend = stats.get("trend", {})
        self.trend_table.setRowCount(len(trend))
        for i, (d, v) in enumerate(trend.items()):
            self.trend_table.setItem(i, 0, QTableWidgetItem(str(d)))
            self.trend_table.setItem(i, 1, QTableWidgetItem(str(v)))
