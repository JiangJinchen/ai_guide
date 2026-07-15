import React, { useEffect, useRef, useState } from 'react'
import request from '../../api/request'

const DEFAULT_MODEL_PATH = '/static/live2d/epsilon_ja/epsilon_free/runtime/Epsilon_free.model3.json'
const defaultVisitorPreviewUrl = () => {
  if (typeof window === 'undefined') return 'http://localhost:8080/#/pages/digital-human-preview/index'
  return `${window.location.protocol}//${window.location.hostname}:8080/#/pages/digital-human-preview/index`
}
const VISITOR_PREVIEW_URL = import.meta.env.VITE_VISITOR_PREVIEW_URL || defaultVisitorPreviewUrl()

function DigitalHumanPage() {
  const [configs, setConfigs] = useState([])
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({
    name: '',
    model: '',
    voice: 'female',
    clothes: '',
    is_active: false
  })
  const [message, setMessage] = useState('')
  const [previewConfig, setPreviewConfig] = useState({ name: '', model: DEFAULT_MODEL_PATH, clothes: '' })
  const previewAudioRef = useRef(null)
  const previewUrl = `${VISITOR_PREVIEW_URL}?${new URLSearchParams({
    name: previewConfig.name || '灵山数字导游',
    model: previewConfig.model || DEFAULT_MODEL_PATH,
    clothes: previewConfig.clothes || '默认服装'
  }).toString()}`

  useEffect(() => {
    loadConfigs()
    return () => {
      if (previewAudioRef.current) previewAudioRef.current.pause()
      if (window.speechSynthesis) window.speechSynthesis.cancel()
    }
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
    if (!form.name.trim()) {
      setMessage('请填写数字人名称')
      return
    }

    try {
      if (editingId) {
        await request.put(`/admin/digital-human/${editingId}`, form)
        setMessage(form.is_active ? '数字人配置已更新并发布' : '数字人配置已更新')
      } else {
        await request.post('/admin/digital-human', form)
        setMessage(form.is_active ? '数字人配置已创建并发布' : '数字人配置已保存为未发布配置')
      }
      resetForm()
      loadConfigs()
    } catch (error) {
      setMessage(error.response?.data?.detail || '数字人配置保存失败')
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setForm({ name: '', model: '', voice: 'female', clothes: '', is_active: false })
  }

  const editConfig = (config) => {
    setEditingId(config.id)
    setForm({
      name: config.name || '',
      model: config.model || '',
      voice: config.voice === 'male' ? 'male' : 'female',
      clothes: config.clothes || '',
      is_active: config.is_active === true
    })
    setPreviewConfig({
      name: config.name || '',
      model: config.model || DEFAULT_MODEL_PATH,
      clothes: config.clothes || ''
    })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const refreshVisualPreview = () => {
    setPreviewConfig({
      name: form.name,
      model: form.model || DEFAULT_MODEL_PATH,
      clothes: form.clothes
    })
    setMessage('Live2D 预览已刷新')
  }

  const publishConfig = async (config) => {
    try {
      await request.put(`/admin/digital-human/${config.id}/activate`)
      setMessage('数字人配置已发布；选择历史配置时即完成回滚')
      loadConfigs()
    } catch (error) {
      setMessage(error.response?.data?.detail || '数字人配置发布失败')
    }
  }

  const previewVoice = async () => {
    const text = `您好，我是${form.name || '灵山数字导游'}，欢迎来到灵山胜境。`
    try {
      const res = await request.post('/ai/tts', {
        text,
        voice: form.voice,
        reply_id: 'admin-preview'
      })
      if (res.data.audio_data) {
        if (previewAudioRef.current) previewAudioRef.current.pause()
        previewAudioRef.current = new Audio(res.data.audio_data)
        await previewAudioRef.current.play()
        setMessage('正在播放音色试听')
        return
      }
    } catch (error) {
      // Fall through to browser speech synthesis when the TTS service is unavailable.
    }

    if (!window.speechSynthesis) {
      setMessage('当前浏览器不支持音色试听')
      return
    }
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.pitch = form.voice === 'male' ? 0.85 : 1
    window.speechSynthesis.speak(utterance)
    setMessage('TTS 服务不可用，已使用浏览器音色试听')
  }

  const deleteConfig = async (config) => {
    if (!window.confirm(`确认删除数字人配置“${config.name}”吗？`)) return
    try {
      await request.delete(`/admin/digital-human/${config.id}`)
      setMessage('数字人配置已删除')
      loadConfigs()
    } catch (error) {
      setMessage(error.response?.data?.detail || '数字人配置删除失败')
    }
  }

  return (
    <div>
      <h2>数字人形象管理</h2>
      {message && <p className="success">{message}</p>}

      <div className="card">
        <h3>{editingId ? '编辑配置' : '新增配置'}</h3>
        <label>名称</label>
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        <label>模型资源路径</label>
        <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} placeholder="例如：/static/live2d/.../model3.json" />
        <label>音色</label>
        <select value={form.voice} onChange={(e) => setForm({ ...form, voice: e.target.value })}>
          <option value="female">女声</option>
          <option value="male">男声</option>
        </select>
        <label>服装</label>
        <input value={form.clothes} onChange={(e) => setForm({ ...form, clothes: e.target.value })} />
        <label className="inline-field">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          保存后发布为当前配置
        </label>
        <div className="table-actions">
          <button onClick={createConfig}>{editingId ? '保存修改' : '保存配置'}</button>
          <button className="secondary-button" onClick={refreshVisualPreview}>刷新画面</button>
          <button className="secondary-button" onClick={previewVoice}>试听音色</button>
          {editingId && <button className="secondary-button" onClick={resetForm}>取消编辑</button>}
        </div>
      </div>

      <div className="card digital-human-preview">
        <div className="preview-heading">
          <div><h3>Live2D 画面预览</h3><p>使用游客端相同渲染组件，不影响当前已发布配置</p></div>
          <a className="preview-link" href={previewUrl} target="_blank" rel="noreferrer">新窗口预览</a>
        </div>
        <iframe className="live2d-preview-frame" title="Live2D 数字人画面预览" src={previewUrl} allow="autoplay" />
        <p className="preview-note">模型资源：{previewConfig.model || DEFAULT_MODEL_PATH}</p>
      </div>

      <div className="card">
        <h3>配置列表</h3>
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>名称</th>
              <th>模型</th>
              <th>音色</th>
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
                <td>{config.model || '默认模型'}</td>
                <td>{config.voice === 'male' ? '男声' : '女声'}</td>
                <td>{config.clothes || '-'}</td>
                <td>{config.is_active ? '当前生效' : '未发布'}</td>
                <td className="table-actions">
                  <button onClick={() => editConfig(config)}>编辑</button>
                  {!config.is_active && <button className="secondary-button" onClick={() => publishConfig(config)}>发布/回滚</button>}
                  <button onClick={() => deleteConfig(config)} disabled={config.is_active}>删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!configs.length && <p className="empty-state">暂无数字人配置。</p>}
      </div>
    </div>
  )
}

export default DigitalHumanPage
