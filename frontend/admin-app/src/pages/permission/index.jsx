import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = { username: '', password: '', display_name: '', role: 'content_operator' }
const emptyRoleForm = { role_key: '', label: '', permissions: [] }

function PermissionPage({ user }) {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState({})
  const [roleItems, setRoleItems] = useState([])
  const [permissionOptions, setPermissionOptions] = useState({})
  const [roleForm, setRoleForm] = useState(emptyRoleForm)
  const [editingRoleId, setEditingRoleId] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [passwordTarget, setPasswordTarget] = useState(null)
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => { loadUsers() }, [])

  const loadUsers = async () => {
    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        request.get('/admin/auth/users'),
        request.get('/admin/auth/roles')
      ])
      setUsers(usersResponse.data.items || [])
      setRoles(usersResponse.data.roles || {})
      setRoleItems(rolesResponse.data.items || [])
      setPermissionOptions(rolesResponse.data.permission_options || {})
    } catch (error) {
      setMessage(error.response?.data?.detail || '管理员账号加载失败')
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setForm(emptyForm)
  }

  const submit = async () => {
    if (!form.username.trim() || !form.display_name.trim() || (!editingId && !form.password)) {
      setMessage('请完整填写用户名、显示名称和初始密码')
      return
    }
    try {
      if (editingId) {
        await request.put(`/admin/auth/users/${editingId}`, {
          display_name: form.display_name,
          role: form.role
        })
        setMessage('管理员账号已更新')
      } else {
        await request.post('/admin/auth/users', form)
        setMessage('管理员账号已创建')
      }
      resetForm()
      loadUsers()
    } catch (error) {
      setMessage(error.response?.data?.detail || '管理员账号保存失败')
    }
  }

  const editUser = (item) => {
    setEditingId(item.id)
    setForm({ username: item.username, password: '', display_name: item.display_name, role: item.role })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const toggleUser = async (item) => {
    try {
      await request.put(`/admin/auth/users/${item.id}`, { is_active: !item.is_active })
      setMessage(item.is_active ? '管理员账号已停用' : '管理员账号已启用')
      loadUsers()
    } catch (error) {
      setMessage(error.response?.data?.detail || '管理员状态更新失败')
    }
  }

  const resetPassword = async () => {
    if (!passwordTarget || newPassword.length < 10) {
      setMessage('新密码至少需要 10 个字符')
      return
    }
    try {
      await request.put(`/admin/auth/users/${passwordTarget.id}/password`, { password: newPassword })
      setMessage('密码已重置，该账号现有会话已撤销')
      setPasswordTarget(null)
      setNewPassword('')
    } catch (error) {
      setMessage(error.response?.data?.detail || '密码重置失败')
    }
  }

  const resetRoleForm = () => {
    setEditingRoleId(null)
    setRoleForm(emptyRoleForm)
  }

  const togglePermission = (permission) => {
    setRoleForm((current) => ({
      ...current,
      permissions: current.permissions.includes(permission)
        ? current.permissions.filter(item => item !== permission)
        : [...current.permissions, permission]
    }))
  }

  const submitRole = async () => {
    if (!roleForm.role_key.trim() || !roleForm.label.trim()) {
      setMessage('请填写角色标识和角色名称')
      return
    }
    try {
      if (editingRoleId) {
        const payload = { label: roleForm.label }
        if (roleForm.role_key !== 'admin') payload.permissions = roleForm.permissions
        await request.put(`/admin/auth/roles/${editingRoleId}`, payload)
        setMessage('角色策略已更新')
      } else {
        await request.post('/admin/auth/roles', roleForm)
        setMessage('自定义角色已创建')
      }
      resetRoleForm()
      loadUsers()
    } catch (error) {
      setMessage(error.response?.data?.detail || '角色保存失败')
    }
  }

  const editRole = (role) => {
    setEditingRoleId(role.id)
    setRoleForm({ role_key: role.role_key, label: role.label, permissions: role.permissions || [] })
  }

  const deleteRole = async (role) => {
    if (!window.confirm(`确认删除角色“${role.label}”吗？`)) return
    try {
      await request.delete(`/admin/auth/roles/${role.id}`)
      setMessage('角色已删除')
      loadUsers()
    } catch (error) {
      setMessage(error.response?.data?.detail || '角色删除失败')
    }
  }

  return (
    <div>
      <h2>权限管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑管理员' : '新增管理员'}</h3>
        <div className="toolbar ticket-form">
          <div><label>用户名</label><input value={form.username} disabled={Boolean(editingId)} onChange={(event) => setForm({ ...form, username: event.target.value })} /></div>
          <div><label>显示名称</label><input value={form.display_name} onChange={(event) => setForm({ ...form, display_name: event.target.value })} /></div>
          {!editingId && <div><label>初始密码</label><input type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></div>}
          <div>
            <label>角色</label>
            <select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value })}>
              {Object.entries(roles).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </div>
        </div>
        <div className="table-actions">
          <button onClick={submit}>{editingId ? '保存修改' : '创建账号'}</button>
          {editingId && <button className="secondary-button" onClick={resetForm}>取消编辑</button>}
        </div>
      </div>

      {passwordTarget && (
        <div className="card">
          <h3>重置密码：{passwordTarget.username}</h3>
          <label>新密码</label>
          <input type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          <div className="table-actions">
            <button onClick={resetPassword}>确认重置</button>
            <button className="secondary-button" onClick={() => { setPasswordTarget(null); setNewPassword('') }}>取消</button>
          </div>
        </div>
      )}

      <div className="card">
        <h3>{editingRoleId ? '编辑角色策略' : '新增自定义角色'}</h3>
        <div className="toolbar ticket-form">
          <div><label>角色标识</label><input value={roleForm.role_key} disabled={Boolean(editingRoleId)} placeholder="例如：service_operator" onChange={(event) => setRoleForm({ ...roleForm, role_key: event.target.value })} /></div>
          <div><label>角色名称</label><input value={roleForm.label} onChange={(event) => setRoleForm({ ...roleForm, label: event.target.value })} /></div>
        </div>
        <div className="role-permission-grid">
          {Object.entries(permissionOptions).map(([permission, label]) => (
            <label className="inline-field" key={permission}>
              <input
                type="checkbox"
                checked={roleForm.permissions.includes(permission) || roleForm.permissions.includes('*')}
                disabled={roleForm.role_key === 'admin'}
                onChange={() => togglePermission(permission)}
              />
              {label}
            </label>
          ))}
        </div>
        <div className="table-actions">
          <button onClick={submitRole}>{editingRoleId ? '保存角色' : '创建角色'}</button>
          {editingRoleId && <button className="secondary-button" onClick={resetRoleForm}>取消编辑</button>}
        </div>
      </div>

      <div className="card">
        <h3>角色策略</h3>
        <table>
          <thead><tr><th>角色标识</th><th>名称</th><th>权限</th><th>类型</th><th>操作</th></tr></thead>
          <tbody>
            {roleItems.map(role => (
              <tr key={role.id}>
                <td>{role.role_key}</td>
                <td>{role.label}</td>
                <td>{role.permissions.includes('*') ? '全部权限' : role.permissions.map(item => permissionOptions[item] || item).join('、') || '无权限'}</td>
                <td>{role.is_system ? '系统角色' : '自定义角色'}</td>
                <td className="table-actions">
                  <button onClick={() => editRole(role)}>编辑</button>
                  {!role.is_system && <button onClick={() => deleteRole(role)}>删除</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>管理员账号</h3>
        <table>
          <thead><tr><th>用户名</th><th>显示名称</th><th>角色</th><th>状态</th><th>最近登录</th><th>操作</th></tr></thead>
          <tbody>
            {users.map(item => (
              <tr key={item.id}>
                <td>{item.username}{item.id === user.id ? '（当前）' : ''}</td>
                <td>{item.display_name}</td>
                <td>{item.role_label || roles[item.role] || item.role}</td>
                <td>{item.is_active ? '启用' : '停用'}</td>
                <td>{item.last_login_at ? new Date(item.last_login_at).toLocaleString() : '尚未登录'}</td>
                <td className="table-actions">
                  <button onClick={() => editUser(item)}>编辑</button>
                  <button className="secondary-button" onClick={() => setPasswordTarget(item)}>重置密码</button>
                  <button onClick={() => toggleUser(item)} disabled={item.id === user.id}>{item.is_active ? '停用' : '启用'}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default PermissionPage
