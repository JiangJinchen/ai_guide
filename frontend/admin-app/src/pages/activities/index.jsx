import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  name: '',
  activity_type: 'performance',
  location: '',
  latitude: '',
  longitude: '',
  schedule_times: '',
  duration_minutes: '',
  content: '',
  significance: '',
  is_active: true
}

const typeLabels = {
  intro: '活动介绍',
  performance: '演出时间',
  zen: '禅修体验'
}

function ActivitiesPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadActivities()
  }, [])

  const loadActivities = async () => {
    try {
      const res = await request.get('/admin/activities')
      setItems(res.data.items || [])
    } catch (error) {
      setMessage('活动信息加载失败')
    }
  }

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const buildPayload = () => ({
    name: form.name,
    activity_type: form.activity_type,
    location: form.location,
    latitude: form.latitude ? Number(form.latitude) : null,
    longitude: form.longitude ? Number(form.longitude) : null,
    schedule_times: form.schedule_times,
    duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : null,
    content: form.content,
    significance: form.significance,
    is_active: form.is_active
  })

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.location.trim()) {
      setMessage('请填写活动名称和地点')
      return
    }

    try {
      if (editingId) {
        await request.put(`/admin/activities/${editingId}`, buildPayload())
      } else {
        await request.post('/admin/activities', buildPayload())
      }
      setForm(emptyForm)
      setEditingId(null)
      setMessage(editingId ? '活动信息已更新' : '活动信息已添加')
      loadActivities()
    } catch (error) {
      setMessage(error.response?.data?.detail || '活动信息添加失败')
    }
  }

  const editItem = (item) => {
    let scheduleTimes = item.schedule_times || ''
    try {
      const parsed = JSON.parse(scheduleTimes)
      if (Array.isArray(parsed)) scheduleTimes = parsed.join(', ')
    } catch (error) {
      // Keep legacy plain-text schedules editable.
    }
    setEditingId(item.id)
    setForm({ ...emptyForm, ...item, schedule_times: scheduleTimes, latitude: item.latitude ?? '', longitude: item.longitude ?? '', duration_minutes: item.duration_minutes ?? '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const toggleActive = async (item) => {
    try {
      await request.put(`/admin/activities/${item.id}`, { is_active: !item.is_active })
      setMessage(item.is_active ? '活动信息已下线' : '活动信息已上线')
      loadActivities()
    } catch (error) {
      setMessage('状态更新失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await request.delete(`/admin/activities/${id}`)
      setMessage('活动信息已删除')
      loadActivities()
    } catch (error) {
      setMessage('活动信息删除失败')
    }
  }

  const formatTimes = (value) => {
    if (!value) return '无固定时间'
    try {
      const list = JSON.parse(value)
      return Array.isArray(list) && list.length ? list.join('、') : '无固定时间'
    } catch (error) {
      return value
    }
  }

  return (
    <div className="activities-page">
      <h2>活动信息管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑活动信息' : '新增活动信息'}</h3>
        <div className="toolbar ticket-form">
          <div>
            <label>活动名称</label>
            <input value={form.name} onChange={(e) => updateForm('name', e.target.value)} />
          </div>
          <div>
            <label>活动类型</label>
            <select value={form.activity_type} onChange={(e) => updateForm('activity_type', e.target.value)}>
              {Object.entries(typeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label>地点</label>
            <input value={form.location} onChange={(e) => updateForm('location', e.target.value)} />
          </div>
          <div>
            <label>纬度</label>
            <input type="number" value={form.latitude} onChange={(e) => updateForm('latitude', e.target.value)} />
          </div>
          <div>
            <label>经度</label>
            <input type="number" value={form.longitude} onChange={(e) => updateForm('longitude', e.target.value)} />
          </div>
          <div>
            <label>演出时间</label>
            <input placeholder="09:30, 14:00" value={form.schedule_times} onChange={(e) => updateForm('schedule_times', e.target.value)} />
          </div>
          <div>
            <label>时长</label>
            <input type="number" value={form.duration_minutes} onChange={(e) => updateForm('duration_minutes', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label>活动内容</label>
          <textarea rows={4} value={form.content} onChange={(e) => updateForm('content', e.target.value)} />
        </div>
        <div className="form-group">
          <label>活动意义</label>
          <textarea rows={3} value={form.significance} onChange={(e) => updateForm('significance', e.target.value)} />
        </div>
        <div className="table-actions">
          <button onClick={handleSubmit}>{editingId ? '保存修改' : '添加活动信息'}</button>
          {editingId && <button className="secondary-button" onClick={() => { setEditingId(null); setForm(emptyForm) }}>取消编辑</button>}
        </div>
      </div>

      <div className="card">
        <h3>活动信息列表</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>类型</th>
              <th>地点</th>
              <th>时间</th>
              <th>活动内容</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td>{typeLabels[item.activity_type] || item.activity_type}</td>
                <td>{item.location || '-'}</td>
                <td>{formatTimes(item.schedule_times)}</td>
                <td>{item.content || '-'}</td>
                <td>{item.is_active ? '已上线' : '已下线'}</td>
                <td className="table-actions">
                  <button onClick={() => editItem(item)}>编辑</button>
                  <button onClick={() => toggleActive(item)}>{item.is_active ? '下线' : '上线'}</button>
                  <button onClick={() => handleDelete(item.id)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ActivitiesPage
