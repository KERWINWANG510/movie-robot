"""内置 OpenAI 兼容 API 服务商预设（Base URL）；自定义模式使用库内用户填写的地址。"""

from typing import TypedDict


class AiProviderPreset(TypedDict):
    id: str
    label: str
    base_url: str


# 均为常见 OpenAI-compatible Chat Completions + /v1/models 形态（各厂商以官方文档为准）。
PRESETS: list[AiProviderPreset] = [
    {"id": "openai", "label": "OpenAI（ChatGPT）", "base_url": "https://api.openai.com/v1"},
    {"id": "deepseek", "label": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
    {"id": "qwen", "label": "通义千问（DashScope 兼容模式）", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    {"id": "moonshot", "label": "Moonshot（Kimi）", "base_url": "https://api.moonshot.cn/v1"},
    {"id": "glm", "label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4"},
    {"id": "doubao", "label": "豆包（火山方舟，北京）", "base_url": "https://ark.cn-beijing.volces.com/api/v3"},
    {"id": "siliconflow", "label": "SiliconFlow", "base_url": "https://api.siliconflow.cn/v1"},
    {"id": "groq", "label": "Groq", "base_url": "https://api.groq.com/openai/v1"},
    {"id": "openrouter", "label": "OpenRouter", "base_url": "https://openrouter.ai/api/v1"},
]

PRESET_BY_ID: dict[str, AiProviderPreset] = {p["id"]: p for p in PRESETS}

ALLOWED_PROVIDER_IDS: frozenset[str] = frozenset({"custom", *PRESET_BY_ID.keys()})


def preset_base_url(provider_id: str) -> str:
    p = PRESET_BY_ID.get(provider_id.strip().lower())
    return p["base_url"] if p else ""


def resolve_effective_base_url(*, ai_provider: str, stored_custom_url: str) -> str:
    """自定义模式用库内 URL；预设模式用内置 URL（库内 openai_base_url 可留空）。"""
    pid = (ai_provider or "custom").strip().lower()
    if pid == "custom":
        return (stored_custom_url or "").strip()
    return preset_base_url(pid) or (stored_custom_url or "").strip()


def list_presets_public() -> list[AiProviderPreset]:
    return list(PRESETS)
