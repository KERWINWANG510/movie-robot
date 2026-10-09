"""对外开放业务接口（API Key 鉴权）。"""

from pathlib import Path
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_open_api_token
from app.api.routes.rename import _perform_rename
from app.database import get_db
from app.models.api_access_token import ApiAccessToken
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
from app.schemas.media import (
    MediaSubscribeRequest,
    MediaSubscriptionItem,
    MediaSubscriptionListResponse,
)
from app.schemas.open_api import (
    AutoRenameItemResult,
    AutoRenameRequest,
    AutoRenameResponse,
    OpenApiCatalogResponse,
    OpenExecuteBody,
    OpenHealthResponse,
)
from app.schemas.rename import (
    ExecuteResponse,
    ExecuteResultRow,
    PreviewRequest,
    PreviewResponse,
    PreviewResultRow,
)
from app.schemas.system_settings import TransferDestinationPublic
from app.services.file_transfer import resolve_transfer_target_directory, transfer_paths_to_target
from app.services.folder_merge import merge_folder_trees_flat
from app.services.media_subscriptions import (
    add_subscription_for_user,
    get_builtin_admin_user,
    list_subscriptions_for_user,
    remove_subscription_for_user,
)
from app.services.open_api_catalog import build_open_api_catalog
from app.services.openai_rename import suggest_filenames
from app.services.path_security import PathNotAllowedError, resolve_under_root
from app.services.runtime_config import effective_ai_params, effective_mount_root, get_system_config_row
from app.services.transfer_destinations import (
    destination_ready_from_stored_path,
    get_destination_by_id,
    list_destinations_rows,
)
from pydantic import BaseModel, Field

router = APIRouter(prefix="/open", tags=["开放接口"])


class OpenDestinationsResponse(BaseModel):
    items: list[TransferDestinationPublic] = Field(default_factory=list)


def _rel_from_root(root: Path, full: Path) -> str:
    return str(full.relative_to(root)).replace("\\", "/")


def _mount_ready(cfg_row) -> bool:
    if cfg_row is None:
        return False
    raw = (cfg_row.mount_path or "").strip()
    if not raw:
        return False
    try:
        root = Path(raw).expanduser().resolve()
        return root.exists() and root.is_dir()
    except OSError:
        return False


async def _require_mount(db: AsyncSession) -> Path:
    cfg_row = await get_system_config_row(db)
    try:
        return effective_mount_root(cfg_row)
    except ValueError:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写有效的挂载根目录") from None


@router.get("/health", response_model=OpenHealthResponse)
async def open_health(
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> OpenHealthResponse:
    cfg_row = await get_system_config_row(db)
    return OpenHealthResponse(status="ok", mount_ready=_mount_ready(cfg_row))


@router.get("/catalog", response_model=OpenApiCatalogResponse)
async def open_catalog(
    _token: ApiAccessToken = Depends(get_open_api_token),
) -> OpenApiCatalogResponse:
    """返回当前开放接口能力目录（与管理页清单同源）。"""
    return build_open_api_catalog()


@router.get("/browse", response_model=BrowseResponse)
async def open_browse(
    path: str = Query("", description="相对挂载根的目录，空表示根"),
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> BrowseResponse:
    root = await _require_mount(db)
    rel = path.strip().replace("\\", "/").lstrip("/")
    try:
        base = root if not rel else resolve_under_root(root, rel)
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
            size: int | None = None
            if not child.is_dir():
                try:
                    size = int(child.stat().st_size)
                except OSError:
                    size = None
            entries.append(
                FileEntry(name=child.name, path=full_rel, is_dir=child.is_dir(), size=size)
            )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限读取该目录") from exc

    return BrowseResponse(path="" if not rel else rel, entries=entries)


@router.get("/destinations", response_model=OpenDestinationsResponse)
async def open_destinations(
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> OpenDestinationsResponse:
    dest_rows = await list_destinations_rows(db)
    items = [
        TransferDestinationPublic(
            id=d.id,
            label=d.label,
            path=d.path,
            ready=destination_ready_from_stored_path(d.path),
        )
        for d in dest_rows
    ]
    return OpenDestinationsResponse(items=items)


@router.post("/folders/merge", response_model=FolderMergeResponse)
async def open_merge_folders(
    body: FolderMergeRequest,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> FolderMergeResponse:
    root = await _require_mount(db)
    raw = merge_folder_trees_flat(
        root=root,
        source_rel_paths=body.source_paths,
        target_rel=body.target_path,
    )
    items = [
        FolderMergeResultItem(source_path=s, dest_path=d, ok=ok, message=msg) for s, d, ok, msg in raw
    ]
    moved = sum(1 for x in items if x.ok)
    failed = sum(1 for x in items if not x.ok)
    return FolderMergeResponse(results=items, moved_count=moved, failed_count=failed)


async def _preview_suggestions(
    db: AsyncSession,
    paths: list[str],
) -> list[PreviewResultRow]:
    root = await _require_mount(db)
    cfg_row = await get_system_config_row(db)
    ai = effective_ai_params(cfg_row)

    rows: list[PreviewResultRow] = []
    valid_paths: list[str] = []
    for rel in paths:
        try:
            p = resolve_under_root(root, rel)
        except PathNotAllowedError as exc:
            rows.append(PreviewResultRow(path=rel, original_name="", suggested_name="", error=str(exc)))
            continue
        if not p.exists() or not p.is_file():
            rows.append(
                PreviewResultRow(
                    path=rel,
                    original_name=p.name if p.exists() else "",
                    suggested_name="",
                    error="不是有效文件",
                )
            )
            continue
        valid_paths.append(rel)

    if not valid_paths:
        return rows

    try:
        contexts: dict[str, dict[str, str]] = {}
        for rel in valid_paths:
            rp = PurePosixPath(rel.replace("\\", "/").lstrip("/"))
            parent = rp.parent
            parent_path = "" if str(parent) == "." else str(parent)
            parent_dir = "" if parent_path == "" else parent.name
            contexts[rel] = {"parent_dir": parent_dir, "parent_path": parent_path}
        suggestions = await suggest_filenames(
            ai,
            relative_paths=valid_paths,
            contexts=contexts,
            naming_hint=ai.rename_instruction or None,
        )
    except Exception as exc:
        for rel in valid_paths:
            orig = resolve_under_root(root, rel).name
            rows.append(
                PreviewResultRow(
                    path=rel,
                    original_name=orig,
                    suggested_name="",
                    error=f"调用 AI 失败：{exc}",
                )
            )
        return rows

    for rel in valid_paths:
        orig = resolve_under_root(root, rel).name
        sug = suggestions.get(rel)
        if not sug:
            rows.append(
                PreviewResultRow(
                    path=rel,
                    original_name=orig,
                    suggested_name="",
                    error="未能生成建议文件名（请检查 API Key 与模型配置）",
                )
            )
            continue
        rows.append(
            PreviewResultRow(path=rel, original_name=orig, suggested_name=sug, error=None),
        )
    return rows


@router.post("/rename/preview", response_model=PreviewResponse)
async def open_rename_preview(
    body: PreviewRequest,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> PreviewResponse:
    items = await _preview_suggestions(db, body.paths)
    return PreviewResponse(preview_id=None, items=items)


@router.post("/rename/execute", response_model=ExecuteResponse)
async def open_rename_execute(
    body: OpenExecuteBody,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> ExecuteResponse:
    root = await _require_mount(db)
    results: list[ExecuteResultRow] = []
    for item in body.items:
        ok, msg = _perform_rename(root, item.path, item.new_name)
        results.append(ExecuteResultRow(path=item.path, ok=ok, message=msg))
    return ExecuteResponse(results=results)


@router.post("/rename/auto", response_model=AutoRenameResponse)
async def open_rename_auto(
    body: AutoRenameRequest,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> AutoRenameResponse:
    root = await _require_mount(db)
    preview_rows = await _preview_suggestions(db, body.paths)
    out: list[AutoRenameItemResult] = []
    for row in preview_rows:
        if row.error or not row.suggested_name.strip():
            out.append(
                AutoRenameItemResult(
                    path=row.path,
                    original_name=row.original_name,
                    suggested_name=row.suggested_name,
                    ok=False,
                    message=row.error or "无建议文件名",
                )
            )
            continue
        ok, msg = _perform_rename(root, row.path, row.suggested_name.strip())
        out.append(
            AutoRenameItemResult(
                path=row.path,
                original_name=row.original_name,
                suggested_name=row.suggested_name.strip(),
                ok=ok,
                message=msg,
            )
        )
    ok_n = sum(1 for x in out if x.ok)
    fail_n = sum(1 for x in out if not x.ok)
    return AutoRenameResponse(items=out, ok_count=ok_n, failed_count=fail_n)


@router.post("/transfer", response_model=FileTransferResponse)
async def open_transfer(
    body: FileTransferRequest,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> FileTransferResponse:
    root = await _require_mount(db)
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


@router.get("/media/subscriptions", response_model=MediaSubscriptionListResponse)
async def open_list_media_subscriptions(
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> MediaSubscriptionListResponse:
    """列出想看列表（与内置 admin 账号的想看列表共享）。"""
    owner = await get_builtin_admin_user(db)
    items = await list_subscriptions_for_user(db, owner.id)
    return MediaSubscriptionListResponse(items=items)


@router.post("/media/subscriptions", response_model=MediaSubscriptionItem)
async def open_add_media_subscription(
    body: MediaSubscribeRequest,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> MediaSubscriptionItem:
    """加入想看（需已配置 TMDB API Key；与内置 admin 想看列表共享）。"""
    owner = await get_builtin_admin_user(db)
    return await add_subscription_for_user(
        db,
        owner.id,
        media_type=body.media_type,
        tmdb_id=body.tmdb_id,
    )


@router.delete("/media/subscriptions/{media_type}/{tmdb_id}")
async def open_remove_media_subscription(
    media_type: str,
    tmdb_id: int,
    _token: ApiAccessToken = Depends(get_open_api_token),
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """取消想看（与内置 admin 想看列表共享）。"""
    owner = await get_builtin_admin_user(db)
    await remove_subscription_for_user(
        db,
        owner.id,
        media_type=media_type,
        tmdb_id=tmdb_id,
    )
    return {"ok": True}
