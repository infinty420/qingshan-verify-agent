"""临时诊断端点：回显请求到达后端时的头部与查询参数。

用途：排查云平台反向代理对 Authorization / X-Auth-Token / query 参数的
改写与透传行为。诊断完成后应删除本文件并取消注册。
"""
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/_debug/echo")
async def echo(request: Request):
    headers = {k: (v[:40] + "…" if len(v) > 40 else v) for k, v in request.headers.items()}
    return {"headers": headers, "query_params": dict(request.query_params)}
