"""传输目标目录的持久化与校验（多目标）。"""

from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transfer_destination import TransferDestination
from app.services.file_transfer import transfer_target_ready
from app.services.path_security import PathNotAllowedError, ensure_path_str_no_parent_ref_segments


def normalize_destination_path_for_storage(raw: str) -> str:
    """
    校验并规范化待入库的绝对路径字符串（不要求目录已存在）。
    返回 posix 风格的绝对路径字符串。
    """
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="传输目标路径不能为空")
    try:
        ensure_path_str_no_parent_ref_segments(s)
    except PathNotAllowedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        p = Path(s).expanduser()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"传输目标路径无效：{exc}") from exc
    try:
        resolved = p.resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"传输目标路径无效：{exc}") from exc
    if not resolved.is_absolute():
        raise HTTPException(status_code=400, detail="传输目标须为绝对路径")
    return resolved.as_posix()


async def list_destinations_rows(db: AsyncSession) -> list[TransferDestination]:
    r = await db.execute(select(TransferDestination).order_by(TransferDestination.sort_order, TransferDestination.id))
    return list(r.scalars().all())


def destination_ready_from_stored_path(stored: str | None) -> bool:
    return transfer_target_ready(stored)


async def replace_all_destinations(
    db: AsyncSession,
    items: list[tuple[str, str]],
) -> None:
    """
    用新列表整表替换传输目标。
    items: (label, path_raw) 列表，path 会规范化后写入。
    """
    rows: list[TransferDestination] = []
    for order, (label_raw, path_raw) in enumerate(items):
        label = (label_raw or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail="每个传输目标的显示名称不能为空")
        path_norm = normalize_destination_path_for_storage(path_raw)
        rows.append(
            TransferDestination(
                label=label,
                path=path_norm,
                sort_order=order,
            ),
        )
    await db.execute(delete(TransferDestination))
    for row in rows:
        db.add(row)


async def get_destination_by_id(db: AsyncSession, dest_id: int) -> TransferDestination | None:
    return await db.get(TransferDestination, dest_id)
