from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TransferDestination(Base):
    """文件传输目标（可多选）；路径由服务端校验，须为不含 .. 片段的绝对路径字符串。"""

    __tablename__ = "transfer_destination"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="主键",
    )
    label: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="用户可见名称，如「电影」「电视剧」",
    )
    path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="服务端绝对路径（规范化后存储），与挂载根可不同",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="展示与列表排序，数值越小越靠前",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="创建时间（UTC）",
    )
