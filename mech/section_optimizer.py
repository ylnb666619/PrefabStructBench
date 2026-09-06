# -*- coding: utf-8 -*-
"""
预制舱式变电站三大构件 —— 截面尺寸力学优化（GB 50017-2017 强度验算）
======================================================================

目标：从给定截面库中，选出满足强度要求（应力比 ≤ 1.0）且
      截面积（≈重量）最小的截面，实现轻量化。

对象与强度验算（按题目给定的简化强度公式）：
  · 底座底框横梁（受弯为主）：抗弯 σ=Mx/(γx·Wnx)≤f、抗剪 τ=V/(hw·tw)≤fv
      —— 对应 GB 50017 式(6.1.1) 抗弯强度、式(6.1.3) 抗剪强度（本题简化）
  · 墙体立柱（压弯为主）    ：σ=N/An + Mx/(γx·Wnx) + My/(γy·Wny) ≤ f
      —— 对应 GB 50017 式(8.1.1) 拉弯/压弯构件强度（本题取各项同号叠加）
  · 屋顶桁架杆件（轴力为主） ：σ=N/An ≤ f
      —— 对应 GB 50017 式(7.1.1) 轴心受力构件强度

注：本题按"强度"做优化，未计入稳定、挠度等（简化教学范围）。
"""

import math
import sys
from dataclasses import dataclass

# ---- Windows 控制台编码兜底 ----
# 默认 GBK 无法编码 mm^2/星号 等符号会导致 print 崩溃，
# 这里强制 stdout 以 UTF-8 输出（无法重配时忽略）。
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ============================================================================
# 一、输入参数类
# ============================================================================

@dataclass
class BeamInput:
    """底座底框横梁输入（受弯为主）。"""
    M_x: float          # 弯矩设计值 (kN·m)
    V: float            # 剪力设计值 (kN)
    f: float            # 钢材抗弯强度设计值 (MPa)
    f_v: float          # 钢材抗剪强度设计值 (MPa)
    gamma_x: float = 1.05   # 截面塑性发展系数


@dataclass
class ColumnInput:
    """墙体立柱输入（压弯为主）。"""
    N: float            # 轴力设计值 (kN)，受压为正
    M_x: float          # 绕X轴弯矩设计值 (kN·m)
    M_y: float          # 绕Y轴弯矩设计值 (kN·m)
    f: float            # 钢材抗弯/抗压强度设计值 (MPa)
    gamma_x: float = 1.05   # X轴截面塑性发展系数
    gamma_y: float = 1.05   # Y轴截面塑性发展系数


@dataclass
class TrussInput:
    """屋顶桁架杆件输入（轴力为主）。"""
    N: float            # 轴向拉力或压力设计值 (kN)
    f: float            # 钢材抗拉/抗压强度设计值 (MPa)


# ============================================================================
# 二、截面库（每项含强度验算所需特性，A 用于按重量比较）
# ============================================================================

def _channel_sec(h, b, d, t):
    """C形槽钢截面特性（GB/T 706）：返回 {name,Wnx,hw,tw,A}。"""
    hw = h - 2 * t                       # 腹板计算高度
    A = b * h - (b - d) * hw             # 截面积（外框减开口，忽略圆角）
    Ix = (d * hw ** 3 / 12.0
          + 2 * (b * t ** 3 / 12.0 + b * t * ((h - t) / 2.0) ** 2))
    return {"Wnx": Ix / (h / 2.0), "hw": hw, "tw": d, "A": A}


def _square_sec(b, t):
    """方矩管截面特性（GB/T 6728）：返回 {name,A_n,W_nx,W_ny,A}。"""
    inner = b - 2 * t
    A = b * b - inner * inner
    I = (b ** 4 - inner ** 4) / 12.0
    W = I / (b / 2.0)
    return {"A_n": A, "W_nx": W, "W_ny": W, "A": A}


def _pipe_sec(D, t):
    """圆管截面特性（GB/T 17395）：返回 {name,A_n,A}。"""
    d = D - 2 * t
    A = math.pi * (D * D - d * d) / 4.0
    return {"A_n": A, "A": A}


# —— 1. 底座横梁截面库：热轧槽钢（C 形）——
_CHANNEL_SPEC = {
    "12#": (120, 53, 5.5, 9.0), "14#": (140, 60, 6.0, 9.5),
    "16#": (160, 65, 8.5, 10.0), "18#": (180, 70, 9.0, 10.5),
    "20#": (200, 75, 9.0, 11.0), "22#": (220, 80, 9.5, 11.5),
    "25#": (250, 82, 11.0, 12.0),
}
BEAM_SECTIONS = [
    dict({"name": name}, **_channel_sec(*spec))
    for name, spec in _CHANNEL_SPEC.items()
]

# —— 2. 墙体立柱截面库：方矩管 ——
_SQUARE_SPEC = [
    (60, 3), (80, 3), (100, 4), (120, 5), (150, 6),
]
COLUMN_SECTIONS = [
    dict({"name": "方管%dx%d" % (b, t)}, **_square_sec(b, t))
    for b, t in _SQUARE_SPEC
]

# —— 3. 屋顶桁架杆件截面库：圆管 ——
_PIPE_SPEC = [
    (48, 3), (60, 3), (76, 3.5), (89, 4), (114, 4),
]
TRUSS_SECTIONS = [
    dict({"name": "圆管%dx%d" % (D, t)}, **_pipe_sec(D, t))
    for D, t in _PIPE_SPEC
]


# ============================================================================
# 三、优化函数
# ============================================================================

def _pick_feasible(feasible):
    """在满足条件的 (截面, 应力比) 列表里选截面积最小者。

    返回 (best_section, best_ratio)，无可行返回 (None, None)。
    """
    if not feasible:
        return None, None
    best_sec, best_ratio = min(feasible, key=lambda sr: sr[0]["A"])
    return best_sec, best_ratio


def optimize_beam(inp, sections):
    """底座横梁（受弯+受剪）强度优化，返回 (最优截面, 最优应力比, 可行列表)。

    应力比 = max( σ/f , τ/fv )
    """
    feasible = []
    for sec in sections:
        # 抗弯：σ = M_x·10^6/(γx·Wnx) —— GB50017 式(6.1.1)，单位 MPa
        sigma = inp.M_x * 1e6 / (inp.gamma_x * sec["Wnx"])
        # 抗剪：τ = V·10^3/(hw·tw) —— GB50017 式(6.1.3) 简化
        tau = inp.V * 1e3 / (sec["hw"] * sec["tw"])
        ratio = max(sigma / inp.f, tau / inp.f_v)
        if ratio <= 1.0:
            feasible.append((sec, ratio))
    best, ratio = _pick_feasible(feasible)
    return best, ratio, feasible


def optimize_column(inp, sections):
    """墙体立柱（压弯）强度优化，返回 (最优截面, 最优应力比, 可行列表)。

    应力比 = [ N·10^3/An + Mx·10^6/(γx·Wnx) + My·10^6/(γy·Wny) ] / f
             —— GB50017 式(8.1.1)
    """
    feasible = []
    for sec in sections:
        sigma = (inp.N * 1e3 / sec["A_n"]
                 + inp.M_x * 1e6 / (inp.gamma_x * sec["W_nx"])
                 + inp.M_y * 1e6 / (inp.gamma_y * sec["W_ny"]))
        ratio = sigma / inp.f
        if ratio <= 1.0:
            feasible.append((sec, ratio))
    best, ratio = _pick_feasible(feasible)
    return best, ratio, feasible


def optimize_truss(inp, sections):
    """屋顶桁架杆件（轴力）强度优化，返回 (最优截面, 最优应力比, 可行列表)。

    应力比 = |N|·10^3/An / f —— GB50017 式(7.1.1)
    """
    feasible = []
    for sec in sections:
        sigma = abs(inp.N) * 1e3 / sec["A_n"]
        ratio = sigma / inp.f
        if ratio <= 1.0:
            feasible.append((sec, ratio))
    best, ratio = _pick_feasible(feasible)
    return best, ratio, feasible


# ============================================================================
# 四、主程序
# ============================================================================

def _report(title, load, sections, opt_result, current_name):
    """打印单个构件优化结果。"""
    best, ratio, feasible = opt_result
    print("\n" + "=" * 62)
    print("  %s" % title)
    print("=" * 62)
    current = max(sections, key=lambda s: s["A"])   # 原方案=库中最大截面（保守）
    print("  原方案(库中最大): %-10s A=%.0f mm^2" % (current["name"], current["A"]))
    if best is None:
        print("  [无可行] 截面库中无任何截面满足强度要求，需扩大截面库。")
        return
    saved = current["A"] - best["A"]
    print("  可行截面数      : %d 个（应力比 <= 1.0）" % len(feasible))
    print("  >> 最优截面     : %-10s A=%.0f mm^2  应力比=%.3f"
          % (best["name"], best["A"], ratio))
    print("  节约截面面积    : %.0f mm^2（%.1f%%）"
          % (saved, saved / current["A"] * 100))


def main():
    """示例内力（Q355B：f=305MPa, fv=175MPa）——请按实际荷载组合替换。"""
    F_Q355 = 305.0
    FV_Q355 = 175.0

    # 1. 底座横梁：M=40kN.m, V=50kN
    _report(
        "[1] 底座底框横梁（槽钢，受弯+受剪）",
        BeamInput(M_x=40.0, V=50.0, f=F_Q355, f_v=FV_Q355),
        BEAM_SECTIONS,
        optimize_beam(BeamInput(M_x=40.0, V=50.0, f=F_Q355, f_v=FV_Q355),
                      BEAM_SECTIONS),
        None,
    )

    # 2. 墙体立柱：N=80kN, Mx=15, My=5
    col_inp = ColumnInput(N=80.0, M_x=15.0, M_y=5.0, f=F_Q355)
    _report(
        "[2] 墙体立柱（方矩管，压弯）",
        col_inp,
        COLUMN_SECTIONS,
        optimize_column(col_inp, COLUMN_SECTIONS),
        None,
    )

    # 3. 屋顶桁架杆件：N=250kN（受压）
    tr_inp = TrussInput(N=250.0, f=F_Q355)
    _report(
        "[3] 屋顶三角桁架杆件（圆管，轴心受力）",
        tr_inp,
        TRUSS_SECTIONS,
        optimize_truss(tr_inp, TRUSS_SECTIONS),
        None,
    )

    print("\n提示：替换 main() 中内力即可对任意工况优化；")
    print("     截面库按需增删（各构件截面库见文件中部）。")


if __name__ == "__main__":
    main()
