import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  name: '',
  ticket_type: 'scenic_ticket',
  audience: '成人',
  price: '',
  official_notice: '',
  is_active: true
}

const ticketTypeLabels = {
  scenic_ticket: '景区门票',
  sightseeing_bus: '观光车票',
  package: '套票',
  service: '服务票'
}

function TicketsPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadTickets()
  }, [])

  const loadTickets = async () => {
    try {
      const res = await request.get('/admin/tickets')
      setItems(res.data.items || [])
    } catch (error) {
      setMessage('票务信息加载失败')
    }
  }

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const buildPayload = () => ({
    name: form.name,
    ticket_type: form.ticket_type,
    audience: form.audience,
    price: Number(form.price || 0),
    official_notice: form.official_notice,
    is_active: form.is_active
  })

  const handleSubmit = async () => {
    if (!form.name.trim()) {
      setMessage('请填写票务名称')
      return
    }

    try {
      if (editingId) {
        await request.put(`/admin/tickets/${editingId}`, buildPayload())
      } else {
        await request.post('/admin/tickets', buildPayload())
      }
      setForm(emptyForm)
      setEditingId(null)
      setMessage(editingId ? '票务信息已更新' : '票务信息已添加')
      loadTickets()
    } catch (error) {
      setMessage('票务信息添加失败')
    }
  }

  const editItem = (item) => {
    setEditingId(item.id)
    setForm({ ...emptyForm, ...item, price: item.price ?? '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const toggleActive = async (item) => {
    try {
      await request.put(`/admin/tickets/${item.id}`, { is_active: !item.is_active })
      setMessage(item.is_active ? '票务信息已下线' : '票务信息已上线')
      loadTickets()
    } catch (error) {
      setMessage('状态更新失败')
    }
  }

  const handleDelete = async (id) => {
    try {
      await request.delete(`/admin/tickets/${id}`)
      setMessage('票务信息已删除')
      loadTickets()
    } catch (error) {
      setMessage('票务信息删除失败')
    }
  }

  return (
    <div className="tickets-page">
      <h2>票务信息管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑票务信息' : '新增票务信息'}</h3>
        <div className="toolbar ticket-form">
          <div>
            <label>票务名称</label>
            <input value={form.name} onChange={(e) => updateForm('name', e.target.value)} />
          </div>
          <div>
            <label>票务类型</label>
            <select value={form.ticket_type} onChange={(e) => updateForm('ticket_type', e.target.value)}>
              {Object.entries(ticketTypeLabels).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <div>
            <label>适用人群</label>
            <input value={form.audience} onChange={(e) => updateForm('audience', e.target.value)} />
          </div>
          <div>
            <label>价格</label>
            <input type="number" value={form.price} onChange={(e) => updateForm('price', e.target.value)} />
          </div>
        </div>

        <div className="form-group">
          <label>官方提示</label>
          <textarea rows={3} value={form.official_notice} onChange={(e) => updateForm('official_notice', e.target.value)} />
        </div>
        <div className="table-actions">
          <button onClick={handleSubmit}>{editingId ? '保存修改' : '添加票务信息'}</button>
          {editingId && <button className="secondary-button" onClick={() => { setEditingId(null); setForm(emptyForm) }}>取消编辑</button>}
        </div>
      </div>

      <div className="card">
        <h3>票务信息列表</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>类型</th>
              <th>价格</th>
              <th>官方提示</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td>{ticketTypeLabels[item.ticket_type] || item.ticket_type}</td>
                <td>{Number(item.price || 0) > 0 ? `￥${item.price}` : '以公告为准'}</td>
                <td>{item.official_notice || '-'}</td>
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

export default TicketsPage
