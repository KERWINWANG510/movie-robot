"""开放接口目录（供管理页清单与在线调试共用）。"""

from app.schemas.open_api import (
    OpenApiCatalogEndpoint,
    OpenApiCatalogField,
    OpenApiCatalogParam,
    OpenApiCatalogResponse,
)

_AUTH_HEADER = OpenApiCatalogParam(
    name="Authorization",
    location="header",
    type="string",
    required=True,
    description="Bearer <API Key>；也可改用 X-Api-Key 头传递同一明文令牌",
    example="Bearer mr_xxxxxxxxxx",
)

_COMMON_ERRORS = [
    "401：缺少 API Key、Key 无效/已吊销、或 Key 已过期",
    "400：挂载根未配置、路径非法、业务参数不合法",
    "403：没有权限读取目录",
    "404：目录或传输目标不存在",
]

_MEDIA_SUB_ERRORS = [
    "401：缺少 API Key、Key 无效/已吊销、或 Key 已过期",
    "400：TMDB API Key 未配置/无效，或 media_type 非法",
    "404：想看记录不存在，或 TMDB 条目不存在",
    "502：请求 TMDB 上游失败",
]


def _f(
    name: str,
    type_: str,
    description: str,
    *,
    required: bool = False,
    example: object | None = None,
    children: list[OpenApiCatalogField] | None = None,
) -> OpenApiCatalogField:
    return OpenApiCatalogField(
        name=name,
        type=type_,
        required=required,
        description=description,
        example=example,
        children=children or [],
    )


_SUB_ITEM_FIELDS = [
    _f("id", "integer", "订阅记录主键", required=True, example=1),
    _f("tmdb_id", "integer", "TMDB 条目 id", required=True, example=550),
    _f("media_type", "string", "媒体类型：movie 或 tv", required=True, example="movie"),
    _f("title", "string", "标题缓存", required=True, example="搏击俱乐部"),
    _f("poster_path", "string", "海报相对路径（TMDB）", example="/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg"),
    _f(
        "poster_url",
        "string",
        "海报完整 URL，可直接访问",
        example="https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg",
    ),
    _f("overview", "string", "简介缓存"),
    _f("release_date", "string", "上映/首播日期 YYYY-MM-DD", example="1999-10-15"),
    _f("created_at", "string", "订阅时间 ISO 字符串", required=True, example="2026-10-09T12:00:00"),
]


def build_open_api_catalog() -> OpenApiCatalogResponse:
    endpoints = [
        OpenApiCatalogEndpoint(
            id="health",
            method="GET",
            path="/api/v1/open/health",
            summary="健康检查",
            description="校验 API Key 是否有效，并返回挂载根是否可用。适合外部系统启动时探活。",
            notes=["不依赖具体业务路径；mount_ready 为 false 时其它文件类接口可能返回 400。"],
            headers=[_AUTH_HEADER],
            response_fields=[
                _f("status", "string", "固定为 ok，表示鉴权通过且服务可用", required=True, example="ok"),
                _f(
                    "mount_ready",
                    "boolean",
                    "挂载根是否已在系统配置中填写，且路径存在并为目录",
                    required=True,
                    example=True,
                ),
            ],
            response_example={"status": "ok", "mount_ready": True},
            error_codes=_COMMON_ERRORS[:1],
        ),
        OpenApiCatalogEndpoint(
            id="catalog",
            method="GET",
            path="/api/v1/open/catalog",
            summary="能力目录",
            description=(
                "使用 API Key 查询当前系统对外暴露的全部开放接口清单，"
                "含路径、方法、参数、响应字段、示例与错误说明。与管理页「开放接口」目录同源。"
            ),
            notes=[
                "适合第三方系统启动时拉取契约，无需登录管理后台。",
                "本接口本身也会出现在返回的 endpoints 列表中。",
                "目录随服务端版本更新；调用方宜缓存后定期刷新。",
            ],
            headers=[_AUTH_HEADER],
            response_fields=[
                _f(
                    "base_path",
                    "string",
                    "开放接口统一前缀",
                    required=True,
                    example="/api/v1/open",
                ),
                _f(
                    "auth",
                    "string",
                    "鉴权方式说明",
                    required=True,
                    example="Authorization: Bearer <token> 或 X-Api-Key: <token>",
                ),
                _f(
                    "auth_notes",
                    "array",
                    "鉴权与路径等通用约定（字符串列表）",
                    required=True,
                ),
                _f(
                    "endpoints",
                    "array",
                    "接口列表；每项含 id/method/path/summary/description/notes/"
                    "headers/query_params/path_params/request_fields/response_fields/"
                    "body_example/response_example/error_codes",
                    required=True,
                ),
            ],
            response_example={
                "base_path": "/api/v1/open",
                "auth": "Authorization: Bearer <token> 或 X-Api-Key: <token>",
                "auth_notes": ["请求头二选一：Authorization: Bearer <token>，或 X-Api-Key: <token>。"],
                "endpoints": [
                    {
                        "id": "health",
                        "method": "GET",
                        "path": "/api/v1/open/health",
                        "summary": "健康检查",
                    }
                ],
            },
            error_codes=["401：缺少 API Key、Key 无效/已吊销、或 Key 已过期"],
        ),
        OpenApiCatalogEndpoint(
            id="browse",
            method="GET",
            path="/api/v1/open/browse",
            summary="浏览目录",
            description="列出挂载根下某个相对目录的直接子项（文件与文件夹）。路径均相对挂载根，使用正斜杠。",
            notes=[
                "path 留空或省略表示挂载根。",
                "返回的 entries[].path 为相对挂载根的完整相对路径，可直接用于后续 merge / rename / transfer。",
                "不递归列出子目录内容，需自行进入下一级再调本接口。",
                "entries[].size 仅对文件返回字节数；文件夹为 null（不做递归容量统计）。",
            ],
            headers=[_AUTH_HEADER],
            query_params=[
                OpenApiCatalogParam(
                    name="path",
                    location="query",
                    type="string",
                    required=False,
                    description="相对挂载根的目录路径；空字符串或不传表示挂载根。禁止 .. 越界。",
                    example="downloads",
                ),
            ],
            response_fields=[
                _f(
                    "path",
                    "string",
                    "当前浏览目录（相对挂载根）；空字符串表示挂载根",
                    required=True,
                    example="downloads",
                ),
                _f(
                    "entries",
                    "array<object>",
                    "当前目录下的子项列表（目录优先，再按名称不区分大小写排序）",
                    required=True,
                    children=[
                        _f("name", "string", "文件或文件夹名称", required=True, example="电影"),
                        _f(
                            "path",
                            "string",
                            "相对挂载根的完整相对路径",
                            required=True,
                            example="downloads/电影",
                        ),
                        _f(
                            "is_dir",
                            "boolean",
                            "是否为目录；true 为文件夹，false 为文件",
                            required=True,
                            example=True,
                        ),
                        _f(
                            "size",
                            "integer|null",
                            "文件大小（字节）；文件夹为 null，不递归统计目录容量",
                            required=False,
                            example=1048576,
                        ),
                    ],
                ),
            ],
            response_example={
                "path": "downloads",
                "entries": [
                    {"name": "电影", "path": "downloads/电影", "is_dir": True, "size": None},
                    {
                        "name": "a.mkv",
                        "path": "downloads/a.mkv",
                        "is_dir": False,
                        "size": 1048576,
                    },
                ],
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="destinations",
            method="GET",
            path="/api/v1/open/destinations",
            summary="列出传输目标",
            description="返回系统配置中已保存的传输目标，供 transfer 接口填写 destination_id。",
            notes=[
                "仅 ready=true 的目标可成功用于传输；false 表示路径不存在或不是目录。",
                "path 为服务端绝对路径，不是挂载相对路径。",
            ],
            headers=[_AUTH_HEADER],
            response_fields=[
                _f(
                    "items",
                    "array<object>",
                    "传输目标列表（按配置排序）",
                    required=True,
                    children=[
                        _f("id", "integer", "目标 id，传给 transfer.destination_id", required=True, example=1),
                        _f("label", "string", "显示名称", required=True, example="电影库"),
                        _f(
                            "path",
                            "string",
                            "服务端绝对路径",
                            required=True,
                            example="/data/movies",
                        ),
                        _f(
                            "ready",
                            "boolean",
                            "路径存在且为目录时为 true，否则不可用",
                            required=True,
                            example=True,
                        ),
                    ],
                ),
            ],
            response_example={
                "items": [{"id": 1, "label": "电影库", "path": "/data/movies", "ready": True}],
            },
            error_codes=_COMMON_ERRORS[:1],
        ),
        OpenApiCatalogEndpoint(
            id="folders-merge",
            method="POST",
            path="/api/v1/open/folders/merge",
            summary="文件夹合并",
            description=(
                "将多个源文件夹内全部文件（递归含子目录）扁平移动到目标目录；"
                "不保留子目录结构；目标侧重名自动追加 _1、_2… 后缀。"
            ),
            notes=[
                "source_paths 至少 2 个，且均为相对挂载根的文件夹。",
                "源文件夹之间不能互为父子关系。",
                "target_path 不能落在某个源文件夹内部；不存在时会自动创建（支持多级）。",
                "results 按「每个被移动的文件」返回，不是按源文件夹返回。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f(
                    "source_paths",
                    "array<string>",
                    "相对挂载根的源文件夹路径，至少 2 个",
                    required=True,
                    example=["downloads/A", "downloads/B"],
                ),
                _f(
                    "target_path",
                    "string",
                    "相对挂载根的目标文件夹；空字符串表示挂载根；不存在则自动创建",
                    required=False,
                    example="downloads/merged",
                ),
            ],
            response_fields=[
                _f(
                    "results",
                    "array<object>",
                    "每个被移动文件的结果明细",
                    required=True,
                    children=[
                        _f("source_path", "string", "移动前的源文件相对路径", required=True),
                        _f("dest_path", "string", "移动后的目标相对路径（含去重后缀）", required=True),
                        _f("ok", "boolean", "该项是否成功", required=True, example=True),
                        _f("message", "string|null", "失败原因；成功时一般为 null", required=False),
                    ],
                ),
                _f("moved_count", "integer", "成功移动的文件数", required=True, example=1),
                _f("failed_count", "integer", "失败的文件数", required=True, example=0),
            ],
            body_example={
                "source_paths": ["downloads/A", "downloads/B"],
                "target_path": "downloads/merged",
            },
            response_example={
                "results": [
                    {
                        "source_path": "downloads/A/a.mkv",
                        "dest_path": "downloads/merged/a.mkv",
                        "ok": True,
                        "message": None,
                    }
                ],
                "moved_count": 1,
                "failed_count": 0,
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="rename-auto",
            method="POST",
            path="/api/v1/open/rename/auto",
            summary="一键 AI 重命名",
            description=(
                "对指定文件调用 AI 生成建议文件名并立即执行重命名。"
                "适合下载完成后回调；无需 preview_id，也不受 Web 端「预览确认」开关影响。"
            ),
            notes=[
                "paths 须为相对挂载根的文件路径（不是目录），最多 200 条。",
                "依赖系统配置中的 AI Key 与模型；未配置时对应项会失败。",
                "建议名冲突（目标已存在）时该项 ok=false。",
                "成功后原路径失效，后续操作请使用同目录下的新文件名。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f(
                    "paths",
                    "array<string>",
                    "相对挂载根的待重命名文件路径，1～200 条",
                    required=True,
                    example=["downloads/Movie.Name.2024.mkv"],
                ),
            ],
            response_fields=[
                _f(
                    "items",
                    "array<object>",
                    "每个文件的建议名与执行结果",
                    required=True,
                    children=[
                        _f("path", "string", "请求中的源相对路径", required=True),
                        _f("original_name", "string", "原文件名", required=True),
                        _f(
                            "suggested_name",
                            "string",
                            "AI 建议并用于执行的新文件名；失败时可能为空",
                            required=True,
                        ),
                        _f("ok", "boolean", "是否最终重命名成功", required=True, example=True),
                        _f("message", "string|null", "失败原因；成功时一般为 null", required=False),
                    ],
                ),
                _f("ok_count", "integer", "成功重命名的文件数", required=True, example=1),
                _f("failed_count", "integer", "失败的文件数", required=True, example=0),
            ],
            body_example={"paths": ["downloads/Movie.Name.2024.mkv"]},
            response_example={
                "items": [
                    {
                        "path": "downloads/Movie.Name.2024.mkv",
                        "original_name": "Movie.Name.2024.mkv",
                        "suggested_name": "Movie Name (2024).mkv",
                        "ok": True,
                        "message": None,
                    }
                ],
                "ok_count": 1,
                "failed_count": 0,
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="rename-preview",
            method="POST",
            path="/api/v1/open/rename/preview",
            summary="AI 重命名预览",
            description="仅生成建议文件名，不修改磁盘文件。可先预览再调用 rename/execute 执行。",
            notes=[
                "开放接口下 preview_id 固定为 null（无需会话）。",
                "单条 error 非空表示该文件未生成建议名，其余字段可能为空。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f(
                    "paths",
                    "array<string>",
                    "相对挂载根的待预览文件路径，1～200 条",
                    required=True,
                    example=["downloads/Movie.Name.2024.mkv"],
                ),
            ],
            response_fields=[
                _f(
                    "preview_id",
                    "string|null",
                    "预览会话 id；开放接口固定为 null",
                    required=False,
                    example=None,
                ),
                _f(
                    "items",
                    "array<object>",
                    "每条文件的建议结果",
                    required=True,
                    children=[
                        _f("path", "string", "原相对路径", required=True),
                        _f("original_name", "string", "原文件名", required=True),
                        _f(
                            "suggested_name",
                            "string",
                            "AI 建议的新文件名；失败时可能为空",
                            required=True,
                        ),
                        _f(
                            "error",
                            "string|null",
                            "该条生成失败原因；成功时为 null",
                            required=False,
                        ),
                    ],
                ),
            ],
            body_example={"paths": ["downloads/Movie.Name.2024.mkv"]},
            response_example={
                "preview_id": None,
                "items": [
                    {
                        "path": "downloads/Movie.Name.2024.mkv",
                        "original_name": "Movie.Name.2024.mkv",
                        "suggested_name": "Movie Name (2024).mkv",
                        "error": None,
                    }
                ],
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="rename-execute",
            method="POST",
            path="/api/v1/open/rename/execute",
            summary="执行重命名",
            description="按给定 new_name 直接执行重命名，无需 preview_id。可用于自定义命名或在预览后确认执行。",
            notes=[
                "new_name 仅为文件名，不要包含目录路径或斜杠。",
                "目标同目录下已存在同名文件时该项失败。",
                "path 必须指向已存在的文件。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f(
                    "items",
                    "array<object>",
                    "待执行的重命名项，1～200 条",
                    required=True,
                    children=[
                        _f(
                            "path",
                            "string",
                            "相对挂载根的源文件路径",
                            required=True,
                            example="downloads/Movie.Name.2024.mkv",
                        ),
                        _f(
                            "new_name",
                            "string",
                            "仅新文件名，不含目录",
                            required=True,
                            example="Movie Name (2024).mkv",
                        ),
                    ],
                ),
            ],
            response_fields=[
                _f(
                    "results",
                    "array<object>",
                    "每条执行结果",
                    required=True,
                    children=[
                        _f("path", "string", "请求中的源相对路径", required=True),
                        _f("ok", "boolean", "是否重命名成功", required=True, example=True),
                        _f("message", "string|null", "失败原因；成功时一般为 null", required=False),
                    ],
                ),
            ],
            body_example={
                "items": [
                    {
                        "path": "downloads/Movie.Name.2024.mkv",
                        "new_name": "Movie Name (2024).mkv",
                    }
                ]
            },
            response_example={
                "results": [
                    {
                        "path": "downloads/Movie.Name.2024.mkv",
                        "ok": True,
                        "message": None,
                    }
                ]
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="transfer",
            method="POST",
            path="/api/v1/open/transfer",
            summary="文件传输",
            description="将挂载根内的文件或文件夹复制/移动到系统配置的传输目标目录（目标可为挂载外绝对路径）。",
            notes=[
                "destination_id 须先通过 GET /open/destinations 获取，且 ready=true。",
                "paths 不可互为包含关系（例如不要同时选文件夹与其中的文件）。",
                "传输目标不能与某个源路径相同，也不能位于某个源路径内部。",
                "目标侧重名会自动加 _1、_2…；目录整体传输重名时使用目录名_1 形式。",
                "mode=move 会删除源路径；mode=copy 保留源文件。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f(
                    "paths",
                    "array<string>",
                    "相对挂载根的文件或目录路径，至少 1 个",
                    required=True,
                    example=["downloads/Movie Name (2024).mkv"],
                ),
                _f(
                    "mode",
                    "string",
                    "传输方式：copy 复制，move 剪切（移动）",
                    required=True,
                    example="move",
                ),
                _f(
                    "destination_id",
                    "integer",
                    "传输目标 id（见 /open/destinations）",
                    required=True,
                    example=1,
                ),
            ],
            response_fields=[
                _f(
                    "results",
                    "array<object>",
                    "每项传输结果明细",
                    required=True,
                    children=[
                        _f("source_path", "string", "源路径（相对挂载根）", required=True),
                        _f("dest_path", "string", "目标侧路径（通常为绝对路径）", required=True),
                        _f("ok", "boolean", "该项是否成功", required=True, example=True),
                        _f("message", "string|null", "失败原因；成功时一般为 null", required=False),
                    ],
                ),
                _f("ok_count", "integer", "成功项数", required=True, example=1),
                _f("failed_count", "integer", "失败项数", required=True, example=0),
            ],
            body_example={
                "paths": ["downloads/Movie Name (2024).mkv"],
                "mode": "move",
                "destination_id": 1,
            },
            response_example={
                "results": [
                    {
                        "source_path": "downloads/Movie Name (2024).mkv",
                        "dest_path": "/data/movies/Movie Name (2024).mkv",
                        "ok": True,
                        "message": None,
                    }
                ],
                "ok_count": 1,
                "failed_count": 0,
            },
            error_codes=_COMMON_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="media-subscriptions-list",
            method="GET",
            path="/api/v1/open/media/subscriptions",
            summary="列出想看列表",
            description="返回已加入想看的影视条目。与 Web 端内置账号 admin 的想看列表共享同一数据。",
            notes=[
                "不依赖挂载根；仅需有效 API Key。",
                "与使用 admin 登录后在「想看列表」页看到的内容一致。",
            ],
            headers=[_AUTH_HEADER],
            response_fields=[
                _f(
                    "items",
                    "array<object>",
                    "想看条目列表（按订阅时间倒序）",
                    required=True,
                    children=_SUB_ITEM_FIELDS,
                ),
            ],
            response_example={
                "items": [
                    {
                        "id": 1,
                        "tmdb_id": 550,
                        "media_type": "movie",
                        "title": "搏击俱乐部",
                        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg",
                        "poster_url": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg",
                        "overview": "……",
                        "release_date": "1999-10-15",
                        "created_at": "2026-10-09T12:00:00",
                    }
                ]
            },
            error_codes=_MEDIA_SUB_ERRORS[:1],
        ),
        OpenApiCatalogEndpoint(
            id="media-subscriptions-add",
            method="POST",
            path="/api/v1/open/media/subscriptions",
            summary="加入想看",
            description="按 TMDB 条目加入想看；服务端会拉取 TMDB 详情写入标题/海报等缓存。已存在时幂等返回原记录。",
            notes=[
                "须先在系统配置「影视数据源」保存有效的 TMDB API Key。",
                "media_type 仅支持 movie 或 tv。",
                "与内置账号 admin 的想看列表共享。",
            ],
            headers=[_AUTH_HEADER],
            request_fields=[
                _f("media_type", "string", "媒体类型：movie 或 tv", required=True, example="movie"),
                _f("tmdb_id", "integer", "TMDB 条目 id", required=True, example=550),
            ],
            response_fields=_SUB_ITEM_FIELDS,
            body_example={"media_type": "movie", "tmdb_id": 550},
            response_example={
                "id": 1,
                "tmdb_id": 550,
                "media_type": "movie",
                "title": "搏击俱乐部",
                "poster_path": "/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg",
                "poster_url": "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4BrQ6LxyB.jpg",
                "overview": "……",
                "release_date": "1999-10-15",
                "created_at": "2026-10-09T12:00:00",
            },
            error_codes=_MEDIA_SUB_ERRORS,
        ),
        OpenApiCatalogEndpoint(
            id="media-subscriptions-remove",
            method="DELETE",
            path="/api/v1/open/media/subscriptions/{media_type}/{tmdb_id}",
            summary="取消想看",
            description="按媒体类型与 TMDB id 移出想看列表。",
            notes=[
                "路径参数 media_type 为 movie 或 tv；tmdb_id 为正整数。",
                "与内置账号 admin 的想看列表共享。",
            ],
            headers=[_AUTH_HEADER],
            path_params=[
                OpenApiCatalogParam(
                    name="media_type",
                    location="path",
                    type="string",
                    required=True,
                    description="媒体类型：movie 或 tv",
                    example="movie",
                ),
                OpenApiCatalogParam(
                    name="tmdb_id",
                    location="path",
                    type="integer",
                    required=True,
                    description="TMDB 条目 id",
                    example=550,
                ),
            ],
            response_fields=[
                _f("ok", "boolean", "成功时为 true", required=True, example=True),
            ],
            response_example={"ok": True},
            error_codes=_MEDIA_SUB_ERRORS,
        ),
    ]
    return OpenApiCatalogResponse(
        endpoints=endpoints,
        auth_notes=[
            "在「开放接口」页创建访问令牌；明文仅创建时展示一次。",
            "请求头二选一：Authorization: Bearer <token>，或 X-Api-Key: <token>。",
            "第三方可用 GET /api/v1/open/catalog（携带 API Key）拉取完整能力列表，无需登录管理后台。",
            "所有业务路径（除传输目标绝对路径外）均为相对挂载根的相对路径，使用 / 分隔，禁止 ..。",
            "令牌可设有效期；过期或吊销后一律 401。",
            "想看相关接口与内置账号 admin 的想看列表共享；加入想看需已配置 TMDB API Key。",
        ],
    )
