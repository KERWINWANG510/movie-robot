from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.models.user import User
from app.schemas.files import BrowseResponse, FileEntry
from app.services.path_security import PathNotAllowedError, resolve_under_root

router = APIRouter(prefix="/files", tags=["文件浏览"])


def _rel_from_root(root: Path, full: Path) -> str:
    return str(full.relative_to(root)).replace("\\", "/")


@router.get("/browse", response_model=BrowseResponse)
async def browse(
    path: str = Query("", description="相对挂载根的目录，空表示根"),
    user: User = Depends(get_current_user),
) -> BrowseResponse:
    settings = get_settings()
    root = settings.mount_root
    rel = path.strip().replace("\\", "/").lstrip("/")
    try:
        if not rel:
            base = root
        else:
            base = resolve_under_root(root, rel)
    except PathNotAllowedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not base.exists():
        raise HTTPException(status_code=404, detail="目录不存在")
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="目标不是目录")

    entries: list[FileEntry] = []
    try:
        for child in sorted(base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                full_rel = _rel_from_root(root, child.resolve())
            except ValueError:
                continue
            entries.append(
                FileEntry(
                    name=child.name,
                    path=full_rel,
                    is_dir=child.is_dir(),
                )
            )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限读取该目录") from exc

    display_path = "" if not rel else rel
    return BrowseResponse(path=display_path, entries=entries)
