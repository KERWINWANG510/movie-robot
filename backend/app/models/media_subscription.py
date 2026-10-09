from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MediaSubscription(Base):
    """用户「想看」收藏：按 TMDB 条目缓存展示字段。"""

    __tablename__ = "media_subscription"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "media_type",
            "tmdb_id",
            name="uq_media_subscription_user_type_tmdb",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户 id",
    )
    tmdb_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="TMDB 条目 id",
    )
    media_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="媒体类型：movie 或 tv",
    )
    title: Mapped[str] = mapped_column(
        String(512),
        default="",
        nullable=False,
        comment="标题缓存（电影 title / 剧集 name）",
    )
    poster_path: Mapped[str] = mapped_column(
        String(512),
        default="",
        nullable=False,
        comment="海报相对路径缓存（TMDB poster_path）",
    )
    overview: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
        comment="简介缓存（可截断）",
    )
    release_date: Mapped[str] = mapped_column(
        String(32),
        default="",
        nullable=False,
        comment="上映/首播日期缓存（YYYY-MM-DD，可空字符串）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="订阅时间（UTC）",
    )
