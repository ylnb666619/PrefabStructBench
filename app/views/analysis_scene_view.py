# -*- coding: utf-8 -*-
"""
analysis_scene_view —— 页面「场景导入」：读 BIMBase 生成的场景，一键验算构件
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QFileDialog)
from qfluentwidgets import (PushButton, FluentIcon, TitleLabel, BodyLabel,
                            ElevatedCardWidget, PrimaryPushButton,
                            SmoothScrollArea, InfoBar, InfoBarPosition)

from app.models.analysis_model import AnalysisModel
from app.models.event_bus import EventBus

# 工程根入 path（供 mech import）
import os
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class AnalysisSceneView(QWidget):
    """读 %TEMP%/prefab_substation_ai_last_scene.json → 列表 → 一键验算。"""

    def __init__(self):
        super().__init__()
        self.model = AnalysisModel()
        self.event_bus = EventBus.get_instance()
        self._items = []
        self._build_ui()
        self._bind()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(TitleLabel("场景导入 · 整舱构件验算"))

        bar = QHBoxLayout()
        self.load_btn = PushButton(FluentIcon.FOLDER, "读取默认场景")
        self.choose_btn = PushButton(FluentIcon.FOLDER_ADD, "选择场景文件...")
        self.run_btn = PrimaryPushButton(FluentIcon.PLAY, "一键验算全部")
        self.run_btn.setEnabled(False)
        self.scene_info = BodyLabel(
            "来源1: 默认 %TEMP%/prefab_substation_ai_last_scene.json（BIMBase 生成）\n"
            "来源2: 手动选择任一 last_scene.json")
        bar.addWidget(self.load_btn)
        bar.addWidget(self.choose_btn)
        bar.addWidget(self.run_btn)
        bar.addStretch(1)
        lay.addLayout(bar)
        lay.addWidget(self.scene_info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["构件", "截面", "钢材", "控制应力比", "判定"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table)
        lay.addStretch(1)

    def _bind(self):
        self.load_btn.clicked.connect(self.load_scene)
        self.choose_btn.clicked.connect(self.choose_file)
        self.run_btn.clicked.connect(self.run_all)
        self.model.batch_done.connect(self.show_results)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 BIMBase 场景文件",
                                              "", "JSON (*.json)")
        if path:
            self.load_scene(path=path)

    # ---- 读取场景 ----
    def load_scene(self, path=None):
        try:
            from mech import scene_loader
            comps = scene_loader.extract_components(
                scene_loader.load_last_scene(path=path))
        except Exception as exc:
            InfoBar.error("读取失败", str(exc), parent=self)
            return
        if not comps:
            InfoBar.warning("场景", "未在场景中找到结构构件。\n请先在 BIMBase 生成预制舱模型。", parent=self)
            return
        self._items = comps
        self.scene_info.setText("场景含 %d 个结构构件，点击「一键验算全部」开始。" % len(comps))
        self.run_btn.setEnabled(True)
        # 预填表格（参数）
        self.table.setRowCount(len(comps))
        for i, c in enumerate(comps):
            sec = str(c.get("params", {}))
            self.table.setItem(i, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(sec[:40]))
            self.table.setItem(i, 2, QTableWidgetItem(c.get("steel", "Q355B")))
        InfoBar.success("场景", "已读取 %d 个构件" % len(comps), parent=self)

    # ---- 一键验算 ----
    def run_all(self):
        if not self._items:
            return
        self.scene_info.setText("验算中...")
        self.run_btn.setEnabled(False)
        self.model.start_batch(self._items)

    def show_results(self, results):
        self.table.setRowCount(len(results))
        all_pass = True
        for i, r in enumerate(results):
            self.table.setItem(i, 0, QTableWidgetItem(r.get("name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(r.get("section", "")))
            self.table.setItem(i, 2, QTableWidgetItem(r.get("steel", "")))
            self.table.setItem(i, 3, QTableWidgetItem(str(r.get("control_ratio", ""))))
            self.table.setItem(i, 4, QTableWidgetItem(r.get("verdict", "")))
            ok = r.get("verdict") == "合格"
            all_pass = all_pass and ok
            self._save(r)
        self.run_btn.setEnabled(True)
        self.scene_info.setText(
            "验算完成：%d 个构件，全部合格" % len(results) if all_pass
            else "验算完成：%d 个构件，存在不合格" % len(results))
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
