import json
import re

import httpx

from app.services.runtime_config import AiCallParams


async def suggest_filenames(
    ai: AiCallParams,
    *,
    relative_paths: list[str],
    naming_hint: str | None = None,
) -> dict[str, str | None]:
    """
    调用 OpenAI 兼容接口，返回 path -> 建议文件名（不含路径）。
    失败的路径对应值为 None。
    """
    if not ai.openai_api_key.strip():
        return {p: None for p in relative_paths}

    hint_text = (naming_hint or ai.rename_instruction or "").strip()

    system = (
        "你是文件命名助手。用户会提供相对于根目录的文件路径列表。"
        "请为每个文件输出 JSON 对象，键 path 为输入中的完整相对路径（逐字一致），"
        "键 suggested_name 为仅含文件名的建议新文件名（保留合理扩展名）。"
        "不要包含路径分隔符。非法字符替换为下划线。"
        "输出必须是 JSON：{\"items\":[{\"path\":\"...\",\"suggested_name\":\"...\"}]}。"
    )
    if hint_text:
        system += (
            "\n\n【用户对重命名方式的自然语言说明】（必须优先遵守；若与默认规则冲突，以说明为准）：\n"
            + hint_text
        )

    user_payload = {
        "paths": relative_paths,
        "rename_instruction": hint_text,
    }
    url = ai.openai_base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": ai.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {ai.openai_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    items = parsed.get("items") or []
    result: dict[str, str | None] = {p: None for p in relative_paths}
    for it in items:
        p = it.get("path")
        name = it.get("suggested_name")
        if isinstance(p, str) and isinstance(name, str) and p in result:
            cleaned = _sanitize_filename(name)
            result[p] = cleaned if cleaned else None
    return result


def _sanitize_filename(name: str) -> str:
    name = name.strip().split("/")[-1].split("\\")[-1]
    name = re.sub(r'[<>:"|?*\x00-\x1f]', "_", name)
    return name[:240] if name else ""
