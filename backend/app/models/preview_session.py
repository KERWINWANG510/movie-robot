from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PreviewSession(Base):
    """非全自动用户执行改名前须持有的预览会话（仅通过 ORM 写入）。"""

    __tablename__ = "preview_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        comment="会话 UUID",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户 id",
    )
    items_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="预览项 JSON：路径与建议文件名列表",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="创建时间（UTC）",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="过期时间（UTC）",
    )
