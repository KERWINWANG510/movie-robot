from pydantic import BaseModel, Field


class RenameItem(BaseModel):
    path: str = Field(description="相对于挂载根的文件路径", examples=["downloads/Movie.Name.2024.mkv"])
    new_name: str = Field(description="仅新文件名，不含目录路径", examples=["Movie Name (2024).mkv"])


class PreviewRequest(BaseModel):
    paths: list[str] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="相对挂载根的待重命名文件路径列表",
        examples=[["downloads/Movie.Name.2024.mkv"]],
    )


class PreviewResultRow(BaseModel):
    path: str = Field(description="原相对路径")
    original_name: str = Field(description="原文件名")
    suggested_name: str = Field(description="AI 建议的新文件名；失败时可能为空")
    error: str | None = Field(default=None, description="该条生成失败原因；成功时为 null")


class PreviewResponse(BaseModel):
    preview_id: str | None = Field(
        default=None,
        description="预览会话 id（Web 预览确认模式使用）；开放接口预览固定为 null",
    )
    items: list[PreviewResultRow] = Field(description="每条文件的建议结果")


class ExecuteRequest(BaseModel):
    preview_id: str | None = Field(
        default=None,
        description="预览会话 id；全自动/开放接口可省略",
    )
    items: list[RenameItem] = Field(
        ...,
        min_length=1,
        max_length=200,
        description="待执行的重命名项",
    )


class ExecuteResultRow(BaseModel):
    path: str = Field(description="请求中的源相对路径")
    ok: bool = Field(description="是否重命名成功")
    message: str | None = Field(default=None, description="失败原因；成功时一般为 null")


class ExecuteResponse(BaseModel):
    results: list[ExecuteResultRow] = Field(description="每条执行结果")
