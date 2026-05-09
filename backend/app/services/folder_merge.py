"""将多个源目录下的文件扁平合并到目标目录，重名自动加序号。"""

import shutil
from pathlib import Path

from fastapi import HTTPException

from app.services.path_security import PathNotAllowedError, resolve_under_root


def uniquify_filename(dest_dir: Path, filename: str) -> str:
    """在 dest_dir 下生成不冲突的文件名（原文件名可用则不变，否则 name_1.ext）。"""
    if not (dest_dir / filename).exists():
        return filename
    p = Path(filename)
    stem, suffix = p.stem, p.suffix
    n = 1
    while True:
        alt = f"{stem}_{n}{suffix}"
        if not (dest_dir / alt).exists():
            return alt
        n += 1


def _no_nested_sources(resolved_sources: list[Path]) -> None:
    for i, a in enumerate(resolved_sources):
        for j, b in enumerate(resolved_sources):
            if i == j:
                continue
            try:
                b.relative_to(a)
            except ValueError:
                continue
            raise HTTPException(
                status_code=400,
                detail="源文件夹列表中不能包含互为父子关系的目录，请去掉内层或外层其一",
            )


def _validate_target_vs_sources(target: Path, resolved_sources: list[Path]) -> None:
    tr = target.resolve()
    for s in resolved_sources:
        sr = s.resolve()
        if tr == sr:
            raise HTTPException(status_code=400, detail="合并目标不能与某个源文件夹相同")
        try:
            tr.relative_to(sr)
        except ValueError:
            continue
        raise HTTPException(
            status_code=400,
            detail="合并目标不能位于某个源文件夹内部，请另选目标目录",
        )


def merge_folder_trees_flat(
    *,
    root: Path,
    source_rel_paths: list[str],
    target_rel: str,
) -> list[tuple[str, str, bool, str | None]]:
    """
    将每个源目录下（递归）所有文件移动到 target 下，扁平存放。
    返回列表: (源相对路径, 目标相对路径, 成功, 错误信息)
    """
    if len(source_rel_paths) < 2:
        raise HTTPException(status_code=400, detail="请至少选择两个源文件夹")

    root = root.resolve()
    try:
        target_abs = resolve_under_root(root, target_rel.strip())
    except PathNotAllowedError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if target_abs.exists() and not target_abs.is_dir():
        raise HTTPException(status_code=400, detail="目标路径已存在且不是目录")

    resolved_sources: list[Path] = []
    for rel in source_rel_paths:
        rel = rel.strip().replace("\\", "/").lstrip("/")
        if not rel:
            raise HTTPException(status_code=400, detail="源路径不能为空")
        try:
            p = resolve_under_root(root, rel)
        except PathNotAllowedError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"源目录不存在：{rel}")
        if not p.is_dir():
            raise HTTPException(status_code=400, detail=f"源路径不是目录：{rel}")
        resolved_sources.append(p)

    seen: set[Path] = set()
    deduped: list[Path] = []
    for p in resolved_sources:
        k = p.resolve()
        if k in seen:
            continue
        seen.add(k)
        deduped.append(p)
    resolved_sources = deduped
    if len(resolved_sources) < 2:
        raise HTTPException(status_code=400, detail="请至少选择两个不同的源文件夹")

    _no_nested_sources(resolved_sources)
    _validate_target_vs_sources(target_abs, resolved_sources)

    try:
        target_abs.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"无法创建目标目录：{exc}") from exc
    if not target_abs.is_dir():
        raise HTTPException(status_code=400, detail="目标路径不是目录")

    results: list[tuple[str, str, bool, str | None]] = []

    def rel_under_root(abs_path: Path) -> str:
        return str(abs_path.resolve().relative_to(root)).replace("\\", "/")

    # 收集所有待移动文件（源绝对路径），按路径排序保证稳定
    to_move: list[Path] = []
    for src_dir in resolved_sources:
        for f in sorted(src_dir.rglob("*"), key=lambda x: str(x).lower()):
            if f.is_file():
                to_move.append(f)

    for src_file in to_move:
        src_rel = rel_under_root(src_file)
        try:
            final_name = uniquify_filename(target_abs, src_file.name)
            dest_abs = target_abs / final_name
            shutil.move(str(src_file), str(dest_abs))
            results.append((src_rel, rel_under_root(dest_abs), True, None))
        except OSError as exc:
            results.append((src_rel, "", False, str(exc)))

    return results
