from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApiAccessToken(Base):
    """对外开放接口的访问令牌（仅存哈希，明文只在创建时返回一次）。"""

    __tablename__ = "api_access_token"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="令牌备注名称，便于识别用途",
    )
    token_prefix: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="令牌明文前缀，用于列表展示与粗筛",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="令牌 SHA-256 十六进制哈希",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间（UTC）",
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="最近一次成功鉴权时间（UTC）",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="过期时间（UTC）；空表示永久有效",
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="吊销时间（UTC）；非空表示已失效",
    )
