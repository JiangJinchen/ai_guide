import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const today = new Date().toISOString().slice(0, 10)

const actionLabels = {
  create: '新增',
  create_and_publish: '新增并发布',
  update: '修改',
  update_and_publish: '修改并发布',
  publish: '发布/回滚',
  delete: '删除',
  reset_password: '重置密码',
  unpublish: '下线',
  generate: '生成资源'
}

const parseLogMessage = (message) => {
  try {
    const data = JSON.parse(message)
    if (data && data.action && data.resource_type) return data
  } catch (error) {
    // Legacy logs remain plain text.
  }
  return null
}

function LogsPage() {
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [level, setLevel] = useState('')
  const [source, setSource] = useState('')
  const [logs, setLogs] = useState([])
  const [message, setMessage] = useState('')

  const loadLogs = async () => {
    try {
      const params = { start_date: startDate, end_date: endDate }
      if (level) params.level = level
      if (source) params.source = source
      const res = await request.get('/admin/logs', { params })
      setLogs(res.data.logs || [])
      setMessage('')
    } catch (error) {
      setMessage('日志加载失败')
    }
  }

  useEffect(() => {
    loadLogs()
  }, [])

  return (
    <div>
      <h2>日志管理</h2>
      <div className="card toolbar">
        <label>开始日期</label>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <label>结束日期</label>
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <label>等级</label>
        <select value={level} onChange={(e) => setLevel(e.target.value)}>
          <option value="">全部</option>
          <option value="info">info</option>
          <option value="warning">warning</option>
          <option value="error">error</option>
        </select>
        <label>来源</label>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">全部</option>
          <option value="admin.digital-human">数字人配置</option>
          <option value="admin.users">管理员账号</option>
          <option value="admin.roles">角色策略</option>
          <option value="admin.knowledge">知识库</option>
          <option value="admin.faq">FAQ</option>
          <option value="admin.spots">景点</option>
          <option value="admin.tickets">票务</option>
          <option value="admin.activities">活动</option>
          <option value="admin.spot-guide-assets">讲解资源</option>
        </select>
        <button onClick={loadLogs}>查询</button>
      </div>

      {message && <p className="error">{message}</p>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>等级</th>
              <th>来源</th>
              <th>操作</th>
              <th>对象</th>
              <th>详情</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => {
              const audit = parseLogMessage(log.message)
              return (
                <tr key={log.id}>
                  <td>{log.id}</td>
                  <td>{log.level}</td>
                  <td>{log.source || '-'}</td>
                  <td>{audit ? actionLabels[audit.action] || audit.action : '-'}</td>
                  <td>{audit ? `${audit.resource_name || audit.resource_type} #${audit.resource_id}` : '-'}</td>
                  <td>{audit ? JSON.stringify(audit.details || {}) : log.message}</td>
                  <td>{log.created_at ? new Date(log.created_at).toLocaleString() : '-'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!logs.length && <p>暂无日志数据</p>}
      </div>
    </div>
  )
}

export default LogsPage
