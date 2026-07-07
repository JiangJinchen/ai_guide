import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const today = new Date().toISOString().slice(0, 10)

function LogsPage() {
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [level, setLevel] = useState('')
  const [logs, setLogs] = useState([])
  const [message, setMessage] = useState('')

  const loadLogs = async () => {
    try {
      const params = { start_date: startDate, end_date: endDate }
      if (level) params.level = level
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
              <th>消息</th>
              <th>时间</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td>{log.id}</td>
                <td>{log.level}</td>
                <td>{log.source}</td>
                <td>{log.message}</td>
                <td>{log.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!logs.length && <p>暂无日志数据</p>}
      </div>
    </div>
  )
}

export default LogsPage
