<template>
  <view class="detail-page" v-if="routePlan">
    <view class="map-section">
      <view class="map-canvas">
        <view class="map-road road-main"></view>
        <view class="map-road road-side"></view>
        <view class="map-water"></view>
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
      <button class="action-btn" @click="shareRoute">分享路线</button>
    </view>

    <view class="route-summary">
      <text class="route-title">{{ routePlan.route_name }}</text>
      <text class="next-stop" v-if="routeSpots.length">当前下一站：{{ routeSpots[0].name }}</text>
    </view>

    <view class="segment-list" v-if="routeSpots.length">
      <view class="segment-list-head">
        <text class="segment-list-title">游览顺序</text>
        <text class="order-status" :class="{ customized: manualOrderChanged }">
          {{ manualOrderChanged ? '已按您的偏好调整' : '智能推荐顺序' }}
        </text>
      </view>
      <view
        class="segment-swipe"
        :class="dragItemClass(index)"
        v-for="(spot, index) in segmentSpots"
        :key="spot.id"
        @touchstart="handleSegmentTouchStart($event, index)"
        @touchmove="handleSegmentTouchMove"
        @touchend="handleSegmentTouchEnd($event, index)"
      >
        <view class="swipe-delete" @click.stop="removeSpot(index)">删除</view>
        <view
          class="segment-card"
          :class="{ swiped: swipedIndex === index, dragging: dragCurrentIndex === index }"
          :style="dragCardStyle(index, spot)"
        >
          <text class="segment-index">{{ index + 1 }}</text>
          <view class="segment-main" @click="handleSegmentTap(spot)">
            <text class="segment-name">{{ spot.name }}</text>
            <text class="segment-meta">
              {{ segmentInfo(index, spot) }}｜停留 {{ spot.stay_minutes || 25 }} 分钟
            </text>
            <text class="segment-desc">{{ spot.description || '景区推荐游览点' }}</text>
          </view>
          <view class="segment-actions">
            <view class="nav-icon-button" @click.stop="navigateToSpot(spot)">
              <image class="nav-icon-text" src="/static/icons/导航.png" mode="aspectFit"></image>
            </view>
          </view>
          <view
            class="drag-handle"
            title="拖拽调整顺序"
            aria-label="拖拽调整顺序"
            @click.stop
            @touchstart.stop="startSpotDrag($event, index)"
            @touchmove.stop.prevent="moveSpotDrag"
            @touchend.stop="endSpotDrag"
            @touchcancel.stop="cancelSpotDrag"
            @mousedown.stop.prevent="startSpotDrag($event, index)"
          >
            <view class="drag-line"></view>
            <view class="drag-line"></view>
            <view class="drag-line"></view>
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
  灵山大照壁: { latitude: 31.421388, longitude: 120.102499 },
  五明桥: { latitude: 31.421749, longitude: 120.102248 },
  佛足坛: { latitude: 31.422725, longitude: 120.101497 },
  五智门: { latitude: 31.423055, longitude: 120.101292 },
  菩提大道: { latitude: 31.423182, longitude: 120.101143 },
  九龙灌浴: { latitude: 31.424601, longitude: 120.099984 },
  降魔浮雕: { latitude: 31.425559, longitude: 120.099569 },
  阿育王柱: { latitude: 31.426188, longitude: 120.099261 },
  百子戏弥勒: { latitude: 31.42719, longitude: 120.098844 },
  祥符禅寺: { latitude: 31.427949, longitude: 120.098012 },
  灵山大佛: { latitude: 31.430194, longitude: 120.096477 },
  佛教文化博览馆: { latitude: 31.429924, longitude: 120.096629 },
  无尽意斋: { latitude: 31.428768, longitude: 120.096987 },
  灵山梵宫: { latitude: 31.428218, longitude: 120.10242 },
  五印坛城: { latitude: 31.424676, longitude: 120.103054 },
  曼飞龙塔: { latitude: 31.42607, longitude: 120.104609 },
  拈花广场: { latitude: 31.422807, longitude: 120.080082 },
  香月花街: { latitude: 31.416822, longitude: 120.073636 },
  拈花堂: { latitude: 31.423012, longitude: 120.080120 },
  五灯湖: { latitude: 31.418665, longitude: 120.075312 },
  梵天花海: { latitude: 31.415904, longitude: 120.075421 },
  鹿鸣谷: { latitude: 31.438472, longitude: 120.172608 }
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
      manualOrderChanged: false,
      savedOnce: false,
      swipedIndex: null,
      touchStartX: 0,
      touchStartY: 0,
      touchDeltaX: 0,
      touchDeltaY: 0,
      dragPreviewSpots: null,
      dragCurrentIndex: null,
      dragStartY: 0,
      dragLastY: 0,
      dragGrabOffsetY: 0,
      dragOffsetY: 0,
      dragMoved: false,
      dragMeasured: false,
      dragSwapPending: false,
      dragItemRects: [],
      dragShiftOffsets: {},
      dragShiftTimer: null
    }
  },
  computed: {
    segmentSpots() {
      return this.dragPreviewSpots || this.routeSpots
    },
    totalDistance() {
      if (this.routePlan?.total_distance) {
        return Number(this.routePlan.total_distance)
      }
      return this.calculateRouteDistance()
    },
    totalDuration() {
      if (this.routePlan?.total_duration) {
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
  beforeUnmount() {
    this.cancelSpotDrag()
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
      this.manualOrderChanged = Boolean(route.manual_order_changed ?? route.manualOrderChanged)
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
      const range = 700
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
    segmentInfo(index, spot = this.routeSpots[index]) {
      const originalIndex = this.dragPreviewSpots
        ? this.routeSpots.findIndex(item => this.dragSpotKey(item) === this.dragSpotKey(spot))
        : index
      const segment = this.routePlan?.segments?.[originalIndex > -1 ? originalIndex : index]
      if (!segment) return spot?.location || '灵山胜境景区内'
      const fromName = segment.from?.name || '当前位置'
      const distance = this.formatDistance(segment.distance_from_previous)
      const minutes = Number(segment.travel_minutes || segment.walk_minutes || 0)
      return `${fromName}到此约${distance}，行进${minutes}分钟`
    },
    handleSegmentTouchStart(event, index) {
      if (this.dragCurrentIndex !== null) return
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
      if (this.dragCurrentIndex !== null) return
      const touch = event.touches?.[0]
      if (!touch) return
      this.touchDeltaX = touch.clientX - this.touchStartX
      this.touchDeltaY = touch.clientY - this.touchStartY
    },
    handleSegmentTouchEnd(event, index) {
      if (this.dragCurrentIndex !== null) return
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
    dragItemClass(index) {
      if (this.dragCurrentIndex === null) return {}
      return {
        'drag-source': this.dragCurrentIndex === index,
        'drag-placeholder': this.dragCurrentIndex === index && this.dragMoved
      }
    },
    dragSpotKey(spot) {
      return String(spot?.id ?? spot?.spot_id ?? spot?.name ?? '')
    },
    dragCardStyle(index, spot) {
      if (this.dragCurrentIndex === index) {
        return `transform:translateY(${this.dragOffsetY}px) scale(1.015);transition:none;`
      }
      const shift = Number(this.dragShiftOffsets[this.dragSpotKey(spot)] || 0)
      return Math.abs(shift) > 0.5 ? `transform:translateY(${shift}px);` : ''
    },
    dragEventPoint(event) {
      return event?.touches?.[0] || event?.changedTouches?.[0] || event
    },
    startSpotDrag(event, index) {
      if (this.routeSpots.length < 2 || this.dragCurrentIndex !== null) return
      const point = this.dragEventPoint(event)
      if (!Number.isFinite(Number(point?.clientY))) return

      this.swipedIndex = null
      this.dragPreviewSpots = [...this.routeSpots]
      this.dragCurrentIndex = index
      this.dragStartY = Number(point.clientY)
      this.dragLastY = Number(point.clientY)
      this.dragGrabOffsetY = 0
      this.dragOffsetY = 0
      this.dragMoved = false
      this.dragMeasured = false
      this.dragSwapPending = false
      this.dragItemRects = []
      this.dragShiftOffsets = {}
      this.measureDragItems()

      // #ifdef H5
      if (event?.type === 'mousedown' && typeof document !== 'undefined') {
        document.addEventListener('mousemove', this.moveSpotDrag)
        document.addEventListener('mouseup', this.endSpotDrag)
      }
      // #endif
    },
    measureDragItems() {
      this.$nextTick(() => {
        uni.createSelectorQuery()
          .in(this)
          .selectAll('.segment-swipe')
          .boundingClientRect(rects => {
            if (this.dragCurrentIndex === null) return
            this.dragItemRects = Array.isArray(rects) ? rects : []
            const currentRect = this.dragItemRects[this.dragCurrentIndex]
            if (!currentRect) return
            this.dragGrabOffsetY = this.dragStartY - Number(currentRect.top)
            this.dragMeasured = true
            this.updateDraggedCardOffset()
            if (this.dragMoved) this.updateLiveDragOrder(this.dragLastY)
          })
          .exec()
      })
    },
    moveSpotDrag(event) {
      if (this.dragCurrentIndex === null) return
      const point = this.dragEventPoint(event)
      if (!Number.isFinite(Number(point?.clientY))) return
      if (event?.cancelable) event.preventDefault()

      this.dragLastY = Number(point.clientY)
      this.dragMoved = this.dragMoved || Math.abs(this.dragLastY - this.dragStartY) > 4
      this.updateDraggedCardOffset()
      if (this.dragMoved) this.updateLiveDragOrder(this.dragLastY)
    },
    updateDraggedCardOffset() {
      const currentRect = this.dragItemRects[this.dragCurrentIndex]
      if (this.dragMeasured && currentRect) {
        const desiredTop = this.dragLastY - this.dragGrabOffsetY
        this.dragOffsetY = desiredTop - Number(currentRect.top)
        return
      }
      this.dragOffsetY = this.dragLastY - this.dragStartY
    },
    updateLiveDragOrder(clientY) {
      if (this.dragSwapPending || !this.dragItemRects.length || this.dragCurrentIndex === null) return
      const centers = this.dragItemRects.map(rect => Number(rect.top) + Number(rect.height) / 2)
      let closestIndex = this.dragCurrentIndex
      let closestDistance = Infinity
      centers.forEach((centerY, index) => {
        const distance = Math.abs(clientY - centerY)
        if (distance < closestDistance) {
          closestDistance = distance
          closestIndex = index
        }
      })
      if (closestIndex === this.dragCurrentIndex) return

      const direction = closestIndex > this.dragCurrentIndex ? 1 : -1
      const adjacentIndex = this.dragCurrentIndex + direction
      const boundary = (centers[this.dragCurrentIndex] + centers[adjacentIndex]) / 2 + direction * 6
      if ((direction > 0 && clientY <= boundary) || (direction < 0 && clientY >= boundary)) return
      this.swapDragPreview(closestIndex)
    },
    swapDragPreview(targetIndex) {
      if (!this.dragPreviewSpots || this.dragCurrentIndex === null) return
      const sourceIndex = this.dragCurrentIndex
      const sourceRect = this.dragItemRects[sourceIndex]
      const targetRect = this.dragItemRects[targetIndex]
      if (!sourceRect || !targetRect) return

      const previousTops = {}
      this.dragPreviewSpots.forEach((spot, index) => {
        previousTops[this.dragSpotKey(spot)] = Number(this.dragItemRects[index]?.top || 0)
      })
      const draggedVisualTop = Number(sourceRect.top) + this.dragOffsetY
      const list = [...this.dragPreviewSpots]
      const item = list.splice(sourceIndex, 1)[0]
      list.splice(targetIndex, 0, item)

      this.dragSwapPending = true
      this.dragPreviewSpots = list
      this.dragCurrentIndex = targetIndex
      this.dragOffsetY = draggedVisualTop - Number(targetRect.top)

      this.$nextTick(() => {
        uni.createSelectorQuery()
          .in(this)
          .selectAll('.segment-swipe')
          .boundingClientRect(rects => {
            if (this.dragCurrentIndex === null || !this.dragPreviewSpots) return
            const nextRects = Array.isArray(rects) ? rects : []
            const shifts = {}
            this.dragPreviewSpots.forEach((spot, index) => {
              if (index === this.dragCurrentIndex) return
              const previousTop = previousTops[this.dragSpotKey(spot)]
              const nextTop = Number(nextRects[index]?.top || 0)
              const shift = Number(previousTop) - nextTop
              if (Number.isFinite(shift) && Math.abs(shift) > 0.5) {
                shifts[this.dragSpotKey(spot)] = shift
              }
            })
            this.dragItemRects = nextRects
            this.dragShiftOffsets = shifts
            this.dragSwapPending = false
            this.updateDraggedCardOffset()
            this.scheduleShiftReset()
            this.updateLiveDragOrder(this.dragLastY)
          })
          .exec()
      })
    },
    scheduleShiftReset() {
      if (this.dragShiftTimer) clearTimeout(this.dragShiftTimer)
      this.dragShiftTimer = setTimeout(() => {
        this.dragShiftOffsets = {}
        this.dragShiftTimer = null
      }, 20)
    },
    endSpotDrag() {
      if (this.dragCurrentIndex === null) return
      const previewSpots = [...(this.dragPreviewSpots || this.routeSpots)]
      const changed = this.dragMoved && previewSpots.some((spot, index) => {
        return this.dragSpotKey(spot) !== this.dragSpotKey(this.routeSpots[index])
      })

      this.releaseDragMouseListeners()
      this.resetDragState()
      if (!changed) return

      this.routeSpots = previewSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
      this.markManualOrderChanged()
      this.syncRoutePlan(true)
      uni.showToast({ title: '游览顺序已更新', icon: 'none' })
    },
    cancelSpotDrag() {
      this.releaseDragMouseListeners()
      this.resetDragState()
    },
    releaseDragMouseListeners() {
      // #ifdef H5
      if (typeof document !== 'undefined') {
        document.removeEventListener('mousemove', this.moveSpotDrag)
        document.removeEventListener('mouseup', this.endSpotDrag)
      }
      // #endif
    },
    resetDragState() {
      if (this.dragShiftTimer) clearTimeout(this.dragShiftTimer)
      this.dragShiftTimer = null
      this.dragPreviewSpots = null
      this.dragCurrentIndex = null
      this.dragStartY = 0
      this.dragLastY = 0
      this.dragGrabOffsetY = 0
      this.dragOffsetY = 0
      this.dragMoved = false
      this.dragMeasured = false
      this.dragSwapPending = false
      this.dragItemRects = []
      this.dragShiftOffsets = {}
    },
    markManualOrderChanged() {
      this.manualOrderChanged = true
      this.savedOnce = false
    },
    removeSpot(index) {
      this.routeSpots.splice(index, 1)
      this.routeSpots = this.routeSpots.map(spot => ({ ...spot, style: this.pointStyle(spot) }))
      this.swipedIndex = null
      this.markManualOrderChanged()
      this.syncRoutePlan(true)
    },
    removeSpotById(id) {
      const index = this.routeSpots.findIndex(item => item.id === id)
      if (index > -1) this.removeSpot(index)
      this.popupSpot = null
    },
    addSpot(spot) {
      this.routeSpots.push({ ...spot, style: this.pointStyle(spot) })
      this.markManualOrderChanged()
      this.syncRoutePlan(true)
      this.popupSpot = null
    },
    isInRoute(spot) {
      return this.routeSpots.some(item => item.id === spot.id)
    },
    showSpotPopup(spot) {
      this.popupSpot = spot
    },
    syncRoutePlan(recalculate = false) {
      const existingDistance = Number(this.routePlan?.total_distance)
      const existingDuration = Number(this.routePlan?.total_duration)
      const shouldRecalculate = recalculate || !Number.isFinite(existingDistance) || !Number.isFinite(existingDuration)
      const metrics = shouldRecalculate ? this.buildRouteMetrics() : null
      this.routePlan = {
        ...this.routePlan,
        route: this.routeSpots,
        total_spots: this.routeSpots.length,
        total_distance: shouldRecalculate ? metrics.total_distance : existingDistance,
        total_duration: shouldRecalculate ? metrics.total_duration : existingDuration,
        travel_duration: shouldRecalculate ? metrics.travel_duration : this.routePlan?.travel_duration,
        walk_duration: shouldRecalculate ? metrics.walk_duration : this.routePlan?.walk_duration,
        stay_duration: shouldRecalculate ? metrics.stay_duration : this.routePlan?.stay_duration,
        segments: shouldRecalculate ? metrics.segments : this.routePlan?.segments,
        manual_order_changed: this.manualOrderChanged
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
      const shouldReoptimize = outsideScenicArea && !this.manualOrderChanged
      const navigationSpots = shouldReoptimize
        ? this.optimizeSpotsFromStart(startLocation, this.routeSpots)
        : [...this.routeSpots]
      const navigationMetrics = this.buildRouteMetrics(navigationSpots, startLocation)
      const startNotice = outsideScenicArea
        ? shouldReoptimize
          ? `您距离景区约${Math.round(distanceToScenic / 1000)}公里，已从灵山胜境游客中心重新规划游览顺序。`
          : `您距离景区约${Math.round(distanceToScenic / 1000)}公里，将从灵山胜境游客中心开始，并按您调整的顺序导航。`
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
        reoptimized_from_scenic_entry: shouldReoptimize,
        manual_order_locked: this.manualOrderChanged,
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
      this.syncRoutePlan(false)
      try {
        const payload = JSON.parse(JSON.stringify(this.routePlan || {}))
        await post('/routes/history', { user_id: String(this.userId()), route: payload })
        this.savedOnce = true
        if (!silent) uni.showToast({ title: '路线已保存', icon: 'success' })
      } catch (e) {
        console.error('[route-detail] saveRoute failed', e, e?.data || e?.response?.data)
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
      this.syncRoutePlan(false)
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
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
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
  isolation: isolate;
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
  box-shadow: 0 8rpx 20rpx rgba(55, 37, 26, 0.2), 0 0 0 2rpx rgba(255, 248, 232, 0.28);
}

.idle-spot {
  width: 22rpx;
  height: 22rpx;
  background: rgba(255, 248, 232, 0.34);
  box-shadow: 0 0 0 2rpx rgba(255, 248, 232, 0.14);
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
  display: flex;
  flex-direction: row;
  gap: 16rpx;
  padding: 22rpx 24rpx;
}

.action-btn {
  flex: 1;
  min-width: 0;
  box-sizing: border-box;
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

.next-stop {
  margin-top: 10rpx;
  color: #8c3228;
  font-size: 24rpx;
  font-weight: bold;
}

.segment-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
  margin: 0 24rpx 16rpx;
}

.segment-list-title {
  color: #37251a;
  font-size: 28rpx;
  font-weight: bold;
}

.order-status {
  color: #8b7355;
  font-size: 22rpx;
}

.order-status.customized {
  color: #8c3228;
  font-weight: bold;
}

.segment-swipe {
  position: relative;
  margin: 0 24rpx 20rpx;
  overflow: hidden;
  border-radius: 16rpx;
  background: #ff4d4f;
}

.segment-swipe.drag-source {
  z-index: 10;
  overflow: visible;
  background: rgba(140, 50, 40, 0.1);
  box-shadow: inset 0 0 0 2rpx rgba(140, 50, 40, 0.12);
}

.segment-swipe.drag-source .swipe-delete {
  display: none !important;
}

.segment-swipe.drag-placeholder::before {
  content: '';
  position: absolute;
  left: 16rpx;
  right: 16rpx;
  z-index: 20;
  top: -12rpx;
  height: 5rpx;
  border-radius: 5rpx;
  background: #8c3228;
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

.segment-card.dragging {
  z-index: 30;
  opacity: 0.94;
  box-shadow: 0 14rpx 40rpx rgba(55, 37, 26, 0.24);
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

.nav-icon-button {
  width: 54rpx;
  height: 54rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #efe0bd;
  color: #814b00;
}

.nav-icon-button:active {
  background: #e3cea4;
}

.nav-icon-text {
  width: 28rpx;
  height: 28rpx;
  display: block;
}

.drag-handle {
  width: 56rpx;
  height: 64rpx;
  flex-shrink: 0;
  margin-left: 10rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7rpx;
  border-radius: 8rpx;
  touch-action: none;
  user-select: none;
}

.drag-line {
  width: 30rpx;
  height: 4rpx;
  border-radius: 4rpx;
  background: #8b7355;
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

@media screen and (max-width: 380px) {
  .map-section {
    height: 420rpx;
    min-height: 420rpx;
  }

  .user-dot {
    width: 60rpx;
    height: 60rpx;
    font-size: 22rpx;
  }

  .route-marker {
    width: 48rpx;
    height: 48rpx;
    font-size: 21rpx;
  }

  .stats-bar {
    flex-wrap: wrap;
    justify-content: flex-start;
    gap: 8rpx 16rpx;
    padding: 16rpx;
  }

  .deviation-bar,
  .segment-list-head {
    flex-wrap: wrap;
  }

  .action-bar {
    grid-template-columns: 1fr;
    padding-top: 18rpx;
  }

  .route-summary,
  .empty-state,
  .segment-list-head,
  .segment-swipe {
    margin-left: 18rpx;
    margin-right: 18rpx;
  }

  .segment-card {
    padding: 20rpx;
  }

  .segment-actions {
    width: 72rpx;
  }

  .drag-handle {
    width: 48rpx;
    margin-left: 6rpx;
  }

  .popup-actions {
    flex-direction: column;
  }

  .popup-btn {
    min-height: 76rpx;
  }
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
