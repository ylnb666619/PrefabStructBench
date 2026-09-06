# -*- coding: utf-8 -*-
"""
钢材截面特性模块 —— 按真实建模参数计算 A、i、I、W
====================================================

来源: 预制舱变电站三大构件的 BIMBase 参数化建模脚本
    · 槽钢底座.py            → 槽钢 22#（h=220, b=80, d=9.5, t=11.5）
    · 预制舱空心方矩管立柱.py  → 方矩管 100×100×4
    · 预制舱屋面龙骨.py        → 屋顶桁架杆件 150×100（脚本实心矩形建模）

支持截面函数:
    · circular_hollow_properties   圆管
    · square_hollow_properties     方矩管
    · rectangle_properties         实心矩形
    · channel_properties           C 形槽钢（解析计算）

单位:
    尺寸 mm，面积 A mm²，惯性矩 I mm⁴，抵抗矩 W mm³，回转半径 i mm
"""

import math


# ============================================================================
# 圆管截面特性
# ============================================================================

def circular_hollow_properties(D: float, t: float) -> dict:
    """圆管截面特性（外径 D，壁厚 t）。"""
    d = D - 2 * t
    A = math.pi * (D ** 2 - d ** 2) / 4.0
    I = math.pi * (D ** 4 - d ** 4) / 64.0
    i = math.sqrt(I / A)
    W = I / (D / 2.0)
    return {"A": A, "I": I, "i": i, "W": W}


# ============================================================================
# 方矩管截面特性
# ============================================================================

def square_hollow_properties(b: float, t: float) -> dict:
    """方矩管截面特性（外边 b×b，壁厚 t）。"""
    inner = b - 2 * t
    A = b ** 2 - inner ** 2
    I = (b ** 4 - inner ** 4) / 12.0
    i = math.sqrt(I / A)
    W = I / (b / 2.0)
    return {"A": A, "I": I, "i": i, "W": W}


# ============================================================================
# 实心矩形截面特性
# ============================================================================

def rectangle_properties(width: float, height: float) -> dict:
    """实心矩形截面特性（宽 width，高 height）。

    返回含两个方向的特性: Ix/ix/Wx 关于 X 轴，Iy/iy/Wy 关于 Y 轴。
    """
    A = width * height
    Ix = width * height ** 3 / 12.0      # 关于 X 轴（水平轴）
    Iy = height * width ** 3 / 12.0      # 关于 Y 轴（竖轴）
    ix = math.sqrt(Ix / A)
    iy = math.sqrt(Iy / A)
    Wx = Ix / (height / 2.0)
    Wy = Iy / (width / 2.0)
    return {"A": A, "Ix": Ix, "Wx": Wx, "ix": ix,
            "Iy": Iy, "Wy": Wy, "iy": iy}


# ============================================================================
# C 形槽钢截面特性（解析计算）
# ============================================================================

def channel_properties(h: float, b: float, d: float, t: float) -> dict:
    """C 形槽钢截面特性（按板件解析计算，忽略圆角）。

    参数:
        h: 截面高度 (mm)
        b: 翼缘宽度，自腹板外缘算起 (mm)
        d: 腹板厚度 (mm)
        t: 翼缘厚度 (mm)
    返回:
        dict: A, Ix, Wx, ix, Iy, Wy, iy, z0
    """
    h_web = h - 2 * t                      # 腹板净高
    A_w = d * h_web                        # 腹板面积
    A_f = b * t                            # 单块翼缘面积
    A = A_w + 2 * A_f                      # 总面积

    # 形心距腹板外边缘 z0
    z0 = (A_w * (d / 2.0) + 2 * A_f * (b / 2.0)) / A

    # 强轴（水平对称轴）惯性矩 Ix
    Ix_web = d * h_web ** 3 / 12.0
    Ix_flange = b * t ** 3 / 12.0 + A_f * ((h - t) / 2.0) ** 2
    Ix = Ix_web + 2 * Ix_flange

    # 弱轴（过形心竖轴）惯性矩 Iy
    Iy_web = h_web * d ** 3 / 12.0 + A_w * (d / 2.0 - z0) ** 2
    Iy_flange = t * b ** 3 / 12.0 + A_f * (b / 2.0 - z0) ** 2
    Iy = Iy_web + 2 * Iy_flange

    Wx = Ix / (h / 2.0)
    Wy = Iy / (b - z0)                     # 翼缘最外缘距形心

    ix = math.sqrt(Ix / A)
    iy = math.sqrt(Iy / A)
    return {"A": A, "Ix": Ix, "Wx": Wx, "ix": ix,
            "Iy": Iy, "Wy": Wy, "iy": iy, "z0": z0}


# ============================================================================
# 三大构件的截面实例（按真实建模参数）
# ============================================================================

# 1. 底座底框横梁 —— 槽钢 22#（用户建模脚本规格）
#    脚本规格表: "22#": (220, 80, 9.5, 11.5)  → (h, b, d, t)
CHANNEL_22A = channel_properties(220.0, 80.0, 9.5, 11.5)

# 2. 墙体立柱 —— 方矩管 100×100×4（预制舱空心方矩管立柱.py）
SQUARE_100X4 = square_hollow_properties(100.0, 4.0)

# 3. 屋顶三角桁架杆件 —— 150×100（预制舱屋面龙骨.py，实心矩形建模）
RECT_150X100 = rectangle_properties(150.0, 100.0)


# ============================================================================
# 槽钢型号规格表（GB/T 706，来自 槽钢底座.py 建模脚本）
# 型号 → (h, b, d, t)
# ============================================================================
CHANNEL_GRADE_TABLE = {
    "10#": (100.0, 48.0, 5.3, 8.5),
    "12#": (120.0, 53.0, 5.5, 9.0),
    "14#": (140.0, 60.0, 6.0, 9.5),
    "16#": (160.0, 65.0, 8.5, 10.0),
    "18#": (180.0, 70.0, 9.0, 10.5),
    "20#": (200.0, 75.0, 9.0, 11.0),
    "22#": (220.0, 80.0, 9.5, 11.5),
    "25#": (250.0, 82.0, 11.0, 12.0),
}


def channel_by_grade(grade):
    """按槽钢型号（如 '20#'、'22#'）计算截面特性。

    返回 dict: A, Ix, Wx, ix, Iy, Wy, iy, z0
    """
    key = str(grade).strip()
    if key not in CHANNEL_GRADE_TABLE:
        raise ValueError(
            "槽钢型号仅支持 %s，当前为: %s" % ("/".join(CHANNEL_GRADE_TABLE), grade)
        )
    h, b, d, t = CHANNEL_GRADE_TABLE[key]
    return channel_properties(h, b, d, t)


def square_by_size(width, thickness):
    """按方矩管外边尺寸与壁厚计算截面特性（用于任意立柱截面）。

    返回 dict: A, I, i, W
    """
    return square_hollow_properties(float(width), float(thickness))


# ============================================================================
# 自测
# ============================================================================

if __name__ == "__main__":
    c = CHANNEL_22A
    print("槽钢22#: A={A:.0f}, Ix={Ix:.0f}, Wx={Wx:.0f}, ix={ix:.1f}, "
          "Iy={Iy:.0f}, iy={iy:.1f}, z0={z0:.1f}".format(**c))
    s = SQUARE_100X4
    print("方管100x100x4: A={A:.0f}, I={I:.0f}, i={i:.1f}, W={W:.0f}".format(**s))
    r = RECT_150X100
    print("矩形150x100: A={A:.0f}, Ix={Ix:.0f}, ix={ix:.1f}, Iy={Iy:.0f}, iy={iy:.1f}".format(**r))
