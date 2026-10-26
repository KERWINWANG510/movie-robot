"""在挂载根下删除文件或文件夹（支持批量）。"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import HTTPException

from app.services.path_security import PathNotAllowedError, resolve_under_root


def _collapse_nested_rel_paths(rel_paths: list[str]) -> list[str]:
    """若同时勾选父目录与其下子项，只保留父路径（删父即含子项）。"""
    norms = sorted(
        {p.strip().replace("\\", "/").lstrip("/") for p in rel_paths if (p or "").strip()},
        key=lambda s: (s.count("/"), s.lower()),
    )
    kept: list[str] = []
    for p in norms:
        under_kept = False
        for k in kept:
            if p == k or p.startswith(k + "/"):
                under_kept = True
                break
        if not under_kept:
            kept.append(p)
    return kept


def delete_paths_under_mount(
    *,
    root: Path,
    paths: list[str],
) -> list[tuple[str, bool, bool, str | None]]:
    """
    删除相对挂载根的路径。
    返回 [(path, is_dir, ok, message), ...]。
    """
    if not paths:
        raise HTTPException(status_code=400, detail="请至少选择一项要删除的文件或文件夹")

    collapsed = _collapse_nested_rel_paths(paths)
    if not collapsed:
        raise HTTPException(status_code=400, detail="请至少选择一项要删除的文件或文件夹")

    root_r = root.resolve()
    results: list[tuple[str, bool, bool, str | None]] = []

    # 先删更深路径，避免父目录先删导致子路径报错（折叠后通常无此问题）
    ordered = sorted(collapsed, key=lambda s: (-s.count("/"), s.lower()))

    for rel in ordered:
        if not rel:
            results.append(("", True, False, "不能删除挂载根目录"))
            continue
        try:
            target = resolve_under_root(root_r, rel)
        except PathNotAllowedError as exc:
            results.append((rel, False, False, str(exc)))
            continue

        if target == root_r:
            results.append((rel, True, False, "不能删除挂载根目录"))
            continue

        if not target.exists():
            results.append((rel, False, False, "路径不存在"))
            continue

        is_dir = target.is_dir()
        try:
            if is_dir:
                shutil.rmtree(target)
            else:
                target.unlink()
            results.append((rel, is_dir, True, None))
        except PermissionError:
            results.append((rel, is_dir, False, "没有权限删除"))
        except OSError as exc:
            results.append((rel, is_dir, False, f"删除失败：{exc}"))

    return results
