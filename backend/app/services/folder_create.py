"""在挂载根下创建单层文件夹。"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from app.services.path_security import PathNotAllowedError, resolve_under_root

_INVALID_NAME_CHARS = set('\\/:*?"<>|')


def create_folder_under_mount(*, root: Path, parent_rel: str, name: str) -> tuple[str, str]:
    """
    在 parent_rel（相对挂载根，空为根）下新建一层文件夹。
    返回 (相对挂载根路径, 文件夹名)。
    """
    folder_name = (name or "").strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="文件夹名称不能为空")
    if folder_name in (".", ".."):
        raise HTTPException(status_code=400, detail="文件夹名称无效")
    if any(c in _INVALID_NAME_CHARS for c in folder_name):
        raise HTTPException(
            status_code=400,
            detail='文件夹名称不能包含 \\ / : * ? " < > |',
        )
    if folder_name.endswith(".") or folder_name.endswith(" "):
        raise HTTPException(status_code=400, detail="文件夹名称不能以空格或点结尾")

    parent_raw = (parent_rel or "").strip().replace("\\", "/").lstrip("/")
    try:
        parent = root if not parent_raw else resolve_under_root(root, parent_raw)
    except PathNotAllowedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not parent.exists():
        raise HTTPException(status_code=404, detail="父目录不存在")
    if not parent.is_dir():
        raise HTTPException(status_code=400, detail="父路径不是目录")

    dest = (parent / folder_name).resolve()
    try:
        dest.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="路径超出挂载根") from exc

    if dest.exists():
        raise HTTPException(status_code=409, detail=f"已存在同名项：{folder_name}")

    try:
        dest.mkdir(parents=False, exist_ok=False)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"创建失败：{exc}") from exc

    rel = str(dest.relative_to(root.resolve())).replace("\\", "/")
    return rel, folder_name
