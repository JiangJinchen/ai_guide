import React, { useEffect, useState } from 'react'
import request from '../../api/request'

function KnowledgePage() {
  const [knowledgeItems, setKnowledgeItems] = useState([])
  const [newItem, setNewItem] = useState({ title: '', content: '', category: '' })
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadKnowledgeItems()
  }, [])

  const loadKnowledgeItems = async () => {
    try {
      const res = await request.get('/admin/knowledge')
      setKnowledgeItems(res.data.items || [])
    } catch (error) {
      setMessage('知识库加载失败')
    }
  }

  const handleAddItem = async () => {
    if (!newItem.title || !newItem.content) {
      setMessage('请填写标题和内容')
      return
    }

    try {
      await request.post('/admin/knowledge', newItem)
      setNewItem({ title: '', content: '', category: '' })
      setMessage('知识条目已添加')
      loadKnowledgeItems()
    } catch (error) {
      setMessage('知识条目添加失败')
    }
  }

  const handleDeleteItem = async (id) => {
    try {
      await request.delete(`/admin/knowledge/${id}`)
      setMessage('知识条目已删除')
      loadKnowledgeItems()
    } catch (error) {
      setMessage('知识条目删除失败')
    }
  }

  return (
    <div className="knowledge-page">
      <h2>知识库管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>添加知识库条目</h3>
        <div className="form-group">
          <label>标题</label>
          <input
            type="text"
            value={newItem.title}
            onChange={(e) => setNewItem({ ...newItem, title: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label>内容</label>
          <textarea
            value={newItem.content}
            onChange={(e) => setNewItem({ ...newItem, content: e.target.value })}
            rows={4}
          />
        </div>
        <div className="form-group">
          <label>分类</label>
          <input
            type="text"
            value={newItem.category}
            onChange={(e) => setNewItem({ ...newItem, category: e.target.value })}
          />
        </div>
        <button onClick={handleAddItem}>添加</button>
      </div>

      <div className="card">
        <h3>知识库条目列表</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>标题</th>
              <th>分类</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {knowledgeItems.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.title}</td>
                <td>{item.category}</td>
                <td>
                  <button onClick={() => handleDeleteItem(item.id)}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default KnowledgePage
