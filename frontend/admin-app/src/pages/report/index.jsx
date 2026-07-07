import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const today = new Date().toISOString().slice(0, 10)

function ReportPage() {
  const [startDate, setStartDate] = useState(today)
  const [endDate, setEndDate] = useState(today)
  const [report, setReport] = useState(null)
  const [message, setMessage] = useState('')

  const loadReport = async () => {
    try {
      const res = await request.get('/admin/report', {
        params: { start_date: startDate, end_date: endDate }
      })
      setReport(res.data.report)
      setMessage('')
    } catch (error) {
      setMessage('报表加载失败')
    }
  }

  useEffect(() => {
    loadReport()
  }, [])

  return (
    <div>
      <h2>游客感受度报告</h2>
      <div className="card toolbar">
        <label>开始日期</label>
        <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <label>结束日期</label>
        <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <button onClick={loadReport}>查询</button>
      </div>

      {message && <p className="error">{message}</p>}

      <div className="card">
        <h3>满意度概览</h3>
        <p className="metric-value">{report ? `${Number(report.satisfaction_rate || 0).toFixed(1)}%` : '--'}</p>
      </div>

      <div className="card">
        <h3>游客评论</h3>
        {report?.comments?.length ? (
          <ul>
            {report.comments.map((comment, index) => <li key={index}>{comment}</li>)}
          </ul>
        ) : (
          <p>暂无评论数据</p>
        )}
      </div>
    </div>
  )
}

export default ReportPage
