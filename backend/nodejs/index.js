const express = require('express');
const WebSocket = require('ws');
const http = require('http');
const cors = require('cors');
const dotenv = require('dotenv');

// 加载环境变量
dotenv.config();

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// 配置CORS
app.use(cors());
app.use(express.json());

// 存储WebSocket连接
const connections = new Map();

// WebSocket连接处理
wss.on('connection', (ws) => {
  const clientId = Math.random().toString(36).substr(2, 9);
  connections.set(clientId, ws);
  console.log(`Client ${clientId} connected`);

  // 发送欢迎消息
  ws.send(JSON.stringify({
    type: 'welcome',
    message: 'Welcome to AI Digital Human Smart Scenic Spot Guide System'
  }));

  // 接收消息
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      console.log('Received message:', data);

      // 处理不同类型的消息
      switch (data.type) {
        case 'chat':
          // 处理聊天消息
          handleChatMessage(clientId, data);
          break;
        case 'digital_human':
          // 处理数字人控制消息
          handleDigitalHumanMessage(clientId, data);
          break;
        default:
          console.log('Unknown message type:', data.type);
      }
    } catch (error) {
      console.error('Error parsing message:', error);
    }
  });

  // 连接关闭
  ws.on('close', () => {
    connections.delete(clientId);
    console.log(`Client ${clientId} disconnected`);
  });

  // 连接错误
  ws.on('error', (error) => {
    console.error(`Client ${clientId} error:`, error);
  });
});

// 处理聊天消息
function handleChatMessage(clientId, data) {
  // 这里应该集成AI模型进行回答
  const response = {
    type: 'chat',
    message: 'This is a response from the server',
    digital_human_action: 'speak'
  };

  // 发送响应
  const ws = connections.get(clientId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(response));
  }
}

// 处理数字人控制消息
function handleDigitalHumanMessage(clientId, data) {
  // 这里应该处理数字人控制逻辑
  console.log('Digital human control:', data);
}

// SSE端点
app.get('/api/sse', (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  // 发送初始数据
  res.write(`data: ${JSON.stringify({ type: 'init', message: 'SSE connection established' })}\n\n`);

  // 定期发送数据
  const interval = setInterval(() => {
    const data = {
      type: 'update',
      visitor_count: Math.floor(Math.random() * 1000),
      interaction_count: Math.floor(Math.random() * 500),
      satisfaction_rate: (Math.random() * 20 + 80).toFixed(1)
    };
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  }, 5000);

  // 连接关闭
  req.on('close', () => {
    clearInterval(interval);
    console.log('SSE connection closed');
  });
});

// 健康检查
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// 启动服务器
const port = process.env.PORT || 8081;
server.listen(port, () => {
  console.log(`Node.js backend server running on port ${port}`);
  console.log(`WebSocket server running at ws://localhost:${port}`);
  console.log(`SSE endpoint available at http://localhost:${port}/api/sse`);
});