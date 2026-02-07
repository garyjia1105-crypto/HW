# RAG 应用 — GitHub Actions + Railway 自动化部署

本项目是一个基于 FastAPI 的检索增强生成（RAG）应用，包含前端 Web UI（MongoDB 用户认证与聊天持久化），并通过 GitHub Actions + Railway 实现 CI/CD：构建 Docker、运行测试、自动部署。

**技术栈**
- 后端：`FastAPI`、`LangChain`、`FAISS`、`OpenAI`、`MongoDB`
- 前端：`HTML`、`CSS`、`JavaScript`
- DevOps：`Docker`、`GitHub Actions`、`Railway`

**项目概览**
- 提供 `/` 与 `/ui` 前端界面，支持邮箱密码注册/登录；登录后可在聊天窗口调用后端。
- 提供 `/chat` 聊天接口，使用 LangChain + OpenAI 模型并结合本地 `FAISS` 检索。
- 聊天记录持久化存储在 MongoDB；用户认证使用 JWT。
- 挂载静态资源 `/static/*`，提供页面与脚本。

**目录结构**
- `app.py`：FastAPI 应用与路由（`/`、`/ui`、`/health`、`/auth/*`、`/chats`、`/chat`）。
- `static/`：前端页面与静态资源（`index.html`、`app.js`、`styles.css`）。
- `faiss_index/`：向量检索索引（通过 `ingest.py` 生成）。
- `ingest.py`：从 `data.txt` 生成 `FAISS` 索引。
- `tests/test_app.py`：端到端接口测试。
- `.github/workflows/main.yml`：CI/CD 工作流。
- `Dockerfile`、`requirements.txt`：容器与依赖定义。

**环境变量**
- `OPENAI_API_KEY`：OpenAI API 密钥（RAG 必需）
- `MONGODB_URI`：MongoDB 连接字符串（用户认证与聊天持久化）
- `JWT_SECRET`：JWT 签名密钥（生产环境必须修改，默认 `change-me-in-production`）

**本地开发**
- 安装与运行
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - 可选：设置 `OPENAI_API_KEY` 并运行 `python ingest.py` 以更新向量索引。
  - 启动服务：`uvicorn app:app --reload --host 0.0.0.0 --port 8080`
  - 访问界面：`http://localhost:8080/ui`
- 测试
  - `pip install pytest httpx && pytest -q`

**API**
- `GET /`、`GET /ui`：返回前端页面。
- `GET /health`：健康检查，返回 `{"message": ..., "version": ...}`。
- `POST /auth/signup`：注册，`{"email": "...", "password": "..."}`，返回 `{token, user}`。
- `POST /auth/login`：登录，`{"email": "...", "password": "..."}`，返回 `{token, user}`。
- `GET /auth/me`：获取当前用户（需 Bearer token）。
- `POST /chats`：保存聊天记录（需 Bearer token）。
- `GET /chats`：获取聊天历史（需 Bearer token）。
- `POST /chat`：RAG 对话，`{"question": "..."}`，返回 `{"answer": "..."}` 或 `{"error": "..."}`。
- 静态资源：`/static/*`。

**聊天记录持久化（MongoDB）**
- 使用 MongoDB 存储用户与聊天记录。集合：`users`（email、password hash）、`chats`（userId、question、answer、error、createdAt）。
- 游客模式（`/ui?guest=1`）不写入聊天记录。
- 登录后前端自动加载历史消息并按时间排序展示，默认最多 100 条。

**CI/CD（GitHub Actions → Railway）**
- 工作流：`.github/workflows/main.yml:1-37`，触发 `push` 到 `main`
  - Checkout 代码：`actions/checkout@v4`（`.github/workflows/main.yml:12`）
  - 安装 Python 与依赖：`actions/setup-python@v5` + `pip install`（`.github/workflows/main.yml:15-24`）
  - 运行测试：`pytest -q`（`.github/workflows/main.yml:26-27`）
  - 构建镜像（健康校验）：`docker build -t rag-app:ci .`（`.github/workflows/main.yml:29-30`）
  - 部署到 Railway：`bervProject/railway-deploy@main`（`.github/workflows/main.yml:32-37`）
- 仓库 Secrets
  - `RAILWAY_TOKEN`：项目令牌（Railway 项目 Settings → Tokens）
  - `RAILWAY_SERVICE_ID`：服务 ID

**部署与使用**
- 在 Railway 项目中设置环境变量：`OPENAI_API_KEY`、`MONGODB_URI`、`JWT_SECRET`（生产环境必须设置）。
- 推送到 `main` 后，GitHub Actions 将自动构建、测试并部署到 Railway。
- 部署完成后访问 `https://<railway-domain>/ui` 登录并开始聊天。

**文件位置参考**
- 路由与静态挂载：见 `app.py`
- 工作流：`.github/workflows/main.yml:1-37`
- 前端：`static/index.html`、`static/app.js`、`static/styles.css`
- 测试：`tests/test_app.py`

**参考链接**
- Railway 文章：`https://blog.railway.com/p/github-actions`
- 部署 Action：`https://github.com/bervProject/railway-deploy`
