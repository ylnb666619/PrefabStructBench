# -*- coding: utf-8 -*-
"""
analysis_input_view —— 页面「构件录入」：动态表单 + 彩色结果卡
按构件类型只显示相关参数，可一键载入真实构件；结果分项应力比配色。
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                             QDoubleSpinBox, QLabel, QGridLayout)
from qfluentwidgets import (CardWidget, PushButton, ComboBox, FluentIcon,
                            HeaderCardWidget, TitleLabel, BodyLabel,
                            CaptionLabel, ElevatedCardWidget, SmoothScrollArea,
                            PrimaryPushButton, InfoBar)

from app.models.analysis_model import AnalysisModel
from app.models.event_bus import EventBus

KIND_CN = {"beam": "底座底框横梁", "column": "墙体立柱", "truss": "屋顶桁架杆件"}
# 真实构件预设：载入按钮一键填入
PRESETS = {
    "beam":   {"Mx": 15.0, "V": 25.0, "grade": "22#", "span": 4000.0,
               "note": "槽钢 22# · 底座总长 4000mm"},
    "column": {"N": 60.0, "Mx": 8.0, "My": 3.0, "width": 100.0,
               "thick": 4.0, "height": 2850.0, "note": "方管 100×100×4 · 高 2850mm"},
    "truss":  {"N": 1000.0, "l0": 1820.0, "note": "桁架杆件 150×100 · 斜杆 1820mm"},
}


def _mk_spin(dec=1, step=5.0, rmax=1e6):
    sp = QDoubleSpinBox()
    sp.setRange(-rmax, rmax)
    sp.setDecimals(dec)
    sp.setSingleStep(step)
    sp.setValue(0.0)
    sp.setFixedWidth(110)
    return sp


class AnalysisInputView(QWidget):
    def __init__(self):
        super().__init__()
        self.model = AnalysisModel()
        self.event_bus = EventBus.get_instance()
        self._build_ui()
        self._bind()
        self.kind_combo.setCurrentIndex(0)
        self._sync_form()

    # ---------------- UI ----------------
    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(TitleLabel("构件力学分析"))

        scroll = SmoothScrollArea(self)
        scroll.setWidgetResizable(True)
        body = QWidget()
        bl = QVBoxLayout(body)

        panel = ElevatedCardWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        top.addWidget(BodyLabel("构件类型"))
        self.kind_combo = ComboBox()
        for k, cn in KIND_CN.items():
            self.kind_combo.addItem(cn, userData=k)
        self.kind_combo.setFixedWidth(180)
        top.addWidget(self.kind_combo)
        top.addSpacing(20)
        top.addWidget(BodyLabel("钢材"))
        self.steel_combo = ComboBox()
        self.steel_combo.addItems(["Q355B", "Q235B"])
        self.steel_combo.setFixedWidth(120)
        top.addWidget(self.steel_combo)
        top.addSpacing(20)
        self.preset_btn = PushButton(FluentIcon.ROBOT, "载入真实构件")
        top.addWidget(self.preset_btn)
        top.addStretch(1)
        pl.addLayout(top)

        # 三组动态字段（按类型显隐）
        self.group_beam = QFrame(); self._build_beam(self.group_beam)
        self.group_column = QFrame(); self._build_column(self.group_column)
        self.group_truss = QFrame(); self._build_truss(self.group_truss)
        pl.addWidget(self.group_beam)
        pl.addWidget(self.group_column)
        pl.addWidget(self.group_truss)

        btns = QHBoxLayout()
        self.analyze_btn = PrimaryPushButton(FluentIcon.PLAY, "运行验算")
        self.optimize_btn = PushButton(FluentIcon.DOWNLOAD, "截面优化")
        btns.addWidget(self.analyze_btn)
        btns.addWidget(self.optimize_btn)
        btns.addStretch(1)
        pl.addLayout(btns)
        bl.addWidget(panel)

        # 结果区
        self.result_card = HeaderCardWidget("分析结果")
        rl = QVBoxLayout(self.result_card)
        self.verdict_label = BodyLabel("尚未分析")
        self.verdict_label.setStyleSheet("font-size:17px; font-weight:bold;")
        rl.addWidget(self.verdict_label)
        self.grid = QGridLayout()
        self.ratio_labels = {}
        rl.addLayout(self.grid)
        self.opt_label = CaptionLabel("")
        self.opt_label.setStyleSheet("color:#3b82f6;")
        rl.addWidget(self.opt_label)
        bl.addWidget(self.result_card)

        bl.addStretch(1)
        scroll.setWidget(body)
        lay.addWidget(scroll)

    def _field_row(self, parent, fields):
        """fields: [(key,label),(key,label,spin)] → 布局，存 self.spins[key]"""
        self.spins = getattr(self, "spins", {})
        g = QHBoxLayout()
        for f in fields:
            key, label = f[0], f[1]
            sp = f[2] if len(f) > 2 else _mk_spin()
            col = QVBoxLayout()
            col.addWidget(CaptionLabel(label))
            col.addWidget(sp)
            g.addLayout(col)
            self.spins[key] = sp
        g.addStretch(1)
        return g

    def _build_beam(self, parent):
        l = QVBoxLayout(parent)
        l.addWidget(CaptionLabel("底座底框横梁（槽钢）：弯矩 Mx / 剪力 V / 槽钢型号 / 跨长"))
        row = self._field_row(parent, [("Mx", "弯矩 Mx (kN·m)", _mk_spin(step=5)),
                                        ("V", "剪力 V (kN)", _mk_spin(step=5)),
                                        ("span", "跨长 (mm)", _mk_spin(step=100, rmax=1e5))])
        self.grade_combo = ComboBox()
        self.grade_combo.addItems(["12#", "14#", "16#", "18#", "20#", "22#", "25#"])
        self.grade_combo.setCurrentText("22#")
        gcol = QVBoxLayout()
        gcol.addWidget(CaptionLabel("槽钢型号"))
        gcol.addWidget(self.grade_combo)
        row.addLayout(gcol)
        l.addLayout(row)
        l.addStretch(1)

    def _build_column(self, parent):
        l = QVBoxLayout(parent)
        l.addWidget(CaptionLabel("墙体立柱（方矩管）：轴力 N / Mx / My / 截面宽·壁厚 / 高度"))
        row = self._field_row(parent, [("N", "轴力 N (kN)", _mk_spin(step=10)),
                                        ("Mx", "Mx (kN·m)", _mk_spin(step=2)),
                                        ("My", "My (kN·m)", _mk_spin(step=1)),
                                        ("width", "方管宽 (mm)", _mk_spin(step=10)),
                                        ("thick", "壁厚 (mm)", _mk_spin(step=1)),
                                        ("height", "高度 (mm)", _mk_spin(step=100, rmax=1e5))])
        l.addLayout(row)
        l.addStretch(1)

    def _build_truss(self, parent):
        l = QVBoxLayout(parent)
        l.addWidget(CaptionLabel("屋顶桁架杆件（矩形150×100）：轴力 N / 斜杆计算长度"))
        row = self._field_row(parent, [("N", "轴力 N (kN)", _mk_spin(step=100)),
                                        ("l0", "杆长 (mm)", _mk_spin(step=100, rmax=1e5))])
        l.addLayout(row)
        l.addStretch(1)

    def _set_verdict(self, text, ok):
        color = "#16a34a" if ok else "#dc2626"
        self.verdict_label.setStyleSheet("font-size:17px; font-weight:bold; color:%s;" % color)
        self.verdict_label.setText(text)

    # ---------------- 逻辑 ----------------
    def get_kind(self):
        return self.kind_combo.currentData() or "beam"

    def get_steel(self):
        return self.steel_combo.currentText()

    def _sync_form(self):
        kind = self.get_kind()
        self.group_beam.setVisible(kind == "beam")
        self.group_column.setVisible(kind == "column")
        self.group_truss.setVisible(kind == "truss")

    def _apply_preset(self, kind):
        p = PRESETS.get(kind, {})
        self.spins["Mx"].setValue(p.get("Mx", 0))
        self.spins["V"].setValue(p.get("V", 0))
        self.spins["N"].setValue(p.get("N", 0))
        self.spins["span"].setValue(p.get("span", 0))
        self.spins["l0"].setValue(p.get("l0", 0))
        self.spins["width"].setValue(p.get("width", 0))
        self.spins["thick"].setValue(p.get("thick", 0))
        self.spins["height"].setValue(p.get("height", 0))
        if kind == "beam":
            self.grade_combo.setCurrentText(p.get("grade", "22#"))
        InfoBar.success("预设", p.get("note", ""), parent=self)

    def collect_params(self):
        kind = self.get_kind()
        p = {"Mx": self.spins["Mx"].value(), "V": self.spins["V"].value(),
             "N": self.spins["N"].value()}
        if kind == "beam":
            p["grade"] = self.grade_combo.currentText()
            p["span"] = self.spins["span"].value() or 4000.0
        elif kind == "column":
            p["width"] = self.spins["width"].value() or 100.0
            p["thick"] = self.spins["thick"].value() or 4.0
            p["height"] = self.spins["height"].value() or 2850.0
        else:
            p["l0"] = self.spins["l0"].value() or 1820.0
        return p

    def collect_forces(self):
        return {"Mx": self.spins["Mx"].value(), "V": self.spins["V"].value(),
                "N": self.spins["N"].value()}

    def show_result(self, res: dict):
        # 清空旧分项
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.ratio_labels = {}
        verdict = res.get("verdict", "")
        self._set_verdict("【%s】%s  %s  %s" % (
            KIND_CN.get(res.get("kind"), ""), res.get("section", ""),
            res.get("steel", ""), verdict), verdict == "合格")
        # 分项应力比彩色卡
        row = 0
        for name, r in (res.get("ratios") or {}).items():
            card = ElevatedCardWidget()
            cl = QVBoxLayout(card)
            cl.setContentsMargins(10, 6, 10, 6)
            ok = r <= 1.0
            color = "#16a34a" if ok else "#dc2626"
            cl.addWidget(CaptionLabel("%s" % name))
            lbl = QLabel("%.3f" % r)
            lbl.setStyleSheet("font-size:18px; font-weight:bold; color:%s;" % color)
            cl.addWidget(lbl)
            self.grid.addWidget(card, row // 3, row % 3)
            row += 1
        # 控制比说明
        self.opt_label.setText(
            "控制应力比 %.3f %s   ·  已自动保存到分析记录" % (
                res.get("control_ratio", 0),
                "" if verdict == "合格" else "（不满足，需加大截面）"))
        self._save_result(res)

    def show_optimize(self, opt: dict):
        txt = "优化结果：%s   应力比 %.3f   %s" % (
            opt.get("optimal", ""), opt.get("ratio", 0), opt.get("verdict", ""))
        if opt.get("save_pct") is not None:
            txt += "   （可节省约 %.0f%% 材料）" % opt["save_pct"]
        self.opt_label.setText(txt)
        self.event_bus.message_notification.emit("优化", txt)

    def _save_result(self, res: dict):
        try:
            from app.models.database.analysis_dao import AnalysisDAO
            AnalysisDAO().add_analysis(
                component_type=res.get("kind", ""), component_name=res.get("name", ""),
                section_info=res.get("section", ""), steel=res.get("steel", ""),
                params_dict=res.get("params", {}), ratios_dict=res.get("ratios", {}),
                control_ratio=res.get("control_ratio"), verdict=res.get("verdict", ""))
            self.event_bus.inference_data_saved.emit()
        except Exception:
            pass

    def show_error(self, msg: str):
        self._set_verdict("错误：%s" % msg, False)

    def _bind(self):
        # model 信号 → 结果展示；kind 切换显隐；预设按钮
        self.model.analysis_done.connect(self.show_result)
        self.model.optimize_done.connect(self.show_optimize)
        self.model.error_signal.connect(self.show_error)
        self.kind_combo.currentIndexChanged.connect(lambda _: self._sync_form())
        self.preset_btn.clicked.connect(lambda: self._apply_preset(self.get_kind()))
