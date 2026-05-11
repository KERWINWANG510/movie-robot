"""将挂载根内的文件或目录复制/移动到配置的传输目标目录（可在挂载外）。"""

import shutil
from pathlib import Path
from typing import Literal

from fastapi import HTTPException

from app.services.folder_merge import uniquify_filename
from app.services.path_security import PathNotAllowedError, resolve_under_root

TransferMode = Literal["copy", "move"]


def resolve_transfer_target_directory(raw: str | None) -> Path:
    """解析配置中的传输目标为绝对目录路径；须非空、存在且为目录。"""
    s = (raw or "").strip()
    if not s:
        raise HTTPException(status_code=400, detail="请先在系统配置中填写传输目标目录")
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


def _copy_tree(src: Path, dst: Path) -> None:
    """将目录 src 复制到不存在的目标目录 dst（单层根名已 uniquify）。"""
    shutil.copytree(src, dst, symlinks=False, dirs_exist_ok=False, ignore_dangling_symlinks=True)


def transfer_paths_to_target(
    *,
    mount_root: Path,
    transfer_target: Path,
    source_rel_paths: list[str],
    mode: TransferMode,
) -> list[tuple[str, str, bool, str | None]]:
    """
    将若干挂载根相对路径复制或移动到 transfer_target 下。
    返回 (源相对挂载根路径, 目标绝对路径 posix, 成功, 错误信息)
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

    results: list[tuple[str, str, bool, str | None]] = []

    for src in sorted(resolved_sources, key=lambda x: str(x).lower()):
        src_rel = _rel_under_mount(root, src)
        try:
            if src.is_file():
                final_name = uniquify_filename(tt, src.name)
                dest_abs = (tt / final_name).resolve()
                if mode == "copy":
                    shutil.copy2(src, dest_abs)
                else:
                    shutil.move(str(src), str(dest_abs))
                results.append((src_rel, dest_abs.as_posix(), True, None))
            elif src.is_dir():
                top_name = uniquify_filename(tt, src.name)
                dest_root = (tt / top_name).resolve()
                if mode == "copy":
                    _copy_tree(src, dest_root)
                else:
                    shutil.move(str(src), str(dest_root))
                results.append((src_rel, dest_root.as_posix(), True, None))
            else:
                results.append((src_rel, "", False, "源路径既不是文件也不是目录"))
        except OSError as exc:
            results.append((src_rel, "", False, str(exc)))

    return results
