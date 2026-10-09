from typing import Literal

from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    name: str = Field(description="文件或文件夹名称")
    path: str = Field(description="相对挂载根的完整相对路径")
    is_dir: bool = Field(description="是否为目录；true 为文件夹，false 为文件")


class BrowseResponse(BaseModel):
    path: str = Field(description="当前浏览目录（相对挂载根）；空字符串表示挂载根")
    entries: list[FileEntry] = Field(description="当前目录下的子项列表（目录优先，按名称排序）")


class FolderMergeRequest(BaseModel):
    """将多个源目录内（递归）所有文件扁平移动到目标目录；重名自动加 _1、_2…"""

    source_paths: list[str] = Field(
        ...,
        min_length=2,
        description="相对挂载根的源文件夹路径，至少 2 个；不可互为父子关系",
        examples=[["downloads/A", "downloads/B"]],
    )
    target_path: str = Field(
        default="",
        description="相对挂载根的目标文件夹路径；不存在时自动创建（支持多级，如 test/test2）；空字符串表示挂载根",
        examples=["downloads/merged"],
    )


class FolderMergeResultItem(BaseModel):
    source_path: str = Field(description="移动前的源文件相对路径")
    dest_path: str = Field(description="移动后的目标相对路径（含自动去重后缀）")
    ok: bool = Field(description="该项是否成功")
    message: str | None = Field(default=None, description="失败原因；成功时一般为 null")


class FolderMergeResponse(BaseModel):
    results: list[FolderMergeResultItem] = Field(description="每个被移动文件的结果明细")
    moved_count: int = Field(description="成功移动的文件数")
    failed_count: int = Field(description="失败的文件数")


class FileTransferRequest(BaseModel):
    paths: list[str] = Field(
        ...,
        min_length=1,
        description="相对挂载根的文件或目录路径，可多选；不可互为包含关系",
        examples=[["downloads/Movie Name (2024).mkv"]],
    )
    mode: Literal["copy", "move"] = Field(
        ...,
        description="传输方式：copy 复制，move 剪切（移动）",
        examples=["move"],
    )
    destination_id: int = Field(
        ...,
        description="系统配置中的传输目标 id（可通过 GET /open/destinations 查询）",
        examples=[1],
    )


class FileTransferResultItem(BaseModel):
    source_path: str = Field(description="源路径（相对挂载根）")
    dest_path: str = Field(description="目标侧绝对路径或结果路径")
    ok: bool = Field(description="该项是否成功")
    message: str | None = Field(default=None, description="失败原因；成功时一般为 null")


class FileTransferResponse(BaseModel):
    results: list[FileTransferResultItem] = Field(description="每项传输结果明细")
    ok_count: int = Field(description="成功项数")
    failed_count: int = Field(description="失败项数")
