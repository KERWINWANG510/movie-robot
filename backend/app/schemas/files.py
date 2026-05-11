from typing import Literal

from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class BrowseResponse(BaseModel):
    path: str
    entries: list[FileEntry]


class FolderMergeRequest(BaseModel):
    """将多个源目录内（递归）所有文件扁平移动到目标目录；重名自动加 _1、_2…"""

    source_paths: list[str] = Field(..., min_length=2, description="相对挂载根的源文件夹路径")
    target_path: str = Field(
        default="",
        description="相对挂载根的目标文件夹路径；不存在时自动创建（支持多级，如 test/test2）；空字符串表示挂载根",
    )


class FolderMergeResultItem(BaseModel):
    source_path: str
    dest_path: str
    ok: bool
    message: str | None = None


class FolderMergeResponse(BaseModel):
    results: list[FolderMergeResultItem]
    moved_count: int
    failed_count: int


class FileTransferRequest(BaseModel):
    paths: list[str] = Field(..., min_length=1, description="相对挂载根的文件或目录路径，可多选")
    mode: Literal["copy", "move"] = Field(..., description="复制或剪切（移动）")


class FileTransferResultItem(BaseModel):
    source_path: str
    dest_path: str
    ok: bool
    message: str | None = None


class FileTransferResponse(BaseModel):
    results: list[FileTransferResultItem]
    ok_count: int
    failed_count: int
