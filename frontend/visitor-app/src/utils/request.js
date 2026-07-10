const BASE_URL = '/api'

const normalizeUrl = (url) => {
  if (url.startsWith('/visitor/') || url.startsWith('/admin/') || url.startsWith('/ai/')) {
    return url
  }
  return `/visitor${url.startsWith('/') ? url : `/${url}`}`
}

const request = (options) => {
  return new Promise((resolve, reject) => {
    const userId = uni.getStorageSync('userId') || 'guest'
    const fullUrl = BASE_URL + normalizeUrl(options.url)
    
    uni.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
        ...options.header
      },
      timeout: options.timeout || 60000,
      success: (res) => {
        if (res.statusCode === 200) {
          resolve(res.data)
        } else {
          uni.showToast({ title: '请求失败', icon: 'none' })
          reject(res)
        }
      },
      fail: () => {
        uni.showToast({ title: '网络请求失败', icon: 'none' })
        reject()
      }
    })
  })
}

export const get = (url, data = {}) => request({ url, method: 'GET', data })
export const post = (url, data = {}) => request({ url, method: 'POST', data })
export const put = (url, data = {}) => request({ url, method: 'PUT', data })
export const del = (url, data = {}) => request({ url, method: 'DELETE', data })

export default request
