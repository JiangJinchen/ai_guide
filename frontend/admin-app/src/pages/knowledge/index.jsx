import React, { useEffect, useState } from 'react'
import request from '../../api/request'

const emptyForm = { title: '', content: '', category: '' }

function KnowledgePage() {
  const [items, setItems] = useState([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)
  const [keyword, setKeyword] = useState('')
  const [category, setCategory] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [reindexing, setReindexing] = useState(false)
  const [reindexStatus, setReindexStatus] = useState(null)
  const [reindexPollVersion, setReindexPollVersion] = useState(0)

  useEffect(() => {
    loadItems()
    let timer
    let active = true
    const poll = async () => {
      try {
        const res = await request.get('/admin/rag/reindex/status')
        if (!active) return
        setReindexStatus(res.data)
        if (res.data.running) timer = window.setTimeout(poll, 2000)
      } catch (error) {
        if (active) setReindexStatus({ status: 'unavailable', error: '无法获取 RAG 任务状态' })
      }
    }
    poll()
    return () => {
      active = false
      if (timer) window.clearTimeout(timer)
    }
  }, [reindexPollVersion])

  const loadItems = async () => {
    setLoading(true)
    try {
      const res = await request.get('/admin/knowledge', {
        params: { keyword: keyword || undefined, category: category || undefined }
      })
      setItems(res.data.items || [])
      setMessage('')
    } catch (error) {
      setMessage(error.response?.data?.detail || '知识库加载失败')
    } finally {
      setLoading(false)
    }
  }

  const submit = async () => {
    if (!form.title.trim() || !form.content.trim()) {
      setMessage('请填写标题和内容')
      return
    }
    try {
      if (editingId) {
        await request.put(`/admin/knowledge/${editingId}`, form)
        setMessage('知识条目已更新，检索缓存已清理')
      } else {
        await request.post('/admin/knowledge', form)
        setMessage('知识条目已添加，检索缓存已清理')
      }
      setForm(emptyForm)
      setEditingId(null)
      loadItems()
    } catch (error) {
      setMessage(error.response?.data?.detail || '知识条目保存失败')
    }
  }

  const edit = (item) => {
    setEditingId(item.id)
    setForm({ title: item.title || '', content: item.content || '', category: item.category || '' })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const remove = async (id) => {
    if (!window.confirm('确认删除这条知识内容吗？')) return
    try {
      await request.delete(`/admin/knowledge/${id}`)
      setMessage('知识条目已删除，检索缓存已清理')
      loadItems()
    } catch (error) {
      setMessage(error.response?.data?.detail || '知识条目删除失败')
    }
  }

  const reindex = async () => {
    setReindexing(true)
    try {
      await request.post('/admin/rag/reindex', {
        sync_chunks: true,
        sync_embeddings: false,
        build_faiss: false
      })
      const res = await request.get('/admin/rag/reindex/status')
      setReindexStatus(res.data)
      setReindexPollVersion((version) => version + 1)
      setMessage('RAG 内容重建任务已提交')
    } catch (error) {
      setMessage(error.response?.data?.detail || 'RAG 重建任务提交失败')
    } finally {
      setReindexing(false)
    }
  }

  return (
    <div className="knowledge-page">
      <h2>景区知识库管理</h2>
      {message && <p className="success">{message}</p>}
      <div className="card">
        <h3>{editingId ? '编辑知识内容' : '新增知识内容'}</h3>
        <div className="form-group"><label>标题</label><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
        <div className="form-group"><label>分类</label><input value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="例如：开放信息、文化历史、服务设施" /></div>
        <div className="form-group"><label>内容</label><textarea value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} rows={8} /></div>
        <div className="table-actions">
          <button onClick={submit}>{editingId ? '保存修改' : '添加知识'}</button>
          {editingId && <button className="secondary-button" onClick={() => { setEditingId(null); setForm(emptyForm) }}>取消编辑</button>}
        </div>
      </div>
      {reindexStatus && (
        <div className="card rag-status-card">
          <div className="page-heading">
            <div>
              <h3>RAG 重建状态</h3>
              <p>任务状态：{({ idle: '未运行', queued: '排队中', running: '执行中', completed: '已完成', failed: '失败', unavailable: '不可用' })[reindexStatus.status] || reindexStatus.status}</p>
            </div>
            <div className="table-actions">
              {reindexStatus.running && <span className="status-badge">正在处理</span>}
              {reindexStatus.status === 'failed' && <button onClick={reindex} disabled={reindexing}>重新提交</button>}
            </div>
          </div>
          {reindexStatus.error && <p className="error">{reindexStatus.error}</p>}
          {Object.keys(reindexStatus.steps || {}).length > 0 && (
            <table className="compact-table">
              <thead><tr><th>步骤</th><th>结果</th></tr></thead>
              <tbody>
                {Object.entries(reindexStatus.steps).map(([name, result]) => (
                  <tr key={name}><td>{({ sync_chunks: '同步文本分块', sync_embeddings: '同步向量', build_faiss: '构建 FAISS 索引' })[name] || name}</td><td><code>{JSON.stringify(result)}</code></td></tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
      <div className="card">
        <div className="toolbar">
          <div><label>关键词</label><input value={keyword} onChange={(e) => setKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadItems()} /></div>
          <div><label>分类</label><input value={category} onChange={(e) => setCategory(e.target.value)} /></div>
          <button onClick={loadItems} disabled={loading}>{loading ? '加载中...' : '查询'}</button>
          <button onClick={reindex} disabled={reindexing || reindexStatus?.running}>{reindexing || reindexStatus?.running ? '处理中...' : '重建 RAG 内容索引'}</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>标题</th><th>分类</th><th>更新时间</th><th>操作</th></tr></thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td><td>{item.title}</td><td>{item.category || '-'}</td>
                <td>{item.updated_at ? new Date(item.updated_at).toLocaleString() : '-'}</td>
                <td className="table-actions"><button onClick={() => edit(item)}>编辑</button><button onClick={() => remove(item.id)}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !items.length && <p className="empty-state">暂无知识内容。</p>}
      </div>
    </div>
  )
}

export default KnowledgePage
