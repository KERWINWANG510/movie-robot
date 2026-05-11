from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.files import (
    BrowseResponse,
    FileEntry,
    FileTransferRequest,
    FileTransferResponse,
    FileTransferResultItem,
    FolderMergeRequest,
    FolderMergeResponse,
    FolderMergeResultItem,
)
from app.services.file_transfer import resolve_transfer_target_directory, transfer_paths_to_target
from app.services.transfer_destinations import get_destination_by_id
from app.services.folder_merge import merge_folder_trees_flat
from app.services.path_security import PathNotAllowedError, resolve_under_root
from app.services.runtime_config import effective_mount_root, get_system_config_row

router = APIRouter(prefix="/files", tags=["文件浏览"])


def _rel_from_root(root: Path, full: Path) -> str:
    return str(full.relative_to(root)).replace("\\", "/")


@router.get("/browse", response_model=BrowseResponse)
async def browse(
    path: str = Query("", description="相对挂载根的目录，空表示根"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrowseResponse:
    cfg_row = await get_system_config_row(db)
    try:
        root = effective_mount_root(cfg_row)
    except ValueError:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写有效的挂载根目录") from None
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


@router.post("/folders/merge", response_model=FolderMergeResponse)
async def merge_folders(
    body: FolderMergeRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FolderMergeResponse:
    cfg_row = await get_system_config_row(db)
    try:
        root = effective_mount_root(cfg_row)
    except ValueError:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写有效的挂载根目录") from None

    raw = merge_folder_trees_flat(
        root=root,
        source_rel_paths=body.source_paths,
        target_rel=body.target_path,
    )
    items = [
        FolderMergeResultItem(
            source_path=s,
            dest_path=d,
            ok=ok,
            message=msg,
        )
        for s, d, ok, msg in raw
    ]
    moved = sum(1 for x in items if x.ok)
    failed = sum(1 for x in items if not x.ok)
    return FolderMergeResponse(results=items, moved_count=moved, failed_count=failed)


@router.post("/transfer", response_model=FileTransferResponse)
async def transfer_files(
    body: FileTransferRequest,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileTransferResponse:
    cfg_row = await get_system_config_row(db)
    try:
        root = effective_mount_root(cfg_row)
    except ValueError:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写有效的挂载根目录") from None

    dest = await get_destination_by_id(db, body.destination_id)
    if dest is None:
        raise HTTPException(status_code=404, detail="传输目标不存在，请先在系统配置中保存有效的传输目标")
    transfer_dir = resolve_transfer_target_directory(dest.path)

    raw = transfer_paths_to_target(
        mount_root=root,
        transfer_target=transfer_dir,
        source_rel_paths=body.paths,
        mode=body.mode,
    )
    items = [
        FileTransferResultItem(source_path=s, dest_path=d, ok=ok, message=msg) for s, d, ok, msg in raw
    ]
    ok_n = sum(1 for x in items if x.ok)
    fail_n = sum(1 for x in items if not x.ok)
    return FileTransferResponse(results=items, ok_count=ok_n, failed_count=fail_n)
