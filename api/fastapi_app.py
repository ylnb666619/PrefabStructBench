# -*- coding: utf-8 -*-
"""
api/fastapi_app.py —— 力学分析 API（改造自 steel_defect，去掉图片缺陷检测）
端点：
  GET  /health
  GET  /analysis_results            分页查询分析记录
  GET  /analysis_results/{id}       按 id 查询
  POST /analysis                    提交构件参数做力学验算（token 鉴权 + 计费）
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional, Dict

from app.models.database.user_dao import UserDAO
from app.models.database.billing_dao import BillingDAO
from app.models.database.analysis_dao import AnalysisDAO

# 工程根入 path（mech）
import sys as _sys
_ROOT2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT2 not in _sys.path:
    _sys.path.insert(0, _ROOT2)

app = FastAPI(title="预制舱钢结构力学分析 API", version="1.0")

user_dao = UserDAO()
billing_dao = BillingDAO()
analysis_dao = AnalysisDAO()

ANALYSIS_TYPES = {"beam", "column", "truss", "optimize"}
KIND_CN = {"beam": "底座底框横梁", "column": "墙体立柱", "truss": "屋顶桁架杆件",
           "optimize": "截面优化"}


def _auth_token(authorization: str):
    if not authorization:
        raise HTTPException(401, "Missing authorization header")
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    user = user_dao.get_user_by_token(token)
    if not user:
        raise HTTPException(401, "Invalid token")
    return user


@app.get("/")
async def root():
    return {"service": "prefab_mechanics_analysis", "status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/analysis_results")
async def get_results(page: int = Query(1, ge=1), page_size: int = Query(10, ge=1, le=100)):
    rows, total = analysis_dao.fetch_all(page=page, page_size=page_size)
    return {"total": total, "page": page, "page_size": page_size, "data": rows}


@app.get("/analysis_results/{analysis_id}")
async def get_result_by_id(analysis_id: int):
    row = analysis_dao.get_by_id(analysis_id)
    if not row:
        raise HTTPException(404, "analysis record not found")
    return row


class AnalysisBody(BaseModel):
    model_type: str                       # beam/column/truss/optimize
    steel: str = "Q355B"
    params: Dict[str, float] = {}         # Mx/V/N/grade 等
    count: int = 1


@app.post("/analysis")
async def analysis_request(body: AnalysisBody,
                           authorization: str = Header(default=None)):
    user = _auth_token(authorization)
    mtype = body.model_type.lower()
    if mtype not in ANALYSIS_TYPES:
        raise HTTPException(400, "Unknown model_type: %s" % mtype)

    # 定价与计费
    price = billing_dao.get_model_price(mtype)
    if price is None:
        price = 0.0
    total_cost = price * body.count
    if user["balance"] < total_cost:
        raise HTTPException(402,
            "Insufficient balance. Current: %s, Required: %s" % (user["balance"], total_cost))

    balance_deducted = False
    try:
        from mech.analysis_engine import analyze_component, optimize_component
        result = None
        if mtype == "optimize":
            result = optimize_component(body.params.get("kind", "beam"),
                                        body.params, body.steel)
        else:
            result = analyze_component(mtype, body.params, body.steel)

        if not user_dao.deduct_balance(user["id"], total_cost):
            raise HTTPException(402, "Failed to deduct balance")
        balance_deducted = True

        # 存分析记录
        aid = None
        if isinstance(result, dict) and result.get("kind"):
            aid = analysis_dao.add_analysis(
                component_type=result.get("kind", mtype),
                component_name=KIND_CN.get(result.get("kind", mtype), result.get("name", "")),
                section_info=result.get("section", ""),
                steel=result.get("steel", body.steel),
                params_dict=result.get("params", body.params),
                ratios_dict=result.get("ratios", {}),
                control_ratio=result.get("control_ratio"),
                verdict=result.get("verdict", ""))
        billing_dao.record_api_call(user_id=user["id"], token=authorization,
                                    model_name=mtype, endpoint="/analysis",
                                    image_count=body.count, cost=total_cost,
                                    status="success", inference_result_id=aid)
        return {"model_type": mtype, "result": result,
                "cost": total_cost,
                "remaining_balance": (user_dao.get_user_by_token(authorization) or user)["balance"]}
    except HTTPException:
        raise
    except Exception as exc:
        if balance_deducted:
            user_dao.add_balance(user["id"], total_cost, "分析失败退款")
        raise HTTPException(500, "analysis failed: %s" % exc)
