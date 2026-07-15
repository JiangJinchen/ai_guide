import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
const ACCESS_TOKEN_KEY = 'admin_access_token'
const REFRESH_TOKEN_KEY = 'admin_refresh_token'

const request = axios.create({
  baseURL,
  timeout: 15000,
  withCredentials: true
})

let refreshPromise = null

export const saveAdminSession = (data) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export const clearAdminSession = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY) || ''
export const hasAdminSession = () => Boolean(localStorage.getItem(ACCESS_TOKEN_KEY) || getRefreshToken())

const getCookie = (name) => {
  const prefix = `${name}=`
  const item = document.cookie.split('; ').find(value => value.startsWith(prefix))
  return item ? decodeURIComponent(item.slice(prefix.length)) : ''
}

const notifyAuthExpired = () => {
  clearAdminSession()
  window.dispatchEvent(new Event('admin-auth-expired'))
}

const refreshAdminSession = async () => {
  const response = await axios.post(`${baseURL}/admin/auth/refresh`, {}, {
    withCredentials: true,
    headers: { 'X-CSRF-Token': getCookie('admin_csrf_token') }
  })
  saveAdminSession(response.data)
  return response.data.access_token
}

request.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  const csrfToken = getCookie('admin_csrf_token')
  if (csrfToken) config.headers['X-CSRF-Token'] = csrfToken
  return config
})

request.interceptors.response.use(
  response => response,
  async (error) => {
    const original = error.config || {}
    const url = original.url || ''
    const skipRefresh = url.includes('/admin/auth/login') || url.includes('/admin/auth/refresh')
    if (error.response?.status !== 401 || original._retry || skipRefresh) {
      return Promise.reject(error)
    }

    original._retry = true
    try {
      if (!refreshPromise) refreshPromise = refreshAdminSession().finally(() => { refreshPromise = null })
      const accessToken = await refreshPromise
      original.headers = original.headers || {}
      original.headers.Authorization = `Bearer ${accessToken}`
      return request(original)
    } catch (refreshError) {
      notifyAuthExpired()
      return Promise.reject(refreshError)
    }
  }
)

export default request
