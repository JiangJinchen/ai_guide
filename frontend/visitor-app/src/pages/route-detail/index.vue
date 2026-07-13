<template>
  <view class="detail-page" v-if="routePlan">
    <view class="map-section">
      <view class="map-canvas">
        <view class="map-road road-main"></view>
        <view class="map-road road-side"></view>
        <view class="map-water"></view>
        <view class="path-line" v-for="line in pathLines" :key="line.key" :style="line.style"></view>
        <view class="user-dot" v-if="userLocation" :style="userStyle">
          <view class="pulse"></view>
          <text>我</text>
        </view>
        <view
          class="idle-spot"
          v-for="spot in idleSpots"
          :key="'idle-' + spot.id"
          :style="spot.style"
          @click="showSpotPopup(spot)"
        ></view>
        <view
          class="route-marker"
          v-for="(spot, index) in routeSpots"
          :key="spot.id"
          :style="spot.style"
          @click="showSpotPopup(spot)"
        >
          <text>{{ index + 1 }}</text>
        </view>
      </view>
      <view class="stats-bar">
        <text>总游览时长 {{ totalDuration }} 分钟</text>
        <text>途经 {{ routeSpots.length }} 个景点</text>
        <text>{{ routePlan.travel_mode_label || '步行' }}约 {{ formatDistance(totalDistance) }}</text>
      </view>
    </view>

    <view class="deviation-bar" v-if="deviationDistance !== null && deviationDistance > 80">
      <text>您已偏离生成起点约 {{ formatDistance(deviationDistance) }}</text>
      <text class="deviation-action" @click="relocate">重新定位</text>
    </view>

    <view class="action-bar">
      <button class="action-btn primary" @click="navigateFullRoute">导航全程</button>
      <button class="action-btn" @click="relocate">重新定位</button>
      <button class="action-btn" @click="saveRoute">保存路线</button>
      <button class="action-btn" @click="shareRoute">分享路线</button>
    </view>

    <view class="route-summary">
      <text class="route-title">{{ routePlan.route_name }}</text>
      <text class="next-stop" v-if="routeSpots.length">当前下一站：{{ routeSpots[0].name }}</text>
      <text class="route-desc">{{ routePlan.strategy || routePlan.description || '按官方游览顺序规避折返路线。' }}</text>
    </view>

    <view class="segment-list" v-if="routeSpots.length">
      <view
        class="segment-swipe"
        v-for="(spot, index) in routeSpots"
        :key="spot.id"
        @touchstart="handleSegmentTouchStart($event, index)"
        @touchmove="handleSegmentTouchMove"
        @touchend="handleSegmentTouchEnd($event, index)"
      >
        <view class="swipe-delete" @click.stop="removeSpot(index)">删除</view>
        <view class="segment-card" :class="{ swiped: swipedIndex === index }" @longpress="startAdjustMode">
          <text class="segment-index">{{ index + 1 }}</text>
          <view class="segment-main" @click="handleSegmentTap(spot)">
            <text class="segment-name">{{ spot.name }}</text>
            <text class="segment-meta">
              {{ segmentInfo(index) }}｜停留 {{ spot.stay_minutes || 25 }} 分钟
            </text>
            <text class="segment-desc">{{ spot.description || '景区推荐游览点' }}</text>
          </view>
          <view class="segment-actions">
            <text class="mini-btn" @click.stop="navigateToSpot(spot)">导航</text>
            <text class="mini-btn" v-if="adjustMode && index > 0" @click.stop="moveSpot(index, -1)">上移</text>
            <text class="mini-btn" v-if="adjustMode && index < routeSpots.length - 1" @click.stop="moveSpot(index, 1)">下移</text>
          </view>
        </view>
      </view>
    </view>

    <view class="empty-state" v-else>
      <text>选择条件后生成路线</text>
    </view>

    <view class="popup-mask" v-if="popupSpot" @click="popupSpot = null">
      <view class="spot-popup" @click.stop>
        <text class="popup-title">{{ popupSpot.name }}</text>
        <text class="popup-desc">{{ popupSpot.description || '灵山胜境景点' }}</text>
        <view class="popup-actions">
          <text class="popup-btn" v-if="!isInRoute(popupSpot)" @click="addSpot(popupSpot)">加入路线</text>
          <text class="popup-btn disabled" v-else>已在路线中</text>
          <text class="popup-btn" @click="popupSpot = null">关闭</text>
        </view>
      </view>
    </view>
  </view>

  <view class="detail-page empty-page" v-else>
    <view class="empty-state">
      <text>选择条件后生成路线</text>
    </view>
  </view>
</template>

<script>
import { get, post } from '@/utils/request'
import { requestCurrentLocation } from '@/utils/location'

const SHARE_BASE_URL = (import.meta.env?.VITE_SHARE_BASE_URL || '').replace(/\/$/, '')
const LOCAL_HOST_PATTERN = /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?/i
const DEFAULT_LOCATION = { latitude: 31.42892, longitude: 120.09487 }
const SCENIC_ENTRY_LOCATION = {
  ...DEFAULT_LOCATION,
  name: '灵山胜境游客中心',
  source: 'scenic_entry'
}
const SCENIC_AREA_RADIUS_M = 5000
const TRAVEL_MODE_CONFIG = {
  walking: { speed: 70, factor: 1.25, extra: 0 },
  sightseeing_bus: { speed: 180, factor: 1.35, extra: 4 },
  accessible: { speed: 55, factor: 1.35, extra: 1 }
}
const SPOT_COORDS = {
  灵山大照壁: { latitude: 31.42892, longitude: 120.09487 },
  五明桥: { latitude: 31.42924, longitude: 120.09542 },
  佛足坛: { latitude: 31.42966, longitude: 120.09586 },
  五智门: { latitude: 31.43003, longitude: 120.09628 },
  菩提大道: { latitude: 31.43048, longitude: 120.09684 },
  九龙灌浴: { latitude: 31.43102, longitude: 120.09726 },
  灵山大佛: { latitude: 31.43334, longitude: 120.09958 },
  灵山梵宫: { latitude: 31.43072, longitude: 120.10116 },
  五印坛城: { latitude: 31.42998, longitude: 120.10174 },
  香月花街: { latitude: 31.42822, longitude: 120.10282 },
  梵天花海: { latitude: 31.42688, longitude: 120.10418 }
}

export default {
  data() {
    return {
      routePlan: null,
      routeSpots: [],
      allSpots: [],
      userLocation: null,
      shareMode: false,
      shareId: '',
      popupSpot: null,
      adjustMode: false,
      savedOnce: false,
      swipedIndex: null,
      touchStartX: 0,
      touchStartY: 0,
      touchDeltaX: 0,
      touchDeltaY: 0
    }
  },
  computed: {
    totalDistance() {
      if (this.routePlan?.total_distance && !this.adjustMode) {
        return Number(this.routePlan.total_distance)
      }
      return this.calculateRouteDistance()
    },
    totalDuration() {
      if (this.routePlan?.total_duration && !this.adjustMode) {
        return Number(this.routePlan.total_duration)
      }
      const stay = this.routeSpots.reduce((sum, item) => sum + Number(item.stay_minutes || 25), 0)
      return stay + Math.max(8, Math.round(this.totalDistance / 75))
    },
    userStyle() {
      return 'left: 50%; top: 50%;'
    },
    normalizedAllSpots() {
      return this.allSpots.map(this.normalizeSpot).filter(item => item.latitude && item.longitude)
    },
    deviationDistance() {
      const start = this.routePlan?.start_location
      if (!start?.latitude || !start?.longitude || !this.userLocation?.latitude || !this.userLocation?.longitude) {
        return null
      }
      return Math.round(this.distance(start.latitude, start.longitude, this.userLocation.latitude, this.userLocation.longitude))
    },
    idleSpots() {
      const usedIds = this.routeSpots.map(item => item.id)
      return this.normalizedAllSpots
        .filter(item => !usedIds.includes(item.id))
        .slice(0, 12)
        .map(item => ({ ...item, style: this.pointStyle(item) }))
    },
    pathLines() {
      const points = this.routeSpots.map(item => this.pointPosition(item))
      return points.slice(0, -1).map((point, index) => {
        const next = points[index + 1]
        const dx = next.x - point.x
        const dy = next.y - point.y
        const length = Math.sqrt(dx * dx + dy * dy)
        const angle = Math.atan2(dy, dx) * 180 / Math.PI
        return {
          key: `${index}-${index + 1}`,
          style: `left:${point.x}%;top:${point.y}%;width:${length}%;transform:rotate(${angle}deg);`
        }
      })
    }
  },
  async onLoad(options = {}) {
    const shareId = options.share_id || options.shareId
    if (shareId) {
      this.shareMode = true
      this.shareId = decodeURIComponent(shareId)
      try {
        const response = await get(`/routes/share/${encodeURIComponent(this.shareId)}`)
        this.applyRoutePlan(response.route || response, { persist: false })
      } catch (e) {
        uni.showToast({ title: 'Shared route is unavailable', icon: 'none' })
      }
    } else {
      const route = uni.getStorageSync('activeRoutePlan')
      if (route) {
        const fromHistory = Boolean(route.__from_history)
        delete route.__from_history
        this.applyRoutePlan(route)
        if (!fromHistory) this.saveRoute(true)
      }
    }
    this.loadAllSpots()
    const startLocation = this.getRouteStartLocation()
    if (startLocation) {
      this.userLocation = startLocation
      this.routeSpots = this.routeSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
    } else {
      this.refreshLocation()
    }
  },
  onShareAppMessage() {
    const routeName = this.routePlan?.route_name || '\u6e38\u89c8\u8def\u7ebf'
    const path = this.shareId
      ? `/pages/route-detail/index?share_id=${encodeURIComponent(this.shareId)}`
      : '/pages/route-detail/index'
    return {
      title: `\u5206\u4eab\u8def\u7ebf\uff1a${routeName}`,
      path,
      desc: routeName
    }
  },
  methods: {
    userId() {
      return uni.getStorageSync('userId') || 'guest'
    },
    async loadAllSpots() {
      try {
        const list = await get('/spots')
        this.allSpots = Array.isArray(list) ? list : []
      } catch (e) {
        this.allSpots = []
      }
    },
    async refreshLocation(options = {}) {
      try {
        const location = await requestCurrentLocation({
          allowCache: options.allowCache ?? true,
          allowFallback: options.allowFallback ?? true
        })
        this.userLocation = {
          latitude: location.latitude,
          longitude: location.longitude,
          name: location.name || '当前位置',
          source: location.isFallback ? 'fallback' : 'current'
        }
        this.routeSpots = this.routeSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
        if (this.routePlan) {
          this.routePlan.start_location = this.userLocation
          this.syncRoutePlan()
          this.savedOnce = false
        }
        return true
      } catch (e) {
        this.routeSpots = this.routeSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
        return false
      }
    },
    async relocate() {
      const located = await this.refreshLocation({ allowCache: false, allowFallback: false })
      uni.showToast({ title: located ? '已重新定位' : '定位失败，请稍后重试', icon: 'none' })
    },
    applyRoutePlan(route, options = {}) {
      this.routePlan = JSON.parse(JSON.stringify(route || {}))
      this.routeSpots = (route.route || []).map(this.normalizeSpot).map(item => ({ ...item, style: this.pointStyle(item) }))
      if (options.persist !== false && !this.shareMode) {
        uni.setStorageSync('activeRoutePlan', this.routePlan)
      }
    },
    hasValidLocation(location) {
      const latitude = Number(location?.latitude)
      const longitude = Number(location?.longitude)
      return latitude >= -90 && latitude <= 90 && longitude >= -180 && longitude <= 180
    },
    getRouteStartLocation() {
      const start = this.routePlan?.start_location
      if (!this.hasValidLocation(start)) return null
      return {
        latitude: Number(start.latitude),
        longitude: Number(start.longitude),
        name: start.name || '当前位置',
        source: start.source || 'route'
      }
    },
    normalizeSpot(spot) {
      const name = spot.spot_name || spot.name || '灵山景点'
      const coord = SPOT_COORDS[name] || {}
      return {
        ...spot,
        id: spot.id,
        name,
        latitude: Number(spot.latitude || coord.latitude),
        longitude: Number(spot.longitude || coord.longitude),
        description: spot.description || '',
        stay_minutes: spot.stay_minutes || 25
      }
    },
    pointPosition(spot) {
      const center = this.userLocation || DEFAULT_LOCATION
      const meterPerLat = 111000
      const meterPerLon = 111000 * Math.cos(center.latitude * Math.PI / 180)
      const dx = (spot.longitude - center.longitude) * meterPerLon
      const dy = (spot.latitude - center.latitude) * meterPerLat
      const range = 1000
      const x = Math.max(8, Math.min(92, 50 + (dx / range) * 42))
      const y = Math.max(8, Math.min(92, 50 - (dy / range) * 42))
      return { x: Math.round(x), y: Math.round(y) }
    },
    pointStyle(spot) {
      const pos = this.pointPosition(spot)
      return `left:${pos.x}%;top:${pos.y}%;`
    },
    calculateRouteDistance() {
      return this.buildRouteMetrics().total_distance
    },
    travelConfig() {
      return TRAVEL_MODE_CONFIG[this.routePlan?.travel_mode] || TRAVEL_MODE_CONFIG.walking
    },
    estimateSegmentDistance(from, to) {
      const straightDistance = this.distance(from.latitude, from.longitude, to.latitude, to.longitude)
      return {
        straightDistance: Math.round(straightDistance),
        distance: Math.round(straightDistance * this.travelConfig().factor)
      }
    },
    estimateSegmentMinutes(distance) {
      if (!distance) return 0
      const config = this.travelConfig()
      return Math.ceil(distance / config.speed) + config.extra
    },
    buildRouteMetrics(spots = this.routeSpots, startPoint = this.userLocation || this.getRouteStartLocation() || DEFAULT_LOCATION) {
      const start = startPoint
      let prev = {
        id: null,
        name: start.name || '当前位置',
        latitude: Number(start.latitude),
        longitude: Number(start.longitude)
      }
      let totalDistance = 0
      let travelDuration = 0
      const segments = spots.map((spot, index) => {
        const metrics = this.estimateSegmentDistance(prev, spot)
        const travelMinutes = this.estimateSegmentMinutes(metrics.distance)
        totalDistance += metrics.distance
        travelDuration += travelMinutes
        const segment = {
          order: index + 1,
          from: {
            spot_id: prev.id,
            name: prev.name,
            latitude: prev.latitude,
            longitude: prev.longitude
          },
          to: {
            spot_id: spot.id,
            name: spot.name,
            latitude: spot.latitude,
            longitude: spot.longitude
          },
          spot_id: spot.id,
          name: spot.name,
          provider: 'frontend_relocated_estimate',
          straight_distance_from_previous: metrics.straightDistance,
          distance_from_previous: metrics.distance,
          duration_sec: travelMinutes * 60,
          travel_minutes: travelMinutes,
          walk_minutes: travelMinutes,
          stay_minutes: Number(spot.stay_minutes || 25)
        }
        prev = {
          id: spot.id,
          name: spot.name,
          latitude: spot.latitude,
          longitude: spot.longitude
        }
        return segment
      })
      const stayDuration = spots.reduce((sum, item) => sum + Number(item.stay_minutes || 25), 0)
      return {
        total_distance: Math.round(totalDistance),
        travel_duration: travelDuration,
        walk_duration: travelDuration,
        stay_duration: stayDuration,
        total_duration: stayDuration + travelDuration,
        segments
      }
    },
    optimizeSpotsFromStart(startPoint, spots = this.routeSpots) {
      if (!this.hasValidLocation(startPoint)) return [...spots]
      const remaining = spots
        .filter(this.hasValidLocation)
        .map(spot => ({
          ...spot,
          latitude: Number(spot.latitude),
          longitude: Number(spot.longitude)
        }))
      const ordered = []
      let current = {
        latitude: Number(startPoint.latitude),
        longitude: Number(startPoint.longitude)
      }

      while (remaining.length) {
        let bestIndex = 0
        let bestDistance = Infinity
        remaining.forEach((spot, index) => {
          const distance = this.estimateSegmentDistance(current, spot).distance
          if (distance < bestDistance) {
            bestDistance = distance
            bestIndex = index
          }
        })
        const next = remaining.splice(bestIndex, 1)[0]
        ordered.push(next)
        current = next
      }

      return ordered
    },
    distance(lat1, lon1, lat2, lon2) {
      if (!lat1 || !lon1 || !lat2 || !lon2) return 0
      const toRad = value => value * Math.PI / 180
      const radius = 6371000
      const dLat = toRad(lat2 - lat1)
      const dLon = toRad(lon2 - lon1)
      const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
      return radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
    },
    formatDistance(distance) {
      const value = Number(distance || 0)
      if (value < 1000) return `${value}米`
      return `${(value / 1000).toFixed(1)}公里`
    },
    segmentInfo(index) {
      const segment = this.routePlan?.segments?.[index]
      if (!segment) return this.routeSpots[index]?.location || '灵山胜境景区内'
      const fromName = segment.from?.name || '当前位置'
      const distance = this.formatDistance(segment.distance_from_previous)
      const minutes = Number(segment.travel_minutes || segment.walk_minutes || 0)
      return `${fromName}到此约${distance}，行进${minutes}分钟`
    },
    startAdjustMode() {
      this.adjustMode = true
      this.swipedIndex = null
      uni.showToast({ title: '已进入排序调整', icon: 'none' })
    },
    handleSegmentTouchStart(event, index) {
      const touch = event.touches?.[0]
      if (!touch) return
      this.touchStartX = touch.clientX
      this.touchStartY = touch.clientY
      this.touchDeltaX = 0
      this.touchDeltaY = 0
      if (this.swipedIndex !== null && this.swipedIndex !== index) {
        this.swipedIndex = null
      }
    },
    handleSegmentTouchMove(event) {
      const touch = event.touches?.[0]
      if (!touch) return
      this.touchDeltaX = touch.clientX - this.touchStartX
      this.touchDeltaY = touch.clientY - this.touchStartY
    },
    handleSegmentTouchEnd(event, index) {
      const isHorizontal = Math.abs(this.touchDeltaX) > Math.abs(this.touchDeltaY) + 12
      if (!isHorizontal) return
      if (this.touchDeltaX < -56) {
        this.swipedIndex = index
      } else if (this.touchDeltaX > 30) {
        this.swipedIndex = null
      }
    },
    handleSegmentTap(spot) {
      if (this.swipedIndex !== null) {
        this.swipedIndex = null
        return
      }
      this.goToGuide(spot.id)
    },
    moveSpot(index, offset) {
      const target = index + offset
      if (target < 0 || target >= this.routeSpots.length) return
      const list = [...this.routeSpots]
      const item = list.splice(index, 1)[0]
      list.splice(target, 0, item)
      this.routeSpots = list.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
      this.syncRoutePlan()
    },
    removeSpot(index) {
      this.routeSpots.splice(index, 1)
      this.routeSpots = this.routeSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
      this.swipedIndex = null
      this.syncRoutePlan()
    },
    removeSpotById(id) {
      const index = this.routeSpots.findIndex(item => item.id === id)
      if (index > -1) this.removeSpot(index)
      this.popupSpot = null
    },
    addSpot(spot) {
      this.routeSpots.push({ ...spot, style: this.pointStyle(spot) })
      this.syncRoutePlan()
      this.popupSpot = null
    },
    isInRoute(spot) {
      return this.routeSpots.some(item => item.id === spot.id)
    },
    showSpotPopup(spot) {
      this.popupSpot = spot
    },
    syncRoutePlan() {
      const metrics = this.buildRouteMetrics()
      this.routePlan = {
        ...this.routePlan,
        route: this.routeSpots,
        total_spots: this.routeSpots.length,
        total_distance: metrics.total_distance,
        total_duration: metrics.total_duration,
        travel_duration: metrics.travel_duration,
        walk_duration: metrics.walk_duration,
        stay_duration: metrics.stay_duration,
        segments: metrics.segments
      }
      if (!this.shareMode) {
        uni.setStorageSync('activeRoutePlan', this.routePlan)
      }
    },
    navigateToSpot(spot) {
      if (!spot.latitude || !spot.longitude) {
        uni.showToast({ title: '暂无可导航位置', icon: 'none' })
        return
      }
      this.recordNavigateBehavior(spot)
      uni.openLocation({
        latitude: Number(spot.latitude),
        longitude: Number(spot.longitude),
        name: spot.name,
        address: spot.location || '灵山胜境景区内'
      })
    },
    recordNavigateBehavior(spot) {
      const data = {
        behavior_type: 'navigate',
        spot_id: spot.id,
        spot_name: spot.name
      }
      post('/behavior', data).catch(() => {})
    },
    navigateFullRoute() {
      if (!this.routeSpots.length) {
        uni.showToast({ title: '暂无可导航景点', icon: 'none' })
        return
      }
      const userLoc = this.userLocation || this.getRouteStartLocation()
      if (!this.hasValidLocation(userLoc)) {
        uni.showToast({ title: '请先重新定位', icon: 'none' })
        return
      }
      const distanceToScenic = this.calcDistanceM(
        userLoc.latitude,
        userLoc.longitude,
        DEFAULT_LOCATION.latitude,
        DEFAULT_LOCATION.longitude
      )
      const outsideScenicArea = distanceToScenic > SCENIC_AREA_RADIUS_M
      const startLocation = outsideScenicArea ? { ...SCENIC_ENTRY_LOCATION } : userLoc
      const navigationSpots = outsideScenicArea
        ? this.optimizeSpotsFromStart(startLocation, this.routeSpots)
        : [...this.routeSpots]
      const navigationMetrics = this.buildRouteMetrics(navigationSpots, startLocation)
      const startNotice = outsideScenicArea
        ? `您距离景区约${Math.round(distanceToScenic / 1000)}公里，已从灵山胜境游客中心重新规划游览顺序。`
        : ''

      uni.setStorageSync('activeRouteNavigation', {
        route_name: this.routePlan?.route_name || '游览路线',
        travel_mode: this.routePlan?.travel_mode || 'walking',
        travel_mode_label: this.routePlan?.travel_mode_label || '步行',
        start_location: startLocation,
        waypoints: navigationSpots.map((spot, index) => ({
          ...spot,
          order: index + 1
        })),
        total_distance: navigationMetrics.total_distance,
        total_duration: navigationMetrics.total_duration,
        travel_duration: navigationMetrics.travel_duration,
        stay_duration: navigationMetrics.stay_duration,
        segments: navigationMetrics.segments,
        reoptimized_from_scenic_entry: outsideScenicArea,
        start_notice: startNotice
      })

      if (outsideScenicArea) {
        uni.showToast({ title: startNotice, icon: 'none', duration: 3000 })
      }
      setTimeout(() => {
        uni.navigateTo({ url: '/pages/route-navigation/index' })
      }, outsideScenicArea ? 500 : 0)
    },
    calcDistanceM(lat1, lon1, lat2, lon2) {
      if (![lat1, lon1, lat2, lon2].every(value => Number.isFinite(Number(value)))) return Infinity
      const radius = 6371000
      const dlat = (Number(lat2) - Number(lat1)) * Math.PI / 180
      const dlon = (Number(lon2) - Number(lon1)) * Math.PI / 180
      const a = Math.sin(dlat / 2) ** 2 +
        Math.cos(lat1 * Math.PI / 180) *
        Math.cos(lat2 * Math.PI / 180) *
        Math.sin(dlon / 2) ** 2
      return Math.round(radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
    },
    async saveRoute(silent = false) {
      if (!this.routePlan || (!silent && this.savedOnce)) {
        if (!silent) uni.showToast({ title: '路线已保存', icon: 'none' })
        return
      }
      this.syncRoutePlan()
      try {
        await post('/routes/history', { user_id: this.userId(), route: this.routePlan })
        this.savedOnce = true
        if (!silent) uni.showToast({ title: '路线已保存', icon: 'success' })
      } catch (e) {
        if (!silent) uni.showToast({ title: '保存失败', icon: 'none' })
      }
    },
    formatShareDistance(distance) {
      const value = Number(distance || 0)
      if (value < 1000) return `${Math.round(value)}\u7c73`
      return `${(value / 1000).toFixed(1)}\u516c\u91cc`
    },
    async getShareUrl(path = '') {
      if (!this.shareId && this.routePlan) {
        try {
          const res = await post('/routes/share', { route: this.routePlan })
          this.shareId = res.share_id
        } catch (e) {
          console.warn('[SHARE] Failed to create share link:', e)
        }
      }
      if (!this.shareId) return ''
      const sharePath = `/pages/route-share/index?share_id=${encodeURIComponent(this.shareId)}`
      if (SHARE_BASE_URL) {
        return SHARE_BASE_URL.endsWith('/#')
          ? `${SHARE_BASE_URL}${sharePath}`
          : `${SHARE_BASE_URL}/#${sharePath}`
      }
      if (typeof window !== 'undefined' && window.location?.origin) {
        return `${window.location.origin}/#${sharePath}`
      }
      return `http://localhost:8080/#${sharePath}`
    },
    async buildSharePayload() {
      const routeName = this.routePlan?.route_name || '\u6e38\u89c8\u8def\u7ebf'
      const path = this.shareId
        ? `/pages/route-detail/index?share_id=${encodeURIComponent(this.shareId)}`
        : '/pages/route-detail/index'
      const names = this.routeSpots
        .map((item, index) => `${index + 1}. ${item.name || item.spot_name || '\u666f\u70b9'}`)
        .join(' -> ')
      const summary = [
        `${routeName}`,
        `\u9884\u8ba1\u7528\u65f6\uff1a${this.totalDuration}\u5206\u949f`,
        `\u9884\u8ba1\u8ddd\u79bb\uff1a${this.formatShareDistance(this.totalDistance)}`,
        `\u6e38\u89c8\u987a\u5e8f\uff1a${names || '\u6682\u65e0\u666f\u70b9'}`
      ]
      const url = await this.getShareUrl(path)
      if (url) summary.push(`\u6253\u5f00\u94fe\u63a5\uff1a${url}`)
      return {
        title: `\u5206\u4eab\u8def\u7ebf\uff1a${routeName}`,
        text: summary.join('\n'),
        path,
        url
      }
    },
    async createShareRecord() {
      const response = await post('/routes/share', {
        route: JSON.parse(JSON.stringify(this.routePlan))
      })
      if (!response?.share_id) throw new Error('Share id was not returned')
      this.shareId = response.share_id
      return this.shareId
    },
    copyShareText(text) {
      uni.setClipboardData({
        data: text,
        success: () => uni.showToast({ title: '\u8def\u7ebf\u5206\u4eab\u5185\u5bb9\u5df2\u590d\u5236', icon: 'none' }),
        fail: () => uni.showToast({ title: '\u5206\u4eab\u5931\u8d25\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5', icon: 'none' })
      })
    },
    async shareRoute() {
      if (!this.routePlan) {
        uni.showToast({ title: '\u6682\u65e0\u53ef\u5206\u4eab\u8def\u7ebf', icon: 'none' })
        return
      }
      this.syncRoutePlan()
      const payload = await this.buildSharePayload()

      // #ifdef H5
      if (typeof navigator !== 'undefined' && navigator.share) {
        const shareData = {
          title: payload.title,
          text: payload.text
        }
        if (payload.url) shareData.url = payload.url
        try {
          await navigator.share(shareData)
          return
        } catch (error) {
          if (error?.name === 'AbortError') return
        }
      }
      // #endif

      // #ifdef APP-PLUS
      uni.shareWithSystem({
        type: 'text',
        summary: payload.text,
        href: payload.url || undefined,
        success: () => {},
        fail: () => this.copyShareText(payload.text)
      })
      return
      // #endif

      this.copyShareText(payload.text)
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.detail-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #fdf8f0 0%, #f5efe3 100%);
  color: #37251a;
}

.map-section {
  position: relative;
  height: 40vh;
  min-height: 460rpx;
}

.map-canvas {
  position: relative;
  height: 100%;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 28%, rgba(231, 190, 104, 0.32), transparent 22%),
    linear-gradient(180deg, #1f3f3d 0%, #583025 55%, #201611 100%);
}

.map-road {
  position: absolute;
  background: rgba(255, 248, 232, 0.15);
}

.road-main {
  left: -10%;
  right: -10%;
  top: 51%;
  height: 10rpx;
  transform: rotate(-13deg);
}

.road-side {
  top: -10%;
  bottom: -10%;
  left: 56%;
  width: 9rpx;
  transform: rotate(20deg);
}

.map-water {
  position: absolute;
  right: -40rpx;
  bottom: -28rpx;
  width: 240rpx;
  height: 130rpx;
  border-radius: 50%;
  background: rgba(255, 248, 232, 0.12);
}

.path-line {
  position: absolute;
  z-index: 2;
  height: 8rpx;
  transform-origin: left center;
  border-radius: 999rpx;
  background: linear-gradient(90deg, #f2ca70, #fff8e8);
}

.user-dot,
.route-marker,
.idle-spot {
  position: absolute;
  z-index: 4;
  transform: translate(-50%, -50%);
  border-radius: 50%;
}

.user-dot {
  width: 68rpx;
  height: 68rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #8c3228;
  color: #fff8e8;
  font-size: 24rpx;
  font-weight: 850;
}

.pulse {
  position: absolute;
  inset: -12rpx;
  border: 3rpx solid rgba(242, 202, 112, 0.45);
  border-radius: 50%;
}

.route-marker {
  width: 54rpx;
  height: 54rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff8e8;
  color: #8c3228;
  font-size: 23rpx;
  font-weight: 850;
  box-shadow: 0 8rpx 20rpx rgba(55, 37, 26, 0.2);
}

.idle-spot {
  width: 24rpx;
  height: 24rpx;
  background: rgba(255, 248, 232, 0.4);
}

.stats-bar {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 20rpx;
  display: flex;
  justify-content: space-between;
  gap: 10rpx;
  padding: 18rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  color: #6d4b2d;
  font-size: 22rpx;
}

.deviation-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14rpx;
  margin: 22rpx 24rpx 0;
  padding: 18rpx 22rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  color: #ff9800;
  font-size: 23rpx;
}

.deviation-action {
  flex-shrink: 0;
  font-weight: 850;
}

.action-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14rpx;
  padding: 22rpx 24rpx;
}

.action-btn {
  min-height: 72rpx;
  padding: 0 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.95);
  color: #8c3228;
  font-size: 22rpx;
  line-height: 1.2;
}

.action-btn.primary {
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
}

.route-summary,
.empty-state {
  margin: 0 24rpx 20rpx;
  padding: 24rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  box-shadow: 0 4rpx 20rpx rgba(55, 37, 26, 0.08);
}

.route-title,
.next-stop,
.route-desc,
.segment-name,
.segment-meta,
.segment-desc,
.popup-title,
.popup-desc {
  display: block;
}

.route-title {
  color: #37251a;
  font-size: 34rpx;
  font-weight: bold;
}

.route-desc {
  margin-top: 10rpx;
  color: #8b7355;
  font-size: 24rpx;
  line-height: 1.5;
}

.next-stop {
  margin-top: 10rpx;
  color: #8c3228;
  font-size: 24rpx;
  font-weight: bold;
}

.segment-swipe {
  position: relative;
  margin: 0 24rpx 20rpx;
  overflow: hidden;
  border-radius: 16rpx;
  background: #ff4d4f;
}

.swipe-delete {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 128rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ff4d4f;
  color: #fff;
  font-size: 26rpx;
  font-weight: bold;
}

.segment-card {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  margin: 0;
  padding: 24rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  box-shadow: 0 4rpx 20rpx rgba(55, 37, 26, 0.08);
  transition: transform 0.18s ease;
}

.segment-card.swiped {
  transform: translateX(-128rpx);
}

.segment-index {
  width: 54rpx;
  height: 54rpx;
  flex-shrink: 0;
  margin-right: 18rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  font-weight: bold;
}

.segment-main {
  flex: 1;
  min-width: 0;
}

.segment-name {
  color: #37251a;
  font-size: 29rpx;
  font-weight: bold;
}

.segment-meta,
.segment-desc {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
  line-height: 1.4;
}

.segment-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.segment-actions {
  width: 92rpx;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 8rpx;
  margin-left: 14rpx;
}

.mini-btn {
  min-height: 42rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  font-size: 21rpx;
  background: #f3e3c4;
  color: #8c3228;
}

.empty-state {
  text-align: center;
  color: #8b7355;
  font-size: 26rpx;
}

.popup-mask {
  position: fixed;
  inset: 0;
  z-index: 99;
  display: flex;
  align-items: flex-end;
  background: rgba(0, 0, 0, 0.42);
}

.spot-popup {
  width: 100%;
  padding: 30rpx;
  border-radius: 22rpx 22rpx 0 0;
  background: rgba(255, 248, 232, 0.98);
}

.popup-title {
  color: #37251a;
  font-size: 34rpx;
  font-weight: bold;
}

.popup-desc {
  margin-top: 12rpx;
  color: #8b7355;
  font-size: 25rpx;
  line-height: 1.5;
}

.popup-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 24rpx;
}

.popup-btn {
  flex: 1;
  height: 76rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  background: #f3e3c4;
  color: #8c3228;
  font-size: 25rpx;
  font-weight: bold;
}

.popup-btn.danger {
  background: #ff4d4f;
  color: #fff;
}

.popup-btn.disabled {
  color: #8b7355;
}
</style>
