from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.rename import RenameItem


class OpenHealthResponse(BaseModel):
    status: str = Field(description="固定为 ok，表示接口与鉴权正常")
    mount_ready: bool = Field(description="挂载根是否已配置且为可用目录")


class AutoRenameRequest(BaseModel):
    paths: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="相对挂载根的文件路径列表（仅文件，不含目录）",
        examples=[["downloads/Movie.Name.2024.mkv"]],
    )


class AutoRenameItemResult(BaseModel):
    path: str = Field(description="请求中的源相对路径")
    original_name: str = Field(default="", description="原文件名")
    suggested_name: str = Field(default="", description="AI 建议并用于执行的新文件名；失败时可能为空")
    ok: bool = Field(description="是否最终重命名成功")
    message: str | None = Field(default=None, description="失败原因；成功时一般为 null")


class AutoRenameResponse(BaseModel):
    items: list[AutoRenameItemResult] = Field(description="每个文件的建议名与执行结果")
    ok_count: int = Field(description="成功重命名的文件数")
    failed_count: int = Field(description="失败的文件数")


class OpenExecuteBody(BaseModel):
    """开放接口执行重命名：无需 preview_id，直接按给定新文件名执行。"""

    items: list[RenameItem] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="待执行的重命名项列表",
    )


class ApiTokenCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="令牌备注名称")
    expires_in_days: int | None = Field(
        default=None,
        ge=1,
        le=3650,
        description="有效天数；省略或 null 表示永久有效",
    )


class ApiTokenPublic(BaseModel):
    id: int
    name: str
    token_prefix: str
    created_at: datetime
    last_used_at: datetime | None = None
    expires_at: datetime | None = Field(default=None, description="过期时间；空表示永久")
    revoked_at: datetime | None = None
    expired: bool = Field(default=False, description="是否已过期（未吊销但超过 expires_at）")


class ApiTokenCreatedResponse(BaseModel):
    token: ApiTokenPublic
    plain_token: str = Field(description="明文令牌，仅此次返回，请立即保存")


class ApiTokenListResponse(BaseModel):
    items: list[ApiTokenPublic]


class OpenApiCatalogField(BaseModel):
    """请求或响应中的单个字段说明。"""

    name: str = Field(description="字段名；嵌套时可用 items[].path 等形式")
    type: str = Field(description="类型说明，如 string、integer、boolean、object、array")
    required: bool = False
    description: str = ""
    example: object | None = None
    children: list["OpenApiCatalogField"] = Field(
        default_factory=list,
        description="对象/数组元素的子字段说明",
    )


class OpenApiCatalogParam(BaseModel):
    name: str
    location: str = Field(description="query / header / path / body")
    type: str = Field(default="string", description="参数类型")
    required: bool = False
    description: str = ""
    example: object | None = None


class OpenApiCatalogEndpoint(BaseModel):
    id: str
    method: str
    path: str
    summary: str
    description: str = ""
    notes: list[str] = Field(default_factory=list, description="补充约定与限制")
    headers: list[OpenApiCatalogParam] = Field(default_factory=list)
    query_params: list[OpenApiCatalogParam] = Field(default_factory=list)
    path_params: list[OpenApiCatalogParam] = Field(
        default_factory=list,
        description="路径参数（对应 path 中的 {name} 占位）",
    )
    request_fields: list[OpenApiCatalogField] = Field(default_factory=list, description="请求体字段说明")
    response_fields: list[OpenApiCatalogField] = Field(default_factory=list, description="成功响应字段说明")
    body_example: object | None = None
    response_example: object | None = None
    error_codes: list[str] = Field(
        default_factory=list,
        description="常见错误说明，如 401 / 400 文案",
    )


class OpenApiCatalogResponse(BaseModel):
    base_path: str = "/api/v1/open"
    auth: str = "Authorization: Bearer <token> 或 X-Api-Key: <token>"
    auth_notes: list[str] = Field(default_factory=list)
    endpoints: list[OpenApiCatalogEndpoint]


OpenApiCatalogField.model_rebuild()
