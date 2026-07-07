import React, { useEffect, useState } from 'react'
import * as echarts from 'echarts'

function DashboardPage() {
  const [visitorCount, setVisitorCount] = useState(0)
  const [interactionCount, setInteractionCount] = useState(0)
  const [satisfactionRate, setSatisfactionRate] = useState(85)

  useEffect(() => {
    const visitorChart = echarts.init(document.getElementById('visitorChart'))
    visitorChart.setOption({
      title: { text: '游客数量趋势' },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: ['1月', '2月', '3月', '4月', '5月', '6月'] },
      yAxis: { type: 'value' },
      series: [{ data: [1200, 1900, 3000, 2500, 3600, 4200], type: 'line' }]
    })

    const hotspotsChart = echarts.init(document.getElementById('hotspotsChart'))
    hotspotsChart.setOption({
      title: { text: '景点热度分布' },
      tooltip: { trigger: 'item' },
      series: [{
        name: '热度',
        type: 'pie',
        radius: '50%',
        data: [
          { value: 35, name: '景点A' },
          { value: 25, name: '景点B' },
          { value: 20, name: '景点C' },
          { value: 15, name: '景点D' },
          { value: 5, name: '其他' }
        ]
      }]
    })

    const resizeCharts = () => {
      visitorChart.resize()
      hotspotsChart.resize()
    }
    window.addEventListener('resize', resizeCharts)

    const interval = setInterval(() => {
      setVisitorCount(prev => prev + Math.floor(Math.random() * 10))
      setInteractionCount(prev => prev + Math.floor(Math.random() * 5))
      setSatisfactionRate(prev => Math.max(0, Math.min(100, prev + (Math.random() - 0.5) * 2)))
    }, 5000)

    return () => {
      clearInterval(interval)
      window.removeEventListener('resize', resizeCharts)
      visitorChart.dispose()
      hotspotsChart.dispose()
    }
  }, [])

  return (
    <div className="dashboard">
      <h2>数据大屏概览</h2>
      <div className="stats-grid">
        <div className="stat-card">
          <h3>今日游客数</h3>
          <p className="stat-value">{visitorCount}</p>
        </div>
        <div className="stat-card">
          <h3>互动次数</h3>
          <p className="stat-value">{interactionCount}</p>
        </div>
        <div className="stat-card">
          <h3>满意度</h3>
          <p className="stat-value">{satisfactionRate.toFixed(1)}%</p>
        </div>
      </div>
      <div className="charts-grid">
        <div className="chart-card">
          <div id="visitorChart" style={{ width: '100%', height: '400px' }} />
        </div>
        <div className="chart-card">
          <div id="hotspotsChart" style={{ width: '100%', height: '400px' }} />
        </div>
      </div>
    </div>
  )
}

export default DashboardPage
