import React, { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import request from '../../api/request'

const isoDate = (date) => date.toISOString().slice(0, 10)
const today = new Date()
const defaultStart = new Date(today.getTime() - 29 * 24 * 60 * 60 * 1000)

const emptyOverview = {
  visitor_count: 0,
  session_count: 0,
  interaction_count: 0,
  route_count: 0,
  average_spend: 0,
  satisfaction_rate: 0,
  insights: []
}

const emptyComparison = { changes: {}, comparison_period: null }

function MetricTrend({ comparison, suffix = '' }) {
  if (!comparison) return <span className="metric-trend metric-trend-empty">暂无上期数据</span>
  const delta = Number(comparison.delta || 0)
  const rate = comparison.rate
  const className = delta > 0 ? 'metric-trend metric-trend-up'
    : delta < 0 ? 'metric-trend metric-trend-down'
      : 'metric-trend metric-trend-flat'
  const label = rate === null
    ? '上期为 0'
    : delta === 0
      ? '较上期持平'
      : `较上期 ${delta > 0 ? '↑' : '↓'} ${Math.abs(Number(rate)).toFixed(1)}%`
  return <span className={className} title={`上期值：${comparison.previous}${suffix}`}>{label}</span>
}

function Chart({ option }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return undefined
    const chart = echarts.init(containerRef.current)
    chart.setOption(option, true)
    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
    }
  }, [option])

  return <div ref={containerRef} className="analytics-chart" />
}

function DashboardPage() {
  const [startDate, setStartDate] = useState(isoDate(defaultStart))
  const [endDate, setEndDate] = useState(isoDate(today))
  const [overview, setOverview] = useState(emptyOverview)
  const [comparison, setComparison] = useState(emptyComparison)
  const [visitors, setVisitors] = useState([])
  const [focusPoints, setFocusPoints] = useState([])
  const [questions, setQuestions] = useState([])
  const [routes, setRoutes] = useState({ popular_routes: [] })
  const [consumption, setConsumption] = useState({ categories: [] })
  const [satisfaction, setSatisfaction] = useState({ distribution: {}, negative_feedback: [] })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [exportDataset, setExportDataset] = useState('overview')
  const [exporting, setExporting] = useState(false)

  const loadAnalytics = async () => {
    setLoading(true)
    setError('')
    const params = { start_date: startDate, end_date: endDate }
    try {
      const [overviewRes, comparisonRes, visitorsRes, focusRes, questionsRes, routesRes, consumptionRes, satisfactionRes] = await Promise.all([
        request.get('/admin/analytics/overview', { params }),
        request.get('/admin/analytics/comparison', { params }),
        request.get('/admin/analytics/visitors', { params }),
        request.get('/admin/analytics/focus-points', { params }),
        request.get('/admin/analytics/hot-questions', { params }),
        request.get('/admin/analytics/routes', { params }),
        request.get('/admin/analytics/consumption', { params }),
        request.get('/admin/analytics/satisfaction', { params })
      ])
      setOverview(overviewRes.data || emptyOverview)
      setComparison(comparisonRes.data || emptyComparison)
      setVisitors(visitorsRes.data.series || [])
      setFocusPoints(focusRes.data.items || [])
      setQuestions(questionsRes.data.items || [])
      setRoutes(routesRes.data || { popular_routes: [] })
      setConsumption(consumptionRes.data || { categories: [] })
      setSatisfaction(satisfactionRes.data || { distribution: {}, negative_feedback: [] })
    } catch (requestError) {
      setError(requestError.response?.data?.detail || '运营数据加载失败，请确认后端服务和数据库状态')
    } finally {
      setLoading(false)
    }
  }

  const exportAnalytics = async () => {
    setExporting(true)
    setError('')
    try {
      const response = await request.get('/admin/analytics/export', {
        params: { dataset: exportDataset, start_date: startDate, end_date: endDate },
        responseType: 'blob'
      })
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `灵山运营数据_${exportDataset}_${startDate}_${endDate}.csv`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || '运营数据导出失败')
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    loadAnalytics()
  }, [])

  const visitorOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['服务人次', '互动次数'] },
    grid: { left: 48, right: 20, top: 48, bottom: 42 },
    xAxis: { type: 'category', data: visitors.map(item => item.date.slice(5)) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '服务人次', type: 'line', smooth: true, data: visitors.map(item => item.visitor_count), itemStyle: { color: '#2563eb' } },
      { name: '互动次数', type: 'line', smooth: true, data: visitors.map(item => item.interaction_count), itemStyle: { color: '#16a34a' } }
    ]
  }

  const focusOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['路线包含次数', '导航次数'] },
    grid: { left: 90, right: 20, top: 24, bottom: 34 },
    xAxis: { type: 'value', minInterval: 1 },
    yAxis: { type: 'category', inverse: true, data: focusPoints.map(item => item.name) },
    series: [
      { name: '路线包含次数', type: 'bar', stack: 'focus', data: focusPoints.map(item => item.route_count), itemStyle: { color: '#0f766e' } },
      { name: '导航次数', type: 'bar', stack: 'focus', data: focusPoints.map(item => item.navigation_count), itemStyle: { color: '#2563eb' } }
    ]
  }

  const consumptionOption = {
    tooltip: { trigger: 'item', valueFormatter: value => `￥${Number(value).toFixed(2)}` },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: '68%',
      data: (consumption.categories || []).map(item => ({ name: item.name, value: item.total }))
    }]
  }

  const satisfactionOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 20, top: 24, bottom: 38 },
    xAxis: { type: 'category', data: ['1分', '2分', '3分', '4分', '5分'] },
    yAxis: { type: 'value', minInterval: 1 },
    series: [{
      type: 'bar',
      data: [1, 2, 3, 4, 5].map(score => satisfaction.distribution?.[String(score)] || 0),
      itemStyle: { color: '#d97706' }
    }]
  }

  const serviceSatisfactionOption = {
    tooltip: { trigger: 'axis', valueFormatter: value => `${Number(value).toFixed(1)}%` },
    grid: { left: 72, right: 20, top: 24, bottom: 38 },
    xAxis: { type: 'category', data: (satisfaction.by_service || []).map(item => item.feedback_type) },
    yAxis: { type: 'value', min: 0, max: 100 },
    series: [{
      type: 'bar',
      data: (satisfaction.by_service || []).map(item => item.satisfaction_rate),
      itemStyle: { color: '#7c3aed' }
    }]
  }

  return (
    <div className="dashboard analytics-dashboard">
      <div className="page-heading">
        <div><h2>运营数据看板</h2><p>数据来自游客交互、路线、行为和反馈记录</p></div>
        <div className="date-filter">
          <div><label>开始日期</label><input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
          <div><label>结束日期</label><input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
          <button onClick={loadAnalytics} disabled={loading}>{loading ? '加载中...' : '查询'}</button>
          <div><label>导出数据集</label><select value={exportDataset} onChange={(e) => setExportDataset(e.target.value)}>
            <option value="overview">概览指标</option>
            <option value="visitors">服务趋势</option>
            <option value="focus_points">游客关注点</option>
            <option value="hot_questions">热门问答</option>
            <option value="routes">热门路线</option>
            <option value="consumption">消费结构</option>
            <option value="satisfaction">满意度</option>
          </select></div>
          <button className="secondary-button" onClick={exportAnalytics} disabled={exporting}>{exporting ? '导出中...' : '导出 CSV'}</button>
        </div>
      </div>
      {error && <p className="error dashboard-error">{error}</p>}
      {comparison.comparison_period && (
        <p className="comparison-period">
          趋势对比基准：{comparison.comparison_period.start_date} 至 {comparison.comparison_period.end_date}
        </p>
      )}

      <div className="stats-grid analytics-stats">
        <div className="stat-card"><h3>服务人次</h3><p className="stat-value">{overview.visitor_count || 0}</p><MetricTrend comparison={comparison.changes?.visitor_count} /></div>
        <div className="stat-card"><h3>会话数</h3><p className="stat-value">{overview.session_count || 0}</p><MetricTrend comparison={comparison.changes?.session_count} /></div>
        <div className="stat-card"><h3>互动次数</h3><p className="stat-value">{overview.interaction_count || 0}</p><MetricTrend comparison={comparison.changes?.interaction_count} /></div>
        <div className="stat-card"><h3>路线生成</h3><p className="stat-value">{overview.route_count || 0}</p><MetricTrend comparison={comparison.changes?.route_count} /></div>
        <div className="stat-card"><h3>人均消费</h3><p className="stat-value">￥{Number(overview.average_spend || 0).toFixed(2)}</p><MetricTrend comparison={comparison.changes?.average_spend} suffix=" 元" /></div>
        <div className="stat-card"><h3>满意率</h3><p className="stat-value">{Number(overview.satisfaction_rate || 0).toFixed(1)}%</p><MetricTrend comparison={comparison.changes?.satisfaction_rate} suffix="%" /></div>
      </div>

      <section className="analytics-section">
        <h3>服务趋势</h3>
        <Chart option={visitorOption} />
      </section>

      <div className="charts-grid analytics-grid">
        <section className="analytics-section"><h3>游客关注点</h3><Chart option={focusOption} /></section>
        <section className="analytics-section">
          <h3>灵山胜境消费结构</h3>
          <Chart option={consumptionOption} />
          <table className="compact-table">
            <thead><tr><th>类别</th><th>总额</th><th>占比</th></tr></thead>
            <tbody>{(consumption.categories || []).map(item => <tr key={item.name}><td>{item.name}</td><td>￥{Number(item.total || 0).toFixed(2)}</td><td>{Number(item.share || 0).toFixed(1)}%</td></tr>)}</tbody>
          </table>
        </section>
        <section className="analytics-section"><h3>满意度分布</h3><Chart option={satisfactionOption} /></section>
        <section className="analytics-section"><h3>各服务满意率</h3><Chart option={serviceSatisfactionOption} /></section>
      </div>

      <section className="analytics-section">
        <h3>热门路线</h3>
        <table>
          <thead><tr><th>路线名称</th><th>完整路线</th><th>使用次数</th><th>平均游览时长</th><th>平均路线距离</th></tr></thead>
          <tbody>
            {(routes.popular_routes || []).map(item => (
              <tr key={item.route_path}>
                <td>{item.route_name}</td>
                <td>{item.route_path}</td>
                <td>{item.count}</td>
                <td>{item.average_duration ? `${Number(item.average_duration).toFixed(0)} 分钟` : '-'}</td>
                <td>{item.average_distance ? `${Number(item.average_distance).toFixed(0)} 米` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!routes.popular_routes?.length && <p className="empty-state">所选时间范围内暂无已保存路线。</p>}
      </section>

      <section className="analytics-section">
        <h3>热门问答</h3>
        <table>
          <thead><tr><th>问题</th><th>咨询次数</th></tr></thead>
          <tbody>
            {questions.map(item => <tr key={item.question}><td>{item.question}</td><td>{item.count}</td></tr>)}
          </tbody>
        </table>
        {!questions.length && <p className="empty-state">所选时间范围内暂无问答数据。</p>}
      </section>

      <section className="analytics-section insight-section">
        <h3>运营与营销建议</h3>
        {(overview.insights?.length || consumption.insights?.length) ? (
          <ol>{[...(overview.insights || []), ...(consumption.insights || [])].map((item, index) => <li key={`${index}-${item}`}>{item}</li>)}</ol>
        ) : <p className="empty-state">当前数据量不足，暂不生成营销建议。</p>}
      </section>
    </div>
  )
}

export default DashboardPage
