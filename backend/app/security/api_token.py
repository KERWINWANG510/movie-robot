"""开放接口 API Token 的生成与哈希校验。"""

from __future__ import annotations

import hashlib
import secrets


def hash_api_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def generate_api_token() -> tuple[str, str, str]:
    """生成明文令牌、展示前缀、存储用哈希。

    返回 (plain, prefix, token_hash)。
    """
    plain = "mr_" + secrets.token_urlsafe(32)
    prefix = plain[:10]
    return plain, prefix, hash_api_token(plain)


def extract_bearer_or_api_key(authorization: str | None, x_api_key: str | None) -> str | None:
    """从 Authorization: Bearer 或 X-Api-Key 提取明文令牌。"""
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if not authorization:
        return None
    raw = authorization.strip()
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip()
        return token or None
    return None
