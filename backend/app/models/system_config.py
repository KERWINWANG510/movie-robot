from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemConfig(Base):
    """系统级配置单例（id 固定为 1），通过 ORM 读写。"""

    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        comment="固定为 1 的单例主键",
    )
    mount_path: Mapped[str] = mapped_column(
        String(1024),
        default="",
        nullable=False,
        comment="挂载根目录路径；空则使用环境变量 MOUNT_PATH",
    )
    openai_base_url: Mapped[str] = mapped_column(
        String(1024),
        default="",
        nullable=False,
        comment="OpenAI 兼容 API 根地址",
    )
    openai_api_key: Mapped[str] = mapped_column(
        String(512),
        default="",
        nullable=False,
        comment="API 密钥；空则使用环境变量 OPENAI_API_KEY",
    )
    openai_model: Mapped[str] = mapped_column(
        String(256),
        default="",
        nullable=False,
        comment="模型 ID；空则使用环境变量 OPENAI_MODEL",
    )
    rename_instruction: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
        comment="自然语言重命名说明，随请求发送给大模型；空则仅用默认规则",
    )
