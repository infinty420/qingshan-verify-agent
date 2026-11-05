"""认证：登录 + 当前用户。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import create_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginIn, LoginOut, UserOut
from app.services import record_service

router = APIRouter()


@router.post("/auth/login", response_model=LoginOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.username == body.username))
    ).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    await record_service.audit(db, user.id, "login", "user", user.id, {"role": user.role})
    return LoginOut(
        token=create_token(user.id, user.role),
        user=UserOut(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            role=user.role,
        ),
    )


@router.get("/auth/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )
