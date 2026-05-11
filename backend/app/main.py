from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, files, rename, system_settings, users
from app.bootstrap import ensure_builtin_admin, ensure_system_config
from app.config import get_settings
from app.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Path("data").mkdir(parents=True, exist_ok=True)
    await init_db()
    await ensure_system_config()
    await ensure_builtin_admin()
    yield


app = FastAPI(title="Movie Robot API", lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    max_age=settings.session_max_age,
    same_site="lax",
    https_only=settings.session_https_only,
    session_cookie=settings.session_cookie_name,
)

_cors_allow_list = settings.cors_origin_list
if _cors_allow_list:
    # 配置了来源列表：严格只允许列表内的 Origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_allow_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 未配置：不限制来源（允许任意 Origin）。注意：携带 Cookie 时不能用 "*"，因此用正则匹配并回显 Origin。
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(rename.router, prefix="/api/v1")
app.include_router(system_settings.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


_static_root = Path(__file__).resolve().parent.parent / "static"


def _safe_file_under_static(rel: str) -> Path | None:
    base = _static_root.resolve()
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        return None
    if target.is_file():
        return target
    return None


if _static_root.is_dir():

    @app.get("/")
    async def _spa_root():
        return FileResponse(_static_root / "index.html")

    @app.get("/{full_path:path}")
    async def _spa_assets(full_path: str):
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not Found")
        direct = _safe_file_under_static(full_path)
        if direct is not None:
            return FileResponse(direct)
        return FileResponse(_static_root / "index.html")
