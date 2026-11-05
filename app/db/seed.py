"""种子数据：演示账号 + 知识库制度文档（首次启动自动初始化）。"""
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.models import KBDocument, User
from app.services import kb_service

DEMO_USERS = [
    ("admin", "admin123", "admin", "李慧 · 财务制度管理员"),
    ("employee", "employee123", "employee", "林亦舟 · 江南路店店长"),
    ("employee2", "employee123", "employee", "唐映秋 · 筹备项目专员"),
]


async def seed_all():
    async with SessionFactory() as db:
        user_count = (await db.execute(select(func.count(User.id)))).scalar()
        if user_count == 0:
            for uname, pwd, role, disp in DEMO_USERS:
                db.add(
                    User(
                        username=uname,
                        password_hash=hash_password(pwd),
                        role=role,
                        display_name=disp,
                    )
                )
            await db.commit()
            print(f"[seed] 已创建 {len(DEMO_USERS)} 个演示账号")

        doc_count = (await db.execute(select(func.count(KBDocument.id)))).scalar()
        if doc_count == 0 and settings.knowledge_dir.exists():
            for md in sorted(settings.knowledge_dir.glob("*.md")):
                doc = await kb_service.ingest_markdown(
                    db, md.stem, md.read_text(encoding="utf-8"), uploaded_by=None
                )
                print(f"[seed] 知识库入库：{doc.title} v{doc.version}（{doc.chunk_count} 个分块）")
