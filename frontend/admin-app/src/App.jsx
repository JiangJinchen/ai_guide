import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from 'react-router-dom'
import KnowledgePage from './pages/knowledge/index.jsx'
import DigitalHumanPage from './pages/digital-human/index.jsx'
import ReportPage from './pages/report/index.jsx'
import DashboardPage from './pages/dashboard/index.jsx'
import PermissionPage from './pages/permission/index.jsx'
import LogsPage from './pages/logs/index.jsx'
import TicketsPage from './pages/tickets/index.jsx'
import ActivitiesPage from './pages/activities/index.jsx'
import SpotsPage from './pages/spots/index.jsx'
import FaqPage from './pages/faqs/index.jsx'
import LoginPage from './pages/login/index.jsx'
import request, { clearAdminSession, hasAdminSession } from './api/request'

function App() {
  const [user, setUser] = useState(null)
  const [checkingSession, setCheckingSession] = useState(true)

  useEffect(() => {
    const handleExpired = () => {
      setUser(null)
      setCheckingSession(false)
    }
    window.addEventListener('admin-auth-expired', handleExpired)

    const restoreSession = async () => {
      if (!hasAdminSession()) {
        setCheckingSession(false)
        return
      }
      try {
        const response = await request.get('/admin/auth/me')
        setUser(response.data.user)
      } catch (error) {
        clearAdminSession()
      } finally {
        setCheckingSession(false)
      }
    }
    restoreSession()
    return () => window.removeEventListener('admin-auth-expired', handleExpired)
  }, [])

  const logout = async () => {
    try {
      await request.post('/admin/auth/logout', {})
    } finally {
      clearAdminSession()
      setUser(null)
    }
  }

  if (checkingSession) {
    return <main className="login-page"><p className="session-loading">正在验证管理员会话...</p></main>
  }

  if (!user) return <LoginPage onLogin={setUser} />

  const permissions = user.permissions || (user.role === 'admin' ? ['*'] : [])
  const can = (permission) => permissions.includes('*') || permissions.includes(permission)
  const defaultPath = can('analytics.read') ? '/'
    : can('content.read') ? '/knowledge'
      : can('digital_human.read') ? '/digital-human'
        : '/permission'

  return (
    <Router>
      <div className="app">
        <header className="header">
          <h1>AI数字人智慧景区导览系统 - 管理端</h1>
          <div className="user-info">
            <span>{user.display_name || user.username}</span>
            <button onClick={logout}>退出</button>
          </div>
        </header>
        <div className="layout">
          <aside className="sidebar">
            <ul>
              {can('analytics.read') && <li><Link to="/">数据大屏概览</Link></li>}
              {can('content.read') && <li><Link to="/knowledge">知识库管理</Link></li>}
              {can('content.read') && <li><Link to="/spots">景点内容管理</Link></li>}
              {can('content.read') && <li><Link to="/faqs">客服 FAQ 管理</Link></li>}
              {can('content.read') && <li><Link to="/tickets">票务信息管理</Link></li>}
              {can('content.read') && <li><Link to="/activities">活动信息管理</Link></li>}
              {can('digital_human.read') && <li><Link to="/digital-human">数字人形象管理</Link></li>}
              {can('analytics.read') && <li><Link to="/report">游客感受度报告</Link></li>}
              {can('system.manage') && <li><Link to="/permission">权限管理</Link></li>}
              {can('system.logs') && <li><Link to="/logs">日志管理</Link></li>}
            </ul>
          </aside>
          <main className="main-content">
            <Routes>
              {can('analytics.read') && <Route path="/" element={<DashboardPage />} />}
              {can('content.read') && <Route path="/knowledge" element={<KnowledgePage />} />}
              {can('content.read') && <Route path="/spots" element={<SpotsPage />} />}
              {can('content.read') && <Route path="/faqs" element={<FaqPage />} />}
              {can('content.read') && <Route path="/tickets" element={<TicketsPage />} />}
              {can('content.read') && <Route path="/activities" element={<ActivitiesPage />} />}
              {can('digital_human.read') && <Route path="/digital-human" element={<DigitalHumanPage />} />}
              {can('analytics.read') && <Route path="/report" element={<ReportPage />} />}
              {can('system.manage') && <Route path="/permission" element={<PermissionPage user={user} />} />}
              {can('system.logs') && <Route path="/logs" element={<LogsPage />} />}
              <Route path="*" element={<Navigate to={defaultPath} replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}

export default App
