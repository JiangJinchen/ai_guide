# AI Guide 产品部署与使用手册

AI Guide 是一套面向景区导览场景的智能导游系统，当前以“灵山胜境”为演示场景。项目包含游客端 APP、PC 管理端、Python 主业务后端和 Node.js 实时辅助服务，覆盖智能问答、景点讲解、路线规划、附近服务、票务活动、个性化推荐、游客反馈、内容运营和数据分析等流程。

本文档定位为产品部署和使用手册，重点说明如何运行、如何使用，以及迁移到新机器时哪些配置、数据和资产必须处理。

## 1. 系统组成

```text
ai_guide/
|- frontend/
|  |- visitor-app/          # 游客端 APP，Uni-app + Vue 3
|  |- admin-app/            # PC 管理端，React + Vite
|  `- shared/               # 前端共享代码
|- backend/
|  |- python/               # FastAPI 主业务后端
|  `- nodejs/               # WebSocket / SSE 辅助服务
|- data/faiss/              # 本地 FAISS 向量索引
|- docs/                    # 项目补充文档
`- README.md
```

- 游客端 APP：`frontend/visitor-app`，基于 Uni-app，当前产品定位是移动端 APP，也保留 H5、小程序和 App 构建脚本。
- PC 管理端：`frontend/admin-app`，基于 React + Vite，面向景区运营和管理人员。
- Python 后端：`backend/python`，提供主业务 API、AI 接入、RAG 检索、路线规划、高德地图集成和导览资产挂载。
- Node.js 后端：`backend/nodejs`，提供 WebSocket 和 SSE 辅助能力，默认端口 `8081`。

## 2. 部署前准备

建议环境：

- Python 3.10+
- Node.js 18+
- PostgreSQL 12+
- npm
- 能访问 AI、语音、地图等外部服务的网络

依赖文件：

- `backend/python/requirements.txt`
- `backend/python/requirements-rag-ann.txt`
- `backend/nodejs/package.json`
- `frontend/visitor-app/package.json`
- `frontend/admin-app/package.json`

## 3. 数据库与配置

Python 后端当前在 `backend/python/app/database.py` 中直接配置 PostgreSQL 连接：

```python
DATABASE_URL = "postgresql://postgres:...@localhost:5432/ai_guide"
```

新机器部署前需要先创建数据库：

```sql
CREATE DATABASE ai_guide;
```

`backend/python/main.py` 启动时会自动建表，并执行部分兼容性补列逻辑。但它不会自动恢复所有业务数据，因此正式迁移时需要备份并恢复数据库。

后端环境变量位于 `backend/python/.env`。该文件通常包含密钥，已被 `.gitignore` 忽略，部署时应在目标机器重新创建。

常见变量：

```env
AI_PROVIDER=
AI_API_KEY=
AI_API_URL=
AI_MODEL=
ASR_APP_ID=
ASR_API_KEY=
ASR_API_SECRET=
TTS_APP_ID=
TTS_API_KEY=
TTS_API_SECRET=
EMOTION_API_ID=
EMOTION_API_KEY=
EMOTION_SECRET_KEY=
EMOTION_LLM_URL=
EMOTION_LLM_MODEL=
EMOTION_LLM_API_KEY=
AMAP_WEB_KEY=
BAIDU_MAP_AK=
RAG_MODE=
RAG_VECTOR_BACKEND=
RAG_FAISS_DIR=
RAG_WARMUP_ENABLED=
ADMIN_TOKEN_SECRET=
ADMIN_BOOTSTRAP_USERNAME=
ADMIN_BOOTSTRAP_PASSWORD=
ADMIN_BOOTSTRAP_DISPLAY_NAME=
VISITOR_TOKEN_SECRET=
```

生产环境必须自行设置 `ADMIN_TOKEN_SECRET` 和 `VISITOR_TOKEN_SECRET`。如果不配置，后端会使用开发默认密钥，不适合上线。

## 4. Python 主业务后端部署

```bash
cd backend/python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

默认地址：

```text
http://localhost:8000
```

接口文档：

```text
http://localhost:8000/docs
```

如果使用 FAISS 向量检索：

```bash
pip install -r requirements-rag-ann.txt
```

初始化管理员账号：

```bash
cd backend/python
python seed_admin.py
```

初始化路线与景点辅助数据：

```bash
cd backend/python
python init_db_data.py
```

注意：`init_db_data.py` 目前也包含本机数据库连接信息，迁移时需要确认连接配置是否匹配目标环境。

## 5. RAG 检索与向量索引

支持的 RAG 模式：

- `legacy`：从知识库、景点、FAQ 中做关键词检索。
- `chunk`：基于知识切片检索。
- `semantic`：基于向量语义检索。
- `hybrid`：关键词与语义混合检索。

常用命令：

```bash
cd backend/python
python manage_rag.py status
python manage_rag.py sync-chunks
python manage_rag.py sync-embeddings
python manage_rag.py build-faiss
python manage_rag.py faiss-status
```

如果目标机器不能访问模型下载源，建议提前准备 sentence-transformers 模型缓存，或暂时使用：

```env
RAG_WARMUP_ENABLED=false
RAG_MODE=legacy
RAG_VECTOR_BACKEND=exact
```

## 6. Node.js 辅助服务部署

```bash
cd backend/nodejs
npm install
npm run dev
```

默认地址：

```text
http://localhost:8081
ws://localhost:8081
```

该服务目前主要提供 WebSocket 和 SSE 辅助能力，主业务仍由 Python 后端承担。

## 7. 游客端 APP 部署与使用

```bash
cd frontend/visitor-app
npm install
```

开发运行：

```bash
npm run dev:h5
npm run dev:app-android
npm run dev:app-ios
npm run dev:mp-weixin
```

打包：

```bash
npm run build:h5
npm run build:app-android
npm run build:app-ios
npm run build:mp-weixin
```

APP 真机调试或生产打包前，必须检查接口地址：

```text
frontend/visitor-app/src/utils/request.js
frontend/visitor-app/src/utils/sse.js
```

当前代码中存在类似 `http://192.168.x.x:8000/api` 的局域网地址。迁移到其他机器时，要改成手机可访问的后端地址。APP 不能依赖开发机的 `localhost`。

主要功能：

- 首页：景区入口、搜索、热门景点、今日演出。
- 数字人：AI 对话、流式回复、服务动作跳转。
- 景点讲解：查看景点详情、文化内涵和导览素材。
- 路线规划：根据时间、偏好、必去景点和位置生成候选路线。
- 附近服务：查看附近景点、餐饮、停车、游客中心等。
- 票务与活动：查看门票、观光车、演出和禅修信息。
- 我的：游客账号、足迹、反馈和历史记录。

## 8. PC 管理端部署与使用

```bash
cd frontend/admin-app
npm install
npm run dev
```

默认开发地址：

```text
http://localhost:3000
```

生产打包：

```bash
npm run build
```

管理端请求基地址在 `frontend/admin-app/src/api/request.js` 中配置，默认为：

```js
import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
```

生产环境建议通过 `.env.production` 配置：

```env
VITE_API_BASE_URL=https://your-domain.example.com/api
```

管理端功能：

- 数据大屏概览
- 知识库管理
- 景点内容管理
- 客服 FAQ 管理
- 票务信息管理
- 活动信息管理
- 数字人形象管理
- 游客感受度报告
- 权限管理
- 日志管理

## 9. 关键接口

Python 后端统一挂载在 `/api` 下。

游客端：

```text
POST /api/visitor/auth/register
POST /api/visitor/auth/login
GET  /api/visitor/spots
GET  /api/visitor/spots/{spot_id}
GET  /api/visitor/guide/{spot_id}
POST /api/visitor/chat/stream
POST /api/visitor/routes/generate
GET  /api/visitor/ticket-assistant
GET  /api/visitor/activities
GET  /api/visitor/activities/upcoming
GET  /api/visitor/recommendation
POST /api/visitor/behavior
GET  /api/visitor/footprints
POST /api/visitor/feedback
```

PC 管理端：

```text
POST /api/admin/auth/login
POST /api/admin/auth/refresh
GET  /api/admin/auth/me
GET/POST/PUT/DELETE /api/admin/knowledge
GET/POST/PUT/DELETE /api/admin/faqs
GET/POST/PUT/DELETE /api/admin/spots
GET/POST/PUT/DELETE /api/admin/tickets
GET/POST/PUT/DELETE /api/admin/activities
GET/POST/PUT/DELETE /api/admin/digital-human
GET /api/admin/report
GET /api/admin/logs
GET /api/admin/analytics/*
POST /api/admin/rag/reindex
```

AI 能力：

```text
POST /api/ai/inference
POST /api/ai/stream-inference
POST /api/ai/rag
POST /api/ai/asr
POST /api/ai/tts
```

## 10. 迁移到新机器时的重点

这个项目不是只复制源码就能完整运行。以下内容必须迁移或重建。

### 10.1 必须迁移或重建

数据库：

- PostgreSQL 数据库 `ai_guide`。
- 业务数据，包括 `spots`、`knowledge`、`faq_items`、`ticket_products`、`scenic_activities`、管理员账号、游客行为和反馈等。

环境变量：

- `backend/python/.env` 不会随 Git 迁移，新机器需要重新创建。
- AI、语音、地图、Token Secret 都依赖这些配置。

静态资产：

- `frontend/visitor-app/src/static/images`
- `frontend/visitor-app/src/static/live2d`
- `frontend/visitor-app/src/static/vendor`
- `frontend/visitor-app/static`
- `backend/python/storage/guide-assets`

RAG / FAISS 数据：

- 默认路径为 `data/faiss`。
- `.gitignore` 已忽略 `data/faiss/`，因此仅迁移源码不会带上向量索引。
- 可以复制该目录，也可以在新机器重新执行 `sync-chunks`、`sync-embeddings`、`build-faiss`。

### 10.2 可以重新生成

- `node_modules`
- `frontend/visitor-app/dist`
- `frontend/admin-app/dist`
- `.pytest_cache`
- `__pycache__`

### 10.3 常见本机依赖点

- `backend/python/app/database.py` 中的数据库连接串。
- `frontend/visitor-app/src/utils/request.js` 和 `frontend/visitor-app/src/utils/sse.js` 中的 APP 接口地址。
- `frontend/admin-app/src/api/request.js` 和 `VITE_API_BASE_URL` 中的 PC 管理端接口地址。
- `frontend/visitor-app/manifest.json` 中的 AppID、地图 Key、定位和麦克风权限。
- sentence-transformers 默认模型缓存。

### 10.4 推荐迁移流程

1. 在旧机器导出 PostgreSQL 数据。
2. 在新机器安装 Python、Node.js 和 PostgreSQL。
3. 恢复 `ai_guide` 数据库。
4. 拷贝源码。
5. 拷贝或重新生成 `backend/python/storage/guide-assets`。
6. 拷贝或重新生成 `data/faiss`。
7. 在新机器创建 `backend/python/.env`。
8. 修改游客 APP 的 API 地址。
9. 配置 PC 管理端 `VITE_API_BASE_URL`。
10. 分别启动 Python 后端、Node 服务、游客 APP 和 PC 管理端。
11. 测试登录、景点列表、数字人对话、路线规划、附近服务和反馈。

## 11. 本地联调顺序

1. 启动 PostgreSQL。
2. 启动 Python 后端：`cd backend/python && python main.py`。
3. 启动 Node.js 辅助服务：`cd backend/nodejs && npm run dev`。
4. 启动 PC 管理端：`cd frontend/admin-app && npm run dev`。
5. 启动游客端 APP：`cd frontend/visitor-app && npm run dev:app-android`。

## 12. 使用检查清单

后端：

- `http://localhost:8000/docs` 可以打开。
- `GET /api/visitor/spots` 可以返回景点列表。
- `POST /api/admin/auth/login` 可以登录。
- RAG 启用时，`python manage_rag.py status` 可以正常返回。

游客 APP：

- 首页能加载热门景点和今日演出。
- 数字人页面能获取 `/digital-human/config`。
- 对话页面能通过 `/chat/stream` 收到流式回复。
- 路线规划能调用 `/routes/generate`。
- 附近景点能基于定位或兜底位置展示结果。

PC 管理端：

- 管理员账号可以登录。
- 刷新页面后会话可以恢复。
- 知识库、景点、FAQ、票务和活动页面可以增删改查。
- 权限不足的账号不会看到无权菜单。

## 13. 常见问题

### 游客 APP 真机请求不到后端

检查 `frontend/visitor-app/src/utils/request.js` 和 `frontend/visitor-app/src/utils/sse.js` 中的 `BASE_URL`。真机需要使用手机可访问的局域网 IP 或公网域名。

### PC 管理端登录失败

检查 Python 后端是否运行、`ADMIN_TOKEN_SECRET` 是否配置、是否执行过 `python seed_admin.py`，以及 `VITE_API_BASE_URL` 是否指向正确后端。

### RAG 启动慢或失败

检查 `sentence-transformers`、模型缓存、`RAG_WARMUP_ENABLED`、`RAG_VECTOR_BACKEND`、`data/faiss` 和 `faiss-cpu`。

### 景点图片或数字人不显示

检查 `frontend/visitor-app/src/static/images`、`frontend/visitor-app/src/static/live2d` 和 `frontend/visitor-app/src/static/vendor` 是否完整。

### 景点讲解音频不可访问

检查 `backend/python/storage/guide-assets` 是否存在。Python 后端会将该目录挂载到 `/api/visitor/guide-assets`。

## 14. 补充文档

- `docs/project-overview.md`
- `docs/admin-development.md`
- `docs/amap-route-planning-db.md`
- `docs/rag-staged-rollout.md`
- `docs/project-analysis.md`
