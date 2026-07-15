import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = {
  question: '',
  answer: '',
  category: '',
  sort_order: 100,
  is_active: true,
  source_name: '景区客服'
}

function FaqPage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadFaqs()
  }, [])

  const loadFaqs = async (search = keyword) => {
    setLoading(true)
    try {
      const res = await request.get('/admin/faqs', { params: { keyword: search || undefined } })
      setItems(res.data.items || [])
      setMessage('')
    } catch (error) {
      setMessage(error.response?.data?.detail || 'FAQ 加载失败')
    } finally {
      setLoading(false)
    }
  }

  const updateForm = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  const submit = async () => {
    if (!form.question.trim() || !form.answer.trim()) {
      setMessage('请填写问题和答案')
      return
    }
    const payload = { ...form, sort_order: Number(form.sort_order || 100) }
    try {
      if (editingId) {
        await request.put(`/admin/faqs/${editingId}`, payload)
        setMessage('FAQ 已更新')
      } else {
        await request.post('/admin/faqs', payload)
        setMessage('FAQ 已添加')
      }
      setForm(emptyForm)
      setEditingId(null)
      await loadFaqs()
    } catch (error) {
      setMessage(error.response?.data?.detail || 'FAQ 保存失败')
    }
  }

  const edit = (item) => {
    setEditingId(item.id)
    setForm({
      question: item.question || '',
      answer: item.answer || '',
      category: item.category || '',
      sort_order: item.sort_order || 100,
      is_active: item.is_active !== false,
      source_name: item.source_name || ''
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const toggle = async (item) => {
    try {
      await request.put(`/admin/faqs/${item.id}/status`, null, { params: { is_active: !item.is_active } })
      setMessage(item.is_active ? 'FAQ 已停用' : 'FAQ 已启用')
      loadFaqs()
    } catch (error) {
      setMessage(error.response?.data?.detail || 'FAQ 状态更新失败')
    }
  }

  const remove = async (id) => {
    if (!window.confirm('确认删除这条 FAQ 吗？')) return
    try {
      await request.delete(`/admin/faqs/${id}`)
      setMessage('FAQ 已删除')
      loadFaqs()
    } catch (error) {
      setMessage(error.response?.data?.detail || 'FAQ 删除失败')
    }
  }

  return (
    <div className="content-page">
      <h2>客服 FAQ 管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑 FAQ' : '新增 FAQ'}</h3>
        <div className="form-group">
          <label>问题</label>
          <input value={form.question} onChange={(e) => updateForm('question', e.target.value)} />
        </div>
        <div className="form-group">
          <label>答案</label>
          <textarea rows={5} value={form.answer} onChange={(e) => updateForm('answer', e.target.value)} />
        </div>
        <div className="toolbar">
          <div>
            <label>分类</label>
            <input value={form.category} onChange={(e) => updateForm('category', e.target.value)} />
          </div>
          <div>
            <label>来源</label>
            <input value={form.source_name} onChange={(e) => updateForm('source_name', e.target.value)} />
          </div>
          <div>
            <label>排序</label>
            <input type="number" value={form.sort_order} onChange={(e) => updateForm('sort_order', e.target.value)} />
          </div>
          <label className="inline-field">
            <input type="checkbox" checked={form.is_active} onChange={(e) => updateForm('is_active', e.target.checked)} />
            启用
          </label>
        </div>
        <div className="table-actions">
          <button onClick={submit}>{editingId ? '保存修改' : '添加 FAQ'}</button>
          {editingId && <button className="secondary-button" onClick={() => { setEditingId(null); setForm(emptyForm) }}>取消编辑</button>}
        </div>
      </div>

      <div className="card">
        <div className="toolbar">
          <div>
            <label>搜索问题或答案</label>
            <input value={keyword} onChange={(e) => setKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadFaqs()} />
          </div>
          <button onClick={() => loadFaqs()} disabled={loading}>{loading ? '加载中...' : '查询'}</button>
        </div>
        <table>
          <thead>
            <tr><th>ID</th><th>问题</th><th>分类</th><th>排序</th><th>状态</th><th>操作</th></tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.question}</td>
                <td>{item.category || '-'}</td>
                <td>{item.sort_order}</td>
                <td>{item.is_active ? '已启用' : '已停用'}</td>
                <td className="table-actions">
                  <button onClick={() => edit(item)}>编辑</button>
                  <button onClick={() => toggle(item)}>{item.is_active ? '停用' : '启用'}</button>
                  <button onClick={() => remove(item.id)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !items.length && <p className="empty-state">暂无 FAQ，请先添加或运行 seed_faq.py。</p>}
      </div>
    </div>
  )
}

export default FaqPage
