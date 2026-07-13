<template>
  <view class="navigation-page" v-if="navigationPlan">
    <view class="map-section">
      <map
        id="routeMap"
        class="map-view"
        :latitude="mapCenter.latitude"
        :longitude="mapCenter.longitude"
        :scale="17"
        :markers="mapMarkers"
        :polyline="mapPolyline"
        :include-points="includePoints"
        show-location
        @markertap="handleMarkerTap"
      />

      <view class="map-status">
        <view class="status-main">
          <text class="status-title">{{ currentInstruction }}</text>
          <text class="status-desc">{{ trackingStatusText }} · {{ distanceToTargetText }} · {{ providerText }}</text>
        </view>
        <view class="status-pill">{{ navigationStateText }}</view>
      </view>
    </view>

    <view class="scenic-notice" v-if="scenicStartNotice">
      <text>{{ scenicStartNotice }}</text>
    </view>

    <view class="quick-actions">
      <button class="action-btn" @click="toggleTracking">{{ isTracking ? '暂停追踪' : '开始追踪' }}</button>
      <button class="action-btn" @click="openNextWaypoint">系统地图</button>
    </view>

    <view class="route-summary">
      <view class="summary-head">
        <view>
          <text class="route-title">{{ routeName }}</text>
          <text class="route-desc">从{{ startName }}出发，按顺序游览 {{ waypoints.length }} 个景点。</text>
        </view>
        <view class="summary-badge">
          <text>{{ formatDuration(totalDurationSec) }}</text>
        </view>
      </view>
      <view class="metric-row">
        <view class="metric-item">
          <text class="metric-value">{{ formatDistance(totalDistance) }}</text>
          <text class="metric-label">总路程</text>
        </view>
        <view class="metric-item">
          <text class="metric-value">{{ steps.length }}</text>
          <text class="metric-label">导航步骤</text>
        </view>
        <view class="metric-item">
          <text class="metric-value">{{ waypoints.length }}</text>
          <text class="metric-label">途经点</text>
        </view>
      </view>
    </view>

    <view class="waypoint-list">
      <view class="section-head">
        <text class="section-title">路线节点</text>
        <text class="section-note">{{ providerText }}</text>
      </view>

      <view class="waypoint-card start-card">
        <text class="waypoint-index">起</text>
        <view class="waypoint-main">
          <text class="waypoint-name">{{ startName }}</text>
          <text class="waypoint-meta">{{ coordinateText(startLocation) }}</text>
        </view>
      </view>

      <view class="waypoint-card" v-for="spot in waypoints" :key="spot.id || spot.order">
        <text class="waypoint-index" :class="{ arrived: isWaypointArrived(spot) }">
          {{ isWaypointArrived(spot) ? '✓' : spot.order }}
        </text>
        <view class="waypoint-main">
          <text class="waypoint-name">{{ spot.name }}</text>
          <text class="waypoint-meta">{{ spot.location || '灵山胜境景区内' }}</text>
        </view>
        <text class="mini-btn" @click="openSpotMap(spot)">地图</text>
      </view>
    </view>
  </view>

  <view class="navigation-page empty-page" v-else>
    <view class="empty-state">
      <text>暂无可导航路线</text>
    </view>

    <FeedbackModal
      :visible="showFeedbackModal"
      :title="feedbackModalConfig.title"
      :content="feedbackModalConfig.content"
      :params="feedbackModalConfig.params"
      :type="feedbackModalConfig.type"
      :target-key="feedbackModalConfig.targetKey"
      @close="showFeedbackModal = false"
      @later="handleFeedbackLater"
      @submit="handleFeedbackSubmit"
    />
  </view>
</template>

<script>
import FeedbackModal from '@/components/FeedbackModal/index.vue'
import { get, post } from '@/utils/request'
import { requestCurrentLocation } from '@/utils/location'
import { promptForFeedback, markFeedbackPrompt, openFeedbackPage } from '@/utils/feedback'
import startIcon from '@/static/map/起点.png'
import waypointIcon from '@/static/map/途经点.png'

const DEFAULT_LOCATION = {
  latitude: 31.426486,
  longitude: 120.110053,
  name: '灵山胜境游客中心'
}
const SCENIC_AREA_RADIUS_M = 5000

const ARRIVE_STEP_THRESHOLD_M = 22
const ARRIVE_WAYPOINT_THRESHOLD_M = 35
const DEVIATION_THRESHOLD_M = 65
const AUTO_ADVANCE_COOLDOWN_MS = 2500
const AUTO_REPLAN_COOLDOWN_MS = 25000

export default {
  components: {
    FeedbackModal
  },
  data() {
    return {
      navigationPlan: null,
      navigationData: null,
      currentLocation: null,
      activeStepIndex: 0,
      isLoading: false,
      isTracking: false,
      trackingStatus: 'idle',
      navigationCompleted: false,
      arrivedWaypointKeys: [],
      deviationCount: 0,
      lastAutoAdvanceAt: 0,
      lastAutoReplanAt: 0,
      locationChangeHandler: null,
      trackingTimer: null,
      simulationTimer: null,
      simulationIndex: 0,
      hasReordered: false,
      navigationSessionId: '',
      isPageActive: true,
      showFeedbackModal: false,
      feedbackModalConfig: {
        title: '',
        content: '',
        params: {},
        type: '',
        targetKey: ''
      }
    }
  },
  computed: {
    routeName() {
      return this.navigationData?.route_name || this.navigationPlan?.route_name || '游览路线'
    },
    startLocation() {
      return this.navigationData?.start_location || this.navigationPlan?.start_location || DEFAULT_LOCATION
    },
    startName() {
      return this.startLocation?.name || '当前位置'
    },
    waypoints() {
      return this.navigationData?.waypoints || this.navigationPlan?.waypoints || []
    },
    steps() {
      return this.navigationData?.steps || []
    },
    segments() {
      return this.navigationData?.segments || []
    },
    activeStep() {
      return this.steps[this.activeStepIndex] || this.steps[0] || null
    },
    activeSegment() {
      const order = Number(this.activeStep?.segment_order || 0)
      return order > 0 ? this.segments[order - 1] || null : null
    },
    currentTargetPoint() {
      const stepPolyline = this.activeStep?.polyline || []
      const stepTarget = stepPolyline[stepPolyline.length - 1]
      if (this.isValidPoint(stepTarget)) return stepTarget
      if (this.isValidPoint(this.activeSegment?.to)) return this.activeSegment.to
      return this.waypoints[0] || null
    },
    currentInstruction() {
      if (this.navigationCompleted) return '已到达终点，导航结束'
      if (this.isLoading) return '正在重新生成高德导航指引'
      return this.activeStep?.instruction || '按地图路线前往下一站'
    },
    nextWaypointName() {
      return this.currentTargetPoint?.name || this.waypoints[0]?.name || '下一站'
    },
    totalDistance() {
      return this.navigationData?.total_distance_m || this.navigationPlan?.total_distance || 0
    },
    totalDurationSec() {
      return this.navigationData?.total_duration_sec || Number(this.navigationPlan?.total_duration || 0) * 60
    },
    providerText() {
      const type = this.navigationData?.provider_type
      if (type === 'amap_walking') return '高德步行导航'
      if (type === 'amap_walking_with_fallback') return '高德导航含本地兜底'
      if (type === 'haversine_navigation') return '本地估算导航'
      return '路线导航'
    },
    trackingStatusText() {
      if (this.navigationCompleted) return '导航已结束'
      if (this.trackingStatus === 'streaming') return '实时追踪中'
      if (this.trackingStatus === 'polling') return '定位轮询中'
      if (this.trackingStatus === 'simulating') return 'H5模拟移动'
      if (this.trackingStatus === 'starting') return '正在开启定位'
      if (this.trackingStatus === 'paused') return '追踪已暂停'
      return '等待定位'
    },
    navigationStateText() {
      if (this.navigationCompleted) return '已到达'
      if (this.isTracking) return '导航中'
      return this.navigationData?.travel_mode_label || this.navigationPlan?.travel_mode_label || '步行'
    },
    distanceToTarget() {
      if (!this.isValidPoint(this.currentLocation) || !this.isValidPoint(this.currentTargetPoint)) return null
      return this.calcDistanceM(
        this.currentLocation.latitude,
        this.currentLocation.longitude,
        this.currentTargetPoint.latitude,
        this.currentTargetPoint.longitude
      )
    },
    distanceToTargetText() {
      if (this.distanceToTarget === null) return '等待定位'
      return `距下一点${this.formatDistance(this.distanceToTarget)}`
    },
    routePolyline() {
      const polyline = this.navigationData?.polyline || []
      if (polyline.length) return polyline
      const basePoints = []
      if (this.isValidPoint(this.startLocation)) {
        basePoints.push(this.startLocation)
      }
      if (Array.isArray(this.waypoints)) {
        basePoints.push(...this.waypoints.filter(this.isValidPoint))
      }
      return basePoints
    },
    mapCenter() {
      const center = this.currentLocation || this.startLocation || this.routePolyline[0] || DEFAULT_LOCATION
      if (!this.isValidPoint(center)) return DEFAULT_LOCATION
      return {
        latitude: Number(center.latitude),
        longitude: Number(center.longitude)
      }
    },
    mapMarkers() {
      const markers = []
      if (this.isValidPoint(this.currentLocation || this.startLocation)) {
        const start = this.currentLocation || this.startLocation
        markers.push({
          id: 1,
          latitude: Number(start.latitude),
          longitude: Number(start.longitude),
          title: this.currentLocation ? '当前位置' : this.startName,
          width: 28,
          height: 28,
          iconPath: startIcon,
          callout: {
            content: this.currentLocation ? '当前位置' : this.startName,
            display: 'BYCLICK',
            color: '#37251a',
            bgColor: '#fff8e8',
            padding: 8,
            borderRadius: 6
          }
        })
      }

      this.waypoints.forEach((spot, index) => {
        if (!this.isValidPoint(spot)) return
        const arrived = this.isWaypointArrived(spot)
        markers.push({
          id: index + 2,
          latitude: Number(spot.latitude),
          longitude: Number(spot.longitude),
          title: spot.name,
          width: 26,
          height: 26,
          iconPath: waypointIcon,
          label: {
            content: arrived ? '✓' : String(spot.order || index + 1),
            color: arrived ? '#ffffff' : '#8c3228',
            fontSize: 12,
            bgColor: arrived ? '#2f7d55' : '#fff8e8',
            borderRadius: 13,
            padding: 5
          },
          callout: {
            content: spot.name,
            display: 'BYCLICK',
            color: '#37251a',
            bgColor: '#fff8e8',
            padding: 8,
            borderRadius: 6
          }
        })
      })
      return markers
    },
    mapPolyline() {
      const points = this.routePolyline
        .filter(this.isValidPoint)
        .map(point => ({
          latitude: Number(point.latitude),
          longitude: Number(point.longitude)
        }))
      if (points.length < 2) return []
      return [{
        points,
        color: '#8c3228',
        width: 7,
        arrowLine: true,
        borderColor: '#fff8e8',
        borderWidth: 2
      }]
    },
    includePoints() {
      try {
        const polylinePoints = Array.isArray(this.routePolyline) ? this.routePolyline.filter(this.isValidPoint) : []
        const rawPoints = [
          this.currentLocation,
          this.startLocation,
          ...(Array.isArray(this.waypoints) ? this.waypoints : []),
          ...polylinePoints.slice(0, 1),
          ...polylinePoints.slice(-1)
        ]
        const validPoints = rawPoints
          .filter(point => point && typeof point === 'object' && this.isValidPoint(point))
          .map(point => ({ 
            latitude: Number(point.latitude), 
            longitude: Number(point.longitude) 
          }))
        if (process.env.UNI_PLATFORM === 'h5') {
          return this.toAmapH5BoundsPoints(validPoints)
        }
        return validPoints.length > 0 ? validPoints : []
      } catch (e) {
        return []
      }
    }
  },
  onLoad(options) {
    this.navigationSessionId = `route_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    if (options && options.latitude && options.longitude) {
      const targetLat = Number(options.latitude)
      const targetLng = Number(options.longitude)
      const targetName = options.entity_name || '目的地'
      
      this.navigationPlan = {
        route_name: `前往${targetName}`,
        start_location: DEFAULT_LOCATION,
        waypoints: [{
          id: 'target',
          name: targetName,
          latitude: targetLat,
          longitude: targetLng,
          order: 1
        }],
        total_distance: 0,
        travel_mode_label: '步行'
      }
      
      this.currentLocation = null
      this.fetchScenicEntrance().then(() => {
        this.fetchNavigationRoute()
      })
      return
    }
    
    const plan = uni.getStorageSync('activeRouteNavigation')
    this.navigationPlan = plan || null
    if (this.navigationPlan) {
      this.currentLocation = this.navigationPlan.start_location || null
      this.fetchScenicEntrance().then(() => {
        this.fetchNavigationRoute()
      })
    }
  },
  onShow() {
    this.isPageActive = true
  },
  onHide() {
    this.isPageActive = false
    this.showFeedbackModal = false
  },
  onUnload() {
    this.isPageActive = false
    this.stopRealtimeTracking()
    this.showFeedbackModal = false
  },
  methods: {
    isValidPoint(point) {
      const lat = Number(point?.latitude)
      const lon = Number(point?.longitude)
      return Number.isFinite(lat) && Number.isFinite(lon) && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180
    },
    toAmapH5BoundsPoints(points) {
      if (!Array.isArray(points) || !points.length) return []
      let minLat = points[0].latitude
      let maxLat = points[0].latitude
      let minLng = points[0].longitude
      let maxLng = points[0].longitude

      points.forEach(point => {
        minLat = Math.min(minLat, point.latitude)
        maxLat = Math.max(maxLat, point.latitude)
        minLng = Math.min(minLng, point.longitude)
        maxLng = Math.max(maxLng, point.longitude)
      })

      const padding = 0.0004
      if (minLat === maxLat) {
        minLat -= padding
        maxLat += padding
      }
      if (minLng === maxLng) {
        minLng -= padding
        maxLng += padding
      }

      return [
        { latitude: minLat, longitude: minLng },
        { latitude: maxLat, longitude: maxLng }
      ]
    },
    pointKey(point) {
      return String(point?.spot_id || point?.id || point?.order || `${point?.latitude},${point?.longitude}`)
    },
    normalizeWaypoint(spot, index) {
      return {
        id: spot.id || spot.spot_id || index + 1,
        spot_id: spot.spot_id || spot.id || null,
        name: spot.name || spot.spot_name || `第${index + 1}站`,
        latitude: Number(spot.latitude),
        longitude: Number(spot.longitude),
        location: spot.location || spot.address || '灵山胜境景区内',
        order: index + 1
      }
    },
    getRemainingWaypoints() {
      const source = (this.navigationData?.waypoints?.length ? this.navigationData.waypoints : this.navigationPlan?.waypoints) || []
      const validWaypoints = source.filter(this.isValidPoint)
      if (!validWaypoints.length) return []

      const targetKey = this.currentTargetPoint ? this.pointKey(this.currentTargetPoint) : ''
      let startIndex = validWaypoints.findIndex(spot => this.pointKey(spot) === targetKey)
      if (startIndex < 0 && this.activeSegment?.to) {
        const segmentTargetKey = this.pointKey(this.activeSegment.to)
        startIndex = validWaypoints.findIndex(spot => this.pointKey(spot) === segmentTargetKey)
      }
      if (startIndex < 0) {
        startIndex = Math.max(0, Number(this.activeStep?.segment_order || 1) - 1)
      }
      return validWaypoints.slice(startIndex).filter(spot => !this.isWaypointArrived(spot))
    },
    buildRequestPayload(options = {}) {
      const start = options.startPoint || this.currentLocation || this.navigationPlan.start_location || DEFAULT_LOCATION
      const sourceWaypoints = options.remainingOnly ? this.getRemainingWaypoints() : (this.navigationPlan.waypoints || [])
      return {
        user_id: uni.getStorageSync('userId') || 'guest',
        provider: 'amap',
        travel_mode: this.navigationPlan.travel_mode || 'walking',
        route_name: this.navigationPlan.route_name || '游览路线',
        start: {
          id: start.id || start.spot_id || null,
          name: start.name || '当前位置',
          latitude: Number(start.latitude),
          longitude: Number(start.longitude),
          location: start.location || start.address || ''
        },
        waypoints: sourceWaypoints.filter(this.isValidPoint).map(this.normalizeWaypoint)
      }
    },
    async fetchNavigationRoute(options = {}) {
      const payload = this.buildRequestPayload(options)
      if (!payload.waypoints.length) {
        this.completeNavigation()
        return
      }

      this.isLoading = true
      try {
        const result = await post('/routes/navigation', payload)
        this.navigationData = result
        this.activeStepIndex = 0
        this.navigationCompleted = false
        if (!options.keepArrived) this.arrivedWaypointKeys = []
        this.deviationCount = 0
      } catch (e) {
        this.navigationData = this.buildFallbackNavigation(options)
        uni.showToast({ title: '已使用本地路线兜底', icon: 'none' })
      } finally {
        this.isLoading = false
        if (!this.isTracking && !this.navigationCompleted) {
          this.startRealtimeTracking()
        }
      }
    },
    async fetchScenicEntrance() {
      try {
        const res = await get('/scenic/entrance')
        if (res && res.success && res.latitude && res.longitude) {
          DEFAULT_LOCATION.latitude = res.latitude
          DEFAULT_LOCATION.longitude = res.longitude
          DEFAULT_LOCATION.name = res.name || DEFAULT_LOCATION.name
        }
      } catch (e) {
        console.warn('[Navigation] 获取景区入口位置失败，使用默认位置')
      }
    },
    buildFallbackNavigation(options = {}) {
      const start = this.currentLocation || this.navigationPlan.start_location || DEFAULT_LOCATION
      const waypoints = (options.remainingOnly ? this.getRemainingWaypoints() : (this.navigationPlan.waypoints || [])).filter(this.isValidPoint)
      const normalizedWaypoints = waypoints.map(this.normalizeWaypoint)
      const polyline = [start, ...normalizedWaypoints].map(point => ({
        latitude: Number(point.latitude),
        longitude: Number(point.longitude)
      }))
      return {
        route_name: this.navigationPlan.route_name || '游览路线',
        provider_type: 'haversine_navigation',
        travel_mode_label: this.navigationPlan.travel_mode_label || '步行',
        start_location: start,
        waypoints: normalizedWaypoints,
        total_distance_m: this.navigationPlan.total_distance || 0,
        total_duration_sec: Number(this.navigationPlan.total_duration || 0) * 60,
        polyline,
        steps: normalizedWaypoints.map((spot, index) => ({
          instruction: `前往${spot.name || `第${index + 1}站`}`,
          distance_m: spot.distance_from_previous || 0,
          from_name: index === 0 ? (start.name || '当前位置') : normalizedWaypoints[index - 1]?.name,
          to_name: spot.name,
          segment_order: index + 1,
          polyline: [index === 0 ? start : normalizedWaypoints[index - 1], spot].filter(this.isValidPoint)
        })),
        segments: normalizedWaypoints.map((spot, index) => ({
          order: index + 1,
          from: index === 0 ? start : normalizedWaypoints[index - 1],
          to: spot
        }))
      }
    },
    startRealtimeTracking() {
      if (this.navigationCompleted) return
      this.clearTrackingTimers()
      this.isTracking = true
      this.trackingStatus = 'starting'
      this.locationChangeHandler = this.handleLocationChange

      if (process.env.UNI_PLATFORM === 'h5') {
        this.startPollingTracking()
        return
      }

      const canStream = typeof uni.startLocationUpdate === 'function' && typeof uni.onLocationChange === 'function'
      if (canStream) {
        uni.startLocationUpdate({
          type: 'gcj02',
          success: () => {
            uni.onLocationChange(this.locationChangeHandler)
            this.trackingStatus = 'streaming'
          },
          fail: () => {
            this.startPollingTracking()
          }
        })
        return
      }
      this.startPollingTracking()
    },
    startPollingTracking() {
      this.trackingStatus = 'polling'
      this.pullLocationOnce(false)
      this.trackingTimer = setInterval(() => {
        this.pullLocationOnce(true)
      }, 4000)
    },
    async pullLocationOnce(allowSimulation = true) {
      try {
        const location = await requestCurrentLocation({
          allowCache: false,
          allowFallback: false,
          highAccuracy: true
        })
        this.handleLocationChange(location)
      } catch (e) {
        if (allowSimulation && !this.simulationTimer) {
          this.startSimulationTracking()
        }
      }
    },
    startSimulationTracking() {
      const points = this.routePolyline.filter(this.isValidPoint)
      if (points.length < 2) return
      this.trackingStatus = 'simulating'
      this.simulationIndex = 0
      this.simulationTimer = setInterval(() => {
        if (!this.isTracking || this.navigationCompleted) {
          this.clearTrackingTimers()
          return
        }
        const point = points[Math.min(this.simulationIndex, points.length - 1)]
        this.handleLocationChange({
          ...point,
          accuracy: 8,
          provider: 'simulation',
          name: '模拟当前位置'
        })
        if (this.simulationIndex >= points.length - 1) {
          clearInterval(this.simulationTimer)
          this.simulationTimer = null
        } else {
          this.simulationIndex += 1
        }
      }, 1800)
    },
    stopRealtimeTracking() {
      this.isTracking = false
      if (!this.navigationCompleted) this.trackingStatus = 'paused'
      this.clearTrackingTimers()
      if (typeof uni.offLocationChange === 'function' && this.locationChangeHandler) {
        uni.offLocationChange(this.locationChangeHandler)
      }
      if (typeof uni.stopLocationUpdate === 'function') {
        uni.stopLocationUpdate({})
      }
      this.locationChangeHandler = null
    },
    clearTrackingTimers() {
      if (this.trackingTimer) {
        clearInterval(this.trackingTimer)
        this.trackingTimer = null
      }
      if (this.simulationTimer) {
        clearInterval(this.simulationTimer)
        this.simulationTimer = null
      }
    },
    toggleTracking() {
      if (this.isTracking) {
        this.stopRealtimeTracking()
      } else {
        this.startRealtimeTracking()
      }
    },
    handleLocationChange(rawLocation) {
      const location = this.normalizeTrackingLocation(rawLocation)
      if (!location || this.navigationCompleted) return

      const distanceToScenic = this.calcDistanceM(
        location.latitude,
        location.longitude,
        DEFAULT_LOCATION.latitude,
        DEFAULT_LOCATION.longitude
      )

      if (distanceToScenic > SCENIC_AREA_RADIUS_M) {
        this.currentLocation = {
          ...DEFAULT_LOCATION,
          source: 'scenic_entry',
          name: '灵山胜境游客中心',
          timestamp: Date.now()
        }

        if (!this.hasReordered) {
          this.hasReordered = true
          uni.showToast({
            title: '检测到您不在景区内，正在重新规划路线',
            icon: 'none',
            duration: 3000
          })
          this.fetchNavigationRoute({ 
            startPoint: this.currentLocation,
            remainingOnly: true,
            keepArrived: true
          })
        }
      } else {
        this.currentLocation = location
      }

      this.evaluateNavigationProgress(this.currentLocation)
    },
    normalizeTrackingLocation(source = {}) {
      const latitude = Number(source.latitude)
      const longitude = Number(source.longitude)
      if (!this.isValidPoint({ latitude, longitude })) return null
      return {
        latitude,
        longitude,
        accuracy: Number(source.accuracy || 0),
        provider: source.provider || 'gcj02',
        timestamp: Date.now(),
        name: source.name || '当前位置'
      }
    },
    evaluateNavigationProgress(location) {
      if (!this.activeStep || !this.currentTargetPoint) return
      const distance = this.calcDistanceM(
        location.latitude,
        location.longitude,
        this.currentTargetPoint.latitude,
        this.currentTargetPoint.longitude
      )
      const threshold = this.getArrivalThreshold(location, this.currentTargetPoint)
      if (distance <= threshold) {
        this.handleArriveCurrentTarget()
        return
      }
      this.evaluateDeviation(location)
    },
    getArrivalThreshold(location, target) {
      const isWaypoint = this.waypoints.some(spot => this.pointKey(spot) === this.pointKey(target))
      const base = isWaypoint ? ARRIVE_WAYPOINT_THRESHOLD_M : ARRIVE_STEP_THRESHOLD_M
      const accuracy = Number(location?.accuracy || 0)
      return Math.max(base, accuracy ? Math.min(60, accuracy * 1.5) : base)
    },
    handleArriveCurrentTarget() {
      const now = Date.now()
      if (now - this.lastAutoAdvanceAt < AUTO_ADVANCE_COOLDOWN_MS) return
      this.lastAutoAdvanceAt = now

      if (this.currentTargetPoint) {
        const matched = this.waypoints.find(spot => this.pointKey(spot) === this.pointKey(this.currentTargetPoint))
        if (matched) this.markWaypointArrived(matched)
      }

      if (this.activeStepIndex < this.steps.length - 1) {
        this.activeStepIndex += 1
        this.deviationCount = 0
        uni.showToast({ title: '已自动进入下一指引', icon: 'none' })
        return
      }
      this.completeNavigation()
    },
    /*
    completeNavigation() {
      if (this.navigationCompleted) return
      this.navigationCompleted = true
      this.trackingStatus = 'completed'
      this.isTracking = false
      this.clearTrackingTimers()
      setTimeout(() => this.maybePromptRouteFeedback(), 800)
      uni.showToast({ title: '已到达终点', icon: 'success' })
    },
    getRouteFeedbackKey() {
      const planId = this.navigationPlan?.route_id || this.navigationPlan?.id
      if (planId) return String(planId)
      const waypointKey = (this.waypoints || []).map(spot => this.pointKey(spot)).join('-')
      return `${this.routeName}:${waypointKey || this.navigationSessionId || 'default'}`
    },
    maybePromptRouteFeedback() {
      const targetKey = this.getRouteFeedbackKey()
      promptForFeedback({
        type: 'route',
        targetKey,
        title: '评价',
        content: '导航已经结束，愿意花几秒钟评价这条路线和导航指引吗？',
        params: {
          feedback_type: 'route',
          target_type: 'route',
          target_id: targetKey,
          target_name: this.routeName,
          source: 'route-navigation',
          session_id: this.navigationSessionId
        }
      })
    },
    */
    completeNavigation() {
      if (this.navigationCompleted) return
      this.navigationCompleted = true
      this.trackingStatus = 'completed'
      this.isTracking = false
      this.clearTrackingTimers()
      setTimeout(() => this.maybePromptRouteFeedback(), 800)
      uni.showToast({ title: 'Arrived', icon: 'success' })
    },
    getRouteFeedbackKey() {
      const planId = this.navigationPlan?.route_id || this.navigationPlan?.id
      if (planId) return String(planId)
      const waypointKey = (this.waypoints || []).map(spot => this.pointKey(spot)).join('-')
      return `${this.routeName}:${waypointKey || this.navigationSessionId || 'default'}`
    },
    async maybePromptRouteFeedback() {
      if (!this.isPageActive) return
      const targetKey = this.getRouteFeedbackKey()
      const result = await promptForFeedback({
        type: 'route',
        targetKey,
        title: '评价',
        content: '导航已经结束，愿意花几秒钟评价这条路线和导航指引吗？',
        params: {
          feedback_type: 'route',
          target_type: 'route',
          target_id: targetKey,
          target_name: this.routeName,
          source: 'route-navigation',
          session_id: this.navigationSessionId
        },
        useCustomModal: true
      })
      if (result && result.shouldShow) {
        this.feedbackModalConfig = {
          title: result.title,
          content: result.content,
          params: result.params,
          type: result.type,
          targetKey: result.targetKey
        }
        this.showFeedbackModal = true
      }
    },
    handleFeedbackLater() {
      if (this.feedbackModalConfig.type && this.feedbackModalConfig.targetKey) {
        markFeedbackPrompt(this.feedbackModalConfig.type, this.feedbackModalConfig.targetKey, 'dismissed')
      }
    },
    handleFeedbackSubmit() {
      if (this.feedbackModalConfig.params) {
        openFeedbackPage(this.feedbackModalConfig.params)
      }
    },
    markWaypointArrived(spot) {
      const key = this.pointKey(spot)
      if (!this.arrivedWaypointKeys.includes(key)) {
        this.arrivedWaypointKeys.push(key)
      }
    },
    isWaypointArrived(spot) {
      return this.arrivedWaypointKeys.includes(this.pointKey(spot))
    },
    evaluateDeviation(location) {
      const polyline = this.activeStep?.polyline || this.activeSegment?.polyline || this.routePolyline
      const distance = this.minDistanceToPolyline(location, polyline)
      const accuracy = Number(location?.accuracy || 0)
      const threshold = Math.max(DEVIATION_THRESHOLD_M, accuracy ? accuracy * 2 : 0)
      this.deviationCount = distance > threshold ? this.deviationCount + 1 : 0
      if (this.deviationCount >= 4) {
        this.autoReplanAfterDeviation()
      }
    },
    async autoReplanAfterDeviation() {
      const now = Date.now()
      if (this.isLoading || now - this.lastAutoReplanAt < AUTO_REPLAN_COOLDOWN_MS) return
      this.lastAutoReplanAt = now
      this.deviationCount = 0
      uni.showToast({ title: '检测到偏离路线，正在重算指引', icon: 'none' })
      await this.fetchNavigationRoute({ 
        remainingOnly: true, 
        keepArrived: true,
        startPoint: this.currentLocation
      })
    },
    goPreviousStep() {
      if (this.activeStepIndex > 0) this.activeStepIndex -= 1
    },
    goNextStep() {
      if (this.activeStepIndex < this.steps.length - 1) {
        this.activeStepIndex += 1
      }
    },
    openNextWaypoint() {
      const target = this.currentTargetPoint || this.waypoints[0]
      if (target) this.openSpotMap(target)
    },
    openSpotMap(spot) {
      if (!this.isValidPoint(spot)) {
        uni.showToast({ title: '暂无可导航位置', icon: 'none' })
        return
      }
      uni.openLocation({
        latitude: Number(spot.latitude),
        longitude: Number(spot.longitude),
        name: spot.name || '导航点',
        address: spot.location || '灵山胜境景区内'
      })
    },
    handleMarkerTap(event) {
      const markerId = Number(event.detail?.markerId)
      if (markerId >= 2) {
        const target = this.waypoints[markerId - 2]
        if (target) this.openSpotMap(target)
      }
    },
    calcDistanceM(lat1, lon1, lat2, lon2) {
      if (![lat1, lon1, lat2, lon2].every(value => Number.isFinite(Number(value)))) return Infinity
      const radius = 6371000
      const dlat = this.toRadians(Number(lat2) - Number(lat1))
      const dlon = this.toRadians(Number(lon2) - Number(lon1))
      const a = Math.sin(dlat / 2) ** 2 +
        Math.cos(this.toRadians(Number(lat1))) *
        Math.cos(this.toRadians(Number(lat2))) *
        Math.sin(dlon / 2) ** 2
      return Math.round(radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
    },
    toRadians(value) {
      return value * Math.PI / 180
    },
    minDistanceToPolyline(point, polyline = []) {
      const points = polyline.filter(this.isValidPoint)
      if (!this.isValidPoint(point) || points.length === 0) return 0
      if (points.length === 1) {
        return this.calcDistanceM(point.latitude, point.longitude, points[0].latitude, points[0].longitude)
      }
      let min = Infinity
      for (let index = 0; index < points.length - 1; index += 1) {
        min = Math.min(min, this.distanceToSegmentM(point, points[index], points[index + 1]))
      }
      return min === Infinity ? 0 : min
    },
    distanceToSegmentM(point, start, end) {
      const origin = point
      const p = this.projectPoint(point, origin)
      const a = this.projectPoint(start, origin)
      const b = this.projectPoint(end, origin)
      const dx = b.x - a.x
      const dy = b.y - a.y
      if (dx === 0 && dy === 0) return Math.sqrt((p.x - a.x) ** 2 + (p.y - a.y) ** 2)
      const t = Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy)))
      const x = a.x + t * dx
      const y = a.y + t * dy
      return Math.sqrt((p.x - x) ** 2 + (p.y - y) ** 2)
    },
    projectPoint(point, origin) {
      const lat = Number(point.latitude)
      const lon = Number(point.longitude)
      const originLat = Number(origin.latitude)
      const originLon = Number(origin.longitude)
      const metersPerLat = 111000
      const metersPerLon = 111000 * Math.cos(this.toRadians(originLat))
      return {
        x: (lon - originLon) * metersPerLon,
        y: (lat - originLat) * metersPerLat
      }
    },
    formatDistance(distance) {
      const value = Number(distance || 0)
      if (value < 1000) return `${Math.round(value)}米`
      return `${(value / 1000).toFixed(1)}公里`
    },
    formatDuration(seconds) {
      const minutes = Math.max(0, Math.ceil(Number(seconds || 0) / 60))
      if (minutes < 60) return `${minutes}分钟`
      const hour = Math.floor(minutes / 60)
      const rest = minutes % 60
      return rest ? `${hour}小时${rest}分钟` : `${hour}小时`
    },
    coordinateText(location) {
      if (!this.isValidPoint(location)) return '当前位置'
      return `${Number(location.latitude).toFixed(5)}，${Number(location.longitude).toFixed(5)}`
    }
  }
}
</script>

<style lang="scss" scoped>
.navigation-page {
  min-height: 100vh;
  padding-bottom: 40rpx;
  background: linear-gradient(180deg, #fdf8f0 0%, #f5efe3 100%);
  color: #37251a;
}

.map-section {
  position: relative;
  height: 52vh;
  min-height: 620rpx;
  overflow: hidden;
  background: #e9dfcf;
}

.map-view {
  width: 100%;
  height: 100%;
}

.map-status {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 24rpx;
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 20rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.96);
  box-shadow: 0 10rpx 28rpx rgba(55, 37, 26, 0.16);
}

.status-main {
  flex: 1;
  min-width: 0;
}

.status-title,
.status-desc,
.route-title,
.route-desc,
.metric-value,
.metric-label,
.step-instruction,
.step-meta,
.waypoint-name,
.waypoint-meta {
  display: block;
}

.status-title {
  color: #37251a;
  font-size: 30rpx;
  font-weight: 800;
}

.status-desc {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
  line-height: 1.35;
}

.status-pill,
.summary-badge {
  flex-shrink: 0;
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: #8c3228;
  color: #fff8e8;
  font-size: 22rpx;
  font-weight: 700;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12rpx;
  padding: 22rpx 24rpx 0;
}

.scenic-notice {
  margin: 20rpx 24rpx 0;
  padding: 18rpx 22rpx;
  border-left: 8rpx solid #8c3228;
  border-radius: 14rpx;
  background: #fff8e8;
  color: #8c3228;
  font-size: 24rpx;
  line-height: 1.45;
  box-shadow: 0 4rpx 18rpx rgba(55, 37, 26, 0.08);
}

.action-btn,
.step-btn {
  min-width: 0;
  height: 72rpx;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 16rpx;
  background: #fff8e8;
  color: #8c3228;
  font-size: 23rpx;
  font-weight: 700;
  box-shadow: 0 4rpx 18rpx rgba(55, 37, 26, 0.08);
}

.action-btn.primary,
.step-btn.primary {
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
}

.route-summary,
.step-card,
.waypoint-card,
.empty-state {
  margin: 22rpx 24rpx 0;
  padding: 24rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  box-shadow: 0 4rpx 20rpx rgba(55, 37, 26, 0.08);
}

.summary-head,
.section-head,
.step-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16rpx;
}

.route-title {
  font-size: 34rpx;
  font-weight: 850;
}

.route-desc {
  margin-top: 10rpx;
  color: #8b7355;
  font-size: 24rpx;
  line-height: 1.5;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14rpx;
  margin-top: 22rpx;
}

.metric-item {
  padding: 18rpx 12rpx;
  border-radius: 14rpx;
  background: #f3e3c4;
  text-align: center;
}

.metric-value {
  color: #8c3228;
  font-size: 29rpx;
  font-weight: 850;
}

.metric-label {
  margin-top: 6rpx;
  color: #8b7355;
  font-size: 21rpx;
}

.section-title {
  color: #37251a;
  font-size: 29rpx;
  font-weight: 800;
}

.section-note {
  color: #8b7355;
  font-size: 22rpx;
}

.step-instruction {
  margin-top: 18rpx;
  color: #37251a;
  font-size: 32rpx;
  font-weight: 850;
  line-height: 1.45;
}

.step-meta {
  margin-top: 10rpx;
  color: #8b7355;
  font-size: 24rpx;
}

.step-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 22rpx;
}

.step-btn[disabled] {
  opacity: 0.45;
}

.waypoint-list {
  padding-bottom: 20rpx;
}

.waypoint-list > .section-head {
  margin: 28rpx 24rpx 0;
}

.waypoint-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
}

.start-card {
  border: 2rpx solid rgba(140, 50, 40, 0.22);
}

.waypoint-index {
  width: 54rpx;
  height: 54rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  font-weight: bold;
}

.waypoint-index.arrived {
  background: linear-gradient(135deg, #2f7d55, #4c9b70);
}

.waypoint-main {
  flex: 1;
  min-width: 0;
}

.waypoint-name {
  color: #37251a;
  font-size: 29rpx;
  font-weight: bold;
}

.waypoint-meta {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
  line-height: 1.4;
}

.mini-btn {
  min-width: 82rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  font-size: 22rpx;
  background: #f3e3c4;
  color: #8c3228;
}

.empty-page {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  min-width: 360rpx;
  text-align: center;
  color: #8b7355;
  font-size: 26rpx;
}
</style>
