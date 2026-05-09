from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    name: str
    path: str
    is_dir: bool


class BrowseResponse(BaseModel):
    path: str
    entries: list[FileEntry]
