from pydantic import BaseModel, Field


class MediaCardItem(BaseModel):
    """列表卡片用的精简影视条目。"""

    tmdb_id: int = Field(description="TMDB 条目 id")
    media_type: str = Field(description="媒体类型：movie 或 tv")
    title: str = Field(description="标题")
    poster_path: str = Field(default="", description="海报相对路径；空表示无海报")
    poster_url: str = Field(default="", description="可直接访问的海报完整 URL")
    overview: str = Field(default="", description="简介摘要")
    release_date: str = Field(default="", description="上映或首播日期 YYYY-MM-DD")
    vote_average: float = Field(default=0, description="TMDB 评分（0–10）")


class MediaListResponse(BaseModel):
    items: list[MediaCardItem] = Field(default_factory=list, description="条目列表")
    page: int = Field(default=1, description="当前页码")
    total_pages: int = Field(default=1, description="总页数")
    total_results: int = Field(default=0, description="总条数")


class MediaGenre(BaseModel):
    id: int = Field(description="类型 id")
    name: str = Field(description="类型名称")


class MediaPersonCredit(BaseModel):
    """演职员条目。"""

    person_id: int = Field(description="TMDB 人物 id")
    name: str = Field(description="姓名")
    role: str = Field(default="", description="角色名（演员）或职位（职员）")
    profile_path: str = Field(default="", description="头像相对路径")
    profile_url: str = Field(default="", description="头像完整 URL")


class MediaDetail(BaseModel):
    """详情页完整信息。"""

    tmdb_id: int = Field(description="TMDB 条目 id")
    media_type: str = Field(description="媒体类型：movie 或 tv")
    title: str = Field(description="标题")
    original_title: str = Field(default="", description="原始标题")
    poster_path: str = Field(default="", description="海报相对路径")
    poster_url: str = Field(default="", description="海报完整 URL")
    backdrop_path: str = Field(default="", description="背景图相对路径")
    backdrop_url: str = Field(default="", description="背景图完整 URL")
    overview: str = Field(default="", description="简介")
    release_date: str = Field(default="", description="上映或首播日期")
    vote_average: float = Field(default=0, description="评分")
    vote_count: int = Field(default=0, description="评分人数")
    runtime: int | None = Field(default=None, description="片长（分钟）；剧集可为单集时长")
    genres: list[MediaGenre] = Field(default_factory=list, description="类型列表")
    status: str = Field(default="", description="制作/播出状态原文")
    cast: list[MediaPersonCredit] = Field(default_factory=list, description="主要演员")
    crew: list[MediaPersonCredit] = Field(default_factory=list, description="主要职员")
    similar: list[MediaCardItem] = Field(
        default_factory=list,
        description="相似/推荐条目（合并 TMDB recommendations 与 similar）",
    )
    subscribed: bool = Field(default=False, description="当前用户是否已加入想看")


class MediaSubscribeRequest(BaseModel):
    media_type: str = Field(..., description="媒体类型：movie 或 tv")
    tmdb_id: int = Field(..., ge=1, description="TMDB 条目 id")


class MediaSubscriptionItem(BaseModel):
    id: int = Field(description="订阅记录主键")
    tmdb_id: int = Field(description="TMDB 条目 id")
    media_type: str = Field(description="媒体类型：movie 或 tv")
    title: str = Field(description="标题缓存")
    poster_path: str = Field(default="", description="海报相对路径")
    poster_url: str = Field(default="", description="海报完整 URL")
    overview: str = Field(default="", description="简介缓存")
    release_date: str = Field(default="", description="日期缓存")
    created_at: str = Field(description="订阅时间 ISO 字符串")


class MediaSubscriptionListResponse(BaseModel):
    items: list[MediaSubscriptionItem] = Field(default_factory=list, description="想看列表")
