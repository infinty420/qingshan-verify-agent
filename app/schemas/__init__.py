"""Pydantic 请求 / 响应模型（入口层契约）。"""
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


class LoginOut(BaseModel):
    token: str
    user: UserOut


class SessionCreateIn(BaseModel):
    title: str = "新会话"


class SessionOut(BaseModel):
    id: int
    title: str
    created_at: str
    last_message_at: str | None = None
    user_name: str | None = None
    message_count: int = 0


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    intent: str | None = None
    citations: list | None = None
    created_at: str


class ChatStreamIn(BaseModel):
    session_id: int
    content: str = Field(min_length=1, max_length=2000)


class ReimburseIn(BaseModel):
    expense_type: str
    amount: float = Field(gt=0)
    expense_date: str = ""
    description: str = ""
    session_id: int | None = None


class ReimburseOut(BaseModel):
    id: int
    user_name: str | None = None
    session_id: int | None = None
    expense_type: str
    amount: float
    expense_date: str
    description: str
    policy_refs: list | None = None
    status: str
    created_at: str
    submitted_at: str | None = None


class KBUploadIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=20)


class KBDocOut(BaseModel):
    id: int
    title: str
    version: int
    status: str
    chunk_count: int
    created_at: str
    updated_at: str
