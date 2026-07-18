const BASE_URL = '/api'

const normalizeUrl = (url) => {
  if (url.startsWith('/visitor/') || url.startsWith('/admin/') || url.startsWith('/ai/')) {
    return url
  }
  return `/visitor${url.startsWith('/') ? url : `/${url}`}`
}

const formatToastMessage = (detail, fallback = '璇锋眰澶辫触') => {
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (!item || typeof item !== 'object') return ''
        const loc = Array.isArray(item.loc) ? item.loc.join('.') : ''
        const msg = item.msg || item.message || ''
        return loc && msg ? `${loc}: ${msg}` : (msg || loc)
      })
      .filter(Boolean)
    if (messages.length) {
      return messages.join('; ')
    }
    return JSON.stringify(detail)
  }
  if (detail && typeof detail === 'object') {
    if (typeof detail.detail === 'string') return detail.detail
    if (Array.isArray(detail.detail)) return formatToastMessage(detail.detail, fallback)
    if (typeof detail.msg === 'string') return detail.msg
    if (typeof detail.message === 'string') return detail.message
    try {
      return JSON.stringify(detail)
    } catch (error) {
      return fallback
    }
  }
  return fallback
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

const request = (options) => {
  return new Promise((resolve, reject) => {
    const rawUserId = uni.getStorageSync('userId')
    const userId = rawUserId === null || rawUserId === undefined || rawUserId === '' ? 'guest' : String(rawUserId)
    const accessToken = uni.getStorageSync('access_token')
    const fullUrl = BASE_URL + normalizeUrl(options.url)
    
    const headers = {
      'Content-Type': 'application/json',
      'X-User-Id': userId,
      ...options.header
    }
    
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`
    }
    
    uni.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: normalizePayload(options.data || {}),
      header: headers,
      timeout: options.timeout || 60000,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else if (res.statusCode === 401) {
          uni.removeStorageSync('access_token')
          uni.removeStorageSync('refresh_token')
          uni.removeStorageSync('user_info')
          uni.showToast({ title: 'Login expired, please log in again', icon: 'none' })
          setTimeout(() => {
            uni.redirectTo({ url: '/pages/login/index' })
          }, 1500)
          reject(res)
        } else {
          console.error('[request] non-200 response', {
            url: fullUrl,
            statusCode: res.statusCode,
            data: res.data
          })
          const message = formatToastMessage(res.data?.detail, '璇锋眰澶辫触')
          uni.showToast({ title: message, icon: 'none' })
          reject(res)
        }
      },
      fail: (error) => {
        console.error('[request] request failed', {
          url: fullUrl,
          error
        })
        const isTimeout = typeof error?.errMsg === 'string' && error.errMsg.includes('timeout')
        uni.showToast({ title: isTimeout ? '请求超时，请稍后重试' : 'Network request failed', icon: 'none' })
        reject(error || new Error('Network request failed'))
      }
    })
  })
}

export const get = (url, data = {}) => request({ url, method: 'GET', data })
export const post = (url, data = {}, options = {}) => request({ url, method: 'POST', data, ...options })
export const put = (url, data = {}, options = {}) => request({ url, method: 'PUT', data, ...options })
export const del = (url, data = {}, options = {}) => request({ url, method: 'DELETE', data, ...options })

export default request
