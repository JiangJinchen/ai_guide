# AI Guide

AI Guide 是一个面向景区导览场景的智能导游项目，围绕“游客服务 + 管理运营 + AI 能力接入”构建，当前仓库包含：

- `frontend/visitor-app`：游客端 Uni-app
- `frontend/admin-app`：管理端 React + Vite
- `backend/python`：FastAPI 主业务服务
- `backend/nodejs`：Node.js 实时通信/辅助服务

项目当前以“灵山胜境”场景为主要演示对象，已经覆盖路线规划、路线详情、导航、景点讲解、票务助手、活动服务、个性化推荐、游客画像与反馈等核心流程。

## 1. 主要能力

### 游客端

- AI 问答与流式对话
- 景点讲解与导览素材展示
- 路线规划、路线详情、全程导航
- 附近景点 / 服务点查看
- 个性化推荐
- 票务助手、活动服务
- 游客足迹、反馈、个人中心

### 管理端

- 内容与基础数据管理
- 游客行为与反馈查看
- 票务、活动等运营信息维护
- 可视化数据概览

### 后端与 AI 能力

- FastAPI 统一业务接口
- Node.js 辅助实时通信能力
- RAG 检索与模型预热
- 数字人相关配置与资源接口
- 高德地图距离、步行导航、POI 查询集成

## 2. 技术栈

### 前端

- 游客端：`Uni-app`、`Vue 3`
- 管理端：`React 18`、`Vite`、`ECharts`

### 后端

- Python：`FastAPI`、`SQLAlchemy`
- Node.js：`Express`、`ws`、`sse`

### AI / 数据

- RAG 检索与重排
- PostgreSQL
- 本地向量检索相关能力
- 外部地图与模型服务通过环境变量接入

## 3. 目录结构

```text
ai_guide/
├─ frontend/
│  ├─ visitor-app/          # 游客端 Uni-app
│  ├─ admin-app/            # 管理端 React
│  └─ shared/               # 前端共享资源
├─ backend/
│  ├─ python/               # FastAPI 主业务服务
│  ├─ nodejs/               # Node.js 辅助服务
│  └─ shared/               # 后端共享资源
├─ data/                    # 本地数据与存储目录
├─ docs/                    # 项目文档
└─ README.md
```

## 4. 当前核心页面

游客端页面位于 `frontend/visitor-app/src/pages`，当前主要包括：

- `home` 首页
- `chat` AI 导游对话
- `guide` 景点讲解
- `route-planning` 路线规划
- `route-detail` 路线详情
- `route-navigation` 路线导航
- `nearby-spots` 附近景点
- `ticket-assistant` 票务助手
- `activity-service` 活动服务
- `recommendation` 个性推荐
- `spot-detail` 景点详情
- `profile` 个人中心
- `feedback` 反馈页

## 5. 启动方式

### 5.1 Python 后端

```bash
cd backend/python
pip install -r requirements.txt
python main.py
```

默认启动 `FastAPI` 服务，入口位于：

- [backend/python/main.py]

默认端口：

- `http://127.0.0.1:8000`
- API 前缀：`/api`

### 5.2 Node.js 后端

```bash
cd backend/nodejs
npm install
npm run dev
```

### 5.3 游客端

```bash
cd frontend/visitor-app
npm install
npm run dev:h5
```

可用脚本：

- `npm run dev:h5`
- `npm run build:h5`
- `npm run dev:mp-weixin`
- `npm run build:mp-weixin`

### 5.4 管理端

```bash
cd frontend/admin-app
npm install
npm run dev
```

常用脚本：

- `npm run dev`
- `npm run build`
- `npm run preview`

## 6. 环境变量说明

项目支持通过环境变量接入外部能力，常见项包括：

- `AI_API_KEY`
- `AI_API_URL`
- `AI_MODEL`
- `AMAP_WEB_KEY`
- `ADMIN_TOKEN_SECRET`
- `RAG_WARMUP_ENABLED`

说明：

- 未配置部分 AI / 地图能力时，部分功能会降级或使用本地兜底逻辑
- 管理端鉴权密钥建议在本地和部署环境中单独配置

## 7. 测试

当前仓库中已经存在一部分 Python 侧测试，位于：

- `backend/python/tests`

包括但不限于：

- `test_admin_auth.py`
- `test_analytics.py`
- `test_chunk_service.py`
- `test_dialog_orchestrator.py`
- `test_streaming_chat.py`

## 8. 文档

现有文档位于 `docs/`：

- `admin-development.md`
- `amap-route-planning-db.md`
- `project-analysis.md`
- `rag-staged-rollout.md`

## 9. 推荐阅读顺序

如果你是第一次接手这个项目，建议按下面顺序阅读：

1. 先看本 README
2. 再看 [docs/project-overview.md](D:\codes\project\softwareCup\ai_guide\docs\project-overview.md)
3. 然后读 `backend/python/main.py`
4. 再从 `frontend/visitor-app/src/pages/home` 和 `route-planning` 开始看主要用户流程

