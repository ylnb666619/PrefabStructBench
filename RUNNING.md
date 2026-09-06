# 预制舱钢结构力学分析应用 — 运行指引

本项目由「steel_defect 钢材缺陷检测」桌面应用改造而来：
**检测引擎替换为预制舱三大构件的 GB50017 力学验算 + 截面优化**，
保留其 PyQt6-Fluent 多页 GUI + SQLite + FastAPI + 计费外壳。

原钢材缺陷检测代码已整体备份到 `backup_detection/`（可回滚/参考），
新应用**不再需要 torch / ultralytics / opencv**。

## 一、环境（Python 3.12+，建议 conda）

```bash
conda create -n mech python=3.12 -y
conda activate mech
pip install PyQt6 "PyQt6-Fluent-Widgets[full]" fastapi "uvicorn[standard]" numpy pydantic -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 二、启动

```bash
python main.py          # 桌面 GUI
python main.py --api    # GUI + 后台 FastAPI(6006)
```

## 三、界面 6 页

| 页面 | 功能 |
|---|---|
| 仪表盘 | 分析总数 / 不合格数 / 构件类型分布 / 近30日趋势（自动刷新）|
| 构件录入 | 选构件类型 + 填参数 → 运行验算 / 截面优化 → 存库 |
| 场景导入 | 读 `%TEMP%\prefab_substation_ai_last_scene.json`（BIMBase 生成）→ 一键验算整舱 |
| 批量分析 | 多工况批量验算（每行一条 JSON 工况）|
| 数据查看 | 分析记录分页浏览（构件/截面/钢材/应力比/判定）|
| 计费管理 | 用户/余额/Token/分析类型定价/API 记录 |

## 四、首次使用

1. 数据自动建库：`~/SteelDefect/data/database.db`（含 analysis_results 等表）
2. **计费**：若用 API/扣费，先在「计费管理」给分析类型定价
   （`beam / column / truss / optimize`）；未定价时按 0 元免费放行。
3. **场景导入**：需先在 BIMBase（PrefabSubstation-AI 插件）生成变电站并落盘场景，
   再在本应用点「读取 BIMBase 场景」。
4. 力学参数/内力请按实际工况填写（示例为占位值）。

## 五、技术结构（新增/改造）

```
mech/                        力学引擎（纯标准库，可独立运行/自测）
  sections.py / stability.py / steel_sections.py   验算核心+截面库
  section_optimizer.py       截面优化
  analysis_engine.py         验算+优化封装入口（analyze/optimize_component）
  scene_loader.py            读 BIMBase last_scene 提取构件
app/
  main_window.py             主窗口装配（6 页）
  views/analysis_input_view.py   构件录入
  views/analysis_scene_view.py   场景导入
  views/analysis_batch_view.py   批量分析
  views/analysis_dashboard_view.py 仪表盘
  views/analysis_data_view.py    数据查看
  models/analysis_model.py       QThreadPool 后台计算模型
  models/database/base_db.py     内嵌建表（不再依赖缺失的 resources/sql）
  models/database/analysis_dao.py 分析记录 CRUD + 统计
api/fastapi_app.py           /analysis 力学分析 API（token 鉴权 + 计费）
main.py                      入口（GUI / --api）
```

## 六、扩展点

- 新增构件类型：在 `mech/analysis_engine.py` 加分支 + `section_optimizer.py` 加候选
- 新增分析类型定价：计费管理页（表 model_pricing）
- 输出/统计改造：`analysis_dao.py`

## 七、已知说明

- 仪表盘"构件类型"即原"缺陷类型"统计语义（横梁/立柱/桁架）。
- 原 camera/实时摄像头页面已移除（力学分析无视频流需求）。
- GUI 实跑需 PyQt6+qfluentwidgets 环境；引擎与数据层可在无 GUI 环境运行验证：
  `cd mech && python analysis_engine.py`
