import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.system_config import SystemConfig
from app.models.user import User
from app.schemas.system_settings import (
    ModelsListResponse,
    ModelsProbeRequest,
    ModelOption,
    SystemSettingsPatch,
    SystemSettingsPublic,
)
from app.services.runtime_config import get_system_config_row

router = APIRouter(prefix="/settings", tags=["系统配置"])


def _row_to_public(row: SystemConfig | None) -> SystemSettingsPublic:
    env = get_settings()
    mount = (row.mount_path if row else "") or ""
    base = (row.openai_base_url if row else "") or ""
    model = (row.openai_model if row else "") or ""
    key_stored = (row.openai_api_key if row else "") or ""
    key_env = (env.openai_api_key or "").strip()
    has_key = bool(key_stored.strip()) or bool(key_env)
    ri = (getattr(row, "rename_instruction", "") or "") if row else ""
    return SystemSettingsPublic(
        mount_path=mount,
        openai_base_url=base,
        openai_model=model,
        rename_instruction=ri,
        has_openai_api_key=has_key,
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
    env = get_settings()
    row = await get_system_config_row(db)

    base = (body.openai_base_url or "").strip()
    key = (body.openai_api_key or "").strip()
    if not base and row:
        base = (row.openai_base_url or "").strip()
    if not base:
        base = env.openai_base_url.strip()
    if not key and row:
        key = (row.openai_api_key or "").strip()
    if not key:
        key = env.openai_api_key.strip()

    if not base or not key:
        raise HTTPException(status_code=400, detail="请先填写 API 地址与密钥，或在配置中保存后再试")

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
