from pydantic import BaseModel, Field


class SystemSettingsPublic(BaseModel):
    """返回给前端的配置（不回显 API Key 明文）。"""

    mount_path: str = ""
    transfer_target_path: str = ""
    ai_provider: str = "custom"
    openai_base_url: str = ""
    effective_openai_base_url: str = ""
    openai_model: str = ""
    rename_instruction: str = ""
    # 仅在库中保存了 API Key 时为 True（用于是否展示「清除库内密钥」）
    api_key_saved_in_db: bool = False
    # 合并后的挂载根路径存在且为目录时可用；否则首页应引导先配置
    mount_ready: bool = False
    # 传输目标已配置且为已存在目录时可用
    transfer_target_ready: bool = False


class SystemSettingsPatch(BaseModel):
    mount_path: str | None = Field(default=None, description="挂载根路径")
    transfer_target_path: str | None = Field(
        default=None,
        description="文件传输目标目录（服务端绝对路径或当前环境下可用的路径字符串）",
    )
    ai_provider: str | None = Field(default=None, description="内置服务商 id 或 custom")
    openai_base_url: str | None = None
    openai_model: str | None = None
    rename_instruction: str | None = Field(default=None, description="自然语言重命名说明")
    openai_api_key: str | None = Field(
        default=None,
        description="传入则更新；传空字符串表示清空库内密钥",
    )


class ModelsProbeRequest(BaseModel):
    ai_provider: str | None = Field(default=None, description="探测未保存表单时可传，与库内合并解析 Base URL")
    openai_base_url: str | None = Field(default=None, description="可与表单一致；省略则按服务商与库内解析")
    openai_api_key: str | None = Field(default=None, description="省略则用库内已保存值")


class AiProviderOption(BaseModel):
    id: str
    label: str
    base_url: str


class AiProvidersListResponse(BaseModel):
    providers: list[AiProviderOption]


class ModelOption(BaseModel):
    id: str
    label: str


class ModelsListResponse(BaseModel):
    models: list[ModelOption]
