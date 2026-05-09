from pydantic import BaseModel, Field


class SystemSettingsPublic(BaseModel):
    """返回给前端的配置（不回显 API Key 明文）。"""

    mount_path: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    rename_instruction: str = ""
    has_openai_api_key: bool = False


class SystemSettingsPatch(BaseModel):
    mount_path: str | None = Field(default=None, description="挂载根路径")
    openai_base_url: str | None = None
    openai_model: str | None = None
    rename_instruction: str | None = Field(default=None, description="自然语言重命名说明")
    openai_api_key: str | None = Field(
        default=None,
        description="传入则更新；传空字符串表示清空库内密钥（回退仅用环境变量）",
    )


class ModelsProbeRequest(BaseModel):
    openai_base_url: str | None = Field(default=None, description="可与表单一致；省略则用库内或环境变量")
    openai_api_key: str | None = Field(default=None, description="省略则用库内或环境变量")


class ModelOption(BaseModel):
    id: str
    label: str


class ModelsListResponse(BaseModel):
    models: list[ModelOption]
