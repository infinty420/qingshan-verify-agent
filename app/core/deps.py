"""FastAPI 依赖注入：数据库会话、当前用户、管理员权限。"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models import User


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    # token 来源优先级：Authorization Bearer > X-Auth-Token > query 参数 access_token
    # （云端反向代理会改写 Authorization 头，X-Auth-Token 作为透传通道）
    auth = request.headers.get("authorization") or ""
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token:
        token = (request.headers.get("x-auth-token") or "").strip()
    if not token:
        token = (request.query_params.get("access_token") or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="缺少认证令牌")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="令牌无效或已过期")
    user = await db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
