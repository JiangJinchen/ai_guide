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
  if (/translate|coordinate|system|转换|坐标系/.test(message)) {
    return '坐标转换失败，请检查网络或稍后重试'
  }
  return '暂时无法获取定位，可稍后刷新'
}

export const requestCurrentLocation = (options = {}) => {
  const {
    allowCache = true,
    allowFallback = false,
    highAccuracy = true
  } = options

  console.log('[Location] 开始请求定位', { allowCache, allowFallback, highAccuracy })

  const isH5 = process.env.UNI_PLATFORM === 'h5'
  const locationType = isH5 ? 'wgs84' : 'gcj02'
  console.log('[Location] 当前平台:', process.env.UNI_PLATFORM, '定位类型:', locationType)

  return new Promise((resolve, reject) => {
    uni.getLocation({
      type: locationType,
      isHighAccuracy: highAccuracy,
      success: (res) => {
        console.log('[Location] ✅ 定位成功', {
          latitude: res.latitude,
          longitude: res.longitude,
          accuracy: res.accuracy,
          errMsg: res.errMsg,
          type: locationType
        })
        const location = saveLocation({
          latitude: res.latitude,
          longitude: res.longitude,
          accuracy: res.accuracy,
          provider: locationType
        })
        if (location) {
          console.log('[Location] ✅ 返回真实位置', location)
          resolve(location)
        } else {
          console.log('[Location] ❌ 定位结果无效')
          reject(new Error('定位结果无效'))
        }
      },
      fail: (error) => {
        const errMsg = error?.errMsg || error?.message || JSON.stringify(error)
        console.log('[Location] ❌ 定位失败', {
          errMsg,
          errorCode: error?.code
        })
        
        if (/auth|authorize|permission|denied|拒绝|权限/.test(errMsg)) {
          console.log('[Location] 原因：用户未授权定位权限')
        } else if (/timeout|超时/.test(errMsg)) {
          console.log('[Location] 原因：定位超时，可能GPS信号弱或网络问题')
        } else if (/not|available|不支持/.test(errMsg)) {
          console.log('[Location] 原因：当前环境不支持定位API')
        } else if (/translate|coordinate|system|转换|坐标系/.test(errMsg)) {
          console.log('[Location] 原因：坐标转换失败，通常是因为缺少高德地图key或网络问题')
        } else {
          console.log('[Location] 原因：其他未知错误')
        }

        if (allowCache) {
          const cached = getCachedLocation()
          if (cached) {
            console.log('[Location] ⚠️ 降级使用缓存位置', cached)
            resolve(cached)
            return
          }
          console.log('[Location] ℹ️ 无缓存位置可用')
        }

        if (allowFallback) {
          console.log('[Location] ⚠️ 降级使用默认位置（灵山胜境游客中心）', DEFAULT_SCENIC_LOCATION)
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
