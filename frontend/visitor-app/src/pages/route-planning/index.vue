<template>
  <view class="route-page">
    <view class="top-bar">
      <view>
        <text class="page-title">路线规划</text>
        <text class="page-subtitle">偏好、时间、必去景点，一次生成可选路线</text>
      </view>
      <view class="top-actions">
        <view class="icon-btn" @click="openHistory">
          <image class="history-icon" src="/static/icons/history.png" mode="aspectFit"></image>
        </view>
      </view>
    </view>

    <view class="location-card" :class="statusClass">
      <view class="status-dot"></view>
      <view class="location-copy">
        <text class="location-title">{{ statusTitle }}</text>
        <text class="location-desc">{{ statusDescription }}</text>
      </view>
      <view class="location-actions">
        <view class="icon-btn-small" @click.stop="refreshLocation">
          <text class="icon-text">⟳</text>
        </view>
        <view class="icon-btn-small" @click.stop="openLocationSelector">
          <text class="icon-text">📍</text>
        </view>
      </view>
    </view>

    <view class="condition-panel">
      <view class="section-head">
        <text class="section-title">我想怎么玩</text>
        <text class="section-note">可多选</text>
      </view>
      <view class="chip-grid">
        <text
          class="preference-chip"
          :class="{ active: selectedPreferences.includes(item.value) }"
          v-for="item in preferences"
          :key="item.value"
          @click="togglePreference(item.value)"
        >
          {{ item.label }}
        </text>
      </view>
    </view>

    <view class="condition-panel">
      <view class="section-head">
        <text class="section-title">我有多少时间</text>
        <text class="section-note">用于控制选择的景点数</text>
      </view>
      <view class="time-row">
        <text
          class="time-chip"
          :class="{ active: activeDuration === item.value }"
          v-for="item in durationOptions"
          :key="item.value"
          @click="activeDuration = item.value"
        >
          {{ item.label }}
        </text>
      </view>
    </view>

    <view class="condition-panel">
      <view class="section-head">
        <text class="section-title">怎么游览</text>
        <text class="section-note">影响路程耗时估算</text>
      </view>
      <view class="time-row">
        <text
          class="time-chip travel-chip"
          :class="{ active: travelMode === item.value }"
          v-for="item in travelOptions"
          :key="item.value"
          @click="travelMode = item.value"
        >
          {{ item.label }}
        </text>
      </view>
    </view>

    <view class="condition-panel">
      <view class="section-head">
        <text class="section-title">我一定想去哪里</text>
        <text class="section-note">{{ selectedSpots.length ? `已选${selectedSpots.length}个` : '可不选' }}</text>
      </view>
      <view class="spot-grid">
        <view
          class="spot-option"
          :class="{ selected: isSpotSelected(spot) }"
          v-for="spot in allSpots"
          :key="spot.id || spot.spot_id || spot.spot_name"
          @click="toggleSpot(spot)"
        >
          <view class="check-dot">{{ isSpotSelected(spot) ? '✓' : '' }}</view>
          <view class="spot-copy">
            <text class="spot-name">{{ spot.spot_name || spot.name }}</text>
            <text class="spot-desc">{{ spot.location || spot.description || '灵山胜境景区内' }}</text>
          </view>
        </view>
      </view>
    </view>

    <button class="generate-btn" @click="generateRoutes">生成路线</button>

    <view class="result-section">
      <view class="section-head result-head">
        <text class="section-title">生成结果</text>
        <text class="section-note">{{ resultNote }}</text>
      </view>

      <view
        class="route-card"
        v-for="(route, index) in routeOptions"
        :key="route.route_id"
        @click="openRouteDetail(route)"
      >
        <view class="route-card-head">
          <view class="route-main">
            <text class="route-label">推荐 {{ index + 1 }}</text>
            <text class="route-name">{{ route.route_name }}</text>
            <text class="route-desc">{{ route.description }}</text>
          </view>
          <view class="route-badge" :class="{ warning: route.is_over_time }">
            <text>{{ route.total_duration }}min</text>
          </view>
        </view>
        <view class="route-stats">
          <text>{{ route.total_spots }}个景点</text>
          <text>{{ route.travel_mode_label || '步行' }}约{{ formatDistance(route.total_distance) }}</text>
          <text>行进{{ route.travel_duration || route.walk_duration || 0 }}分钟</text>
          <text>{{ route.is_over_time ? '可能超时' : '时间合适' }}</text>
        </view>
        <view class="route-preview">
          <text v-for="(spot, spotIndex) in route.route" :key="spot.id">
            {{ spotIndex + 1 }}.{{ spot.name }}
          </text>
        </view>
      </view>

      <view class="empty-state" v-if="routeOptions.length === 0">
        <text>选择条件后点击生成路线</text>
      </view>
    </view>

    <view class="history-mask" v-if="showHistory" @click="showHistory = false">
      <view class="history-panel" @click.stop>
        <view class="history-head">
          <text class="history-title">历史路线</text>
          <text class="history-close" @click="showHistory = false">×</text>
        </view>
        <view class="timeline">
          <view
            class="timeline-row"
            v-for="record in routeHistory"
            :key="record.id"
            @click="openRouteDetail(record.route, true)"
          >
            <view class="timeline-left">
              <view class="timeline-dot"></view>
              <view class="timeline-line"></view>
            </view>
            <view class="timeline-card">
              <text class="history-time">{{ formatTime(record.created_at) }}</text>
              <text class="history-route">{{ record.route_name }}</text>
              <text class="history-meta">{{ record.spot_count }}个景点｜{{ record.total_duration }}分钟｜{{ formatDistance(record.total_distance) }}</text>
            </view>
          </view>
          <view class="empty-state" v-if="routeHistory.length === 0">
            <text>暂无历史路线</text>
          </view>
        </view>
      </view>
    </view>

    <view class="location-mask" v-if="showLocationSelector" @click="showLocationSelector = false">
      <view class="location-panel" @click.stop>
        <view class="location-head">
          <text class="location-title-text">选择当前所在景点</text>
          <text class="location-close" @click="showLocationSelector = false">×</text>
        </view>
        <view class="location-list">
          <view
            class="location-item"
            :class="{ active: isLocationActive(spot) }"
            v-for="spot in allSpots"
            :key="spot.id"
            @click="selectLocation(spot)"
          >
            <view class="location-check">{{ isLocationActive(spot) ? '✓' : '' }}</view>
            <view class="location-info">
              <text class="location-name">{{ spot.spot_name || spot.name }}</text>
            </view>
          </view>
          <view class="empty-state" v-if="allSpots.length === 0">
            <text>暂无可选景点</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { get, post } from '@/utils/request'
import { formatLocationText, getLocationErrorMessage, requestCurrentLocation } from '@/utils/location'

const fallbackSpots = [
  { id: 1, spot_name: '灵山大照壁', description: '进入灵山胜境后的第一处标志性打卡点。', location: '景区入口' },
  { id: 2, spot_name: '五智门', description: '通向核心礼佛区域的重要门楼。', location: '菩提大道前段' },
  { id: 3, spot_name: '九龙灌浴', description: '经典动态演出场景，适合家庭游客。', location: '景区中轴' },
  { id: 4, spot_name: '灵山大佛', description: '太湖之滨的地标佛像，适合祈福与远眺。', location: '大佛广场' },
  { id: 5, spot_name: '灵山梵宫', description: '佛教艺术殿堂，建筑、壁画与演出皆值得停留。', location: '梵宫片区' },
  { id: 6, spot_name: '五印坛城', description: '藏传佛教文化空间，色彩浓烈，适合拍照打卡。', location: '梵宫东侧' }
]

export default {
  data() {
    return {
      locationStatus: 'idle',
      locationMessage: '',
      userLocation: null,
      allSpots: [],
      routeOptions: [],
      selectedPreferences: [],
      selectedSpots: [],
      activeDuration: 90,
      travelMode: 'walking',
      showHistory: false,
      routeHistory: [],
      showLocationSelector: false,
      preferences: [
        { label: '历史文化', value: 'history' },
        { label: '风景拍照', value: 'scenery' },
        { label: '亲子轻松', value: 'family' },
        { label: '建筑艺术', value: 'architecture' },
        { label: '礼佛祈福', value: 'blessing' }
      ],
      durationOptions: [
        { label: '1h', value: 60 },
        { label: '2h', value: 120 },
        { label: '3h', value: 180 },
        { label: '4h+', value: 240 }
      ],
      travelOptions: [
        { label: '步行', value: 'walking' },
        { label: '观光车', value: 'sightseeing_bus' },
        { label: '无障碍慢行', value: 'accessible' }
      ]
    }
  },
  computed: {
    statusClass() {
      return `status-${this.locationStatus}`
    },
    statusTitle() {
      if (this.locationStatus === 'idle') return '尚未定位'
      if (this.locationStatus === 'loading') return '正在获取当前位置'
      if (this.locationStatus === 'success') return '已获取生成起点'
      return '定位暂不可用'
    },
    statusDescription() {
      if (this.locationStatus === 'idle') return '点击手动定位后，会以真实当前位置作为路线起点。'
      if (this.locationStatus === 'loading') return '路线生成会以定位成功时的位置作为起点。'
      if (this.locationStatus === 'success') return `${this.locationMessage}`
      return this.locationMessage || '可继续生成路线，或稍后手动定位后重新规划。'
    },
    resultNote() {
      if (!this.routeOptions.length) return '最多生成3条'
      return `已生成${this.routeOptions.length}条`
    }
  },
  onLoad() {
    this.loadAllSpots()
  },
  methods: {
    userId() {
      const value = uni.getStorageSync('userId')
      return value === null || value === undefined || value === '' ? 'guest' : String(value)
    },
    async loadAllSpots() {
      try {
        const list = await get('/spots')
        this.allSpots = Array.isArray(list) && list.length ? list : fallbackSpots
      } catch (e) {
        this.allSpots = fallbackSpots
      }
    },
    async refreshLocation() {
      this.locationStatus = 'loading'
      this.userLocation = null
      try {
        const location = await requestCurrentLocation({ allowCache: true, allowFallback: true })
        this.userLocation = {
          latitude: location.latitude,
          longitude: location.longitude,
          name: location.name || '',
          spot_id: null,
          source: location.isFallback ? 'fallback' : 'current'
        }
        this.locationStatus = 'success'
        this.locationMessage = formatLocationText(location)
      } catch (error) {
        this.locationStatus = 'failed'
        this.locationMessage = getLocationErrorMessage(error)
      }
    },
    togglePreference(value) {
      const index = this.selectedPreferences.indexOf(value)
      if (index > -1) {
        this.selectedPreferences.splice(index, 1)
      } else {
        this.selectedPreferences.push(value)
      }
    },
    resolveSpotId(spot) {
      const rawId = spot?.id ?? spot?.spot_id
      const intId = Number.parseInt(rawId, 10)
      return Number.isFinite(intId) && intId > 0 ? intId : null
    },
    isSpotSelected(spot) {
      const id = this.resolveSpotId(spot)
      return id ? this.selectedSpots.includes(id) : false
    },
    toggleSpot(spot) {
      const intId = this.resolveSpotId(spot)
      if (!intId) return
      const index = this.selectedSpots.indexOf(intId)
      if (index > -1) {
        this.selectedSpots.splice(index, 1)
      } else {
        this.selectedSpots.push(intId)
      }
    },
    async generateRoutes() {
      uni.showLoading({ title: '生成路线中...' })
      try {
        const mustSpotIds = this.selectedSpots
          .map(item => Number.parseInt(item, 10))
          .filter(item => Number.isFinite(item) && item > 0)
        const startSpotId = Number.parseInt(this.userLocation?.spot_id, 10)
        const payload = {
          user_id: String(this.userId()),
          preferences: this.selectedPreferences,
          duration_minutes: this.activeDuration,
          travel_mode: this.travelMode,
          must_spot_ids: mustSpotIds,
          start_spot_id: Number.isFinite(startSpotId) && startSpotId > 0 ? startSpotId : null,
          latitude: Number.isFinite(Number(this.userLocation?.latitude)) ? Number(this.userLocation.latitude) : null,
          longitude: Number.isFinite(Number(this.userLocation?.longitude)) ? Number(this.userLocation.longitude) : null
        }
        console.info('[route-planning] generateRoutes payload', payload)
        const res = await post('/routes/generate', payload, { timeout: 180000 })
        this.routeOptions = res.routes || []
        if (!this.routeOptions.length) {
          uni.showToast({ title: '暂无可用路线', icon: 'none' })
        }
      } catch (e) {
        console.error('[route-planning] generateRoutes failed', e, e?.data || e?.response?.data)
        uni.showToast({ title: '路线生成失败', icon: 'none' })
      } finally {
        uni.hideLoading()
      }
    },
    async openHistory() {
      this.showHistory = true
      try {
        const userId = encodeURIComponent(String(this.userId()))
        this.routeHistory = await get(`/routes/history?user_id=${userId}&limit=20`)
      } catch (e) {
        console.warn('[route-planning] history load failed', e)
        this.routeHistory = []
      }
    },
    openLocationSelector() {
      if (!this.allSpots.length) {
        this.loadAllSpots()
      }
      this.showLocationSelector = true
    },
    openRouteDetail(route, fromHistory = false) {
      const startLocation = fromHistory ? route.start_location : (this.userLocation || route.start_location || null)
      uni.setStorageSync('activeRoutePlan', {
        ...route,
        start_location: startLocation,
        __from_history: fromHistory
      })
      uni.navigateTo({ url: '/pages/route-detail/index' })
    },
    formatDistance(distance) {
      const value = Number(distance || 0)
      if (value < 1000) return `${value}米`
      return `${(value / 1000).toFixed(1)}公里`
    },
    formatTime(value) {
      if (!value) return '刚刚'
      const date = new Date(value)
      const pad = num => String(num).padStart(2, '0')
      return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
    },
    formatCoordinate(value) {
      return Number(value || 0).toFixed(5)
    },
    selectLocation(location) {
      const latitude = Number(location.latitude)
      const longitude = Number(location.longitude)
      const name = location.spot_name || location.name || '景区景点'
      const spotId = this.resolveSpotId(location)
      if (!latitude || !longitude) {
        uni.showToast({ title: '该景点暂无定位坐标', icon: 'none' })
        return
      }
      this.userLocation = {
        latitude,
        longitude,
        name,
        spot_id: spotId,
        source: 'manual'
      }
      this.locationStatus = 'success'
      this.locationMessage = `${name}`
      this.showLocationSelector = false
    },
    isLocationActive(location) {
      if (!this.userLocation || !location) return false
      return Math.abs(this.userLocation.latitude - Number(location.latitude)) < 0.00001 &&
             Math.abs(this.userLocation.longitude - Number(location.longitude)) < 0.00001
    }
  }
}
</script>

<style lang="scss" scoped>
.route-page {
  min-height: 100vh;
  padding-bottom: 48rpx;
  background: linear-gradient(180deg, #fdf8f0 0%, #f5efe3 100%);
  color: #37251a;
}

.top-bar,
.top-actions,
.location-card,
.section-head,
.route-card-head,
.route-stats,
.history-head,
.timeline-row,
.location-head,
.location-item {
  display: flex;
  align-items: center;
}

.top-bar {
  justify-content: space-between;
  gap: 20rpx;
  padding: 56rpx 30rpx 44rpx;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
}

.top-actions {
  gap: 14rpx;
}

.page-title,
.page-subtitle,
.location-title,
.location-desc,
.section-title,
.section-note,
.spot-name,
.spot-desc,
.route-label,
.route-name,
.route-desc,
.history-title,
.history-time,
.history-route,
.history-meta,
.location-name,
.location-coord {
  display: block;
}

.page-title {
  color: #fff8e8;
  font-size: 44rpx;
  font-weight: 900;
}

.page-subtitle {
  margin-top: 8rpx;
  color: rgba(255, 248, 232, 0.8);
  font-size: 24rpx;
}

.icon-btn {
  width: 68rpx;
  height: 68rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 248, 232, 0.18);
  color: #fff8e8;
  font-size: 25rpx;
  font-weight: bold;
}

.history-icon {
  width: 32rpx;
  height: 32rpx;
  display: block;
}

.icon-btn.loading {
  opacity: 0.7;
}

.location-card,
.condition-panel,
.route-card,
.history-panel,
.timeline-card,
.location-panel {
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  box-shadow: 0 4rpx 20rpx rgba(55, 37, 26, 0.08);
}

.location-card {
  gap: 18rpx;
  margin: -28rpx 30rpx 24rpx;
  padding: 24rpx;
}

.status-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  background: #f2ca70;
}

.status-success .status-dot {
  background: #52c41a;
}

.status-failed .status-dot {
  background: #ff4d4f;
}

.location-copy {
  flex: 1;
  min-width: 0;
}

.location-title {
  color: #37251a;
  font-size: 28rpx;
  font-weight: bold;
}

.location-desc {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
  line-height: 1.45;
}

.location-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.icon-btn-small {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f3e3c4;
  color: #8c3228;
}

.icon-text {
  font-size: 28rpx;
  line-height: 1;
}

.condition-panel {
  margin: 0 30rpx 20rpx;
  padding: 22rpx;
}

.section-head {
  justify-content: space-between;
  gap: 16rpx;
  margin-bottom: 16rpx;
}

.section-title {
  color: #37251a;
  font-size: 28rpx;
  font-weight: bold;
}

.section-note {
  color: #8b7355;
  font-size: 22rpx;
}

.chip-grid,
.time-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.preference-chip,
.time-chip {
  min-height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 22rpx;
  border-radius: 999rpx;
  background: #f3e3c4;
  color: #6d4b2d;
  font-size: 24rpx;
  line-height: 1.25;
  white-space: nowrap;
}

.preference-chip.active {
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  font-weight: bold;
}

.time-chip.active {
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  font-weight: bold;
}

.spot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.spot-option {
  min-height: 128rpx;
  display: flex;
  align-items: flex-start;
  padding: 18rpx;
  border: 2rpx solid transparent;
  border-radius: 12rpx;
  background: #efe0bd;
}

.spot-option.selected {
  border-color: #8c3228;
  background: #f3e3c4;
}

.check-dot {
  width: 38rpx;
  height: 38rpx;
  min-width: 38rpx;
  margin-right: 14rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #d4b483;
  border-radius: 50%;
  color: #8c3228;
  font-size: 24rpx;
  font-weight: bold;
}

.spot-copy {
  flex: 1;
  min-width: 0;
}

.spot-name {
  color: #37251a;
  font-size: 26rpx;
  font-weight: bold;
}

.spot-desc {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 22rpx;
  line-height: 1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.generate-btn {
  margin: 26rpx 30rpx;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  border-radius: 999rpx;
  font-size: 30rpx;
  font-weight: bold;
}

.result-section {
  margin: 8rpx 30rpx 0;
}

.route-card {
  margin-bottom: 20rpx;
  padding: 26rpx;
}

.route-card-head {
  justify-content: space-between;
  gap: 18rpx;
}

.route-main {
  flex: 1;
  min-width: 0;
}

.route-label {
  color: #8c3228;
  font-size: 22rpx;
  font-weight: bold;
}

.route-name {
  margin-top: 6rpx;
  color: #37251a;
  font-size: 30rpx;
  font-weight: bold;
}

.route-desc {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
  line-height: 1.45;
}

.route-badge {
  width: 104rpx;
  height: 104rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f3e3c4;
  color: #8c3228;
  font-size: 22rpx;
  font-weight: bold;
}

.route-badge.warning {
  background: #fff3e0;
  color: #ff9800;
}

.route-stats {
  gap: 12rpx;
  flex-wrap: wrap;
  margin-top: 18rpx;
}

.route-stats text {
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: #f3e3c4;
  color: #6d4b2d;
  font-size: 22rpx;
}

.route-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
  margin-top: 18rpx;
}

.route-preview text {
  color: #8b7355;
  font-size: 23rpx;
}

.empty-state {
  padding: 70rpx 20rpx;
  text-align: center;
  color: #8b7355;
  font-size: 26rpx;
}

.history-mask,
.location-mask {
  position: fixed;
  inset: 0;
  z-index: 99;
  display: flex;
  align-items: flex-end;
  background: rgba(0, 0, 0, 0.42);
}

.history-panel,
.location-panel {
  width: 100%;
  max-height: 76vh;
  padding: 28rpx;
  border-radius: 22rpx 22rpx 0 0;
  overflow-y: auto;
}

.history-head,
.location-head {
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.history-title,
.location-title-text {
  color: #37251a;
  font-size: 34rpx;
  font-weight: bold;
}

.history-close,
.location-close {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f3e3c4;
  color: #8c3228;
  font-size: 38rpx;
}

.timeline-row {
  align-items: stretch;
}

.timeline-left {
  width: 52rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.timeline-dot {
  width: 18rpx;
  height: 18rpx;
  margin-top: 28rpx;
  border-radius: 50%;
  background: #8c3228;
}

.timeline-line {
  flex: 1;
  width: 3rpx;
  background: rgba(140, 50, 40, 0.18);
}

.timeline-card {
  flex: 1;
  margin-bottom: 18rpx;
  padding: 22rpx;
}

.history-time {
  color: #8c3228;
  font-size: 22rpx;
}

.history-route {
  margin-top: 8rpx;
  color: #37251a;
  font-size: 28rpx;
  font-weight: bold;
}

.history-meta {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 23rpx;
}

.location-list {
  max-height: 60vh;
  overflow-y: auto;
}

.location-item {
  padding: 22rpx;
  margin-bottom: 16rpx;
  border-radius: 12rpx;
  background: #f3e3c4;
  transition: all 0.2s ease;
}

.location-item.active {
  background: #efe0bd;
  border: 2rpx solid #8c3228;
}

.location-check {
  width: 38rpx;
  height: 38rpx;
  min-width: 38rpx;
  margin-right: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2rpx solid #d4b483;
  border-radius: 50%;
  color: #8c3228;
  font-size: 24rpx;
  font-weight: bold;
}

.location-item.active .location-check {
  background: #8c3228;
  border-color: #8c3228;
  color: #fff8e8;
}

.location-info {
  flex: 1;
  min-width: 0;
}

.location-name {
  color: #37251a;
  font-size: 28rpx;
  font-weight: bold;
}

.location-coord {
  margin-top: 8rpx;
  color: #8b7355;
  font-size: 22rpx;
}
</style>
