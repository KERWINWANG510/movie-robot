from pathlib import Path


class PathNotAllowedError(ValueError):
    pass


def resolve_under_root(root: Path, relative_path: str) -> Path:
    """将相对路径解析为挂载根之下的绝对路径，防止路径穿越。"""
    root = root.resolve()
    rel = relative_path.strip().replace("\\", "/").lstrip("/")
    if ".." in rel.split("/"):
        raise PathNotAllowedError("路径中不允许包含 ..")
    target = (root / rel).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PathNotAllowedError("路径超出允许的根目录") from exc
    return target
