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
        show-location
        @markertap="handleMarkerTap"
      />

      <view class="map-status">
        <view class="status-main">
          <text class="status-title">{{ currentInstruction }}</text>
          <text class="status-desc">{{ providerText }} · {{ formatDistance(totalDistance) }} · {{ formatDuration(totalDurationSec) }}</text>
        </view>
        <view class="status-pill">{{ navigationData?.travel_mode_label || navigationPlan.travel_mode_label || '步行' }}</view>
      </view>
    </view>

    <view class="quick-actions">
      <button class="action-btn primary" :loading="isLoading" @click="replanFromCurrent">重新定位规划</button>
      <button class="action-btn" @click="openNextWaypoint">打开系统地图</button>
      <button class="action-btn" @click="exitNavigation">退出</button>
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

    <view class="step-card" v-if="activeStep">
      <view class="step-head">
        <text class="section-title">当前指引</text>
        <text class="section-note">{{ activeStepIndex + 1 }} / {{ steps.length }}</text>
      </view>
      <text class="step-instruction">{{ activeStep.instruction }}</text>
      <text class="step-meta">
        {{ activeStep.from_name || startName }} 到 {{ activeStep.to_name || nextWaypointName }}，约{{ formatDistance(activeStep.distance_m) }}
      </text>
      <view class="step-actions">
        <button class="step-btn" :disabled="activeStepIndex <= 0" @click="activeStepIndex -= 1">上一步</button>
        <button class="step-btn primary" :disabled="activeStepIndex >= steps.length - 1" @click="activeStepIndex += 1">下一步</button>
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
        <text class="waypoint-index">{{ spot.order }}</text>
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
  </view>
</template>

<script>
import { post } from '@/utils/request'
import { requestCurrentLocation } from '@/utils/location'
import startIcon from '@/static/map/起点.png'
import waypointIcon from '@/static/map/途经点.png'

const DEFAULT_LOCATION = {
  latitude: 31.43039,
  longitude: 120.09658,
  name: '灵山胜境游客中心'
}

export default {
  data() {
    return {
      navigationPlan: null,
      navigationData: null,
      currentLocation: null,
      activeStepIndex: 0,
      isLoading: false
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
    activeStep() {
      return this.steps[this.activeStepIndex] || this.steps[0] || null
    },
    currentInstruction() {
      if (this.isLoading) return '正在生成高德导航路线'
      return this.activeStep?.instruction || '按地图路线前往下一站'
    },
    nextWaypointName() {
      return this.waypoints[0]?.name || '下一站'
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
    routePolyline() {
      const polyline = this.navigationData?.polyline || []
      if (polyline.length) return polyline
      return [this.startLocation, ...this.waypoints].filter(this.isValidPoint)
    },
    mapCenter() {
      return this.currentLocation || this.startLocation || this.routePolyline[0] || DEFAULT_LOCATION
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
          label: {
            content: '起',
            color: '#ffffff',
            fontSize: 12,
            bgColor: '#8c3228',
            borderRadius: 14,
            padding: 5
          },
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
        markers.push({
          id: index + 2,
          latitude: Number(spot.latitude),
          longitude: Number(spot.longitude),
          title: spot.name,
          width: 26,
          height: 26,
          iconPath: waypointIcon,
          label: {
            content: String(spot.order || index + 1),
            color: '#8c3228',
            fontSize: 12,
            bgColor: '#fff8e8',
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
      const points = [
        this.currentLocation,
        this.startLocation,
        ...this.waypoints,
        this.routePolyline[0],
        this.routePolyline[this.routePolyline.length - 1]
      ]
      return points
        .filter(this.isValidPoint)
        .map(point => ({ latitude: Number(point.latitude), longitude: Number(point.longitude) }))
    }
  },
  onLoad() {
    const plan = uni.getStorageSync('activeRouteNavigation')
    
    this.navigationPlan = plan || null
    
    if (this.navigationPlan) {
      this.currentLocation = this.navigationPlan.start_location || null
      this.fetchNavigationRoute()
    }
  },
  methods: {
    isValidPoint(point) {
      const lat = Number(point?.latitude)
      const lon = Number(point?.longitude)
      return lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180
    },
    buildRequestPayload() {
      const start = this.currentLocation || this.navigationPlan.start_location || DEFAULT_LOCATION
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
        waypoints: (this.navigationPlan.waypoints || []).filter(this.isValidPoint).map((spot, index) => ({
          id: spot.id || spot.spot_id || index + 1,
          spot_id: spot.spot_id || spot.id || null,
          name: spot.name || spot.spot_name || `第${index + 1}站`,
          latitude: Number(spot.latitude),
          longitude: Number(spot.longitude),
          location: spot.location || spot.address || '灵山胜境景区内',
          order: spot.order || index + 1
        }))
      }
    },
    async fetchNavigationRoute() {
      if (!this.navigationPlan?.waypoints?.length) return
      this.isLoading = true
      try {
        const result = await post('/routes/navigation', this.buildRequestPayload())
        this.navigationData = result
        this.activeStepIndex = 0
      } catch (e) {
        this.navigationData = this.buildFallbackNavigation()
        uni.showToast({ title: '已使用本地路线兜底', icon: 'none' })
      } finally {
        this.isLoading = false
      }
    },
    buildFallbackNavigation() {
      const start = this.currentLocation || this.navigationPlan.start_location || DEFAULT_LOCATION
      const waypoints = (this.navigationPlan.waypoints || []).filter(this.isValidPoint)
      const polyline = [start, ...waypoints].map(point => ({
        latitude: Number(point.latitude),
        longitude: Number(point.longitude)
      }))
      return {
        route_name: this.navigationPlan.route_name || '游览路线',
        provider_type: 'haversine_navigation',
        travel_mode_label: this.navigationPlan.travel_mode_label || '步行',
        start_location: start,
        waypoints,
        total_distance_m: this.navigationPlan.total_distance || 0,
        total_duration_sec: Number(this.navigationPlan.total_duration || 0) * 60,
        polyline,
        steps: waypoints.map((spot, index) => ({
          instruction: `前往${spot.name || `第${index + 1}站`}`,
          distance_m: spot.distance_from_previous || 0,
          from_name: index === 0 ? (start.name || '当前位置') : waypoints[index - 1]?.name,
          to_name: spot.name
        }))
      }
    },
    async replanFromCurrent() {
      this.isLoading = true
      try {
        const location = await requestCurrentLocation({ allowCache: true, allowFallback: true })
        this.currentLocation = {
          ...location,
          name: location.isFallback ? '默认起点' : '当前位置'
        }
        await this.fetchNavigationRoute()
      } catch (e) {
        uni.showToast({ title: '定位失败，仍使用原起点', icon: 'none' })
      } finally {
        this.isLoading = false
      }
    },
    openNextWaypoint() {
      const target = this.waypoints[0]
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
    exitNavigation() {
      uni.navigateBack()
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
  display: flex;
  gap: 14rpx;
  padding: 22rpx 24rpx 0;
}

.action-btn,
.step-btn {
  flex: 1;
  height: 72rpx;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 16rpx;
  background: #fff8e8;
  color: #8c3228;
  font-size: 24rpx;
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
