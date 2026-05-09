from pydantic import BaseModel, Field


class RenameItem(BaseModel):
    path: str = Field(description="相对于挂载根的路径")
    new_name: str = Field(description="仅文件名，不含路径")


class PreviewRequest(BaseModel):
    paths: list[str] = Field(min_length=1, max_length=200)


class PreviewResultRow(BaseModel):
    path: str
    original_name: str
    suggested_name: str
    error: str | None = None


class PreviewResponse(BaseModel):
    preview_id: str | None = None
    items: list[PreviewResultRow]


class ExecuteRequest(BaseModel):
    preview_id: str | None = None
    items: list[RenameItem] = Field(min_length=1, max_length=200)


class ExecuteResultRow(BaseModel):
    path: str
    ok: bool
    message: str | None = None


class ExecuteResponse(BaseModel):
    results: list[ExecuteResultRow]
