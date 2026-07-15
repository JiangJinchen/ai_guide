# 管理端开发文档

> 版本：v1.0
> 更新时间：2026-07-14
> 适用范围：`frontend/admin-app`、`backend/python/app/api/admin.py` 及相关数据库模型

## 1. 文档目标

管理端服务景区运营人员，负责维护游客端可检索的景区内容、配置数字人、查看运营数据，并对票务和活动等业务信息进行维护。本文件用于统一当前实现状态、目标功能、接口约定和验收标准，作为后续开发和联调依据。

## 2. 当前基线

管理端技术栈为 React + Vite + React Router + ECharts，后端为 FastAPI + SQLAlchemy + PostgreSQL。当前管理端已经注册以下路由：

| 页面 | 路由 | 当前状态 |
| --- | --- | --- |
| 数据看板 | `/` | 已接入真实聚合接口，支持日期筛选、核心指标、图表和营销建议 |
| 知识库 | `/knowledge` | 查询、新增、编辑、删除、关键词筛选和 RAG 重建入口已接入 |
| 景点内容 | `/spots` | 已新增管理页面和 CRUD 接口 |
| 客服 FAQ | `/faqs` | 已新增数据库模型、管理页面和游客端数据库读取 |
| 票务信息 | `/tickets` | 查询、新增、编辑、上下线、删除已接通 |
| 活动信息 | `/activities` | 查询、新增、编辑、上下线、删除已接通 |
| 数字人配置 | `/digital-human` | 查询、新增、编辑、互斥发布、历史快照回滚、Live2D 画面/音色预览、删除及游客端读取已接通；审计关联操作人 |
| 游客反馈报告 | `/report` | 查询和满意度统计已接通，评论渲染仍需修复 |
| 权限管理 | `/permission` | 已接入登录、账号维护、密码重置、停用、固定/自定义角色、菜单权限和领域接口 RBAC |
| 系统日志 | `/logs` | 日期、级别和来源查询已接通，支持数字人配置结构化操作审计 |

后端现有管理接口位于 `/api/admin`，包括认证、知识库、数字人、票务、活动、报告、日志以及 `/api/admin/rag/reindex`。除登录、刷新和退出接口外，管理接口已统一要求管理员访问令牌；自动化测试和完整部署闭环仍待完善。

## 3. 建设目标

### 3.1 内容管理目标

管理员可以对景区知识内容进行增、删、改、查，内容保存后游客端 AI/RAG 检索必须能够使用最新版本。知识内容至少包括：景点介绍、历史文化、开放信息、游览须知、交通、餐饮、服务设施和活动说明。

游客端客服页的 FAQ 也必须由管理端维护，支持问题、答案、分类、排序、启用/停用和更新时间管理，避免继续使用前端或后端硬编码内容。

### 3.2 数据分析目标

管理端看板需要展示服务人次、游客关注点、热门问答、游览路线偏好、消费分析和满意度，并支持日期范围筛选、趋势对比和导出，为活动营销、内容运营和服务改进提供依据。

### 3.3 数字人配置目标

管理员可以配置数字人的外观形象、模型资源、语音音色、服装风格、默认启用状态，并能够预览配置、切换当前生效版本。配置变更需要记录操作人和时间，避免影响正在使用的会话而无法追溯。

### 3.4 业务扩展目标

根据游客端已有功能逐步补充票务、活动、景点讲解资源和服务公告等管理页面，所有面向游客展示的运营内容都应具有唯一数据来源，避免管理端和游客端各自维护一套静态数据。

## 4. 功能设计

### 4.1 景区知识库管理

现有基础表为 `Knowledge`，字段包括 `id`、`title`、`content`、`category`、`created_at`、`updated_at`。管理端应提供：

1. 分页列表：按标题、分类、更新时间、状态筛选。
2. 新增：标题、正文、分类、关键词、来源和发布状态必填校验。
3. 编辑：修改后显示版本更新时间，并支持取消未保存修改。
4. 删除：二次确认；已被引用的内容优先软删除或下线，不直接破坏历史记录。
5. 详情预览：以游客端实际检索到的格式预览文本。
6. 批量操作：批量发布、下线、删除和触发索引更新。
7. RAG 同步：内容变更后标记索引过期，管理员可手动触发重建并查看任务状态。

建议补充字段：`status`、`source`、`keywords`、`version`、`published_at`、`deleted_at`。如果暂时不扩展表结构，至少使用 `category` 区分内容类型，并在服务层统一处理发布状态。

### 4.2 FAQ 管理

第一阶段已新增 `faq_items` 表和 `/faqs` 管理页面。游客端客服接口现在优先从数据库读取启用的 FAQ；数据库尚未初始化时保留默认内容作为兼容兜底。FAQ 独立于普通知识正文，便于客服页结构化展示：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | bigint | 主键 |
| `question` | varchar(500) | 常见问题 |
| `answer` | text | 标准答案 |
| `category` | varchar(100) | 票务、入园、交通、服务等 |
| `sort_order` | int | 展示顺序 |
| `is_active` | boolean | 是否在游客端展示 |
| `source_name` | varchar(255) | 信息来源 |
| `updated_at` | timestamp | 更新时间 |

管理端页面至少提供 FAQ 列表、新增、编辑、启停、删除、排序和关键词搜索。游客端接口改为从数据库读取启用的 FAQ，并按 `sort_order` 返回。FAQ 也可以同步写入 RAG 索引，但应保留结构化字段，便于客服页直接展示。

已实现接口：

```text
GET    /api/admin/faqs
POST   /api/admin/faqs
GET    /api/admin/faqs/{faq_id}
PUT    /api/admin/faqs/{faq_id}
DELETE /api/admin/faqs/{faq_id}
PUT    /api/admin/faqs/{faq_id}/status
GET    /api/visitor/customer-service
```

默认 FAQ 可通过 `backend/python/seed_faq.py` 幂等初始化。FAQ 表的迁移脚本位于 `backend/python/migrations/001_content_management.sql`，执行入口为 `backend/python/migrate_content.py`。

### 4.2.1 景点内容管理

第一阶段新增 `Spot` 管理页面 `/spots` 和以下接口：

```text
GET    /api/admin/spots
POST   /api/admin/spots
GET    /api/admin/spots/{spot_id}
PUT    /api/admin/spots/{spot_id}
DELETE /api/admin/spots/{spot_id}
```

管理员可以维护景区名称、景点名称、位置、经纬度、开放信息、核心功能、文化内涵、景点介绍、亮点、建筑参数和备注。游客端景点详情、讲解、推荐和路线规划继续读取同一张 `spots` 表，避免管理端和游客端维护两份景点内容。

### 4.3 运营数据看板

看板采用“概览卡片 + 趋势图 + 排行榜 + 分析结论”的布局。所有接口都必须支持 `start_date`、`end_date`，时间边界按左闭右开处理，避免漏掉结束日期当天的数据。

#### 指标定义

| 指标 | 数据来源 | 计算口径 |
| --- | --- | --- |
| 服务人次 | `VisitorInteraction`、会话数据 | 去重访客数、会话数、问答轮次分别展示 |
| 游客关注点 | `RouteHistory.route_data`、`AppUserBehavior` 导航记录 | 统计景点被路线包含的次数和实际导航次数 |
| 热门问答 | `VisitorInteraction.content` | 对游客问题归一化后计数，展示问题和咨询次数 |
| 热门路线 | `RouteHistory.route_data`、`total_duration`、`total_distance` | 按完整景点顺序聚合，展示路线名称、路径、时长、距离和使用次数 |
| 消费分析 | 灵山胜境相关 `VisitorBehavior` 消费字段 | 分析人均消费、非票消费、消费结构、占比和客单价区间 |
| 满意度 | `VisitorFeedback.satisfaction_score`、`feedback_type` | 只使用正式反馈，按服务类型计算平均分和满意率 |

#### 已实现后端接口

```text
GET /api/admin/analytics/overview
GET /api/admin/analytics/comparison
GET /api/admin/analytics/visitors
GET /api/admin/analytics/focus-points
GET /api/admin/analytics/hot-questions
GET /api/admin/analytics/routes
GET /api/admin/analytics/consumption
GET /api/admin/analytics/satisfaction
```

`overview` 返回卡片指标和营销建议；其余接口返回图表所需的时间序列、排行数据和筛选条件。当前版本直接聚合现有业务表。由于移除了 `visitor_interaction.satisfaction_score`，需要执行 `002_remove_interaction_satisfaction.sql`。查询量较大时再增加按日聚合表或物化视图，不在前端计算核心指标。

#### 营销决策分析

看板除展示原始数据，还应生成可解释的分析结论：

- 某景点关注度高但停留时间短：推荐增加讲解、休息点或动线引导。
- 某类问题集中在节假日前：提前更新 FAQ、公告和票务说明。
- 某路线使用率高但满意度低：检查拥堵、导航和景点顺序。
- 餐饮或文创消费占比下降：结合游客画像和活动安排制定促销策略。
- 负面评价集中于某服务场景：生成待处理事项并跟踪整改结果。

分析结论必须标注统计周期、数据量和生成时间，不能把低样本结果当作确定性结论。

### 4.4 数字人配置

现有 `DigitalHumanConfig` 已包含 `name`、`model`、`voice`、`clothes`、`is_active`。管理端应完善为：

1. 配置列表和当前生效标识。
2. 外观模型、封面图、Live2D/3D 资源地址配置。
3. 语音音色、语速、音量和语言配置。
4. 服装风格和节日主题配置。
5. 预览按钮：加载游客端相同资源，测试文本和语音播放。
6. 发布/回滚：配置先保存为草稿，发布后成为当前版本。
7. 操作记录：记录管理员、时间、变更字段和发布结果。

配置更新接口需要使用部分更新语义，未提交的字段不能被覆盖为 `null`。资源文件应使用对象存储或后端静态资源目录，数据库只保存 URL、版本和校验信息。

### 4.5 票务与活动管理

票务页面维护现有 `TicketProduct` 的名称、票种、适用人群、价格、官方说明和启用状态。活动页面维护现有 `ScenicActivity` 的类型、名称、地点、经纬度、时间、时长、活动内容、活动意义和启用状态。

管理端必须提供编辑、上下线、排序和来源标注。游客端只读取已发布数据；管理端录入错误、来源缺失或过期信息时，应阻止发布并提示原因。

## 5. 系统架构与数据流

```text
管理员浏览器
    |
    | React 管理端 /api/admin
    v
FastAPI 管理 API
    |
    +-- PostgreSQL：Knowledge / FAQ / TicketProduct / ScenicActivity
    |                VisitorInteraction / VisitorBehavior
    |                RouteHistory / VisitorFeedback / DigitalHumanConfig
    |
    +-- RAG 索引同步：KnowledgeChunk / Embedding / FAISS（可选）
    +-- 统计聚合：按日期、景点、问题、路线和消费类别聚合
    |
    +-- 游客端 /api/visitor：读取已发布内容和 FAQ
```

管理端和游客端必须共享同一套业务 API 和数据库，不允许在前端保留运营内容的第二份长期数据。所有写操作应通过服务层完成校验、审计和索引失效通知。

## 6. API 约定

### 6.1 通用规则

- 基础路径：`/api/admin`。
- 列表统一返回 `{ items, total, page, page_size }`。
- 成功写入返回资源对象和 `message`。
- 参数错误返回 400，资源不存在返回 404，重复或状态冲突返回 409。
- 所有写接口需要管理员身份和操作权限。
- 日期查询使用 ISO 日期，统计区间采用 `[start_date, end_date + 1 day)`。
- 删除优先使用软删除；真正物理删除需要管理员二次确认并记录审计日志。

### 6.2 已有接口与待补接口

| 领域 | 已有接口 | 待补或需完善 |
| --- | --- | --- |
| 知识库 | `/knowledge` CRUD、搜索、RAG 重建入口 | 状态、批量操作、软删除 |
| 景点 | `/spots` CRUD、关键词查询 | 发布状态、标签和讲解资源关联 |
| FAQ | `/faqs` CRUD、启停、排序；游客端数据库优先读取 | RAG 同步、批量排序、审计 |
| 数字人 | `/digital-human` CRUD、互斥发布、历史快照回滚、Live2D 画面预览、音色试听、带操作人审计；游客端当前配置接口 | - |
| 票务 | `/tickets` CRUD、编辑、上下线 | 审核、来源同步 |
| 活动 | `/activities` CRUD、编辑、上下线 | 审核、过期处理 |
| 报告 | `/report` | 拆分分析接口、真实看板数据、导出 |
| 日志 | `/logs` 日期/级别/来源查询、数字人操作审计 | 分页、详情、其他业务操作审计 |
| RAG | `/rag/reindex`、状态查询、任务步骤展示、失败重试 | 历史任务记录 |
| 权限 | 认证接口、管理员账号 CRUD、密码重置、固定/自定义角色、领域 RBAC、HttpOnly Cookie、CSRF 校验 | 更细粒度资源级策略 |

## 7. 安全与运营要求

1. 管理端增加登录页，使用短期 access token 和可撤销 refresh token。
2. FastAPI 增加管理员依赖，所有 `/api/admin/*` 默认拒绝匿名访问。
3. 使用 RBAC：系统管理员、内容运营、数据分析、数字人运营等角色按菜单和操作授权。
4. 知识、FAQ、票务、活动和数字人配置的新增、修改、删除、发布必须记录审计日志。
5. 对 HTML、脚本、文件 URL 和超长文本进行输入校验，防止 XSS、恶意文件和提示词注入。
6. 生产环境通过环境变量配置 API 地址，不能写死 `localhost`。
7. 数据看板只展示聚合数据；游客标识、问答内容等敏感信息按最小权限和脱敏原则处理。

## 8. 开发阶段与优先级

### 第一阶段：内容闭环（核心开发已完成，部署验证待完成）

- 已完成知识库编辑、关键词/分类查询、删除和 RAG 内容重建入口。
- 已新增 FAQ 表、管理页面、启停/排序能力和游客端数据库优先读取。
- 已新增景点 `Spot` 管理 CRUD，游客端继续读取同一张表。
- 已将票务和活动表单收敛到现有数据库字段，并增加编辑流程。
- 已在知识库写操作后清理检索缓存。
- 待在目标数据库执行 `migrate_content.py` 和 `seed_faq.py`，完成真实环境联调。
- 待补内容发布状态、软删除、批量操作和自动 embedding 更新；知识和 FAQ 等现有写操作已具备审计记录。

### 第二阶段：运营看板（核心开发已完成，运行联调待完成）

- 已新增概览、服务趋势、关注点、热门问答、路线、消费和满意度统计接口。
- 已将仪表盘随机数据替换为数据库聚合数据，并增加日期筛选。
- 已增加热门问答、路线偏好、消费结构和满意度图表。
- 已提供基于数据量和统计周期的营销建议及空数据状态。
- 已完成按日期和数据集导出 CSV；待补同比/环比、大数据量预聚合和真实数据库联调。

### 第三阶段：配置与业务扩展

- 已完成数字人配置编辑、取消编辑、互斥发布、历史快照回滚、音色试听、操作审计和游客端配置读取，更新接口采用部分更新语义，避免未提交字段被覆盖为空值。
- 已完成票务、活动编辑和发布状态维护；发布审核、来源校验仍待补充。
- 已完成 RAG 重建任务状态查询、轮询、分步骤结果展示和失败后重新提交；历史任务记录待补充。
- 已完成管理端 Live2D 真实画面预览和数字人审计的管理员身份关联。当前配置字段严格沿用现有模型，不新增未确认的资源字段。

### 第四阶段：安全和质量

- 已完成管理员登录、短期访问令牌、可撤销刷新令牌、管理员账号维护、密码重置、四类角色、领域接口 RBAC 和数字人/账号操作审计。
- 待补更细粒度资源级策略和权限审批流程。
- 增加后端接口测试、前端关键流程测试和端到端联调。
- 增加生产环境配置、部署脚本、监控和备份策略。

## 9. 验收标准

### 内容管理验收

- 管理员新增或修改知识条目后，游客端检索能得到最新内容。
- FAQ 在管理端修改、排序、停用后，客服页无需重新发布前端即可更新。
- 删除或下线内容后，游客端不会继续返回已失效内容。
- RAG 索引任务有明确的运行中、成功、失败和重试状态。

### 数据看板验收

- 所有核心指标均来自数据库或明确的聚合接口，不使用随机数。
- 日期筛选边界正确，空数据、异常数据和低样本情况有提示。
- 热门问答、路线偏好和消费分析能追溯到统计周期和数据量。
- 分析结论能够说明依据，不把推测展示为事实。

### 配置与业务验收

- 数字人配置保存后可预览，发布后游客端使用对应资源和语音配置。
- 票务和活动信息支持新增、编辑、上下线和删除，游客端只显示有效数据。
- 所有管理写操作均有权限校验和审计记录。

### 工程验收

- `npm run build`、`npm run lint` 和后端测试在干净环境通过。
- 管理端 API 地址、数据库连接和外部服务配置均来自环境变量。
- 至少覆盖知识库、FAQ、报告统计和权限校验的自动化测试。

## 10. 当前风险与处理建议

- 仪表盘已切换为真实聚合接口，但大数据量下仍需增加索引、预聚合或物化视图。
- 报告接口返回的评论对象与前端渲染字段不一致，需先修复再进行演示。
- 管理端已增加基础鉴权，但使用默认开发签名密钥时仍不应部署到公网；生产环境必须设置 `ADMIN_TOKEN_SECRET` 并通过 HTTPS 提供服务。
- 现有项目文档与代码进度不同步，完成每个阶段后应更新本文件的状态表和接口表。

## 11. 第一阶段开发同步记录

### 11.1 本次代码变更

| 范围 | 变更内容 |
| --- | --- |
| 数据模型 | 新增 `FAQItem`；票务和活动沿用现有数据库字段 |
| 数据迁移 | 新增 `migrations/001_content_management.sql`、`002_remove_interaction_satisfaction.sql` 和按序执行的 `migrate_content.py` |
| FAQ 初始化 | 新增幂等脚本 `seed_faq.py` |
| 管理 API | 新增 FAQ CRUD/启停、Spot CRUD；知识库支持关键词查询和缓存失效 |
| 检索服务 | FAQ 纳入 chunk 同步和 legacy 检索，启用 FAQ 可被 AI 问答检索 |
| 游客 API | `/api/visitor/customer-service` 改为数据库优先读取 FAQ |
| 管理端 | 新增 `/faqs`、`/spots` 页面；知识、票务和活动增加编辑流程 |
| 配置 | 管理端 API 基地址支持 `VITE_API_BASE_URL` 环境变量 |

### 11.2 部署步骤

```powershell
cd backend/python
pip install -r requirements.txt
python migrate_content.py
python seed_faq.py
python main.py
```

管理端启动：

```powershell
cd frontend/admin-app
npm install
npm run dev
```

### 11.3 验证记录

- `npm run build`：通过，新增 FAQ、Spot 和编辑页面可完成生产构建。
- Python `py_compile`：通过，模型、管理 API、游客 API、迁移和初始化脚本无语法错误。
- `git diff --check`：通过，仅存在 Windows 换行符提示。
- 数据库端口：本地 PostgreSQL `5432` 可访问。
- 数据库迁移：用户已执行第一阶段迁移和 FAQ 初始化；后续结构调整继续通过编号迁移脚本执行。
- 后端运行测试：当前 Python 环境同时缺少 `fastapi`，需安装依赖后继续接口联调。

## 12. 第二阶段开发同步记录

### 12.1 统计口径

- 服务人次：统计周期内交互、路线、反馈和行为数据中的去重 `visitor_id`。
- 会话数：`VisitorInteraction.session_id` 去重数量。
- 热门问答：`VisitorInteraction` 中 `interaction_type = chat` 的问题归一化后计数。
- 游客关注点：解析 `RouteHistory.route_data.route`，并叠加 `AppUserBehavior.behavior_type = navigate` 的导航次数。
- 热门路线：以有序景点序列作为路线签名，聚合相同路线并展示名称、路径、平均时长、平均距离和使用次数。
- 消费分析：仅保留 `attraction_name` 与当前 `spots` 表匹配的灵山胜境行为记录，分析五类消费、总消费、非票消费和客单价区间。
- 满意度：只使用 `VisitorFeedback.satisfaction_score`，并按 `feedback_type` 分组。

所有接口采用 `[start_date, end_date + 1 day)` 时间边界，避免遗漏结束日期当天的数据；单次查询最多 366 天。

### 12.2 本次代码变更

| 范围 | 变更内容 |
| --- | --- |
| 后端路由 | 新增 `app/api/analytics.py`，挂载到 `/api/admin/analytics` |
| 概览指标 | 服务人次、会话数、互动次数、路线数、人均消费、满意率 |
| 专项分析 | 服务趋势、路线/导航关注点、热门问答、热门路线、灵山消费结构、反馈满意度分布 |
| 营销分析 | 根据最高关注景点、热门问题、消费类别和满意率生成数据化建议 |
| 管理端 | 仪表盘移除全部随机数据，接入七个真实统计接口 |
| 交互状态 | 增加日期筛选、加载、错误和空数据状态 |

### 12.3 接口列表

```text
GET /api/admin/analytics/overview
GET /api/admin/analytics/visitors
GET /api/admin/analytics/focus-points
GET /api/admin/analytics/hot-questions
GET /api/admin/analytics/routes
GET /api/admin/analytics/consumption
GET /api/admin/analytics/satisfaction
```

所有接口支持 `start_date` 和 `end_date`，关注点、热门问答和热门路线支持 `limit`。热门路线仅能统计已经写入 `route_history` 的路线；如果游客生成路线但未保存，系统无法将其纳入历史路线排行。

### 12.4 数据库说明

本次口径调整移除了未被业务写入的 `visitor_interaction.satisfaction_score`。需要重新执行：

```powershell
cd backend/python
python migrate_content.py
```

迁移执行器会按文件名顺序执行 `001_content_management.sql` 和 `002_remove_interaction_satisfaction.sql`；两者均可重复执行。

### 12.5 验证记录

- `npm run build`：通过，真实数据看板和全部图表可完成生产构建。
- Python `py_compile`：通过，analytics 路由和路由注册无语法错误。
- `git diff --check`：通过，仅存在 Windows 换行符提示。
- 后端接口运行测试：当前执行环境缺少 `fastapi`，未能在本机启动服务；安装项目依赖后需要使用真实数据库完成七个接口的联调验证。
- 构建提示：ECharts 使主包超过 500 kB，功能不受影响，后续可通过路由懒加载和手动分包优化。

## 13. 第三阶段开发同步记录

### 13.1 数字人配置

- 管理端 `/digital-human` 已支持新增、编辑、取消编辑、互斥发布、历史快照回滚、配置预览、音色试听和删除。
- 编辑表单沿用现有 `DigitalHumanConfig` 字段：`name`、`model`、`voice`、`clothes`、`is_active`，未新增原项目没有确认的资源字段。
- `PUT /api/admin/digital-human/{config_id}` 使用 `model_dump(exclude_unset=True)` 做部分更新；仅切换启用状态时不会清空其他配置，名称为空会返回 400。
- 新增 `PUT /api/admin/digital-human/{config_id}/activate`。发布时会停用其他配置，保证游客端只有一个当前配置；当前生效配置不能直接删除。
- 修改当前生效配置时，后端会先在同一张表保存一个未发布历史快照；列表中的历史配置可以通过“发布/回滚”重新生效，不需要新增版本表。
- 新增 `GET /api/visitor/digital-human/config`。游客端聊天页加载时读取当前配置，将 `model` 作为 Live2D 模型路径，并将 `voice` 传给 TTS；数据库没有已发布配置时使用项目内置模型和女声。
- `voice` 目前与现有 TTS 能力保持一致，仅支持 `female` 和 `male`。管理端试听优先调用 `/api/ai/tts`，服务不可用时降级到浏览器语音。
- 管理端当前预览展示配置摘要和音色效果，尚未在 React 管理端重复引入游客端 Live2D 渲染运行时。

### 13.2 数字人操作审计

- 数字人新增、修改、发布/回滚和删除会在同一数据库事务中写入 `system_logs`，日志来源为 `admin.digital-human`。
- 日志消息使用结构化 JSON 保存操作类型、配置 ID、配置名称、变更字段、快照 ID 和操作人信息。
- `/api/admin/logs` 新增 `source` 筛选，修复结束日期只查询到当天零点的问题，并按时间倒序返回。
- 管理端日志页面支持按“数字人配置”来源筛选，并将结构化日志显示为操作、对象和详情。

### 13.3 RAG 运维

- 知识库页面已接入 `GET /api/admin/rag/reindex/status`，进入页面时读取任务状态。
- 提交重建后自动轮询运行状态，展示排队中、执行中、已完成、失败等状态，以及 `sync_chunks`、`sync_embeddings`、`build_faiss` 各步骤返回结果和失败信息。
- 重建期间按钮自动禁用，后端仍以运行锁防止重复任务。失败重试可通过再次提交任务完成，历史任务记录暂未持久化。

### 13.4 本阶段验证

- 管理端 `npm run build`：通过，数字人发布和预览页面可完成生产构建（ECharts 主包体积警告仍存在）。
- 游客端 `npm run build:h5`：通过，当前配置读取、模型切换和 TTS 音色传递可完成 H5 构建；仅有现有 Sass 弃用提示。
- Python `py_compile`：通过，覆盖 `app/api/admin.py`、`app/api/visitor.py` 和 `app/api/rag_admin.py`。
- 管理端 `npm run lint`：第四阶段已补充 ESLint 配置并通过检查。
- 真实 RAG 重建依赖 embedding/FAISS 环境，未在缺少完整 Python 依赖的环境中启动联调。

## 14. 第四阶段开发同步记录

### 14.1 管理员认证

- 新增 `admin_users` 和 `admin_sessions`。密码使用 PBKDF2-SHA256 加盐哈希，不保存明文；刷新令牌在数据库中只保存 SHA-256 摘要。
- 访问令牌默认有效期 15 分钟，刷新令牌默认有效期 7 天。刷新时执行令牌轮换，旧刷新令牌立即撤销；退出登录也会撤销当前刷新令牌。
- 新增以下接口：

```text
POST /api/admin/auth/login
POST /api/admin/auth/refresh
POST /api/admin/auth/logout
GET  /api/admin/auth/me
```

- `/api/admin/*`、`/api/admin/rag/*` 和 `/api/admin/analytics/*` 已统一挂载 `require_admin` 鉴权依赖，认证接口除外。
- 管理端新增登录页、会话恢复、请求头注入、访问令牌自动刷新、刷新失败回到登录页和服务端退出撤销。

### 14.2 初始化步骤

本阶段新增 `migrations/003_admin_auth.sql` 和 `004_admin_roles.sql`，必须执行迁移并创建初始管理员：

```powershell
cd backend/python
$env:ADMIN_TOKEN_SECRET = "请替换为足够长的随机字符串"
$env:ADMIN_BOOTSTRAP_USERNAME = "admin"
$env:ADMIN_BOOTSTRAP_PASSWORD = "请设置至少10位的强密码"
$env:ADMIN_BOOTSTRAP_DISPLAY_NAME = "系统管理员"
python migrate_content.py
python seed_admin.py
python main.py
```

生产环境必须将 `ADMIN_TOKEN_SECRET` 固定配置在安全的环境变量管理系统中。未设置时后端会使用仅限本地开发的默认密钥并输出警告，服务重启后虽然令牌格式仍可验证，但该默认值不具备生产安全性。

### 14.3 当前边界

- 已提供 `admin`、`content_operator`、`analyst`、`digital_operator` 四类固定角色，尚未提供自定义角色和权限策略编辑器。
- 初始系统管理员仍由 `seed_admin.py` 创建；登录后可在权限管理页面新增、编辑、停用其他管理员并重置密码。
- 前端只在 `localStorage` 保存短期访问令牌；刷新令牌已迁移到 `HttpOnly`、`SameSite` Cookie，生产环境通过 `ADMIN_COOKIE_SECURE=true` 启用 `Secure` 属性。后续仍需补充 CSRF 防护和更严格的 Cookie 域策略。
- 管理业务审计日志已从认证上下文写入操作人 ID 和用户名。

### 14.4 验证记录

- 管理端 `npm run build`：通过，登录、会话恢复和受保护管理页面可完成生产构建。
- 管理端 `npm run lint`：通过，新增 `.eslintrc.cjs` 并修复现有不规则空白字符。
- Python `py_compile`：通过，覆盖认证服务、认证依赖、认证 API、模型、迁移和初始化脚本。
- `003_admin_auth.sql`：现有迁移器可正确识别 6 条幂等迁移语句。
- 真实登录联调：需要先执行 `003_admin_auth.sql` 和 `seed_admin.py`。

## 15. 第五阶段开发同步记录

### 15.1 固定角色与权限

| 角色 | 权限范围 |
| --- | --- |
| `admin` | 全部管理页面、接口、日志和账号维护 |
| `content_operator` | 知识库、FAQ、景点、票务、活动、讲解资源和 RAG 读写 |
| `analyst` | 数据看板、运营分析接口和游客反馈报告只读访问 |
| `digital_operator` | 数字人配置查询、编辑、发布和回滚 |

后端根据请求路径和方法映射 `content.read/write`、`analytics.read`、`digital_human.read/write`、`system.logs` 和 `system.manage`。前端根据登录响应中的 `permissions` 显示菜单和注册路由；后端权限依赖仍是最终安全边界，越权请求返回 403。

### 15.2 管理员账号管理

系统管理员可在 `/permission` 页面完成：

- 查询管理员账号、角色、状态和最近登录时间。
- 新增管理员并分配固定角色。
- 修改显示名称和角色。
- 启用或停用账号；停用时撤销该账号的刷新会话。
- 重置密码；密码重置后撤销该账号的全部刷新会话。
- 系统阻止当前管理员停用自己或移除自己的 `admin` 角色，避免误操作导致管理端无人可用。

新增接口：

```text
GET  /api/admin/auth/users
POST /api/admin/auth/users
PUT  /api/admin/auth/users/{user_id}
PUT  /api/admin/auth/users/{user_id}/password
```

账号新增、修改和密码重置写入 `system_logs`，来源为 `admin.users`，并记录操作人 ID 和用户名。

### 15.3 验证记录

- 管理端 `npm run build`：通过。
- 管理端 `npm run lint`：通过，0 错误、0 警告。
- Python `py_compile`：通过，覆盖 RBAC 依赖、认证 API、路由注册和模型。
- `git diff --check`：通过，仅有 Windows 换行符提示。
- 真实数据库权限联调：需先执行第四阶段认证迁移并创建初始管理员。

## 16. 第六阶段开发同步记录

### 16.1 运营数据导出

- 新增 `GET /api/admin/analytics/export`，复用看板已有统计函数，避免前端重新计算指标。
- 支持 `overview`、`visitors`、`focus_points`、`hot_questions`、`routes`、`consumption`、`satisfaction` 七类数据集。
- 所有导出都支持 `start_date` 和 `end_date`，沿用看板的日期校验和最多 366 天限制。
- CSV 使用 UTF-8 BOM，便于 Windows Excel 正确识别中文；导出接口继承 `analytics.read` 权限。
- 看板新增数据集选择和“导出 CSV”按钮，文件名包含数据集和统计日期范围。

### 16.2 管理写操作审计

- 知识库、FAQ、景点、票务、活动和景点讲解资源的新增、修改、删除、发布/下线和资源生成现在均写入 `system_logs`。
- 日志来源分别为 `admin.knowledge`、`admin.faq`、`admin.spots`、`admin.tickets`、`admin.activities` 和 `admin.spot-guide-assets`。
- 知识库、FAQ、景点、票务和活动 CRUD 审计与业务写入使用同一事务；讲解资源生成沿用服务内部提交机制，生成成功后追加审计记录。
- `/logs` 页面已增加上述来源筛选和操作类型展示。

### 16.3 验证记录

- 管理端 `npm run build`：通过，数据集选择和 CSV 下载功能可完成生产构建。
- 管理端 `npm run lint`：通过，0 错误、0 警告。
- Python `py_compile`：通过，覆盖 `app/api/analytics.py` 和管理写操作审计代码。

## 17. 生产强化开发同步记录

### 17.1 Live2D 真实画面预览

- 游客端新增 `/pages/digital-human-preview/index`，复用 `digital-human-simple` 组件及 Pixi/Cubism 运行时，实际加载 `.model3.json`、纹理、动作和表情资源。
- 预览页支持待机、聆听、思考、说话四种状态，以及平和、微笑、安抚、惊喜四种表情切换，并展示模型正常、加载中和加载失败状态。
- 管理端数字人页面通过 iframe 嵌入预览页，将未保存的名称、模型路径和服装作为查询参数传入；点击“刷新画面”不会修改数据库或当前游客端配置。
- 管理端保留“新窗口预览”，方便检查较大画面和浏览器 WebGL 兼容性。

开发环境默认预览地址：

```text
http://localhost:8080/#/pages/digital-human-preview/index
```

如果游客端部署在其他地址，需要在管理端构建环境设置：

```text
VITE_VISITOR_PREVIEW_URL=https://visitor.example.com/#/pages/digital-human-preview/index
```

模型路径必须能由游客端站点访问，并包含模型 JSON 所引用的 `.moc3`、纹理、动作、表情和物理配置文件。预览成功只证明资源可加载；模型动作组或表情名称与项目约定不一致时，相应交互仍可能不执行。

### 17.2 验证记录

- 管理端 `npm run build`：通过，Live2D iframe 预览页面可完成生产构建。
- 管理端 `npm run lint`：通过，0 错误、0 警告。
- 游客端 `npm run build:h5`：通过，新增预览路由和模型查询参数可完成 H5 构建；仍有现有 Sass 弃用提示。
- 浏览器画面验证：由开发人员手动启动管理端和游客端 H5 服务后检查 WebGL 画面、动作和表情。

### 17.3 会话安全强化

- 管理端刷新令牌改为 `HttpOnly` Cookie，前端不再把新的刷新令牌写入 `localStorage`；访问令牌仍保持短期有效。
- `/api/admin/auth/login` 和 `/refresh` 设置或轮换 Cookie，`/logout` 撤销数据库会话并清理 Cookie。
- 登录后同时设置非 HttpOnly 的 CSRF Cookie；管理端自动发送 `X-CSRF-Token`，刷新和退出接口要求 Cookie 与请求头匹配。
- 开发环境默认 `ADMIN_COOKIE_SECURE=false`，生产环境必须使用 HTTPS 并设置 `ADMIN_COOKIE_SECURE=true`。

## 18. 自动化测试强化记录

### 18.1 管理认证测试

新增 `tests/test_admin_auth.py`，使用 `unittest` 和 SQLite 内存数据库覆盖：

- 登录响应中的 `created_at`、`last_login_at` 可正确序列化，防止再次出现 `datetime is not JSON serializable`。
- 登录设置 `HttpOnly` 刷新 Cookie 和 CSRF Cookie。
- 刷新接口拒绝错误 CSRF 请求头，并轮换刷新令牌、撤销旧会话。
- 退出接口撤销数据库会话并清理刷新 Cookie、CSRF Cookie。
- 内容运营、数据分析、数字人运营和系统管理员的固定权限边界。

运行方式：

```powershell
cd backend/python
python -m unittest tests.test_admin_auth -v
```

当前 Codex 工具使用的 Python 环境缺少 FastAPI/SQLAlchemy，测试按项目既有规则自动跳过；在已经能够运行 Uvicorn 的项目 Python 环境中会执行完整测试。测试文件语法检查和差异检查已通过。

## 19. 自定义角色策略开发记录

### 19.1 数据库角色策略

- 新增 `admin_roles` 表，保存角色标识、显示名称、权限列表和系统角色标记。
- `004_admin_roles.sql` 幂等初始化 `admin`、`content_operator`、`analyst`、`digital_operator` 四个系统角色。
- 后端鉴权优先读取数据库角色权限，数据库策略不可用时仅使用内置策略作为兼容兜底。
- 系统管理员角色不能删除或修改全部权限；自定义角色被管理员账号使用时不能删除。

### 19.2 管理端角色维护

权限管理页面新增角色策略区域，系统管理员可以：

- 创建自定义角色并勾选内容、分析、数字人、日志和账号管理权限。
- 编辑自定义角色权限，也可以调整系统内容运营、数据分析和数字人运营角色的权限。
- 删除未被任何管理员使用的自定义角色。

新增接口：

```text
GET    /api/admin/auth/roles
POST   /api/admin/auth/roles
PUT    /api/admin/auth/roles/{role_id}
DELETE /api/admin/auth/roles/{role_id}
```

角色新增、修改和删除会写入 `admin.roles` 审计日志；账号分配角色时只允许选择数据库中存在的角色。

### 19.3 验证记录

- 管理端 `npm run build`：通过，包含自定义角色表单、编辑和删除流程。
- 管理端 `npm run lint`：通过，0 错误、0 警告。
- Python `py_compile`：通过，覆盖角色模型、鉴权依赖、认证 API 和路由注册。
- `git diff --check`：通过，仅有 Windows 换行符提示。

## 20. 运营看板趋势分析开发记录

### 20.1 同周期对比接口

- 新增 `GET /api/admin/analytics/comparison`，沿用看板的 `start_date`、`end_date` 参数和最多 366 天校验。
- 接口自动计算当前筛选区间之前的等长周期，并返回服务人次、会话数、互动次数、路线生成、反馈数、人均消费和满意率的当前值、上期值、绝对变化和变化率。
- 上期指标为 0 时不伪造百分比，变化率返回 `null`；当前值和上期值均为 0 时返回 `0`，前端显示“上期为 0”或“较上期持平”。
- 接口复用已有概览聚合逻辑，不新增数据表，也不改变既有统计口径。

### 20.2 管理端展示

- 看板首次加载或修改日期后查询时并行请求对比接口。
- 六个核心指标卡片展示趋势文字和颜色状态，并在看板上标注实际对比日期范围。
- 趋势只作为运营参考，不替代原始数值；导出 CSV 和其他明细图表保持原有行为。

### 20.3 验证记录

- 管理端 `npm run build`：通过。
- 管理端 `npm run lint`：通过，0 错误、0 警告。
- Python `py_compile`：通过，覆盖新增对比接口和分析路由。
- `tests/test_analytics.py`：已覆盖等长上一周期、百分比变化和上期为 0 的边界；当前工具解释器因缺少 FastAPI/SQLAlchemy 自动跳过，需在项目运行环境执行完整测试。
