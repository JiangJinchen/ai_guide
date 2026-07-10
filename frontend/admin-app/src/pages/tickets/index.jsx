import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  name: '',
  ticket_type: 'scenic_ticket',
  audience: '成人',
  price: '',
  original_price: '',
  valid_period: '',
  sales_status: 'available',
  purchase_url: '',
  source_name: '',
  source_type: 'manual',
  official_notice: '',
  use_policy: '',
  refund_policy: '',
  sort_order: 100,
  is_active: true
}

const ticketTypeLabels = {
  scenic_ticket: '景区门票',
  sightseeing_bus: '观光车票',
  package: '套票',
  service: '服务票'
}

const sourceLabels = {
  official: '景区官方渠道',
  ota: '第三方票务平台',
  manual: '管理端人工维护'
}

function TicketsPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
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
    ...form,
    price: Number(form.price || 0),
    original_price: form.original_price ? Number(form.original_price) : null,
    sort_order: Number(form.sort_order || 100)
  })

  const handleAdd = async () => {
    if (!form.name || !form.source_name) {
      setMessage('请填写票务名称和信息来源')
      return
    }

    try {
      await request.post('/admin/tickets', buildPayload())
      setForm(emptyForm)
      setMessage('票务信息已添加')
      loadTickets()
    } catch (error) {
      setMessage('票务信息添加失败')
    }
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
        <h3>新增票务信息</h3>
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
          <div>
            <label>原价</label>
            <input type="number" value={form.original_price} onChange={(e) => updateForm('original_price', e.target.value)} />
          </div>
          <div>
            <label>销售状态</label>
            <select value={form.sales_status} onChange={(e) => updateForm('sales_status', e.target.value)}>
              <option value="available">可咨询</option>
              <option value="info_only">信息参考</option>
              <option value="onsite_confirm">现场确认</option>
              <option value="sold_out">暂不可售</option>
            </select>
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
          <label>购票链接</label>
          <input value={form.purchase_url} onChange={(e) => updateForm('purchase_url', e.target.value)} />
        </div>
        <div className="form-group">
          <label>有效期说明</label>
          <input value={form.valid_period} onChange={(e) => updateForm('valid_period', e.target.value)} />
        </div>
        <div className="form-group">
          <label>官方提示</label>
          <textarea rows={3} value={form.official_notice} onChange={(e) => updateForm('official_notice', e.target.value)} />
        </div>
        <div className="form-group">
          <label>使用规则</label>
          <textarea rows={3} value={form.use_policy} onChange={(e) => updateForm('use_policy', e.target.value)} />
        </div>
        <div className="form-group">
          <label>退改规则</label>
          <textarea rows={3} value={form.refund_policy} onChange={(e) => updateForm('refund_policy', e.target.value)} />
        </div>
        <button onClick={handleAdd}>添加票务信息</button>
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
                <td>{ticketTypeLabels[item.ticket_type] || item.ticket_type}</td>
                <td>{Number(item.price || 0) > 0 ? `￥${item.price}` : '以公告为准'}</td>
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

export default TicketsPage
