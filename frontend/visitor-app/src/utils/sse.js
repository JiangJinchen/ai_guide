const BASE_URL = 'http://192.168.208.6:8000/api' //鎵嬫満鐑偣
//const BASE_URL = 'http://10.27.246.115:8000/api' //鏍″洯缃?
const normalizeUrl = (url) => {
  if (url.startsWith('/visitor/') || url.startsWith('/admin/') || url.startsWith('/ai/')) {
    return url
  }
  return `/visitor${url.startsWith('/') ? url : `/${url}`}`
}

const normalizePayload = (payload) => {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return payload
  }
  const normalized = { ...payload }
  if (normalized.user_id !== undefined && normalized.user_id !== null) {
    normalized.user_id = String(normalized.user_id)
  }
  if (normalized.session_id !== undefined && normalized.session_id !== null) {
    normalized.session_id = String(normalized.session_id)
  }
  return normalized
}

export class SSEClient {
  constructor(url, options = {}) {
    this.url = BASE_URL + normalizeUrl(url)
    this.options = options
    this.xhr = null
    this.requestTask = null
    this.closed = false
    this.listeners = {
      message: [],
      error: [],
      close: []
    }
    this.responseOffset = 0
    this.eventBuffer = ''
    this.userId = uni.getStorageSync('userId') || 'guest'
  }

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback)
    }
    return this
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data))
    }
  }

  getXHRConstructor() {
    if (typeof XMLHttpRequest === 'function') return XMLHttpRequest
    if (typeof plus !== 'undefined' && plus.net && typeof plus.net.XMLHttpRequest === 'function') {
      return plus.net.XMLHttpRequest
    }
    return null
  }

  async send(data) {
    const payload = normalizePayload(data)
    const XHR = this.getXHRConstructor()
    if (!XHR) {
      return this._sendWithUniRequest(payload)
    }

    return new Promise((resolve, reject) => {
      try {
        this.xhr = new XHR()
      } catch (error) {
        console.warn('[sse] xhr constructor failed, fallback to uni.request', error)
        this._sendWithUniRequest(payload).then(resolve).catch(reject)
        return
      }
      console.log('[sse] xhr request', { url: this.url, plus_xhr: typeof XMLHttpRequest !== 'function' })
      this.xhr.open('POST', this.url, true)
      this.xhr.setRequestHeader('Content-Type', 'application/json')
      this.xhr.setRequestHeader('X-User-Id', this.userId)
      this.xhr.setRequestHeader('Accept', 'text/event-stream')

      this.xhr.onreadystatechange = () => {
        if (this.xhr.readyState === 3) {
          this._processData()
        } else if (this.xhr.readyState === 4) {
          if (this.xhr.status === 200) {
            this._processData()
            this.emit('close', { status: this.xhr.status })
            resolve()
          } else {
            console.error('[sse] http error', {
              url: this.url,
              status: this.xhr.status,
              readyState: this.xhr.readyState,
              responseText: this.xhr.responseText?.slice(0, 500),
              headers: this.xhr.getAllResponseHeaders?.()
            })
            const error = new Error(`HTTP ${this.xhr.status}`)
            this.emit('error', error)
            reject(error)
          }
        }
      }

      this.xhr.onerror = () => {
        console.error('[sse] network error', {
          url: this.url,
          status: this.xhr.status,
          readyState: this.xhr.readyState,
          responseText: this.xhr.responseText?.slice(0, 500)
        })
        const error = new Error('Network error')
        this.emit('error', error)
        reject(error)
      }

      this.xhr.ontimeout = () => {
        console.error('[sse] timeout', {
          url: this.url,
          status: this.xhr.status,
          readyState: this.xhr.readyState,
          timeout: this.xhr.timeout
        })
        const error = new Error('Timeout')
        this.emit('error', error)
        reject(error)
      }

      this.xhr.timeout = this.options.timeout || 120000
      this.xhr.send(JSON.stringify(payload))
    })
  }

  _sendWithUniRequest(payload) {
    return new Promise((resolve, reject) => {
      const headers = {
        'Content-Type': 'application/json',
        'X-User-Id': this.userId,
        'Accept': 'text/event-stream'
      }
      console.log('[sse] app fallback request', { url: this.url })
      this.requestTask = uni.request({
        url: this.url,
        method: 'POST',
        data: payload,
        header: headers,
        timeout: this.options.timeout || 120000,
        responseType: 'text',
        success: (res) => {
          if (this.closed) {
            resolve()
            return
          }
          const statusCode = res.statusCode || 0
          const responseText = typeof res.data === 'string' ? res.data : JSON.stringify(res.data || '')
          if (statusCode === 200) {
            console.log('[sse] app fallback response', { url: this.url, length: responseText.length })
            this._processText(responseText)
            this.emit('close', { status: statusCode })
            resolve()
            return
          }
          console.error('[sse] app fallback http error', {
            url: this.url,
            statusCode,
            data: responseText.slice(0, 500)
          })
          const error = new Error(`HTTP ${statusCode}`)
          this.emit('error', error)
          reject(error)
        },
        fail: (error) => {
          if (this.closed) {
            resolve()
            return
          }
          console.error('[sse] app fallback request failed', { url: this.url, error })
          const nextError = error instanceof Error ? error : new Error(error && error.errMsg ? error.errMsg : 'Network error')
          this.emit('error', nextError)
          reject(nextError)
        }
      })
    })
  }

  _processData() {
    if (!this.xhr || this.closed) return
    this._processText(this.xhr.responseText)
  }

  _processText(responseText = '') {
    if (this.closed) return
    try {
      const text = String(responseText || '')
      this.eventBuffer += text.substring(this.responseOffset)
      this.responseOffset = text.length

      let delimiter = this.eventBuffer.match(/\r?\n\r?\n/)
      while (delimiter) {
        const rawEvent = this.eventBuffer.substring(0, delimiter.index)
        this.eventBuffer = this.eventBuffer.substring(delimiter.index + delimiter[0].length)
        this._processEvent(rawEvent)
        delimiter = this.eventBuffer.match(/\r?\n\r?\n/)
      }
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }

  _processEvent(rawEvent) {
    let eventName = 'message'
    const dataLines = []

    rawEvent.split(/\r?\n/).forEach((line) => {
      if (line.startsWith('event:')) {
        eventName = line.substring(6).trim()
      } else if (line.startsWith('data:')) {
        const value = line.substring(5)
        dataLines.push(value.startsWith(' ') ? value.substring(1) : value)
      }
    })

    if (eventName !== 'message' || dataLines.length === 0) return

    const eventData = dataLines.join('\n')
    try {
      this.emit('message', JSON.parse(eventData))
    } catch (error) {
      console.error('Invalid SSE message:', eventData, error)
    }
  }

  close() {
    this.closed = true
    if (this.xhr) {
      this.xhr.abort()
      this.xhr = null
    }
    if (this.requestTask && typeof this.requestTask.abort === 'function') {
      this.requestTask.abort()
      this.requestTask = null
    }
    this.emit('close', { status: 'aborted' })
  }
}

export const streamChat = async (data, onMessage, onError, onClose) => {
  const client = new SSEClient('/chat/stream')

  if (onMessage) client.on('message', onMessage)
  if (onError) client.on('error', onError)
  if (onClose) client.on('close', onClose)

  await client.send(data)
  return client
}

export const streamInference = async (data, onMessage, onError, onClose) => {
  const client = new SSEClient('/ai/stream-inference')

  if (onMessage) client.on('message', onMessage)
  if (onError) client.on('error', onError)
  if (onClose) client.on('close', onClose)

  await client.send(data)
  return client
}

export default SSEClient
