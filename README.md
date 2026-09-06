# 预制舱钢结构力学分析

基于 **GB 50017-2017** 的预制舱式变电站三大构件（底座底框横梁 / 墙体立柱 /
屋顶三角桁架杆件）强度验算、稳定验算与截面优化的**桌面应用**。

- 界面：PyQt6-Fluent 多页桌面端
- 引擎：纯 Python（无 torch / ultralytics 等重依赖）
- 存储：SQLite（分析记录 / 用户计费）
- API：FastAPI（可选，`/analysis` 验算，token 鉴权 + 计费）

> 本项目为力学分析**外壳**，原「钢材缺陷检测」业务已移除并另行备份，与本仓库无关。

## 功能

| 页面 | 说明 |
|---|---|
| 仪表盘 | 分析总数 / 不合格数 / 构件类型分布 / 近 30 日趋势 |
| 构件录入 | 选构件类型 → 填参数（内力/截面/钢材）→ 运行验算 / 截面优化，一键载入真实构件 |
| 场景导入 | 读取 BIMBase 生成的 `last_scene.json` → 一键验算整舱 |
| 批量分析 | 多工况批量验算（每行 JSON 工况）|
| 数据查看 | 分析记录分页浏览 |
| 计费管理 | 用户 / 余额 / 分析类型定价 / API 记录 |

快捷键：`Ctrl+T` 切换深/浅主题。

## 三大构件（GB 50017-2017）

| 构件 | 截面 | 验算 |
|---|---|---|
| 底座底框横梁 | 槽钢 22#（h220 b80 d9.5 t11.5）| 抗弯 式6.1.1、抗剪 式6.1.3、整体稳定 |
| 墙体立柱 | 方矩管 100×100×4 | 压弯 式8.1.1、平面内/外稳定、长细比 |
| 屋顶桁架杆件 | 150×100 | 轴心受力 式7.1.1、轴压稳定 |

钢材：Q355B / Q235B 可选。单位：力 kN、弯矩 kN·m、应力 MPa。

## 环境与运行

需要 **Python 3.11+**：

```bash
pip install PyQt6 "PyQt6-Fluent-Widgets[full]" fastapi "uvicorn[standard]" numpy pydantic
python main.py          # 桌面 GUI
python main.py --api    # 同时启动 FastAPI :6006
```

数据自动建库于 `~/SteelDefect/data/database.db`。

## 目录

```
main.py                 入口（GUI / --api）
mech/                   力学引擎（纯标准库，可独立运行）
  analysis_engine.py    验算 + 优化统一入口
  scene_loader.py       BIMBase last_scene.json 构件提取
  sections / stability / steel_sections / section_optimizer
app/                    桌面端（6 页 MVC + 数据层）
  views/                analysis_input / scene / batch / dashboard / data + billing
  models/analysis_model.py + database/（analysis_dao / base_db / billing / user）
api/fastapi_app.py      /analysis 力学验算 API
```

## 命令行自测（无需 GUI）

```bash
cd mech && python analysis_engine.py        # 三构件验算+优化自测
```

## 免责声明

本项目用于结构校核参考与教学演示。正式工程设计请由具备资质的专业人员进行，
内力按实际荷载组合（GB 50009）取用后校核。

## 许可

[MIT](LICENSE)
