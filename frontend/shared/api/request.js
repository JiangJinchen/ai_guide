import axios from 'axios';
//只能给admin-app使用，因为它使用的是axios
// 创建axios实例
const request = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 可以在这里添加token等认证信息
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
request.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    // 统一处理错误
    console.error('请求错误:', error);
    return Promise.reject(error);
  }
);

export default request;