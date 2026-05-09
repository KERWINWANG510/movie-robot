from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemConfig(Base):
    """系统级配置单例（id 固定为 1），通过 ORM 读写。"""

    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mount_path: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    openai_base_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)
    openai_api_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    openai_model: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    # 自然语言形式的重命名要求，会随请求一并发送给大模型
    rename_instruction: Mapped[str] = mapped_column(Text, default="", nullable=False)
