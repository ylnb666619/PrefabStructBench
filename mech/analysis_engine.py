# -*- coding: utf-8 -*-
"""
mech/analysis_engine —— 预制舱构件力学分析引擎（GUI / API 统一入口）
=====================================================================
把 GB50017 强度/稳定验算与截面优化封装为纯函数，供桌面 GUI 与 FastAPI
调用。纯标准库，无第三方依赖（Py3.12/3.13 均可跑）。

分析对象（三大构件）：
  beam   底座底框横梁  槽钢(C形)  受弯+受剪
  column 墙体立柱      方矩管     压弯
  truss  屋顶桁架杆件   矩形/圆管  轴心受力
"""

from __future__ import print_function

import os
import sys

_mech_dir = os.path.dirname(os.path.abspath(__file__))
if _mech_dir not in sys.path:
    sys.path.insert(0, _mech_dir)

from sections import (
    BaseBeam, WallColumn, RoofTrussMember, set_steel,
)
from steel_sections import (
    CHANNEL_GRADE_TABLE, channel_by_grade,
    square_by_size, rectangle_properties, circular_hollow_properties,
)
import section_optimizer as so

# ============================================================================
# 构件枚举与默认参数
# ============================================================================

COMPONENTS = {
    "beam":   "底座底框横梁",
    "column": "墙体立柱",
    "truss":  "屋顶桁架杆件",
}
STEEL_OPTIONS = ["Q355B", "Q235B"]

# 各构件默认截面/内力（便于"默认分析"；GUI 可覆盖）
DEFAULTS = {
    "beam":   {"Mx": 15.0, "V": 25.0, "grade": "22#", "span": 4000.0},
    "column": {"N": 60.0, "Mx": 8.0, "My": 3.0, "width": 100.0,
               "thick": 4.0, "height": 2850.0},
    "truss":  {"N": 1000.0, "l0": 1820.0, "sec": "rect", "dia": 89.0},
}


def _v(d, key, default=0.0):
    try:
        val = d.get(key, default)
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# ============================================================================
# 强度 + 稳定验算
# ============================================================================

def analyze_component(kind, params=None, steel="Q355B", build_report=True):
    """验算单个构件，返回结构化 dict + 可选报告文本。

    params 按 COMPONENTS/DEFAULTS 的键提供；缺省用默认值。
    """
    kind = str(kind).lower()
    if kind not in COMPONENTS:
        raise ValueError("kind 必须是 beam/column/truss: %s" % kind)
    p = dict(DEFAULTS[kind])
    if params:
        p.update({k: params[k] for k in params if params[k] is not None})

    f = 305.0 if str(steel).upper().startswith("Q355") else 215.0
    result = {
        "kind": kind,
        "name": COMPONENTS[kind],
        "steel": steel,
        "f": f,
        "params": p,
    }

    if kind == "beam":
        grade = str(p.get("grade", "22#"))
        if grade not in CHANNEL_GRADE_TABLE:
            grade = "22#"
        h, b, d, t = CHANNEL_GRADE_TABLE[grade]
        ch = channel_by_grade(grade)
        beam = BaseBeam(M_x=_v(p, "Mx"), V=_v(p, "V"))
        set_steel(beam, steel)
        beam.W_nx = ch["Wx"]; beam.W_x = ch["Wx"]
        beam.h_w = h - 2 * t; beam.t_w = d
        beam.A = ch["A"]; beam.I_x = ch["Ix"]; beam.i_x = ch["ix"]
        beam.l1 = _v(p, "span", 4000.0)
        rsig, rtau = beam.check_strength()
        rstab = beam.check_stability()
        ratio = max(rsig, rtau, rstab)
        result["section"] = "槽钢%s" % grade
        result["stresses"] = {"正应力": rsig * f, "剪应力": rtau * f, "稳定应力": rstab * f}
        result["ratios"] = {"抗弯": round(rsig, 3), "抗剪": round(rtau, 3),
                            "整体稳定": round(rstab, 3)}

    elif kind == "column":
        width = _v(p, "width", 100.0)
        thick = _v(p, "thick", 4.0)
        height = _v(p, "height", 2850.0)
        sq = square_by_size(width, thick)
        column = WallColumn(N=_v(p, "N"), M_x=_v(p, "Mx"), M_y=_v(p, "My"))
        set_steel(column, steel)
        column.A_n = sq["A"]; column.A = sq["A"]
        column.I_x = sq["I"]; column.I_y = sq["I"]
        column.i_x = sq["i"]; column.i_y = sq["i"]
        column.W_nx = sq["W"]; column.W_ny = sq["W"]; column.W1x = sq["W"]
        l0 = 0.5 * height
        column.l0x = l0; column.l0y = l0
        r1 = column.check_strength()
        r2, r3 = column.check_stability()
        ratio = max(r1, r2, r3)
        result["section"] = "方管%.0fx%.0f 壁厚%.1f" % (width, width, thick)
        result["ratios"] = {"强度": round(r1, 3), "平面内稳定": round(r2, 3),
                            "平面外稳定": round(r3, 3)}

    else:  # truss
        l0 = _v(p, "l0", 1820.0)
        sec = str(p.get("sec", "rect"))
        if sec == "圆管":
            dia = _v(p, "dia", 89.0)
            pipe = circular_hollow_properties(dia, 4.0)
            truss = RoofTrussMember(N=_v(p, "N"))
            set_steel(truss, steel)
            truss.A_n = pipe["A"]; truss.A = pipe["A"]
            truss.I = pipe["I"]; truss.i = pipe["i"]; truss.W = pipe["W"]
            sec_name = "圆管Phi%.0f" % dia
        else:
            rect = rectangle_properties(150.0, 100.0)
            truss = RoofTrussMember(N=_v(p, "N"))
            set_steel(truss, steel)
            truss.A_n = rect["A"]; truss.A = rect["A"]
            truss.I = rect["Ix"]; truss.i = rect["ix"]; truss.W = rect["Wx"]
            sec_name = "矩形150x100"
        truss.l0 = l0
        r1 = truss.check_strength()
        r2 = truss.check_stability()
        ratio = max(r1, r2)
        result["section"] = sec_name
        result["ratios"] = {"强度": round(r1, 3), "轴压稳定": round(r2, 3)}

    result["control_ratio"] = round(ratio, 3)
    result["verdict"] = "合格" if ratio <= 1.0 else "不合格"
    if build_report:
        result["report"] = _report_text(result)
    return result


# ============================================================================
# 截面优化（最小满足截面）
# ============================================================================

def optimize_component(kind, forces=None, steel="Q355B"):
    """对构件做最小截面优化。返回 {当前截面, 最优截面, 应力比, 节约%}。"""
    kind = str(kind).lower()
    if kind == "beam":
        mx = _v(forces, "Mx", 15.0) if forces else 15.0
        v = _v(forces, "V", 25.0) if forces else 25.0
        inp = so.BeamInput(M_x=mx, V=v, f=305.0 if "Q355" in steel.upper() else 215.0,
                           f_v=175.0 if "Q355" in steel.upper() else 125.0)
        best, ratio, _ = so.optimize_beam(inp, so.BEAM_SECTIONS)
        current = so.BEAM_SECTIONS[-1]
        if best is None:
            return {"kind": kind, "verdict": "无可行截面"}
        saved = 1 - best["A"] / current["A"]
        return {"kind": kind,
                "current": "槽钢" + current["name"] if current["name"].isdigit() else current["name"],
                "optimal": best["name"], "ratio": round(ratio, 3),
                "save_pct": round(saved * 100, 1),
                "verdict": "可减小" if saved > 0.01 else "已最优"}
    if kind == "column":
        n = _v(forces, "N", 60.0) if forces else 60.0
        mx = _v(forces, "Mx", 8.0) if forces else 8.0
        my = _v(forces, "My", 3.0) if forces else 3.0
        inp = so.ColumnInput(N=n, M_x=mx, M_y=my, f=305.0 if "Q355" in steel.upper() else 215.0)
        best, ratio, _ = so.optimize_column(inp, so.COLUMN_SECTIONS)
        if best is None:
            return {"kind": kind, "verdict": "无可行截面"}
        return {"kind": kind, "optimal": best.get("name", str(best)),
                "ratio": round(ratio, 3), "verdict": "最优"}
    # truss
    n = _v(forces, "N", 1000.0) if forces else 1000.0
    inp = so.TrussInput(N=n, f=305.0 if "Q355" in steel.upper() else 215.0)
    best, ratio, _ = so.optimize_truss(inp, so.TRUSS_SECTIONS)
    if best is None:
        return {"kind": kind, "verdict": "无可行截面"}
    return {"kind": kind, "optimal": best.get("name", str(best)),
            "ratio": round(ratio, 3), "verdict": "最优"}


# ============================================================================
# 报告文本
# ============================================================================

def _report_text(r):
    lines = []
    lines.append("【%s】%s  (%s)" % (r["kind"], r["name"], r["section"]))
    lines.append("  钢材 %s (f=%.0f)" % (r["steel"], r["f"]))
    for k, v in r.get("ratios", {}).items():
        lines.append("  %s 应力比: %.3f" % (k, v))
    lines.append("  控制应力比: %.3f → %s" % (r["control_ratio"], r["verdict"]))
    return "\n".join(lines)


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    import json
    for kind in ("beam", "column", "truss"):
        res = analyze_component(kind)
        print(json.dumps(res, ensure_ascii=False, indent=1)[:400])
        print(res["report"])
        print("优化:", json.dumps(optimize_component(kind), ensure_ascii=False))
        print("-" * 40)
