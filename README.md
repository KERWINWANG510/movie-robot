# 智能文件重命名（NAS / Docker）

基于 **Vue 3 + Vite + TypeScript** 前端与 **FastAPI + SQLAlchemy 2（异步）+ SQLite** 后端的 Web 应用：在 **NAS 挂载目录** 内浏览文件，调用 **OpenAI 兼容 API** 生成建议文件名，支持 **单选 / 批量**，**登录**后按用户偏好选择 **预览确认** 或 **全自动**。

## 功能概要

- 挂载目录浏览（相对路径，禁止目录穿越）
- AI 建议名（OpenAI 兼容 `/v1/chat/completions`）
- 批量预览、编辑建议名后执行；全自动模式可一键「预览并立即执行」
- 预览确认模式下服务端校验预览会话，降低误操作风险
- 会话 Cookie 登录；HTTPS 反代时可开启 `SESSION_HTTPS_ONLY`

## 本地开发

**环境**：Node.js 22+、Python 3.12+（与 Docker 镜像一致）

**后端**（仓库根目录下）：

```powershell
cd backend
pip install -r requirements.txt
$env:MOUNT_PATH="D:\你的测试目录"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**前端**：

```powershell
cd frontend
npm install
npm run dev
```

浏览器访问开发服务器地址（默认 `http://localhost:5173`），API 经 Vite 代理至 `http://127.0.0.1:8000`。

首次部署若无账号：直接访问注册接口对应的 UI（登录页切换「注册」），**允许创建第一个用户**。第二个用户起需在环境变量中设置 `ALLOW_REGISTRATION=true` 或由管理员策略控制（见 `.env.example`）。

## Docker 部署（NAS）

1. 复制 `.env.example` 为 `.env`，填写 `SECRET_KEY`、`OPENAI_API_KEY`、`CORS_ORIGINS`（公网访问域名或 `http://NAS_IP:8000`）等。
2. 在 `docker-compose.yml` 中为 NAS 目录增加只读或读写挂载，例如：

```yaml
volumes:
  - movie_robot_data:/app/data
  - /实际/NAS/共享路径:/data:rw
```

3. 构建并启动：

```powershell
docker compose up -d --build
```

4. 访问 `http://<主机>:8000`。生产环境建议在前面加 **HTTPS 反代**（Caddy / Traefik / NAS 自带），并将 `SESSION_HTTPS_ONLY=true`、`CORS_ORIGINS` 设为实际站点来源。

## 环境变量说明

见仓库根目录 **`.env.example`**。

## 项目结构（摘要）

```
movie-robot/
├── backend/app/          # FastAPI 应用（API、模型、服务）
├── frontend/src/         # Vue 单页应用
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 规范提醒

仓库 **`.cursor/rules/project-standards.mdc`** 约定：简体中文界面与文档、SQL 使用参数化/ORM、前端响应式布局、目录结构保持清晰。开发与迭代时请一并遵守。
