export const DEFAULT_SCENIC_LOCATION = {
  latitude: 31.43039,
  longitude: 120.09658,
  name: '灵山胜境游客中心'
}

const LOCATION_STORAGE_KEY = 'lastKnownLocation'

export const isValidLocation = (location) => {
  const latitude = Number(location?.latitude)
  const longitude = Number(location?.longitude)
  return latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
}

export const normalizeLocation = (source = {}) => {
  const latitude = Number(source.latitude)
  const longitude = Number(source.longitude)
  if (!isValidLocation({ latitude, longitude })) return null

  return {
    latitude,
    longitude,
    accuracy: Number(source.accuracy || 0),
    provider: source.provider || 'gcj02',
    timestamp: source.timestamp || Date.now(),
    isCached: Boolean(source.isCached),
    isFallback: Boolean(source.isFallback),
    name: source.name || ''
  }
}

export const saveLocation = (location) => {
  const normalized = normalizeLocation(location)
  if (!normalized) return null
  uni.setStorageSync(LOCATION_STORAGE_KEY, normalized)
  return normalized
}

export const getCachedLocation = () => {
  return normalizeLocation({ ...uni.getStorageSync(LOCATION_STORAGE_KEY), isCached: true })
}

export const getLocationErrorMessage = (error) => {
  const message = String(error?.errMsg || error?.message || '')
  if (/auth|authorize|permission|denied|拒绝|权限/.test(message)) {
    return '定位权限未开启，请在系统设置中允许访问位置'
  }
  if (/timeout|超时/.test(message)) {
    return '定位超时，请走到开阔处后重试'
  }
  return '暂时无法获取定位，可稍后刷新'
}

export const requestCurrentLocation = (options = {}) => {
  const {
    allowCache = true,
    allowFallback = false,
    highAccuracy = true
  } = options

  return new Promise((resolve, reject) => {
    uni.getLocation({
      type: 'gcj02',
      isHighAccuracy: highAccuracy,
      success: (res) => {
        const location = saveLocation({
          latitude: res.latitude,
          longitude: res.longitude,
          accuracy: res.accuracy,
          provider: 'gcj02'
        })
        if (location) {
          resolve(location)
        } else {
          reject(new Error('定位结果无效'))
        }
      },
      fail: (error) => {
        const cached = allowCache ? getCachedLocation() : null
        if (cached) {
          resolve(cached)
          return
        }
        if (allowFallback) {
          resolve(normalizeLocation({ ...DEFAULT_SCENIC_LOCATION, isFallback: true, provider: 'gcj02' }))
          return
        }
        reject(error)
      }
    })
  })
}

export const formatLocationText = (location) => {
  const normalized = normalizeLocation(location)
  if (!normalized) return ''
  const prefix = normalized.isFallback ? '默认起点' : normalized.isCached ? '上次位置' : '当前位置'
  return `${prefix} ${normalized.latitude.toFixed(5)}, ${normalized.longitude.toFixed(5)}`
}
