import json
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.models.preview_session import PreviewSession
from app.models.user import User
from app.schemas.rename import (
    ExecuteRequest,
    ExecuteResponse,
    ExecuteResultRow,
    PreviewRequest,
    PreviewResponse,
    PreviewResultRow,
)
from app.services.openai_rename import suggest_filenames
from app.services.path_security import PathNotAllowedError, resolve_under_root

router = APIRouter(prefix="/rename", tags=["智能重命名"])


def _utcnow() -> datetime:
    return datetime.utcnow()


async def _cleanup_expired(db: AsyncSession) -> None:
    await db.execute(delete(PreviewSession).where(PreviewSession.expires_at < _utcnow()))
    await db.commit()


def _perform_rename(settings: Settings, path_rel: str, new_name: str) -> tuple[bool, str | None]:
    root = settings.mount_root
    try:
        src = resolve_under_root(root, path_rel)
    except PathNotAllowedError as exc:
        return False, str(exc)
    if not src.exists():
        return False, "文件不存在"
    if not src.is_file():
        return False, "只能重命名文件"
    cleaned = new_name.strip().split("/")[-1]
    if not cleaned:
        return False, "新文件名无效"
    dest = src.parent / cleaned
    try:
        dest.relative_to(root.resolve())
    except ValueError:
        return False, "目标路径非法"
    if dest.resolve() == src.resolve():
        return True, None
    if dest.exists():
        return False, "目标文件名已存在"
    try:
        src.rename(dest)
    except OSError as exc:
        return False, f"重命名失败：{exc}"
    return True, None


@router.post("/preview", response_model=PreviewResponse)
async def preview_rename(
    body: PreviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PreviewResponse:
    settings = get_settings()
    await _cleanup_expired(db)

    rows: list[PreviewResultRow] = []
    valid_paths: list[str] = []
    for rel in body.paths:
        try:
            p = resolve_under_root(settings.mount_root, rel)
        except PathNotAllowedError as exc:
            rows.append(
                PreviewResultRow(
                    path=rel,
                    original_name="",
                    suggested_name="",
                    error=str(exc),
                )
            )
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

    preview_id: str | None = None
    stored_items: list[dict[str, str]] = []

    if valid_paths:
        try:
            suggestions = await suggest_filenames(settings, relative_paths=valid_paths)
        except Exception as exc:
            for rel in valid_paths:
                orig = resolve_under_root(settings.mount_root, rel).name
                rows.append(
                    PreviewResultRow(
                        path=rel,
                        original_name=orig,
                        suggested_name="",
                        error=f"调用 AI 失败：{exc}",
                    )
                )
            return PreviewResponse(preview_id=None, items=rows)

        for rel in valid_paths:
            orig = resolve_under_root(settings.mount_root, rel).name
            sug = suggestions.get(rel)
            if sug is None or sug == "":
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
                PreviewResultRow(
                    path=rel,
                    original_name=orig,
                    suggested_name=sug,
                    error=None,
                )
            )
            stored_items.append({"path": rel, "suggested_name": sug})

    if not user.auto_rename_without_preview and stored_items:
        pid = str(uuid4())
        expires = _utcnow() + timedelta(minutes=30)
        sess = PreviewSession(
            id=pid,
            user_id=user.id,
            items_json=json.dumps(stored_items, ensure_ascii=False),
            created_at=_utcnow(),
            expires_at=expires,
        )
        db.add(sess)
        await db.commit()
        preview_id = pid

    return PreviewResponse(preview_id=preview_id, items=rows)


@router.post("/execute", response_model=ExecuteResponse)
async def execute_rename(
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExecuteResponse:
    settings = get_settings()
    allowed_paths: set[str] | None = None
    preview_row: PreviewSession | None = None

    if not user.auto_rename_without_preview:
        if not body.preview_id:
            raise HTTPException(status_code=400, detail="当前为预览确认模式，请先获取预览或开启全自动开关")
        result = await db.execute(
            select(PreviewSession).where(
                PreviewSession.id == body.preview_id,
                PreviewSession.user_id == user.id,
            )
        )
        preview_row = result.scalar_one_or_none()
        if preview_row is None:
            raise HTTPException(status_code=400, detail="预览会话无效或已过期，请重新预览")
        if preview_row.expires_at < _utcnow():
            await db.delete(preview_row)
            await db.commit()
            raise HTTPException(status_code=400, detail="预览已过期，请重新预览")
        try:
            parsed = json.loads(preview_row.items_json)
            allowed_paths = {str(x.get("path")) for x in parsed if x.get("path")}
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="预览数据损坏") from None

    results: list[ExecuteResultRow] = []
    for item in body.items:
        if allowed_paths is not None and item.path not in allowed_paths:
            results.append(ExecuteResultRow(path=item.path, ok=False, message="不在本次预览范围内"))
            continue
        ok, msg = _perform_rename(settings, item.path, item.new_name)
        results.append(ExecuteResultRow(path=item.path, ok=ok, message=msg))

    if preview_row is not None:
        await db.delete(preview_row)
        await db.commit()

    return ExecuteResponse(results=results)
