# app/main_window.py
# 主窗口：预制舱钢结构力学分析（改造自 steel_defect 外壳）
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShortcut, QKeySequence
from qfluentwidgets import (FluentWindow, FluentIcon, InfoBar, InfoBarPosition,
                            setTheme, Theme)

from app.models.event_bus import EventBus

# —— 力学分析 6 页 ——
from app.controllers.analysis_controller import AnalysisController
from app.views.analysis_input_view import AnalysisInputView
from app.views.analysis_scene_view import AnalysisSceneView
from app.views.analysis_batch_view import AnalysisBatchView
from app.views.analysis_dashboard_view import AnalysisDashboardView
from app.views.analysis_data_view import AnalysisDataView
from app.views.billing_view import BillingView
from app.controllers.billing_controller import BillingController


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.navigationInterface.setExpandWidth(150)

        # view 层
        self.analysis_input_view = AnalysisInputView()      # 构件录入
        self.analysis_scene_view = AnalysisSceneView()      # 场景导入
        self.analysis_batch_view = AnalysisBatchView()      # 批量分析
        self.analysis_dashboard_view = AnalysisDashboardView()  # 仪表盘
        self.analysis_data_view = AnalysisDataView()        # 数据查看
        self.billing_view = BillingView()                   # 计费管理

        # controller（录入页显式 controller；其余页自含 model/数据）
        self.analysis_controller = AnalysisController(
            self.analysis_input_view, self.analysis_input_view.model)
        self.billing_controller = BillingController(self.billing_view)

        self.init_navigation()
        self.init_window()
        self.setMicaEffectEnabled(True)
        self.init_global_event()

    def init_global_event(self):
        EventBus.get_instance().message_notification.connect(self.info)

    def init_navigation(self):
        # FluentWindow 要求每个 view 有 objectName
        pages = [
            (self.analysis_dashboard_view, "analysis_dashboard", FluentIcon.HOME, "仪表盘"),
            (self.analysis_input_view, "analysis_input", FluentIcon.EDIT, "构件录入"),
            (self.analysis_scene_view, "analysis_scene", FluentIcon.FOLDER, "场景导入"),
            (self.analysis_batch_view, "analysis_batch", FluentIcon.LIBRARY, "批量分析"),
            (self.analysis_data_view, "analysis_data", FluentIcon.BOOK_SHELF, "数据查看"),
            (self.billing_view, "billing", FluentIcon.CERTIFICATE, "计费管理"),
        ]
        for view, obj, icon, text in pages:
            view.setObjectName(obj)
            self.addSubInterface(view, icon, text)

    def init_window(self):
        self.setWindowTitle("预制舱钢结构力学分析")
        self.resize(1280, 720)
        # Ctrl+T 切换深/浅主题
        self._theme_dark = False
        sc = QShortcut(QKeySequence("Ctrl+T"), self)
        sc.activated.connect(self.toggle_theme)

    def toggle_theme(self):
        self._theme_dark = not self._theme_dark
        setTheme(Theme.DARK if self._theme_dark else Theme.LIGHT)
        self.info("主题", "已切换为" + ("深色" if self._theme_dark else "浅色"))

    def info(self, title: str, content: str):
        InfoBar.success(
            title=title, content=content,
            orient=Qt.Orientation.Horizontal, isClosable=True,
            position=InfoBarPosition.TOP, duration=2000, parent=self)
