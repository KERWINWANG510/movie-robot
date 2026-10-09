"""将挂载根内的文件或目录复制/移动到配置的传输目标目录（可在挂载外）。"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, Literal

from fastapi import HTTPException

from app.services.folder_merge import uniquify_filename
from app.services.path_security import PathNotAllowedError, ensure_path_str_no_parent_ref_segments, resolve_under_root

TransferMode = Literal["copy", "move"]
ProgressCallback = Callable[[dict[str, Any]], None]


def resolve_transfer_target_directory(raw: str | None) -> Path:
    """解析配置中的传输目标为绝对目录路径；须非空、存在且为目录。"""
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写传输目标目录")
    try:
        ensure_path_str_no_parent_ref_segments(s)
    except PathNotAllowedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        p = Path(s).expanduser().resolve()
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"传输目标路径无效：{exc}") from exc
    if not p.exists():
        raise HTTPException(status_code=400, detail="传输目标路径不存在或不可访问")
    if not p.is_dir():
        raise HTTPException(status_code=400, detail="传输目标路径不是目录")
    return p


def transfer_target_ready(raw: str | None) -> bool:
    """与 mount_ready 类似：配置非空且解析后为已存在目录则 True。"""
    s = (raw or "").strip()
    if not s:
        return False
    try:
        ensure_path_str_no_parent_ref_segments(s)
    except PathNotAllowedError:
        return False
    try:
        p = Path(s).expanduser().resolve()
        return p.exists() and p.is_dir()
    except OSError:
        return False


def _no_nested_sources(resolved: list[Path]) -> None:
    """任意被选路径不能是另一路径的子路径。"""
    norm = [p.resolve() for p in resolved]
    for i, a in enumerate(norm):
        for j, b in enumerate(norm):
            if i == j:
                continue
            try:
                b.relative_to(a)
            except ValueError:
                continue
            raise HTTPException(
                status_code=400,
                detail="所选路径不能互为包含关系（例如不要同时勾选文件夹与其中的文件或子文件夹）",
            )


def _reject_transfer_inside_sources(transfer: Path, sources: list[Path]) -> None:
    tr = transfer.resolve()
    for s in sources:
        sr = s.resolve()
        if tr == sr:
            raise HTTPException(status_code=400, detail="传输目标不能与某个待传输的路径相同")
        try:
            tr.relative_to(sr)
        except ValueError:
            continue
        raise HTTPException(
            status_code=400,
            detail="传输目标不能位于某个待传输的文件或文件夹内部",
        )


def _reject_transfer_is_mount_root(transfer: Path, mount_root: Path) -> None:
    if transfer.resolve() == mount_root.resolve():
        raise HTTPException(status_code=400, detail="传输目标不能与挂载根目录相同")


def _rel_under_mount(mount_root: Path, abs_path: Path) -> str:
    return str(abs_path.resolve().relative_to(mount_root.resolve())).replace("\\", "/")


_CHUNK_SIZE = 1024 * 1024
_EMIT_EVERY_BYTES = 256 * 1024


def _file_size(path: Path) -> int:
    try:
        return int(path.stat().st_size)
    except OSError:
        return 0


def _count_bytes(src: Path) -> int:
    """待传输内容的总字节数（目录递归统计文件）。"""
    if src.is_file():
        return _file_size(src)
    if not src.is_dir():
        return 0
    total = 0
    for full, _rel in _iter_dir_files(src):
        total += _file_size(full)
    return total


def _same_filesystem(src: Path, dest_parent: Path) -> bool:
    try:
        return src.stat().st_dev == dest_parent.stat().st_dev
    except OSError:
        return False


def _iter_dir_files(src: Path) -> Iterator[tuple[Path, str]]:
    for root, _dirs, files in os.walk(src):
        for name in files:
            full = Path(root) / name
            rel = full.relative_to(src).as_posix()
            yield full, rel


def _copy_file_with_progress(
    src: Path,
    dest: Path,
    *,
    display_name: str,
    add_bytes: Callable[[int, str], None],
) -> None:
    """分块复制并按字节上报进度，保留元数据。"""
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = _file_size(src)
    with open(src, "rb") as fsrc, open(dest, "wb") as fdst:
        while True:
            chunk = fsrc.read(_CHUNK_SIZE)
            if not chunk:
                break
            fdst.write(chunk)
            add_bytes(len(chunk), display_name)
    shutil.copystat(src, dest, follow_symlinks=True)
    if size == 0:
        add_bytes(0, display_name)


def _copy_tree_with_progress(
    src: Path,
    dest_root: Path,
    add_bytes: Callable[[int, str], None],
) -> None:
    dest_root.mkdir(parents=True, exist_ok=False)
    file_count = 0
    for full, rel in _iter_dir_files(src):
        _copy_file_with_progress(full, dest_root / rel, display_name=rel, add_bytes=add_bytes)
        file_count += 1
    if file_count == 0:
        add_bytes(0, src.name)


def _move_with_progress(
    src: Path,
    dest: Path,
    *,
    display_name: str,
    byte_total: int,
    add_bytes: Callable[[int, str], None],
) -> None:
    """同盘直接移动并一次性计入容量；跨盘则分块复制后删除源。"""
    dest_parent = dest.parent
    dest_parent.mkdir(parents=True, exist_ok=True)
    if _same_filesystem(src, dest_parent):
        shutil.move(str(src), str(dest))
        add_bytes(byte_total if byte_total > 0 else 0, display_name)
        return
    if src.is_file():
        _copy_file_with_progress(src, dest, display_name=display_name, add_bytes=add_bytes)
        src.unlink()
        return
    if src.is_dir():
        _copy_tree_with_progress(src, dest, add_bytes)
        shutil.rmtree(src)
        return
    raise OSError("源路径既不是文件也不是目录")


def transfer_paths_to_target(
    *,
    mount_root: Path,
    transfer_target: Path,
    source_rel_paths: list[str],
    mode: TransferMode,
    on_progress: ProgressCallback | None = None,
) -> list[tuple[str, str, bool, str | None]]:
    """
    将若干挂载根相对路径复制或移动到 transfer_target 下。
    返回 (源相对挂载根路径, 目标绝对路径 posix, 成功, 错误信息)
    on_progress 可选，接收 {"event","done","total","current","unit"}；
    done/total 为字节数（unit=bytes）。
    """
    if not source_rel_paths:
        raise HTTPException(status_code=400, detail="请至少选择一项要传输的路径")

    root = mount_root.resolve()
    tt = transfer_target.resolve()
    _reject_transfer_is_mount_root(tt, root)

    resolved_sources: list[Path] = []
    seen: set[Path] = set()
    for rel in source_rel_paths:
        r = rel.strip().replace("\\", "/").lstrip("/")
        if not r:
            raise HTTPException(status_code=400, detail="源路径不能为空")
        try:
            p = resolve_under_root(root, r)
        except PathNotAllowedError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"源路径不存在：{r}")
        key = p.resolve()
        if key in seen:
            continue
        seen.add(key)
        resolved_sources.append(p)

    if not resolved_sources:
        raise HTTPException(status_code=400, detail="没有有效的待传输路径")

    _no_nested_sources(resolved_sources)
    _reject_transfer_inside_sources(tt, resolved_sources)

    total = sum(_count_bytes(s) for s in resolved_sources)
    # 全空目录/空文件时仍给出可推进的进度刻度
    progress_total = total if total > 0 else max(len(resolved_sources), 1)
    done = 0
    last_emit = 0

    def emit(current: str = "", *, force: bool = False) -> None:
        nonlocal last_emit
        if not on_progress:
            return
        if not force and done - last_emit < _EMIT_EVERY_BYTES and done < progress_total:
            return
        last_emit = done
        on_progress(
            {
                "event": "progress",
                "done": done,
                "total": progress_total,
                "current": current,
                "unit": "bytes" if total > 0 else "items",
            }
        )

    def add_bytes(n: int, current: str = "") -> None:
        nonlocal done
        if total > 0:
            done = min(done + max(n, 0), progress_total)
        else:
            # 无容量可计时按项推进
            done = min(done + 1, progress_total)
        emit(current)

    if on_progress:
        on_progress(
            {
                "event": "start",
                "done": 0,
                "total": progress_total,
                "item_count": len(resolved_sources),
                "unit": "bytes" if total > 0 else "items",
            }
        )

    results: list[tuple[str, str, bool, str | None]] = []

    for src in sorted(resolved_sources, key=lambda x: str(x).lower()):
        src_rel = _rel_under_mount(root, src)
        src_bytes = _count_bytes(src)
        expected = src_bytes if total > 0 else 1
        done_before = done
        try:
            if src.is_file():
                final_name = uniquify_filename(tt, src.name)
                dest_abs = (tt / final_name).resolve()
                if mode == "copy":
                    _copy_file_with_progress(src, dest_abs, display_name=src.name, add_bytes=add_bytes)
                else:
                    _move_with_progress(
                        src,
                        dest_abs,
                        display_name=src.name,
                        byte_total=src_bytes,
                        add_bytes=add_bytes,
                    )
                results.append((src_rel, dest_abs.as_posix(), True, None))
            elif src.is_dir():
                top_name = uniquify_filename(tt, src.name)
                dest_root = (tt / top_name).resolve()
                if mode == "copy":
                    _copy_tree_with_progress(src, dest_root, add_bytes)
                else:
                    _move_with_progress(
                        src,
                        dest_root,
                        display_name=src.name,
                        byte_total=src_bytes,
                        add_bytes=add_bytes,
                    )
                results.append((src_rel, dest_root.as_posix(), True, None))
            else:
                results.append((src_rel, "", False, "源路径既不是文件也不是目录"))
                if done < done_before + expected:
                    add_bytes(expected - (done - done_before), src.name)
        except OSError as exc:
            results.append((src_rel, "", False, str(exc)))
            remain = done_before + expected - done
            if remain > 0:
                add_bytes(remain, src.name)

    if on_progress:
        done = progress_total
        on_progress(
            {
                "event": "complete",
                "done": done,
                "total": progress_total,
                "unit": "bytes" if total > 0 else "items",
            }
        )

    return results
