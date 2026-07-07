# AI数字人智慧景区导览系统

## 项目介绍

AI数字人智慧景区导览系统是一个基于多模态AI技术的智能导览系统，旨在为游客提供个性化、智能化的景区导览体验，同时为景区管理员提供高效的管理工具。

### 核心功能

- **智能问答**：与数字人进行实时对话，获取景区信息
- **景点讲解**：详细了解景区各个景点的历史文化
- **个性化推荐**：根据用户兴趣推荐最佳游览路线
- **情感互动**：数字人会根据用户情绪调整交互方式
- **弱GPS适配**：在GPS信号弱的环境下提供定位服务
- **数字人渲染**：2D数字人实时渲染和表情/口型驱动
- **知识库管理**：管理景区知识，支持知识上传、编辑、检索、更新
- **数字人形象管理**：配置数字人形象、服装、声音等
- **游客感受度报告**：分析游客反馈，生成感受度报告
- **数据大屏概览**：实时展示景区数据，支持数据可视化

## 技术栈

### 前端
- **游客端前端**：Uniapp
- **管理端前端**：React + ECharts
- **前端公共依赖**：统一接口请求工具、实时通信工具、全局异常处理、通用组件

### 后端
- **开发语言**：Python + Node.js
- **API框架**：FastAPI（Python）、Express（Node.js）
- **实时通信**：WebSocket、SSE

### AI核心
- **多模态大模型**：通义千问免费API / 讯飞星火免费API
- **语音识别**：讯飞免费语音识别API
- **语音合成**：讯飞免费在线TTS API
- **数字人技术**：Live2D

### 数据存储
- **向量数据库**：Chroma/FAISS（本地CPU运行）
- **关系型数据库**：PostgreSQL

### 部署
- **部署模式**：本地部署（CPU运行，无需GPU）

## 项目结构

```
ai_guide/
├── frontend/                # 前端目录
│   ├── visitor-app/         # 游客端前端（Uniapp）
│   ├── admin-app/           # 管理端前端（React+ECharts）
│   └── shared/              # 前端公共依赖
├── backend/                 # 公共后端目录
│   ├── python/              # Python后端
│   ├── nodejs/              # Node.js后端
│   └── shared/              # 后端公共依赖
├── data/                    # 数据存储目录
│   ├── chroma/              # Chroma向量数据库
│   ├── faiss/               # FAISS向量数据库
│   └── postgres/             # PostgreSQL数据库配置
└── docs/                    # 项目文档
```

## 部署步骤

### 本地运行

1. **环境准备**
   - 安装Python 3.8+
   - 安装Node.js 14+
   - 安装PostgreSQL 15+
   - 确保端口8080、3000、8000、8081、5432可用

2. **数据库配置**
   - 启动PostgreSQL服务
   - 创建数据库：
     ```bash
     psql -U postgres -c "CREATE DATABASE ai_guide;"
     ```

3. **配置AI API（可选）**
   - 系统默认提供基础问答功能
   - 如需更强大的AI能力，请配置免费在线API：
     ```bash
     # Windows环境
     set AI_PROVIDER=qwen
     set AI_API_KEY=your_qwen_api_key

     # 或设置讯飞星火API
     set AI_PROVIDER=xinghuo
     set XINGHUO_APP_ID=your_app_id
     set XINGHUO_API_SECRET=your_api_secret

     # 讯飞语音识别API（可选）
     set ASR_API_KEY=your_asr_api_key

     # 讯飞语音合成API（可选）
     set TTS_API_KEY=your_tts_api_key
     
     # Linux/macOS环境
     export AI_PROVIDER=qwen
     export AI_API_KEY=your_qwen_api_key
     ```

4. **启动服务**
   
   **启动Python后端**
   ```bash
   cd backend/python
   pip install -r requirements.txt
   python main.py
   ```
   
   **启动Node.js后端**
   ```bash
   cd backend/nodejs
   npm install
   npm run dev
   ```
   
   **启动游客端前端**
   ```bash
   cd frontend/visitor-app
   npm install
   npm run dev
   ```
   
   **启动管理端前端**
   ```bash
   cd frontend/admin-app
   npm install
   npm run dev
   ```

5. **访问服务**
   - 游客端前端：http://localhost:8080
   - 管理端前端：http://localhost:3000
   - 后端API：http://localhost:8000/api
   - WebSocket服务：ws://localhost:8081

## 开发指南

### 前端开发

1. **游客端前端（Uniapp）**
   ```bash
   cd frontend/visitor-app
   # 安装依赖
   npm install
   # 启动开发服务器
   npm run dev
   ```

2. **管理端前端（React）**
   ```bash
   cd frontend/admin-app
   # 安装依赖
   npm install
   # 启动开发服务器
   npm run dev
   ```

### 后端开发

1. **Python后端**
   ```bash
   cd backend/python
   # 安装依赖
   pip install -r requirements.txt
   # 启动开发服务器
   python main.py
   ```

2. **Node.js后端**
   ```bash
   cd backend/nodejs
   # 安装依赖
   npm install
   # 启动开发服务器
   npm run dev
   ```

## 关键接口

### 游客端前端与公共后端接口
- **多模态交互接口**：语音输入/输出、文本输入/输出、数字人驱动
- **实时交互接口**：WebSocket连接建立/关闭、实时语音/文本数据传输、数字人实时响应推送
- **业务接口**：个性化路线推荐、景点讲解、弱GPS适配

### 管理端前端与公共后端接口
- **知识库接口**：知识上传、编辑、检索、更新
- **数字人配置接口**：形象、服装、声音配置
- **数据统计与分析接口**：交互数据采集、报告生成、数据大屏
- **系统通用接口**：权限验证、日志查询、异常告警

### AI核心接口（内部调用）
- **AI推理接口**：调用在线多模态API进行智能问答
- **语音识别（ASR）接口**：调用在线API进行语音转文字
- **语音合成（TTS）接口**：调用在线API进行文字转语音
- **RAG检索接口**：基于本地向量数据库进行知识检索

## 注意事项

1. **在线API配置**：如需使用在线AI能力，请自行申请免费的API Key
   - 通义千问：https://dashscope.console.aliyun.com/
   - 讯飞星火：https://xinghuo.xfyun.cn/
   - 申请后通过环境变量配置即可使用

2. **调用频率限制**：免费API有调用频率限制，请注意控制请求频率
   - 通义千问免费版：QPS限制为2
   - 讯飞星火免费版：每日调用次数有限

3. **本地降级**：未配置API Key时，系统会使用本地降级响应，保证基本功能可用

4. **数据安全**：确保敏感数据的加密存储和传输

5. **性能优化**：针对高并发场景进行优化，确保系统响应速度

6. **兼容性**：确保前端在不同设备上的兼容性

7. **监控与日志**：建立完善的监控和日志系统，便于问题排查

## 后续开发计划

1. **增强AI能力**：集成更多先进的AI模型，提升智能问答和推荐能力
2. **扩展数字人功能**：支持更多数字人形象和交互方式
3. **优化用户体验**：提升前端交互体验，增加更多个性化功能
4. **完善数据分析**：提供更丰富的数据统计和分析功能
5. **支持多语言**：增加多语言支持，服务国际游客

## 联系方式

如有问题或建议，请联系项目团队。

---

© 2026 AI数字人智慧景区导览系统