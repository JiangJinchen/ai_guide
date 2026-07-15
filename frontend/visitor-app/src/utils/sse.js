const BASE_URL = '/api'

const normalizeUrl = (url) => {
  if (url.startsWith('/visitor/') || url.startsWith('/admin/') || url.startsWith('/ai/')) {
    return url
  }
  return `/visitor${url.startsWith('/') ? url : `/${url}`}`
}

export class SSEClient {
  constructor(url, options = {}) {
    this.url = BASE_URL + normalizeUrl(url)
    this.options = options
    this.xhr = null
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

  async send(data) {
    return new Promise((resolve, reject) => {
      this.xhr = new XMLHttpRequest()
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
            this.emit('error', new Error(`HTTP ${this.xhr.status}`))
            reject(new Error(`HTTP ${this.xhr.status}`))
          }
        }
      }
      
      this.xhr.onerror = () => {
        this.emit('error', new Error('Network error'))
        reject(new Error('Network error'))
      }
      
      this.xhr.ontimeout = () => {
        this.emit('error', new Error('Timeout'))
        reject(new Error('Timeout'))
      }
      
      this.xhr.timeout = this.options.timeout || 120000
      this.xhr.send(JSON.stringify(data))
    })
  }

  _processData() {
    if (!this.xhr || this.closed) return
    
    try {
      const responseText = this.xhr.responseText
      this.eventBuffer += responseText.substring(this.responseOffset)
      this.responseOffset = responseText.length

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
    this.emit('close', { status: 'aborted' })
  }
}

export const streamChat = async (data, onMessage, onError, onClose) => {
  const client = new SSEClient('/chat/stream')
  
  if (onMessage) client.on('message', onMessage)
  if (onError) client.on('error', onError)
  if (onClose) client.on('close', onClose)
  
  try {
    await client.send(data)
  } catch (error) {}
  
  return client
}

export const streamInference = async (data, onMessage, onError, onClose) => {
  const client = new SSEClient('/ai/stream-inference')
  
  if (onMessage) client.on('message', onMessage)
  if (onError) client.on('error', onError)
  if (onClose) client.on('close', onClose)
  
  try {
    await client.send(data)
  } catch (error) {}
  
  return client
}

export default SSEClient
