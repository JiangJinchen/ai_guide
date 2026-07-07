# AI 数字人智慧景区导览项目整理

## 1. 项目定位

本项目是一个面向景区游客和景区管理人员的“AI 数字人智慧景区导览系统”。从 README、后端接口和前端页面来看，项目当前聚焦于灵山胜境场景，目标是让游客通过移动端获得智能问答、景点讲解、个性化推荐、附近景点和路线规划等服务，同时为管理端提供知识库、数字人配置、数据大屏、反馈报表和日志管理能力。

项目采用前后端分离结构：

- 游客端：UniApp/Vue 移动端页面。
- 管理端：React + Vite + ECharts。
- Python 后端：FastAPI，承担主要业务接口、数据库模型、AI 推理、RAG 检索、ASR/TTS、推荐和 GPS 相关接口。
- Node.js 后端：Express + WebSocket + SSE，承担实时通信和数据推送的基础框架，目前实现较轻。
- 数据层：SQLAlchemy 模型面向 PostgreSQL，知识检索目前是基于数据库内容的本地关键词匹配。

## 2. 项目结构概览

```text
ai_guide/
├─ README.md
├─ backend/
│  ├─ python/
│  │  ├─ main.py
│  │  ├─ requirements.txt
│  │  └─ app/
│  │     ├─ api/
│  │     │  ├─ visitor.py
│  │     │  ├─ admin.py
│  │     │  └─ ai.py
│  │     ├─ database.py
│  │     ├─ models.py
│  │     ├─ schemas.py
│  │     ├─ services/
│  │     │  └─ knowledge_service.py
│  │     └─ utils/
│  └─ nodejs/
│     ├─ index.js
│     └─ package.json
├─ frontend/
│  ├─ visitor-app/
│  │  ├─ src/pages/
│  │  │  ├─ home/
│  │  │  ├─ smart-play/
│  │  │  ├─ chat/
│  │  │  ├─ guide/
│  │  │  ├─ recommendation/
│  │  │  ├─ feedback/
│  │  │  └─ profile/
│  │  └─ src/utils/request.js
│  ├─ admin-app/
│  │  └─ src/
│  │     ├─ App.jsx
│  │     └─ pages/
│  │        ├─ dashboard/
│  │        └─ knowledge/
│  └─ shared/
├─ data/
└─ docs/
```

说明：仓库中同时存在 `frontend/visitor-app/pages` 与 `frontend/visitor-app/src/pages` 两套相似页面文件，疑似是 UniApp 项目迁移或复制后留下的重复目录，后续需要统一入口。

## 3. 已有功能

### 3.1 游客端功能

当前游客端已经有较完整的页面雏形：

- 首页：作为游客入口，跳转到 AI 对话、景点讲解、推荐等功能。
- 智慧游玩：包含附近景点、景点列表、路线规划三个 tab。
- AI 对话：支持文本输入、快捷问题、聊天消息展示，预留语音模式开关。
- 景点讲解：支持景点列表、景点详情、讲解内容展示和语音播放按钮。
- 个性化推荐：展示推荐景点卡片，并可跳转景点讲解。
- 服务评价：支持星级评分、评价内容、标签选择和提交。
- 我的：提供个人中心相关入口。

### 3.2 Python 后端业务接口

FastAPI 后端通过 `/api` 挂载三组路由：

- `/api/visitor`：游客端业务。
- `/api/admin`：管理端业务。
- `/api/ai`：AI 能力接口。

游客端已有接口包括：

- 景点列表：`GET /api/visitor/spots`
- 景点详情：`GET /api/visitor/spots/{spot_id}`
- 景点讲解：`GET /api/visitor/guide/{spot_id}`
- AI 对话：`POST /api/visitor/chat`
- 对话历史：`GET /api/visitor/chat/history`
- 反馈提交：`POST /api/visitor/feedback`
- 个性化推荐：`GET /api/visitor/recommendation`
- 路线规划：`GET /api/visitor/route`
- 情感分析：`POST /api/visitor/emotion`
- 附近景点/GPS：`GET /api/visitor/gps`
- 游客行为数据：`GET /api/visitor/behavior`、`GET /api/visitor/behavior/{visitor_id}`

管理端已有接口包括：

- 知识库增删改查：`/api/admin/knowledge`
- 数字人配置增删改查：`/api/admin/digital-human`
- 游客满意度报表：`GET /api/admin/report`
- 系统日志查询：`GET /api/admin/logs`

AI 相关接口包括：

- 大模型推理：`POST /api/ai/inference`
- 语音识别 ASR：`POST /api/ai/asr`
- 语音合成 TTS：`POST /api/ai/tts`
- RAG 检索：`POST /api/ai/rag`

### 3.3 AI 与推荐能力

已有 AI 能力主要包括：

- 接入通义千问兼容接口，模型配置为 `qwen3-max`。
- 使用系统提示词限制回答范围，使其专注于灵山胜境相关内容。
- 调用知识服务，从 `Knowledge` 和 `Spot` 表中检索相关内容，并作为参考信息拼接进大模型请求。
- 未配置大模型 API 或调用失败时，使用本地兜底回答。
- 预留讯飞 ASR/TTS 接入，未配置密钥时走本地兜底。
- 情感分析接口接入百度 NLP 情感倾向分析，并在游客聊天接口中根据情绪调整回复前缀。
- 个性化推荐目前基于关键词标签匹配；新用户可根据游客行为数据进行冷启动推荐。
- 路线规划目前根据预置景点顺序权重排序，尚未接入真实地图路径规划。

### 3.4 数据模型

后端已经定义以下核心表模型：

- `Knowledge`：知识库条目。
- `DigitalHumanConfig`：数字人形象、模型、声音、服装等配置。
- `VisitorInteraction`：游客交互记录、反馈、满意度和情绪。
- `VisitorBehavior`：游客行为数据，包括停留时长、消费、满意度等。
- `Spot`：景区景点基础信息、坐标、介绍、文化内涵、开放信息等。
- `SystemLog`：系统日志。

### 3.5 Node.js 实时服务

Node.js 后端已有以下基础能力：

- WebSocket 连接管理。
- 接收 `chat` 和 `digital_human` 类型消息。
- 对聊天消息返回固定模拟响应。
- SSE 接口 `/api/sse`，每 5 秒推送模拟游客数、互动次数、满意度。
- 健康检查接口 `/api/health`。

## 4. 当前存在的问题

### 4.1 前后端接口路径不一致

游客端 `request.js` 的基础地址是：

```js
http://localhost:8000/api
```

但页面中调用的是 `/spots`、`/chat`、`/guide/{id}` 等路径，实际后端路由挂在 `/api/visitor` 下。因此当前游客端真实请求会变成：

```text
/api/spots
/api/chat
/api/guide/{id}
```

而后端实际提供的是：

```text
/api/visitor/spots
/api/visitor/chat
/api/visitor/guide/{id}
```

管理端也缺少统一 API 请求封装，知识库页面当前使用模拟数据，没有真正对接 `/api/admin/knowledge`。

### 4.2 请求和响应字段不匹配

部分页面传参和后端 schema 不一致：

- 游客端聊天页面提交 `{ text }`，但后端 `MessageRequest` 需要 `{ text, user_id }`。
- 聊天页面读取 `res.response` 或 `res.answer`，但后端返回字段是 `text` 和 `digital_human_action`。
- 聊天历史页面按 `role`、`timestamp` 解析，但后端返回的是 `visitor_id`、`interaction_type`、`content`、`emotion`、`created_at`。
- 反馈页面提交 `{ rating, comment, tags }`，但后端需要 `{ user_id, chat_content, satisfaction_score, comment }`。
- 推荐页面展示 `spot_id`、`spot_name`、`reason`、`tags`，但后端返回的是 `id`、`name`、`description`。
- 智慧游玩页面路线规划只显示 loading，没有真正调用 `/api/visitor/route`。

### 4.3 管理端页面不完整

`App.jsx` 中引用了以下页面：

- `pages/digital-human`
- `pages/report`
- `pages/permission`
- `pages/logs`

但当前目录列表中只存在：

- `pages/dashboard`
- `pages/knowledge`

因此管理端项目在当前状态下很可能无法正常编译运行。

### 4.4 数据大屏和知识库仍以模拟数据为主

管理端仪表盘数据由前端随机生成，并没有连接 Node.js SSE 或 Python 后端统计接口。知识库页面也只是本地状态模拟，未调用真实接口。

### 4.5 AI/RAG 仍是轻量实现

当前 RAG 检索没有真正使用 Chroma/FAISS 向量数据库，而是从数据库读取知识库和景点内容后进行关键词/中文双字片段打分。这个实现适合作为原型，但语义检索能力有限。

### 4.6 代码质量和可运行性风险

当前源码中存在明显的编码显示问题，README 和部分中文字符串在终端中显示为乱码。另有一些潜在风险：

- Python 后端部分字符串在当前显示下疑似引号不完整，需要实际运行验证。
- `VisitorInteraction` 模型字段为 `satisfaction_score`，但管理端报表中使用了 `i.satisfaction`。
- 管理端缺少多个被路由引用的页面文件。
- 游客端存在 `src` 与非 `src` 重复代码目录，后续维护容易产生分叉。
- Node.js WebSocket 聊天未真正调用 Python AI 后端。
- 权限认证、管理员登录、接口鉴权尚未落地。

## 5. 待实现功能

### 5.1 优先级高

- 统一游客端接口路径，补齐 `/visitor` 前缀或调整后端路由。
- 修正游客端与后端之间的请求/响应字段。
- 补齐管理端缺失页面，至少保证项目可编译。
- 管理端知识库页面接入真实 `/api/admin/knowledge`。
- 路线规划页面调用真实 `/api/visitor/route` 并展示结果。
- 修复报表接口中的满意度字段错误。
- 统一前端重复目录，明确实际构建入口。
- 检查并修复中文编码问题，确保 README、源码字符串和页面文案可读。

### 5.2 优先级中

- 管理端数字人配置页面接入 `/api/admin/digital-human`。
- 管理端日志页面接入 `/api/admin/logs`。
- 管理端报表页面接入 `/api/admin/report`。
- 数据大屏接入真实统计数据或 Node.js SSE。
- 游客端聊天历史按后端字段正确渲染。
- 反馈功能关联具体聊天内容或服务场景。
- AI 对话补齐 ASR/TTS 的前端录音、播放流程。
- Node.js WebSocket 与 Python AI 接口打通，实现实时聊天和数字人动作同步。

### 5.3 优先级低但有价值

- 引入真正的向量数据库 Chroma/FAISS，实现语义检索。
- 推荐算法从关键词标签升级为 TF-IDF、Embedding 或协同过滤。
- 接入百度地图，实现真实步行/驾车距离、用时、路线展示。
- 增加管理员登录、权限管理、接口鉴权和操作审计。
- 增加系统监控、异常日志和统一错误处理。
- 增加测试：后端接口测试、前端关键流程测试、管理端编译验证。
- 增加 Docker Compose 或一键启动脚本，降低部署复杂度。

## 6. 建议实施路线

第一阶段建议先保证“能跑通”：

1. 修复编码和明显语法问题。
2. 统一游客端 API 前缀和字段。
3. 补齐管理端缺失页面或暂时移除未实现路由。
4. 跑通游客端：景点列表、讲解、AI 对话、推荐、反馈。
5. 跑通管理端：知识库列表、新增、编辑、删除。

第二阶段再补“核心体验”：

1. 聊天接入 RAG 和 TTS 播放。
2. 路线规划展示真实返回结果。
3. 管理端报表和日志连接后端。
4. 数据大屏从模拟数据切换为真实统计或 SSE 推送。

第三阶段做“比赛/演示增强”：

1. 数字人形象、语音、口型和动作联动。
2. 地图路线可视化。
3. 更强的推荐算法和知识检索。
4. 完善权限、安全和部署文档。

## 7. 总结

该项目已经具备比较完整的产品设想和原型骨架：游客端页面、管理端框架、FastAPI 业务接口、AI/RAG/ASR/TTS 接口、数据库模型和实时通信服务都有初步实现。当前主要问题不是“缺方向”，而是“前后端尚未完全对齐、部分页面仍是模拟实现、管理端文件不完整、AI 与实时数字人能力还未真正串起来”。

如果后续以比赛演示为目标，建议优先修复接口联调和可运行性，再集中打磨 AI 对话、景点讲解、个性化推荐、路线规划和数据大屏这几条最容易展示价值的主链路。
