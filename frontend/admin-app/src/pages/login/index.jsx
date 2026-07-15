import React, { useState } from 'react'
import request, { saveAdminSession } from '../../api/request'


function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    if (!username.trim() || !password) {
      setError('请输入用户名和密码')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await request.post('/admin/auth/login', { username: username.trim(), password })
      saveAdminSession(response.data)
      onLogin(response.data.user)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || '登录失败，请检查账号和服务状态')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-page">
      <form className="login-panel" onSubmit={submit}>
        <div className="login-heading">
          <span className="login-mark">LS</span>
          <div>
            <h1>灵山智慧导览管理端</h1>
            <p>管理员登录</p>
          </div>
        </div>
        {error && <p className="error login-error">{error}</p>}
        <label htmlFor="admin-username">用户名</label>
        <input id="admin-username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} autoFocus />
        <label htmlFor="admin-password">密码</label>
        <input id="admin-password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <button type="submit" disabled={loading}>{loading ? '登录中...' : '登录'}</button>
      </form>
    </main>
  )
}

export default LoginPage
