# -*- coding: utf-8 -*-
"""
analysis_model —— 构件力学分析业务模型（QThreadPool 后台计算）
对应界面页「构件录入」：选构件类型 + 录入参数 → 后台验算/优化。
"""
import sys

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal

from app.models.utils import WorkerSignals, Worker
from app.models.event_bus import EventBus

# 工程根入 path（保证 mech 可 import）
import os
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


class AnalysisModel(QObject):
    """构件录入/场景/批量页共用后台：调 mech 引擎做验算/优化。"""
    analysis_done = pyqtSignal(object)   # 单构件验算结果 dict
    optimize_done = pyqtSignal(object)   # 优化结果 dict
    batch_done = pyqtSignal(object)      # 批量/场景验算结果 list
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.thread_pool = QThreadPool()
        self.event_bus = EventBus.get_instance()

    # ---- 后台任务 ----
    def start_analysis(self, kind: str, params: dict, steel: str):
        worker = Worker(self._task_analysis, kind, params, steel)
        worker.signals.result.connect(self.analysis_done.emit)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def start_optimize(self, kind: str, forces: dict, steel: str):
        worker = Worker(self._task_optimize, kind, forces, steel)
        worker.signals.result.connect(self.optimize_done.emit)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    def start_batch(self, items: list):
        """批量验算：items=[{kind,params,steel},...]，串行后台计算。
        完成后 batch_done 发出 results list（每项含原 params + 结果）。"""
        worker = Worker(self._task_batch, items)
        worker.signals.result.connect(self.batch_done.emit)
        worker.signals.error.connect(self._on_error)
        self.thread_pool.start(worker)

    # ---- 工作线程函数（signals 由 Worker 注入）----
    @staticmethod
    def _task_analysis(kind, params, steel, signals: WorkerSignals):
        from mech.analysis_engine import analyze_component
        return analyze_component(kind, params, steel)

    @staticmethod
    def _task_optimize(kind, forces, steel, signals: WorkerSignals):
        from mech.analysis_engine import optimize_component
        return optimize_component(kind, forces, steel)

    @staticmethod
    def _task_batch(items, signals: WorkerSignals):
        from mech.analysis_engine import analyze_component
        results = []
        for it in items or []:
            res = analyze_component(it.get("kind"), it.get("params"),
                                    it.get("steel", "Q355B"))
            results.append(res)
        return results

    def _on_error(self, err_tuple):
        exctype, value, tb = err_tuple
        msg = "计算失败: %s" % value
        self.error_signal.emit(msg)
        self.event_bus.message_notification.emit("错误", msg)
