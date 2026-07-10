import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  name: '',
  activity_type: 'performance',
  location: '',
  latitude: '',
  longitude: '',
  description: '',
  detail: '',
  schedule_times: '',
  schedule_note: '以景区当日公告为准',
  duration_minutes: '',
  status: 'available',
  navigation_tips: '',
  notice: '',
  source_name: '灵山胜境官方小程序',
  source_type: 'manual',
  sort_order: 100,
  is_active: true
}

const typeLabels = {
  intro: '活动介绍',
  performance: '演出时间',
  zen: '禅修体验'
}

const sourceLabels = {
  official: '景区官方渠道',
  ota: '第三方票务平台',
  manual: '管理端人工维护'
}

function ActivitiesPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
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
    ...form,
    latitude: form.latitude ? Number(form.latitude) : null,
    longitude: form.longitude ? Number(form.longitude) : null,
    duration_minutes: form.duration_minutes ? Number(form.duration_minutes) : null,
    sort_order: Number(form.sort_order || 100)
  })

  const handleAdd = async () => {
    if (!form.name || !form.source_name) {
      setMessage('请填写活动名称和信息来源')
      return
    }

    try {
      await request.post('/admin/activities', buildPayload())
      setForm(emptyForm)
      setMessage('活动信息已添加')
      loadActivities()
    } catch (error) {
      setMessage(error.response?.data?.detail || '活动信息添加失败')
    }
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
        <h3>新增活动信息</h3>
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
          <div>
            <label>来源类型</label>
            <select value={form.source_type} onChange={(e) => updateForm('source_type', e.target.value)}>
              {Object.entries(sourceLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label>来源名称</label>
            <input value={form.source_name} onChange={(e) => updateForm('source_name', e.target.value)} />
          </div>
          <div>
            <label>排序</label>
            <input type="number" value={form.sort_order} onChange={(e) => updateForm('sort_order', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label>时间说明</label>
          <input value={form.schedule_note} onChange={(e) => updateForm('schedule_note', e.target.value)} />
        </div>
        <div className="form-group">
          <label>简要介绍</label>
          <textarea rows={3} value={form.description} onChange={(e) => updateForm('description', e.target.value)} />
        </div>
        <div className="form-group">
          <label>活动详情</label>
          <textarea rows={4} value={form.detail} onChange={(e) => updateForm('detail', e.target.value)} />
        </div>
        <div className="form-group">
          <label>导航提示</label>
          <textarea rows={2} value={form.navigation_tips} onChange={(e) => updateForm('navigation_tips', e.target.value)} />
        </div>
        <div className="form-group">
          <label>注意事项</label>
          <textarea rows={2} value={form.notice} onChange={(e) => updateForm('notice', e.target.value)} />
        </div>
        <button onClick={handleAdd}>添加活动信息</button>
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
              <th>来源</th>
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
                <td>{sourceLabels[item.source_type] || item.source_name}</td>
                <td>{item.is_active ? '已上线' : '已下线'}</td>
                <td className="table-actions">
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
