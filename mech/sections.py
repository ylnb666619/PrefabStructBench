# -*- coding: utf-8 -*-
"""
预制舱式变电站结构强度分析 —— 构件参数定义
============================================

本模块定义三大构件的「内力 + 截面 + 材料」参数类，
包含强度验算 check_strength() 与稳定性验算 check_stability()，
支持运行时切换钢材牌号（Q235B / Q355B）。

规范依据: GB 50017-2017《钢结构设计标准》

构件与截面（按真实 BIMBase 建模参数）:
    1. BaseBeam        底座底框横梁      槽钢 22#（h=220,b=80,d=9.5,t=11.5）
    2. WallColumn      墙体立柱          方矩管 100×100×4
    3. RoofTrussMember 屋顶三角桁架杆件   150×100（屋面龙骨实心矩形建模）

计算长度（按建模尺寸）:
    · 底座横梁       底座总长 4000mm，两端铰接，侧向支承点间距 l1=4000
    · 墙体立柱       高 2850mm，两端刚接，l0x=l0y=0.5×2850=1425
    · 桁架杆件       三角桁架斜杆，屋宽3500/起坡500，l0≈1820mm，两端铰接

单位约定:
    力: kN，弯矩: kN·m，面积: mm²，惯性矩: mm⁴，
    抵抗矩: mm³，回转半径: mm，应力: MPa
"""

from dataclasses import dataclass

from stability import (
    calc_slenderness,
    calc_phi,
    calc_euler_force,
    calc_phi_b_channel,
    E_STEEL,
    FY_Q235,
    FY_Q355,
    ALLOWED_LAMBDA_COMPRESSION,
)
from steel_sections import (
    CHANNEL_22A,     # 底座横梁 槽钢 22#
    SQUARE_100X4,    # 墙体立柱 方矩管 100×100×4
    RECT_150X100,    # 屋顶桁架杆件 150×100
)


# ============================================================================
# 钢材强度设计值（MPa）—— 按 GB 50017-2017 表 4.4.1（厚度 ≤ 16mm）
# ============================================================================
STEEL_F_Q235 = 215.0       # Q235 抗弯 / 抗拉 / 抗压强度设计值 f
STEEL_FV_Q235 = 125.0      # Q235 抗剪强度设计值 fv
STEEL_F_Q355 = 305.0       # Q355 抗弯 / 抗拉 / 抗压强度设计值 f
STEEL_FV_Q355 = 175.0      # Q355 抗剪强度设计值 fv


def get_steel_strength(grade: str = "Q355B") -> tuple:
    """按钢材牌号返回 (f, fv, fy)。支持 'Q235B' / 'Q355B'。"""
    g = str(grade).upper()
    if g in ("Q235", "Q235B"):
        return STEEL_F_Q235, STEEL_FV_Q235, FY_Q235
    if g in ("Q355", "Q355B"):
        return STEEL_F_Q355, STEEL_FV_Q355, FY_Q355
    raise ValueError("钢材牌号仅支持 Q235B 或 Q355B: {0}".format(grade))


def set_steel(component, grade: str):
    """为构件实例切换钢材牌号（更新 f / fv / fy 强度设计值）。"""
    f, fv, fy = get_steel_strength(grade)
    component.f = f
    component.fy = fy
    if hasattr(component, "f_v"):
        component.f_v = fv
    return component


# ============================================================================
# 类 1：底座底框横梁 —— 槽钢 22#，Q355B
# ============================================================================

@dataclass
class BaseBeam:
    """底座底框横梁 —— 强度 + 整体稳定验算所需参数。

    截面: 槽钢 22#（h=220, b=80, d=9.5, t=11.5）
          A=3711.5mm², Ix=26.07e6mm⁴, Wx=237001mm³, ix=83.8mm
    钢材: 默认 Q355B（可 set_steel 切换）
    """

    # ---- 内力设计值（占位值，请替换为实际荷载组合结果）----
    M_x: float = 0.0        # 绕X轴（强轴）弯矩设计值 (kN·m)
    V: float = 0.0          # 剪力设计值 (kN)

    # ---- 截面参数（槽钢 22#）----
    gamma_x: float = 1.05                                # 截面塑性发展系数
    W_nx: float = CHANNEL_22A["Wx"]                      # 净截面抵抗矩 237001mm³
    h_w: float = 220.0 - 2 * 11.5                        # 腹板计算高度 197mm
    t_w: float = 9.5                                     # 腹板厚度 (mm)

    # ---- 整体稳定验算参数 ----
    A: float = CHANNEL_22A["A"]        # 截面面积 3711.5mm²
    I_x: float = CHANNEL_22A["Ix"]     # 绕X轴惯性矩 26070100mm⁴
    W_x: float = CHANNEL_22A["Wx"]     # 绕X轴毛截面抵抗矩 237001mm³
    i_x: float = CHANNEL_22A["ix"]     # 绕X轴回转半径 83.8mm
    l1: float = 4000.0                 # 侧向支承点间距 4000mm（底座总长）
    fy: float = FY_Q355                # 屈服强度 (MPa)
    E: float = E_STEEL                 # 弹性模量 (MPa)

    # ---- 材料强度设计值（默认 Q355B）----
    f: float = STEEL_F_Q355       # 抗弯强度设计值 (MPa)
    f_v: float = STEEL_FV_Q355    # 抗剪强度设计值 (MPa)

    def check_strength(self) -> tuple:
        """底座底框横梁强度验算（抗弯 + 抗剪）。

        计算公式:
            · 正应力: sigma = M_x * 10^6 / (gamma_x * W_nx)
            · 剪应力: tau   = V * 10^3 / (h_w * t_w)
        判定: sigma / f <= 1.0 且 tau / f_v <= 1.0 为合格。

        返回: (正应力比, 剪应力比)
        """
        sigma = self.M_x * 10 ** 6 / (self.gamma_x * self.W_nx)
        tau = self.V * 10 ** 3 / (self.h_w * self.t_w)

        ratio_sigma = sigma / self.f
        ratio_tau = tau / self.f_v

        print(f"  正应力 sigma = Mx*10^6/(gx*Wnx) = {sigma:.2f} MPa，"
              f"应力比 sigma/f = {ratio_sigma:.3f}，"
              f"{'合格' if ratio_sigma <= 1.0 else '不合格'}")
        print(f"  剪应力 tau   = V*10^3/(hw*tw)   = {tau:.2f} MPa，"
              f"应力比 tau/fv  = {ratio_tau:.3f}，"
              f"{'合格' if ratio_tau <= 1.0 else '不合格'}")

        return ratio_sigma, ratio_tau

    def check_stability(self) -> float:
        """底座底框横梁整体稳定验算（受弯构件，GB50017-2017 §6.2）。

        计算公式（轧制槽钢简支梁，附录 C.2.2）:
            · phi_b = 570 * b * t / (l1 * h) * 235 / fy
            · 整体稳定应力: sigma = M_x * 10^6 / (phi_b * W_x)
        判定: sigma / f <= 1.0 为合格。

        返回: 整体稳定应力比
        """
        b = 80.0    # 翼缘宽度 (mm)
        t = 11.5    # 翼缘平均厚度 (mm)
        h = 220.0   # 槽钢高度 (mm)

        phi_b = calc_phi_b_channel(b, t, self.l1, h, self.fy)

        sigma = self.M_x * 10 ** 6 / (phi_b * self.W_x)
        ratio = sigma / self.f

        print(f"  整体稳定系数 phi_b = {phi_b:.3f}")
        print(f"  稳定应力 sigma = Mx/(phi_b·Wx) = {sigma:.2f} MPa，"
              f"应力比 = {ratio:.3f}，"
              f"{'合格' if ratio <= 1.0 else '不合格'}")

        return ratio


# ============================================================================
# 类 2：墙体立柱 —— 方矩管 100×100×4，Q355B
# ============================================================================

@dataclass
class WallColumn:
    """墙体立柱 —— 压弯（双向弯矩）构件强度 + 稳定验算所需参数。

    截面: 方矩管 100×100×4（A=1536mm², I=2363392mm⁴, i=39.2mm, W=47268mm³）
    钢材: 默认 Q355B（可 set_steel 切换）
    计算长度: 高2850mm，两端刚接，l0x=l0y=1425mm
    """

    # ---- 内力设计值（占位值，请替换）----
    N: float = 0.0          # 轴力设计值 (kN)，受压为正、受拉为负
    M_x: float = 0.0        # 绕X轴弯矩设计值 (kN·m)
    M_y: float = 0.0        # 绕Y轴弯矩设计值 (kN·m)

    # ---- 截面参数（方矩管 100×100×4，x/y 对称）----
    A_n: float = SQUARE_100X4["A"]    # 净截面面积 1536mm²
    gamma_x: float = 1.05             # X轴截面塑性发展系数
    gamma_y: float = 1.05             # Y轴截面塑性发展系数
    W_nx: float = SQUARE_100X4["W"]   # X轴净截面抵抗矩 47268mm³
    W_ny: float = SQUARE_100X4["W"]   # Y轴净截面抵抗矩 47268mm³

    # ---- 稳定性验算所需参数 ----
    A: float = SQUARE_100X4["A"]      # 毛截面面积 1536mm²
    I_x: float = SQUARE_100X4["I"]    # 绕X轴惯性矩 2363392mm⁴
    I_y: float = SQUARE_100X4["I"]    # 绕Y轴惯性矩 2363392mm⁴
    i_x: float = SQUARE_100X4["i"]    # 绕X轴回转半径 39.2mm
    i_y: float = SQUARE_100X4["i"]    # 绕Y轴回转半径 39.2mm
    l0x: float = 1425.0               # 平面内计算长度 1425mm（0.5×2850 两端刚接）
    l0y: float = 1425.0               # 平面外计算长度 1425mm（檩条支撑）
    W1x: float = SQUARE_100X4["W"]    # 弯矩作用平面内毛截面模量 47268mm³
    fy: float = FY_Q355               # 屈服强度 (MPa)
    E: float = E_STEEL                # 弹性模量 (MPa)
    curve_x: str = "b"                # 绕X轴稳定曲线类别（箱形截面取 b）
    curve_y: str = "b"                # 绕Y轴稳定曲线类别（箱形截面取 b）
    beta_mx: float = 1.0              # 平面内等效弯矩系数（保守取 1.0）
    beta_tx: float = 1.0              # 平面外等效弯矩系数（保守取 1.0）
    phi_b: float = 1.0                # 受弯整体稳定系数（闭口箱形截面取 1.0）
    eta: float = 1.0                  # 截面影响系数（保守取 1.0）
    allowed_lambda: float = ALLOWED_LAMBDA_COMPRESSION  # 容许长细比 150

    # ---- 材料强度设计值（默认 Q355B）----
    f: float = STEEL_F_Q355       # 抗弯 / 抗压强度设计值 (MPa)

    def check_strength(self) -> float:
        """墙体立柱强度验算（压弯构件）。"""
        sigma = (self.N * 10 ** 3 / self.A_n
                 + self.M_x * 10 ** 6 / (self.gamma_x * self.W_nx)
                 + self.M_y * 10 ** 6 / (self.gamma_y * self.W_ny))

        ratio = sigma / self.f

        print(f"  组合正应力 sigma = N*10^3/An + Mx*10^6/(gx*Wnx) + My*10^6/(gy*Wny)"
              f" = {sigma:.2f} MPa，"
              f"应力比 sigma/f = {ratio:.3f}，"
              f"{'合格' if ratio <= 1.0 else '不合格'}")

        return ratio

    def check_stability(self) -> tuple:
        """墙体立柱整体稳定验算（压弯构件，GB50017-2017 §8.2.1）。

        计算公式:
            · 长细比: lambda_x = l0x / i_x，lambda_y = l0y / i_y
            · 平面内稳定（绕X轴失稳）:
              sigma = N/(phi_x·A) + beta_mx·Mx·10^6/[gamma_x·W1x·(1-0.8·N/N'Ex)]
            · 平面外稳定（绕Y轴失稳）:
              sigma = N/(phi_y·A) + eta·beta_tx·Mx·10^6/(phi_b·W1x)
        返回: (平面内应力比, 平面外应力比)
        """
        N_force = self.N * 10 ** 3            # kN -> N

        # ---- 平面内稳定（绕X轴）----
        lamb_x = calc_slenderness(self.l0x, self.i_x)
        phi_x = calc_phi(lamb_x, self.fy, self.curve_x, self.E)
        N_Ex = calc_euler_force(self.A, lamb_x, self.E)

        sigma_in = (N_force / (phi_x * self.A)
                    + self.beta_mx * self.M_x * 10 ** 6
                    / (self.gamma_x * self.W1x * (1 - 0.8 * N_force / N_Ex)))
        ratio_in = sigma_in / self.f

        # ---- 平面外稳定（绕Y轴）----
        lamb_y = calc_slenderness(self.l0y, self.i_y)
        phi_y = calc_phi(lamb_y, self.fy, self.curve_y, self.E)

        sigma_out = (N_force / (phi_y * self.A)
                     + self.eta * self.beta_tx * self.M_x * 10 ** 6
                     / (self.phi_b * self.W1x))
        ratio_out = sigma_out / self.f

        ok_lambda = lamb_x <= self.allowed_lambda and lamb_y <= self.allowed_lambda

        print(f"  长细比 lambda_x = l0x/ix = {lamb_x:.1f}，"
              f"lambda_y = l0y/iy = {lamb_y:.1f}"
              f"（容许 [{self.allowed_lambda:.0f}]，"
              f"{'满足' if ok_lambda else '不满足'}）")
        print(f"  稳定系数 phi_x = {phi_x:.3f}，phi_y = {phi_y:.3f}")
        print(f"  平面内稳定应力 sigma = {sigma_in:.2f} MPa，"
              f"应力比 = {ratio_in:.3f}，"
              f"{'合格' if ratio_in <= 1.0 else '不合格'}")
        print(f"  平面外稳定应力 sigma = {sigma_out:.2f} MPa，"
              f"应力比 = {ratio_out:.3f}，"
              f"{'合格' if ratio_out <= 1.0 else '不合格'}")

        return ratio_in, ratio_out


# ============================================================================
# 类 3：屋顶三角桁架杆件 —— 150×100，Q355B
# ============================================================================

@dataclass
class RoofTrussMember:
    """屋顶三角桁架杆件 —— 轴心受力构件强度 + 稳定验算所需参数。

    截面: 150×100（屋面龙骨脚本实心矩形建模）
          A=15000mm², Ix=12.5e6mm⁴, ix=28.9mm, Wx=250000mm³
    钢材: 默认 Q355B（可 set_steel 切换）
    计算长度: 三角桁架斜杆 l0≈1820mm（屋宽3500/2=1750，起坡500），两端铰接
    """

    # ---- 内力设计值（占位值，请替换）----
    N: float = 0.0          # 轴向拉力或压力设计值 (kN)，受拉为正、受压为负
                            # （验算时内部自动取绝对值）

    # ---- 截面参数（矩形 150×100）----
    A_n: float = RECT_150X100["A"]    # 净截面面积 15000mm²

    # ---- 稳定性验算所需参数 ----
    A: float = RECT_150X100["A"]      # 毛截面面积 15000mm²
    I: float = RECT_150X100["Ix"]     # 惯性矩（绕弱轴）12.5e6mm⁴
    i: float = RECT_150X100["ix"]     # 回转半径（取较小值）28.9mm
    W: float = RECT_150X100["Wx"]     # 截面抵抗矩 250000mm³
    l0: float = 1820.0                # 计算长度 (mm)，桁架斜杆两端铰接
    fy: float = FY_Q355               # 屈服强度 (MPa)
    E: float = E_STEEL                # 弹性模量 (MPa)
    curve_type: str = "b"             # 截面稳定曲线类别（矩形取 b）
    allowed_lambda: float = ALLOWED_LAMBDA_COMPRESSION  # 容许长细比 150

    # ---- 材料强度设计值（默认 Q355B）----
    f: float = STEEL_F_Q355       # 抗拉 / 抗压强度设计值 (MPa)

    def check_strength(self) -> float:
        """屋顶三角桁架杆件强度验算（轴心受力构件）。"""
        sigma = abs(self.N) * 10 ** 3 / self.A_n
        ratio = sigma / self.f

        print(f"  正应力 sigma = N*10^3/An = {sigma:.2f} MPa，"
              f"应力比 sigma/f = {ratio:.3f}，"
              f"{'合格' if ratio <= 1.0 else '不合格'}")

        return ratio

    def check_stability(self) -> float:
        """屋顶三角桁架杆件整体稳定验算（轴心受压，GB50017-2017 §7.2）。"""
        lamb = calc_slenderness(self.l0, self.i)
        phi = calc_phi(lamb, self.fy, self.curve_type, self.E)

        sigma = abs(self.N) * 10 ** 3 / (phi * self.A)
        ratio = sigma / self.f

        ok_lambda = lamb <= self.allowed_lambda

        print(f"  长细比 lambda = l0/i = {lamb:.1f}"
              f"（容许 [{self.allowed_lambda:.0f}]，"
              f"{'满足' if ok_lambda else '不满足'}）")
        print(f"  稳定系数 phi = {phi:.3f}（截面类别 {self.curve_type}）")
        print(f"  稳定应力 sigma = |N|/(phi·A) = {sigma:.2f} MPa，"
              f"应力比 = {ratio:.3f}，"
              f"{'合格' if ratio <= 1.0 else '不合格'}")

        return ratio


# ============================================================================
# 示例用法
# ============================================================================

if __name__ == "__main__":
    beam = BaseBeam(M_x=6.0, V=10.0)
    print("【底座底框横梁】A={:.0f} Ix={:.0f} Wx={:.0f} ix={:.1f}".format(
        beam.A, beam.I_x, beam.W_x, beam.i_x))
    column = WallColumn(N=120.0, M_x=18.0, M_y=6.0)
    print("【墙体立柱】A={:.0f} I={:.0f} i={:.1f} W={:.0f}".format(
        column.A, column.I_x, column.i_x, column.W1x))
    truss = RoofTrussMember(N=88.0)
    print("【屋顶桁架杆件】A={:.0f} I={:.0f} i={:.1f} W={:.0f}".format(
        truss.A, truss.I, truss.i, truss.W))
