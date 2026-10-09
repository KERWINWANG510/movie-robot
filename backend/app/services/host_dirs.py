"""列出本机/容器内的绝对目录，供存储配置选择挂载根与传输目标。"""

from __future__ import annotations

import os
import string
from pathlib import Path

from fastapi import HTTPException

from app.schemas.system_settings import HostDirBrowseResponse, HostDirEntry

_MAX_ENTRIES = 400
_SKIP_ROOT_NAMES = frozenset({"proc", "sys", "dev", "run"})


def _native_path(p: Path) -> str:
    resolved = p.resolve()
    if os.name == "nt":
        return str(resolved)
    return resolved.as_posix()


def _drive_roots() -> list[HostDirEntry]:
    roots: list[HostDirEntry] = []
    listdrives = getattr(os, "listdrives", None)
    candidates: list[str] = []
    if callable(listdrives):
        try:
            candidates = list(listdrives())
        except OSError:
            candidates = []
    if not candidates:
        candidates = [f"{ch}:\\" for ch in string.ascii_uppercase]
    seen: set[str] = set()
    for raw in candidates:
        try:
            p = Path(raw)
            if not p.exists() or not p.is_dir():
                continue
            path = _native_path(p)
            if path in seen:
                continue
            seen.add(path)
            name = path.rstrip("\\/") or path
            roots.append(HostDirEntry(name=name, path=path))
        except OSError:
            continue
    return roots


def list_host_directories(path: str) -> HostDirBrowseResponse:
    """path 为空时返回盘符或 /；否则列出该绝对路径下的子目录。"""
    raw = (path or "").strip()
    if not raw:
        if os.name == "nt":
            return HostDirBrowseResponse(path="", entries=_drive_roots())
        return HostDirBrowseResponse(
            path="",
            entries=[HostDirEntry(name="/", path="/")],
        )

    try:
        base = Path(raw).expanduser()
        if not base.is_absolute():
            raise HTTPException(status_code=400, detail="请选择绝对路径")
        base = base.resolve()
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"路径无效：{exc}") from exc

    if not base.exists():
        raise HTTPException(status_code=404, detail="目录不存在")
    if not base.is_dir():
        raise HTTPException(status_code=400, detail="目标不是目录")

    at_unix_root = os.name != "nt" and base.as_posix() == "/"
    entries: list[HostDirEntry] = []
    try:
        children = sorted(base.iterdir(), key=lambda p: p.name.lower())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="没有权限读取该目录") from exc
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"无法列出目录：{exc}") from exc

    for child in children:
        if len(entries) >= _MAX_ENTRIES:
            break
        if at_unix_root and child.name.lower() in _SKIP_ROOT_NAMES:
            continue
        try:
            if not child.is_dir():
                continue
            entries.append(HostDirEntry(name=child.name, path=_native_path(child)))
        except OSError:
            continue

    return HostDirBrowseResponse(path=_native_path(base), entries=entries)
