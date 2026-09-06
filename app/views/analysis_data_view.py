# -*- coding: utf-8 -*-
"""
analysis_data_view —— 页面「数据查看」：分析记录分页浏览
（替换原缺陷记录；来源 = analysis_results）
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView)
from qfluentwidgets import (TitleLabel, BodyLabel, PushButton, PrimaryPushButton,
                            FluentIcon, ComboBox, InfoBar)

from app.models.database.analysis_dao import AnalysisDAO
from app.models.event_bus import EventBus

KIND_CN = {"beam": "底座横梁", "column": "墙体立柱", "truss": "桁架杆件"}
PAGE_SIZE = 20


class AnalysisDataView(QWidget):
    def __init__(self):
        super().__init__()
        self.dao = AnalysisDAO()
        self.page = 1
        self._build_ui()
        self.event_bus = EventBus.get_instance()
        self.event_bus.inference_data_saved.connect(lambda: self.load(1))
        self.load(1)

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(TitleLabel("数据查看 · 分析记录"))

        bar = QHBoxLayout()
        bar.addWidget(BodyLabel("构件类型"))
        self.type_filter = ComboBox()
        self.type_filter.addItem("全部", userData="")
        for k, cn in KIND_CN.items():
            self.type_filter.addItem(cn, userData=k)
        self.type_filter.setFixedWidth(150)
        bar.addWidget(self.type_filter)
        self.refresh_btn = PushButton(FluentIcon.SYNC, "刷新")
        bar.addWidget(self.refresh_btn)
        bar.addStretch(1)
        self.page_label = BodyLabel("")
        bar.addWidget(self.page_label)
        self.prev_btn = PushButton(FluentIcon.LEFT_ARROW, "上一页")
        self.next_btn = PushButton(FluentIcon.RIGHT_ARROW, "下一页")
        bar.addWidget(self.prev_btn)
        bar.addWidget(self.next_btn)
        lay.addLayout(bar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "构件", "截面", "钢材", "控制应力比", "判定", "时间"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table)
        lay.addStretch(1)

        self.refresh_btn.clicked.connect(lambda: self.load(self.page))
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.type_filter.currentIndexChanged.connect(lambda _: self.load(1))

    def load(self, page):
        ctype = self.type_filter.currentData() or None
        rows, total = self.dao.fetch_all(page=page, page_size=PAGE_SIZE,
                                         component_type=ctype)
        self.page = page
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(KIND_CN.get(r["component_type"], r["component_type"])))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("section_info", "")))
            self.table.setItem(i, 3, QTableWidgetItem(r.get("steel", "")))
            cr = r.get("control_ratio")
            self.table.setItem(i, 4, QTableWidgetItem("%.3f" % cr if cr is not None else "-"))
            self.table.setItem(i, 5, QTableWidgetItem(r.get("verdict", "")))
            self.table.setItem(i, 6, QTableWidgetItem(str(r.get("timestamp", ""))))
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page_label.setText("第 %d/%d 页 (共 %d 条)" % (self.page, pages, total))
        self.prev_btn.setEnabled(self.page > 1)
        self.next_btn.setEnabled(self.page < pages)

    def prev_page(self):
        if self.page > 1:
            self.load(self.page - 1)

    def next_page(self):
        self.load(self.page + 1)
