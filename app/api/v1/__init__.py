"""API v1 路由聚合。"""
from fastapi import APIRouter

from app.api.v1 import auth, chat, kb, records, reimbursement

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(reimbursement.router, tags=["reimbursement"])
api_router.include_router(kb.router, tags=["kb"])
api_router.include_router(records.router, tags=["records"])
