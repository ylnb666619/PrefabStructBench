# -*- coding: utf-8 -*-
"""
预制舱式变电站结构强度分析 —— 稳定验算公共函数
================================================

按 GB 50017-2017《钢结构设计标准》提供受压构件的
长细比、稳定系数 φ、欧拉临界力 N'Ex 等计算函数。

主要依据:
    · 附录 D.0.2  轴心受压构件稳定系数 φ 的拟合公式
    · 表 D.0.2    截面类别 a/b/c/d 对应的系数 α1、α2、α3
    · §7.4.1      受压构件容许长细比 [λ]=150，受拉构件 [λ]=350
"""

import math


# ============================================================================
# 钢材基本参数
# ============================================================================
E_STEEL = 206000.0       # 钢材弹性模量 (MPa)
FY_Q235 = 235.0          # Q235 屈服强度 (MPa)
FY_Q355 = 355.0          # Q355 屈服强度 (MPa)

# 受压构件容许长细比（GB50017-2017 §7.4.1）
ALLOWED_LAMBDA_COMPRESSION = 150.0
# 受拉构件容许长细比（直接承受动力荷载的除外）
ALLOWED_LAMBDA_TENSION = 350.0


# ============================================================================
# 截面稳定曲线类别系数（GB50017-2017 表 D.0.2）
# 每类曲线对应 (alpha1, alpha2, alpha3)
# ============================================================================
CURVE_COEFFICIENTS = {
    "a": (0.41, 0.986, 0.152),
    "b": (0.65, 0.965, 0.300),
    "c": (0.73, 0.906, 0.595),
    "d": (1.35, 0.868, 0.915),
}


# ============================================================================
# 计算函数
# ============================================================================

def calc_slenderness(l0: float, i: float) -> float:
    """计算长细比 lambda = l0 / i.

    参数:
        l0: 计算长度 (mm)
        i:  回转半径 (mm)
    返回:
        长细比（无量纲）
    """
    return l0 / i


def calc_radius_of_gyration(I: float, A: float) -> float:
    """由惯性矩 I 和毛截面面积 A 计算回转半径 i = sqrt(I / A).

    参数:
        I: 截面惯性矩 (mm⁴)
        A: 毛截面面积 (mm²)
    返回:
        回转半径 (mm)
    """
    return math.sqrt(I / A)


def calc_phi(lamb: float, fy: float = FY_Q235, curve: str = "b",
             E: float = E_STEEL) -> float:
    """按 GB50017-2017 附录 D.0.2 计算轴心受压构件稳定系数 φ.

    参数:
        lamb:   长细比 lambda
        fy:     钢材屈服强度 (MPa)，Q235=235，Q355=355
        curve:  截面稳定曲线类别，'a' / 'b' / 'c' / 'd'
        E:      钢材弹性模量 (MPa)
    返回:
        稳定系数 φ（0 < φ <= 1）

    公式:
        正则化长细比: lambda_n = (lambda / pi) * sqrt(fy / E)
        当 lambda_n <= 0.215: phi = 1 - alpha1 * lambda_n^2
        当 lambda_n >  0.215:
            phi = [a2 + a3*lambda_n + lambda_n^2
                   - sqrt((a2 + a3*lambda_n + lambda_n^2)^2 - 4*lambda_n^2)]
                  / (2 * lambda_n^2)
    """
    if curve not in CURVE_COEFFICIENTS:
        raise ValueError(f"截面曲线类别必须为 a/b/c/d，当前为: {curve}")
    if lamb <= 0:
        raise ValueError(f"长细比必须为正，当前为: {lamb}")

    alpha1, alpha2, alpha3 = CURVE_COEFFICIENTS[curve]

    # 正则化长细比
    lambda_n = (lamb / math.pi) * math.sqrt(fy / E)

    if lambda_n <= 0.215:
        phi = 1.0 - alpha1 * lambda_n ** 2
    else:
        inner = alpha2 + alpha3 * lambda_n + lambda_n ** 2
        phi = (inner - math.sqrt(inner ** 2 - 4 * lambda_n ** 2)) / (2 * lambda_n ** 2)

    # 数值保护（浮点误差可能使 phi 略超 1.0 或略低于 0）
    return max(0.0, min(1.0, phi))


def calc_euler_force(A: float, lamb: float, E: float = E_STEEL) -> float:
    """计算参数化欧拉临界力 N'Ex = pi^2 * E * A / (1.1 * lambda^2).

    参数:
        A:    毛截面面积 (mm²)
        lamb: 长细比
        E:    钢材弹性模量 (MPa)
    返回:
        欧拉临界力 N'Ex（N）
    """
    return math.pi ** 2 * E * A / (1.1 * lamb ** 2)


def calc_phi_b_channel(b: float, t: float, l1: float, h: float,
                       fy: float = FY_Q235) -> float:
    """轧制槽钢简支梁的整体稳定系数 φb（GB50017-2017 附录 C.2.2）。

    公式:
        phi_b = 570 * b * t / (l1 * h) * (235 / fy)
    当 phi_b > 0.6 时需修正:
        phi_b' = 1.07 - 0.282 / phi_b

    参数:
        b:  翼缘宽度 (mm)
        t:  翼缘平均厚度 (mm)
        l1: 梁侧向支承点间距 (mm)
        h:  槽钢截面高度 (mm)
        fy: 钢材屈服强度 (MPa)
    返回:
        受弯构件整体稳定系数 φb（0 < φb <= 1）
    """
    phi_b = 570.0 * b * t / (l1 * h) * 235.0 / fy

    # φb > 0.6 时按公式修正（φb 不应大于 1.0）
    if phi_b > 0.6:
        phi_b = 1.07 - 0.282 / phi_b

    return max(0.0, min(1.0, phi_b))


# ============================================================================
# 自测：与规范常用数值核对
# ============================================================================

if __name__ == "__main__":
    # Q235 b 类截面，lambda=100 时规范查表 phi≈0.555
    print(f"Q235 b类 λ=100: phi = {calc_phi(100.0, FY_Q235, 'b'):.3f}  (规范≈0.555)")
    # Q235 b 类截面，lambda=50 时规范查表 phi≈0.856
    print(f"Q235 b类 λ=50 : phi = {calc_phi(50.0, FY_Q235, 'b'):.3f}  (规范≈0.856)")
    # 回转半径
    print(f"i = sqrt(1000/100) = {calc_radius_of_gyration(1000.0, 100.0):.2f} mm")
    # 槽钢16a 6m跨 Q355 整体稳定系数
    print(f"槽钢16a l1=6000 Q355: phi_b = "
          f"{calc_phi_b_channel(63.0, 10.0, 6000.0, 160.0, FY_Q355):.3f}")
