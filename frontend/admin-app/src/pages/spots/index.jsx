import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  scenic_area_name: '灵山胜境',
  spot_name: '',
  location: '',
  latitude: '',
  longitude: '',
  architecture_params: '',
  core_function: '',
  culture_connotation: '',
  description: '',
  highlights: '',
  open_info: '',
  remark: ''
}

function SpotsPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadSpots()
  }, [])

  const loadSpots = async (search = keyword) => {
    setLoading(true)
    try {
      const res = await request.get('/admin/spots', { params: { keyword: search || undefined } })
      setItems(res.data.items || [])
      setMessage('')
    } catch (error) {
      setMessage(error.response?.data?.detail || '景点加载失败')
    } finally {
      setLoading(false)
    }
  }

  const updateForm = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const buildPayload = () => ({
    ...form,
    latitude: form.latitude === '' ? null : Number(form.latitude),
    longitude: form.longitude === '' ? null : Number(form.longitude)
  })

  const submit = async () => {
    if (!form.scenic_area_name.trim() || !form.spot_name.trim()) {
      setMessage('请填写景区名称和景点名称')
      return
    }
    try {
      if (editingId) {
        await request.put(`/admin/spots/${editingId}`, buildPayload())
        setMessage('景点已更新')
      } else {
        await request.post('/admin/spots', buildPayload())
        setMessage('景点已添加')
      }
      setForm(emptyForm)
      setEditingId(null)
      loadSpots()
    } catch (error) {
      setMessage(error.response?.data?.detail || '景点保存失败')
    }
  }

  const edit = (item) => {
    setEditingId(item.id)
    setForm({ ...emptyForm, ...item, latitude: item.latitude ?? '', longitude: item.longitude ?? '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const remove = async (id) => {
    if (!window.confirm('确认删除这个景点吗？删除后讲解和路线关联可能受到影响。')) return
    try {
      await request.delete(`/admin/spots/${id}`)
      setMessage('景点已删除')
      loadSpots()
    } catch (error) {
      setMessage(error.response?.data?.detail || '景点删除失败')
    }
  }

  return (
    <div className="content-page">
      <h2>景点内容管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑景点' : '新增景点'}</h3>
        <div className="toolbar">
          <div><label>景区名称</label><input value={form.scenic_area_name} onChange={(e) => updateForm('scenic_area_name', e.target.value)} /></div>
          <div><label>景点名称</label><input value={form.spot_name} onChange={(e) => updateForm('spot_name', e.target.value)} /></div>
          <div><label>位置</label><input value={form.location} onChange={(e) => updateForm('location', e.target.value)} /></div>
          <div><label>纬度</label><input type="number" value={form.latitude} onChange={(e) => updateForm('latitude', e.target.value)} /></div>
          <div><label>经度</label><input type="number" value={form.longitude} onChange={(e) => updateForm('longitude', e.target.value)} /></div>
          <div><label>开放信息</label><input value={form.open_info} onChange={(e) => updateForm('open_info', e.target.value)} /></div>
        </div>
        <div className="form-group"><label>核心功能</label><textarea rows={2} value={form.core_function} onChange={(e) => updateForm('core_function', e.target.value)} /></div>
        <div className="form-group"><label>文化内涵</label><textarea rows={3} value={form.culture_connotation} onChange={(e) => updateForm('culture_connotation', e.target.value)} /></div>
        <div className="form-group"><label>景点介绍</label><textarea rows={4} value={form.description} onChange={(e) => updateForm('description', e.target.value)} /></div>
        <div className="form-group"><label>亮点</label><textarea rows={2} value={form.highlights} onChange={(e) => updateForm('highlights', e.target.value)} /></div>
        <div className="form-group"><label>建筑参数</label><textarea rows={2} value={form.architecture_params} onChange={(e) => updateForm('architecture_params', e.target.value)} /></div>
        <div className="form-group"><label>备注</label><textarea rows={2} value={form.remark} onChange={(e) => updateForm('remark', e.target.value)} /></div>
        <div className="table-actions">
          <button onClick={submit}>{editingId ? '保存修改' : '添加景点'}</button>
          {editingId && <button className="secondary-button" onClick={() => { setEditingId(null); setForm(emptyForm) }}>取消编辑</button>}
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div><label>搜索景点</label><input value={keyword} onChange={(e) => setKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadSpots()} /></div>
          <button onClick={() => loadSpots()} disabled={loading}>{loading ? '加载中...' : '查询'}</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>景点</th><th>位置</th><th>开放信息</th><th>操作</th></tr></thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.spot_name}</td>
                <td>{item.location || '-'}</td>
                <td>{item.open_info || '-'}</td>
                <td className="table-actions"><button onClick={() => edit(item)}>编辑</button><button onClick={() => remove(item.id)}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !items.length && <p className="empty-state">暂无景点数据。</p>}
      </div>
    </div>
  )
}

export default SpotsPage
