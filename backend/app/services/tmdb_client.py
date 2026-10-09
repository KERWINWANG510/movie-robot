"""TMDB API 客户端（服务端代理，language=zh-CN）。"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.runtime_config import get_system_config_row

TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
TMDB_LANGUAGE = "zh-CN"


def poster_url(poster_path: str | None, size: str = "w500") -> str:
    path = (poster_path or "").strip()
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return f"{TMDB_IMAGE_BASE}/{size}{path}"


def backdrop_url(backdrop_path: str | None, size: str = "w780") -> str:
    return poster_url(backdrop_path, size=size)


async def require_tmdb_api_key(db: AsyncSession) -> str:
    row = await get_system_config_row(db)
    key = (getattr(row, "tmdb_api_key", "") or "").strip() if row else ""
    if not key:
        raise HTTPException(
            status_code=400,
            detail="请先在系统配置中填写并保存 TMDB API Key",
        )
    return key


async def tmdb_get(
    db: AsyncSession,
    path: str,
    *,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = await require_tmdb_api_key(db)
    query: dict[str, Any] = {"api_key": api_key, "language": TMDB_LANGUAGE}
    if params:
        query.update(params)
    url = f"{TMDB_API_BASE}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params=query)
            if r.status_code == 401:
                raise HTTPException(status_code=400, detail="TMDB API Key 无效或已失效，请在系统配置中更新")
            if r.status_code == 404:
                raise HTTPException(status_code=404, detail="未找到该影视条目")
            if r.status_code >= 400:
                detail = f"TMDB 请求失败：HTTP {r.status_code}"
                try:
                    body = r.json()
                    msg = body.get("status_message") if isinstance(body, dict) else None
                    if isinstance(msg, str) and msg.strip():
                        detail = f"TMDB 请求失败：{msg.strip()}"
                except Exception:
                    pass
                raise HTTPException(status_code=502, detail=detail)
            payload = r.json()
            if not isinstance(payload, dict):
                raise HTTPException(status_code=502, detail="TMDB 返回格式异常")
            return payload
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接 TMDB：{exc}") from exc


def _card_from_movie(item: dict[str, Any]) -> dict[str, Any]:
    poster = item.get("poster_path") or ""
    overview = item.get("overview") or ""
    if isinstance(overview, str) and len(overview) > 500:
        overview = overview[:500]
    return {
        "tmdb_id": int(item.get("id") or 0),
        "media_type": "movie",
        "title": (item.get("title") or item.get("name") or "").strip() or "未命名",
        "poster_path": poster if isinstance(poster, str) else "",
        "poster_url": poster_url(poster if isinstance(poster, str) else ""),
        "overview": overview if isinstance(overview, str) else "",
        "release_date": (item.get("release_date") or "") if isinstance(item.get("release_date"), str) else "",
        "vote_average": float(item.get("vote_average") or 0),
    }


def _card_from_tv(item: dict[str, Any]) -> dict[str, Any]:
    poster = item.get("poster_path") or ""
    overview = item.get("overview") or ""
    if isinstance(overview, str) and len(overview) > 500:
        overview = overview[:500]
    return {
        "tmdb_id": int(item.get("id") or 0),
        "media_type": "tv",
        "title": (item.get("name") or item.get("title") or "").strip() or "未命名",
        "poster_path": poster if isinstance(poster, str) else "",
        "poster_url": poster_url(poster if isinstance(poster, str) else ""),
        "overview": overview if isinstance(overview, str) else "",
        "release_date": (
            (item.get("first_air_date") or "") if isinstance(item.get("first_air_date"), str) else ""
        ),
        "vote_average": float(item.get("vote_average") or 0),
    }


def _card_from_multi(item: dict[str, Any]) -> dict[str, Any] | None:
    """将 multi/trending 条目转为卡片；忽略人物等非影视类型。"""
    mt = (item.get("media_type") or "").strip().lower()
    if mt == "movie":
        return _card_from_movie(item)
    if mt == "tv":
        return _card_from_tv(item)
    return None


async def fetch_now_playing_movies(db: AsyncSession, *, page: int = 1) -> dict[str, Any]:
    data = await tmdb_get(db, "/movie/now_playing", params={"page": page, "region": "CN"})
    results = data.get("results") if isinstance(data.get("results"), list) else []
    items = [_card_from_movie(x) for x in results if isinstance(x, dict) and x.get("id")]
    return {
        "items": items,
        "page": int(data.get("page") or page),
        "total_pages": int(data.get("total_pages") or 1),
        "total_results": int(data.get("total_results") or len(items)),
    }


async def fetch_on_the_air_tv(db: AsyncSession, *, page: int = 1) -> dict[str, Any]:
    data = await tmdb_get(db, "/tv/on_the_air", params={"page": page})
    results = data.get("results") if isinstance(data.get("results"), list) else []
    items = [_card_from_tv(x) for x in results if isinstance(x, dict) and x.get("id")]
    return {
        "items": items,
        "page": int(data.get("page") or page),
        "total_pages": int(data.get("total_pages") or 1),
        "total_results": int(data.get("total_results") or len(items)),
    }


async def fetch_trending_all(db: AsyncSession, *, page: int = 1) -> dict[str, Any]:
    """今日热门（电影 + 电视剧混合）。"""
    data = await tmdb_get(db, "/trending/all/day", params={"page": page})
    results = data.get("results") if isinstance(data.get("results"), list) else []
    items: list[dict[str, Any]] = []
    for x in results:
        if not isinstance(x, dict) or not x.get("id"):
            continue
        card = _card_from_multi(x)
        if card is not None:
            items.append(card)
    return {
        "items": items,
        "page": int(data.get("page") or page),
        "total_pages": int(data.get("total_pages") or 1),
        "total_results": int(data.get("total_results") or len(items)),
    }


async def search_media(
    db: AsyncSession,
    *,
    query: str,
    media_type: str,
    page: int = 1,
) -> dict[str, Any]:
    """按关键词搜索；media_type 为 all 时同时搜电影与电视剧。"""
    q = (query or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="请输入搜索关键词")
    mt = normalize_media_filter(media_type)
    if mt == "all":
        data = await tmdb_get(
            db, "/search/multi", params={"query": q, "page": page, "include_adult": "false"}
        )
        results = data.get("results") if isinstance(data.get("results"), list) else []
        items: list[dict[str, Any]] = []
        for x in results:
            if not isinstance(x, dict) or not x.get("id"):
                continue
            card = _card_from_multi(x)
            if card is not None:
                items.append(card)
    else:
        path = "/search/movie" if mt == "movie" else "/search/tv"
        data = await tmdb_get(db, path, params={"query": q, "page": page, "include_adult": "false"})
        results = data.get("results") if isinstance(data.get("results"), list) else []
        card_fn = _card_from_movie if mt == "movie" else _card_from_tv
        items = [card_fn(x) for x in results if isinstance(x, dict) and x.get("id")]
    return {
        "items": items,
        "page": int(data.get("page") or page),
        "total_pages": int(data.get("total_pages") or 1),
        "total_results": int(data.get("total_results") or len(items)),
    }


def normalize_media_type(raw: str) -> str:
    v = (raw or "").strip().lower()
    if v not in ("movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type 仅支持 movie 或 tv")
    return v


def normalize_media_filter(raw: str) -> str:
    """列表/搜索筛选：all | movie | tv。"""
    v = (raw or "").strip().lower()
    if v not in ("all", "movie", "tv"):
        raise HTTPException(status_code=400, detail="media_type 仅支持 all、movie 或 tv")
    return v


_CREW_JOB_PRIORITY = (
    "Director",
    "Creator",
    "Writer",
    "Screenplay",
    "Story",
    "Novel",
    "Producer",
    "Executive Producer",
    "Director of Photography",
    "Original Music Composer",
    "Composer",
    "Editor",
)

_CREW_JOB_LABELS_ZH = {
    "Director": "导演",
    "Creator": "创作者",
    "Writer": "编剧",
    "Screenplay": "剧本",
    "Story": "故事",
    "Novel": "原著",
    "Producer": "制片人",
    "Executive Producer": "执行制片人",
    "Director of Photography": "摄影指导",
    "Original Music Composer": "配乐",
    "Composer": "配乐",
    "Editor": "剪辑",
}


def _person_credit(
    *,
    person_id: int,
    name: str,
    role: str,
    profile_path: str,
) -> dict[str, Any]:
    return {
        "person_id": person_id,
        "name": name,
        "role": role,
        "profile_path": profile_path,
        "profile_url": poster_url(profile_path, size="w185"),
    }


def _parse_credits(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    credits = data.get("credits")
    if not isinstance(credits, dict):
        credits = {}

    cast_out: list[dict[str, Any]] = []
    cast_raw = credits.get("cast") if isinstance(credits.get("cast"), list) else []
    for item in cast_raw:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        profile = item.get("profile_path") or ""
        character = (item.get("character") or "").strip()
        cast_out.append(
            _person_credit(
                person_id=int(item["id"]),
                name=name,
                role=character,
                profile_path=profile if isinstance(profile, str) else "",
            ),
        )
        if len(cast_out) >= 40:
            break

    crew_out: list[dict[str, Any]] = []
    seen_crew: set[tuple[int, str]] = set()
    crew_raw = credits.get("crew") if isinstance(credits.get("crew"), list) else []
    by_job: dict[str, list[dict[str, Any]]] = {j: [] for j in _CREW_JOB_PRIORITY}
    for item in crew_raw:
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        job = (item.get("job") or "").strip()
        if job not in by_job:
            continue
        by_job[job].append(item)

    for job in _CREW_JOB_PRIORITY:
        for item in by_job[job]:
            pid = int(item["id"])
            key = (pid, job)
            if key in seen_crew:
                continue
            seen_crew.add(key)
            name = (item.get("name") or "").strip()
            if not name:
                continue
            profile = item.get("profile_path") or ""
            role_zh = _CREW_JOB_LABELS_ZH.get(job, job)
            crew_out.append(
                _person_credit(
                    person_id=pid,
                    name=name,
                    role=role_zh,
                    profile_path=profile if isinstance(profile, str) else "",
                ),
            )
            if len(crew_out) >= 24:
                break
        if len(crew_out) >= 24:
            break

    # 剧集 created_by 补充为「创作者」，若 credits 中尚未包含
    created_by = data.get("created_by") if isinstance(data.get("created_by"), list) else []
    for item in created_by:
        if len(crew_out) >= 24:
            break
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        pid = int(item["id"])
        if any(c["person_id"] == pid and c["role"] == "创作者" for c in crew_out):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        profile = item.get("profile_path") or ""
        crew_out.insert(
            0,
            _person_credit(
                person_id=pid,
                name=name,
                role="创作者",
                profile_path=profile if isinstance(profile, str) else "",
            ),
        )

    return cast_out[:40], crew_out[:24]


def _parse_similar_items(data: dict[str, Any], media_type: str, *, limit: int = 12) -> list[dict[str, Any]]:
    """合并 recommendations 与 similar，去重后取前 limit 条。"""
    card_fn = _card_from_movie if media_type == "movie" else _card_from_tv
    out: list[dict[str, Any]] = []
    seen: set[int] = set()

    for key in ("recommendations", "similar"):
        block = data.get(key)
        if not isinstance(block, dict):
            continue
        results = block.get("results") if isinstance(block.get("results"), list) else []
        for item in results:
            if not isinstance(item, dict) or item.get("id") is None:
                continue
            tid = int(item["id"])
            if tid in seen:
                continue
            seen.add(tid)
            card = card_fn(item)
            if card.get("tmdb_id"):
                out.append(card)
            if len(out) >= limit:
                return out
    return out


async def fetch_media_detail(db: AsyncSession, media_type: str, tmdb_id: int) -> dict[str, Any]:
    mt = normalize_media_type(media_type)
    path = f"/movie/{tmdb_id}" if mt == "movie" else f"/tv/{tmdb_id}"
    data = await tmdb_get(
        db,
        path,
        params={"append_to_response": "credits,similar,recommendations"},
    )
    poster = data.get("poster_path") or ""
    backdrop = data.get("backdrop_path") or ""
    genres_raw = data.get("genres") if isinstance(data.get("genres"), list) else []
    genres = []
    for g in genres_raw:
        if isinstance(g, dict) and g.get("id") is not None:
            genres.append({"id": int(g["id"]), "name": str(g.get("name") or "")})

    if mt == "movie":
        title = (data.get("title") or "").strip() or "未命名"
        original_title = (data.get("original_title") or "").strip()
        release_date = data.get("release_date") if isinstance(data.get("release_date"), str) else ""
        runtime = data.get("runtime")
    else:
        title = (data.get("name") or "").strip() or "未命名"
        original_title = (data.get("original_name") or "").strip()
        release_date = data.get("first_air_date") if isinstance(data.get("first_air_date"), str) else ""
        runtime = data.get("episode_run_time")
        if isinstance(runtime, list) and runtime:
            runtime = runtime[0]
        elif isinstance(runtime, list):
            runtime = None

    overview = data.get("overview") or ""
    if not isinstance(overview, str):
        overview = ""

    cast, crew = _parse_credits(data)
    similar = _parse_similar_items(data, mt, limit=20)

    return {
        "tmdb_id": int(data.get("id") or tmdb_id),
        "media_type": mt,
        "title": title,
        "original_title": original_title if isinstance(original_title, str) else "",
        "poster_path": poster if isinstance(poster, str) else "",
        "poster_url": poster_url(poster if isinstance(poster, str) else ""),
        "backdrop_path": backdrop if isinstance(backdrop, str) else "",
        "backdrop_url": backdrop_url(backdrop if isinstance(backdrop, str) else ""),
        "overview": overview,
        "release_date": release_date or "",
        "vote_average": float(data.get("vote_average") or 0),
        "vote_count": int(data.get("vote_count") or 0),
        "runtime": int(runtime) if isinstance(runtime, (int, float)) else None,
        "genres": genres,
        "status": str(data.get("status") or ""),
        "cast": cast,
        "crew": crew,
        "similar": similar,
    }
