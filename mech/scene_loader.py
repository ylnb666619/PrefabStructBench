# -*- coding: utf-8 -*-
"""
mech/scene_loader —— 读取 BIMBase PrefabSubstation-AI 生成的场景，提取结构构件
=====================================================================
场景文件：%TEMP%/prefab_substation_ai_last_scene.json（由 BIMBase 插件落盘）。
把其中的槽钢底座/方矩管立柱/屋面龙骨 → 统一的 {kind, name, params, steel}，
可直接喂给 analysis_engine.analyze_component。
"""
from __future__ import print_function

import json
import math
import os

LAST_SCENE = os.path.join(os.environ.get("TEMP", os.getcwd()),
                          "prefab_substation_ai_last_scene.json")

# component_ref → kind
_REF_KIND = {
    "biandianshebei_dizuo": "beam",
    "feishebeiqu_dizuo": "beam",
    "channel_steel_base_figure1": "beam",
    "hollow_square_column": "column",
    "yuzhicang_wumian_longgu": "truss",
}
_KIND_NAME = {"beam": "底座底框横梁", "column": "墙体立柱", "truss": "屋顶桁架杆件"}


def load_last_scene(scene=None, path=None):
    """读场景：优先用传入的 scene dict；其次指定 path；否则默认路径。"""
    if scene is not None:
        return scene
    target = path or LAST_SCENE
    try:
        if os.path.exists(target):
            with open(target, encoding="utf-8-sig") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def extract_components(scene=None):
    """从场景提取结构构件 → list[ {kind,name,params,steel} ]。"""
    scene = load_last_scene(scene)
    objs = scene.get("objects") if isinstance(scene, dict) else []
    result = []
    for o in objs:
        ref = o.get("component_ref")
        kind = _REF_KIND.get(str(ref or ""))
        if not kind:
            continue
        p = (o.get("params") or {}) if isinstance(o, dict) else {}
        steel = str(p.get("钢材型号") or "Q355B")
        entry = {"kind": kind, "name": _KIND_NAME[kind], "steel": steel, "note": str(ref)}
        if kind == "beam":
            grade = str(p.get("外层槽钢型号") or p.get("槽钢型号") or "22#")
            span = float(p.get("总长X") or p.get("X总宽") or 4000.0)
            entry["params"] = {"grade": grade, "span": span}
        elif kind == "column":
            entry["params"] = {
                "width": float(p.get("外截面宽") or 100.0),
                "thick": float(p.get("壁厚") or 4.0),
                "height": float(p.get("高度") or 2850.0),
            }
        else:  # truss
            w = float(p.get("整体宽度") or 3500.0)
            rise = float(p.get("起坡高度") or 500.0)
            entry["params"] = {
                "l0": math.sqrt((w / 2.0) ** 2 + rise ** 2),
                "sec": str(p.get("截面类型") or "C型钢"),
                "dia": float(p.get("主杆管径") or 89.0),
            }
        result.append(entry)
    return result


if __name__ == "__main__":
    # 自测：注入一个模拟场景
    demo = {"objects": [
        {"id": "b", "component_ref": "feishebeiqu_dizuo",
         "params": {"外层槽钢型号": "22#", "总长X": 4000.0}},
        {"id": "c", "component_ref": "hollow_square_column",
         "params": {"外截面宽": 100.0, "壁厚": 4.0, "高度": 2850.0, "钢材型号": "Q355B"}},
        {"id": "r", "component_ref": "yuzhicang_wumian_longgu",
         "params": {"整体宽度": 3500.0, "起坡高度": 500.0}},
    ]}
    comps = extract_components(demo)
    print("提取构件 %d 个:" % len(comps))
    for c in comps:
        print(" ", c["kind"], c["name"], c["params"], c["steel"])
    # 场景文件存在则读取真实场景
    real = load_last_scene()
    if real:
        real_comps = extract_components(real)
        print("\n真实场景构件 %d 个:" % len(real_comps))
    else:
        print("\n(本机无真实场景文件)")
