# 智能文件重命名（NAS / Docker）

基于 **Vue 3 + Vite + TypeScript** 与 **FastAPI + SQLAlchemy 2（异步）+ SQLite** 的 Web 应用：在 **NAS 挂载目录** 中浏览文件，通过 **OpenAI 兼容 API** 生成建议文件名，支持 **单选 / 批量**；登录后可按偏好使用 **预览确认** 或 **全自动** 流程。

## 功能概要

| 模块 | 说明 |
|------|------|
| 文件浏览 | 相对挂载根的路径列表，禁止 `..` 路径穿越 |
| 智能重命名 | 调用兼容接口 `/v1/chat/completions`，JSON 结构化输出建议文件名 |
| 系统配置 | 页内配置挂载根目录、API Base、密钥、模型（支持拉取 `/v1/models` 列表）、**自然语言重命名说明**（会一并发给模型） |
| 命名模式 | 每位用户可切换「预览确认」与「全自动」；预览模式下服务端校验预览会话 |
| 首页引导 | 挂载根路径不可用（未配置或不存在）时，不请求浏览接口，引导前往系统配置 |
| 认证 | 服务端 Session Cookie；可选内置管理员账号（见下文） |

## 技术栈

- **前端**：Vue 3、Vite、TypeScript、Pinia、Vue Router、Element Plus  
- **后端**：Python 3.12+（Dockerfile）、FastAPI、HTTPX、bcrypt  
- **部署**：根目录 `Dockerfile` 多阶段构建、`docker-compose.yml`

## 本地开发

**环境**：Node.js 22+、Python 3.12+  

**后端**（在 `backend` 目录执行，`PYTHONPATH` 即当前目录）：

```powershell
cd backend
pip install -r requirements.txt
# 可选：复制 .env 仅用于 SECRET_KEY、DATABASE_URL 等，见 .env.example
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后在浏览器打开 **系统配置**，填写挂载根目录等；未配置时首页会引导，不会用环境变量替代业务配置。

**前端**：

```powershell
cd frontend
npm install
npm run dev
```

浏览器默认访问 `http://localhost:5173`，开发模式下 API 由 Vite 代理到 `http://127.0.0.1:8000`。  

生产构建会将静态资源输出到 `frontend/dist`，也可由后端容器打包进镜像并同端口提供页面。

## 登录与账号

- 库中 **无任何用户** 时，可在登录页使用「注册」创建第一个账号（若未关闭 `ALLOW_REGISTRATION`）。  
- 启动时会尝试创建内置账号：**用户名 `admin`，密码 `123456`**（仅当不存在同名用户时插入）。**请务必在生产环境中修改密码或停用该账号。**  

## Docker 部署（NAS）

1. 复制 `.env.example` 为 `.env`，填写 `SECRET_KEY`、`CORS_ORIGINS`（须包含浏览器实际访问来源，含协议与端口）等。  
2. 在 `docker-compose.yml` 中为数据目录与 NAS 共享目录挂载卷；启动后在 **系统配置** 中填写与卷映射一致的 **挂载根目录**（例如容器内 `/data`）。  
3. 启动：

```powershell
docker compose up -d --build
```

4. 访问 `http://<主机>:8000`。公网访问建议在前面加 **HTTPS 反代**，并设置 `SESSION_HTTPS_ONLY=true`、正确的 `CORS_ORIGINS`。

### GitHub Container Registry（CI 镜像）

**仅当推送 Git tag（形如 `v*`）时**，GitHub Actions 会使用仓库根目录 `Dockerfile` 构建并推送镜像到 **GHCR**，标签为 **`vX.Y.Z`（与 tag 同名）** 与 **`latest`**；页面右上角版本与 **tag 名**一致。在 GitHub 仓库的 **Packages**（软件包）中可查看镜像与标签。

本地打标签并发版示例：

```bash
git tag v1.2.0
git push origin v1.2.0
```

合并到 `main` **不会**触发镜像构建。

在 NAS 或其他主机拉取时，镜像名为 `ghcr.io/<GitHub 用户名或组织的小写>/<仓库名小写>`，例如：

```powershell
docker pull ghcr.io/你的用户名小写/movie-robot:latest
```

#### 如何将镜像设为公开（所有人可见）

GitHub 不会在推送镜像时自动公开 Package，须在网页上手动修改可见性。步骤：

1. GitHub 右上角头像 → **Your repositories** → 或直接打开仓库 → 右侧 **Packages**，或在 Profile → **Packages** 中找到 `movie-robot`。  
2. 进入包页面 → **Package settings**（左侧或齿轮图标）。  
3. 滚动到 **Danger Zone** → **Change visibility** → 选择 **Public** → 确认。

说明：仓库本身为私有也可以单独把 Package 设为 Public；匿名执行 `docker pull` 时镜像须为 Public。

若仓库或 Package 为私有，匿名拉取会失败：请将对应 GitHub Package 设为对目标可见，或使用 PAT（含 `read:packages`）登录后再拉取：

```powershell
echo <你的PAT> | docker login ghcr.io -u <GitHub用户名> --password-stdin
```

## 配置说明

**挂载路径、OpenAI API 地址与密钥、模型、自然语言重命名说明** 均在登录后的 **系统配置** 页面填写并写入 SQLite，**不再从环境变量读取**。

仅需通过环境变量 / `.env` 提供的项（见 `.env.example`）：

| 说明 | 环境变量 |
|------|----------|
| 会话密钥 | `SECRET_KEY` |
| 数据库连接 | `DATABASE_URL`（默认 SQLite 于 `data/`） |
| 跨域来源 | `CORS_ORIGINS`（逗号分隔） |
| 允许自助注册 | `ALLOW_REGISTRATION` |
| HTTPS Cookie | `SESSION_HTTPS_ONLY` |

## 项目结构（摘要）

```
movie-robot/
├── backend/app/              # FastAPI：main、api/routes、models、schemas、services
├── frontend/src/
│   ├── layouts/              # 主导航布局
│   ├── views/                # 首页（浏览/重命名）、系统配置、登录
│   └── ...
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .cursor/rules/            # 项目约定（语言、安全、Git 等）
```

## 规范与协作

仓库 **`.cursor/rules/project-standards.mdc`** 中对简体中文文案、SQL/ORM 安全、响应式布局、Git 提交格式等有约定；贡献代码时请一并遵守。
