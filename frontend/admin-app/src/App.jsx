import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import KnowledgePage from './pages/knowledge/index.jsx'
import DigitalHumanPage from './pages/digital-human/index.jsx'
import ReportPage from './pages/report/index.jsx'
import DashboardPage from './pages/dashboard/index.jsx'
import PermissionPage from './pages/permission/index.jsx'
import LogsPage from './pages/logs/index.jsx'
import TicketsPage from './pages/tickets/index.jsx'
import ActivitiesPage from './pages/activities/index.jsx'

function App() {
  return (
    <Router>
      <div className="app">
        <header className="header">
          <h1>AI数字人智慧景区导览系统 - 管理端</h1>
          <div className="user-info">
            <span>管理员</span>
            <button>退出</button>
          </div>
        </header>
        <div className="layout">
          <aside className="sidebar">
            <ul>
              <li><Link to="/">数据大屏概览</Link></li>
              <li><Link to="/knowledge">知识库管理</Link></li>
              <li><Link to="/tickets">票务信息管理</Link></li>
              <li><Link to="/activities">活动信息管理</Link></li>
              <li><Link to="/digital-human">数字人形象管理</Link></li>
              <li><Link to="/report">游客感受度报告</Link></li>
              <li><Link to="/permission">权限管理</Link></li>
              <li><Link to="/logs">日志管理</Link></li>
            </ul>
          </aside>
          <main className="main-content">
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/knowledge" element={<KnowledgePage />} />
              <Route path="/tickets" element={<TicketsPage />} />
              <Route path="/activities" element={<ActivitiesPage />} />
              <Route path="/digital-human" element={<DigitalHumanPage />} />
              <Route path="/report" element={<ReportPage />} />
              <Route path="/permission" element={<PermissionPage />} />
              <Route path="/logs" element={<LogsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
