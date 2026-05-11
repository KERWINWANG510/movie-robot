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
        comment="挂载根目录路径；须在界面保存后方可浏览文件",
    )
    transfer_target_path: Mapped[str] = mapped_column(
        String(1024),
        default="",
        nullable=False,
        comment="文件传输目标目录绝对路径；可与挂载根不同，留空则未配置",
    )
    ai_provider: Mapped[str] = mapped_column(
        String(64),
        default="custom",
        nullable=False,
        comment="AI 服务商：custom 为自定义 Base URL；其余为内置预设 id",
    )
    openai_base_url: Mapped[str] = mapped_column(
        String(1024),
        default="",
        nullable=False,
        comment="自定义模式下 OpenAI 兼容 API 根地址；预设模式下可为空",
    )
    openai_api_key: Mapped[str] = mapped_column(
        String(512),
        default="",
        nullable=False,
        comment="API 密钥；须在界面保存后方可调用 AI",
    )
    openai_model: Mapped[str] = mapped_column(
        String(256),
        default="",
        nullable=False,
        comment="模型 ID；须在界面保存后方可调用 AI",
    )
    rename_instruction: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
        comment="自然语言重命名说明，随请求发送给大模型；空则仅用默认规则",
    )
