from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.system_settings import (
    AiProviderOption,
    AiProvidersListResponse,
    ModelsListResponse,
    ModelsProbeRequest,
    ModelOption,
    SystemSettingsPatch,
    SystemSettingsPublic,
)
from app.services.ai_providers import ALLOWED_PROVIDER_IDS, list_presets_public, resolve_effective_base_url
from app.services.file_transfer import transfer_target_ready as _transfer_target_ready_flag
from app.services.runtime_config import get_system_config_row, resolve_probe_base_url

router = APIRouter(prefix="/settings", tags=["系统配置"])


def _normalize_ai_provider(raw: str | None) -> str:
    v = (raw or "custom").strip().lower()
    return v if v in ALLOWED_PROVIDER_IDS else "custom"


def _mount_ready(row: SystemConfig | None) -> bool:
    if row is None:
        return False
    raw = (row.mount_path or "").strip()
    if not raw:
        return False
    try:
        root = Path(raw).expanduser().resolve()
        return root.exists() and root.is_dir()
    except OSError:
        return False


def _row_to_public(row: SystemConfig | None) -> SystemSettingsPublic:
    mount = (row.mount_path if row else "") or ""
    base = (row.openai_base_url if row else "") or ""
    model = (row.openai_model if row else "") or ""
    key_stored = (row.openai_api_key if row else "") or ""
    key_in_db = bool(key_stored.strip())
    ri = (getattr(row, "rename_instruction", "") or "") if row else ""
    ap = _normalize_ai_provider(getattr(row, "ai_provider", None) if row else None)
    eff_base = resolve_effective_base_url(ai_provider=ap, stored_custom_url=base)
    ttp = (getattr(row, "transfer_target_path", "") or "") if row else ""
    return SystemSettingsPublic(
        mount_path=mount,
        transfer_target_path=ttp,
        ai_provider=ap,
        openai_base_url=base,
        effective_openai_base_url=eff_base,
        openai_model=model,
        rename_instruction=ri,
        api_key_saved_in_db=key_in_db,
        mount_ready=_mount_ready(row),
        transfer_target_ready=_transfer_target_ready_flag(ttp),
    )


@router.get("", response_model=SystemSettingsPublic)
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SystemSettingsPublic:
    row = await get_system_config_row(db)
    return _row_to_public(row)


@router.patch("", response_model=SystemSettingsPublic)
async def patch_system_settings(
    body: SystemSettingsPatch,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> SystemSettingsPublic:
    row = await get_system_config_row(db)
    if row is None:
        raise HTTPException(status_code=500, detail="系统配置未初始化")
    data = body.model_dump(exclude_unset=True)
    if "mount_path" in data and data["mount_path"] is not None:
        row.mount_path = data["mount_path"].strip()
    if "transfer_target_path" in data and data["transfer_target_path"] is not None:
        row.transfer_target_path = data["transfer_target_path"].strip()
    if "ai_provider" in data and data["ai_provider"] is not None:
        row.ai_provider = _normalize_ai_provider(data["ai_provider"])
    if "openai_base_url" in data and data["openai_base_url"] is not None:
        row.openai_base_url = data["openai_base_url"].strip()
    if "openai_model" in data and data["openai_model"] is not None:
        row.openai_model = data["openai_model"].strip()
    if "rename_instruction" in data and data["rename_instruction"] is not None:
        row.rename_instruction = data["rename_instruction"].strip()
    if "openai_api_key" in data:
        val = data["openai_api_key"]
        if val is None:
            pass
        else:
            row.openai_api_key = val.strip()
    await db.commit()
    await db.refresh(row)
    return _row_to_public(row)


@router.post("/models/list", response_model=ModelsListResponse)
async def list_remote_models(
    body: ModelsProbeRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ModelsListResponse:
    row = await get_system_config_row(db)

    base = resolve_probe_base_url(
        body_ai_provider=body.ai_provider,
        body_openai_base_url=body.openai_base_url,
        row=row,
    )
    key = (body.openai_api_key or "").strip()
    if not key and row:
        key = (row.openai_api_key or "").strip()

    if not base or not key:
        raise HTTPException(
            status_code=400,
            detail="请先填写 API 地址与密钥并保存到配置，或在上方输入框中填写后再获取模型列表",
        )

    url = base.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"获取模型列表失败：HTTP {exc.response.status_code}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=400, detail=f"请求失败：{exc}") from exc

    raw_list = payload.get("data")
    if not isinstance(raw_list, list):
        raise HTTPException(status_code=400, detail="接口返回格式异常（缺少 data 数组）")

    options: list[ModelOption] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        mid = item.get("id") or item.get("name") or item.get("model")
        if not isinstance(mid, str) or not mid.strip():
            continue
        label = mid
        owned = item.get("owned_by")
        if isinstance(owned, str) and owned:
            label = f"{mid} ({owned})"
        options.append(ModelOption(id=mid.strip(), label=label))

    options.sort(key=lambda x: x.id.lower())
    return ModelsListResponse(models=options)


@router.get("/ai/providers", response_model=AiProvidersListResponse)
async def list_ai_provider_presets(
    _user: User = Depends(get_current_user),
) -> AiProvidersListResponse:
    return AiProvidersListResponse(
        providers=[AiProviderOption(**p) for p in list_presets_public()],
    )
