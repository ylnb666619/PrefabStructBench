# -*- coding: utf-8 -*-
"""
analysis_controller —— 构件录入页控制器：按钮 → model
"""
from app.models.analysis_model import AnalysisModel
from app.views.analysis_input_view import AnalysisInputView


class AnalysisController:
    def __init__(self, view: AnalysisInputView, model: AnalysisModel):
        self.view = view
        self.model = model

        self.view.analyze_btn.clicked.connect(self.on_analyze)
        self.view.optimize_btn.clicked.connect(self.on_optimize)

    def on_analyze(self):
        kind = self.view.get_kind()
        steel = self.view.get_steel()
        params = self.view.collect_params()
        self.view._set_verdict("计算中...", True)
        self.model.start_analysis(kind, params, steel)

    def on_optimize(self):
        kind = self.view.get_kind()
        steel = self.view.get_steel()
        forces = self.view.collect_forces()
        self.view.opt_label.setText("优化中...")
        self.model.start_optimize(kind, forces, steel)
