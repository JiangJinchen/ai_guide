import React, { useEffect, useState } from 'react'
import request from '../../api/request'

function DigitalHumanPage() {
  const [configs, setConfigs] = useState([])
  const [form, setForm] = useState({
    name: '',
    model: '',
    voice: '',
    clothes: '',
    is_active: true
  })
  const [message, setMessage] = useState('')

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      const res = await request.get('/admin/digital-human')
      setConfigs(res.data.configs || [])
    } catch (error) {
      setMessage('数字人配置加载失败')
    }
  }

  const createConfig = async () => {
    if (!form.name) {
      setMessage('请填写数字人名称')
      return
    }

    try {
      await request.post('/admin/digital-human', form)
      setForm({ name: '', model: '', voice: '', clothes: '', is_active: true })
      setMessage('数字人配置已创建')
      loadConfigs()
    } catch (error) {
      setMessage('数字人配置创建失败')
    }
  }

  const deleteConfig = async (id) => {
    try {
      await request.delete(`/admin/digital-human/${id}`)
      setMessage('数字人配置已删除')
      loadConfigs()
    } catch (error) {
      setMessage('数字人配置删除失败')
    }
  }

  return (
    <div>
      <h2>数字人形象管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>新增配置</h3>
        <label>名称</label>
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <label>模型</label>
        <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} />
        <label>声音</label>
        <input value={form.voice} onChange={(e) => setForm({ ...form, voice: e.target.value })} />
        <label>服装</label>
        <input value={form.clothes} onChange={(e) => setForm({ ...form, clothes: e.target.value })} />
        <label className="inline-field">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          启用
        </label>
        <button onClick={createConfig}>保存配置</button>
      </div>

      <div className="card">
        <h3>配置列表</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>模型</th>
              <th>声音</th>
              <th>服装</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {configs.map(config => (
              <tr key={config.id}>
                <td>{config.id}</td>
                <td>{config.name}</td>
                <td>{config.model}</td>
                <td>{config.voice}</td>
                <td>{config.clothes}</td>
                <td>{config.is_active ? '启用' : '停用'}</td>
                <td><button onClick={() => deleteConfig(config.id)}>删除</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default DigitalHumanPage
