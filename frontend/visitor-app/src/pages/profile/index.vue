<template>
  <view class="profile-page">
    <view class="profile-hero">
      <view class="avatar-ring">
        <text class="avatar-text">{{ nickname.slice(0, 1) }}</text>
      </view>
      <view class="hero-info">
        <input class="name-input" v-model="nickname" @blur="saveProfile" />
        <input class="sign-input" v-model="signature" @blur="saveProfile" />
        <text class="user-id">ID {{ shortUserId }}</text>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的游览偏好</text>
        <text class="section-sub">基于游览行为分析</text>
      </view>
      <view
        class="preference-chart-wrap"
        v-if="preferenceChartItems.length"
        @tap="handlePreferenceChartTap"
        @click="handlePreferenceChartTap"
        @touchstart="handlePreferenceChartTap"
        @mousedown="handlePreferenceChartTap"
      >
        <canvas
          class="preference-canvas"
          canvas-id="preferenceChart"
          id="preferenceChart"
          :width="preferenceChartSize"
          :height="preferenceChartSize"
          @tap="handlePreferenceChartTap"
          @touchstart="handlePreferenceChartTap"
          @touchend="handlePreferenceChartTap"
        ></canvas>
        <view class="preference-center">
          <text class="preference-center-label">{{ activePreferenceItem.label }}</text>
          <text class="preference-center-value">{{ activePreferenceItem.percent }}%</text>
        </view>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的游览足迹</text>
        <text class="section-sub">{{ footprints.length }} 个景点</text>
      </view>
      <view id="footprintMap" class="footprint-map" v-if="footprints.length > 0">
        <view
          v-for="(segment, index) in footprintSegments"
          :key="'line-' + index"
          class="map-line-segment"
          :style="segment.style"
        ></view>
        <view
          v-for="(item, index) in footprints"
          :key="'dot-' + item.spot_name"
          class="map-dot"
          :class="{ start: index === 0, end: index === footprints.length - 1 }"
          :style="{ left: item.svgX + '%', top: item.svgY + '%' }"
        ></view>
        <view
          v-for="(item, index) in footprints"
          :key="'label-' + item.spot_name"
          class="map-pin"
          :style="{ left: item.svgX + '%', top: item.svgY + '%' }"
          @click="goToGuide(item.spot_id)"
        >
          <text class="pin-name">{{ item.spot_name }}</text>
        </view>
      </view>
      <view class="empty-footprint" v-else>
        <text class="empty-icon">👣</text>
        <text class="empty-text">暂无游览记录</text>
        <text class="empty-hint">使用导航前往景点后将记录足迹</text>
      </view>
    </view>

    <view class="section-card">
      <view class="menu-row" @click="goToFeedback">
        <text class="menu-title">评价与反馈</text>
        <text class="menu-arrow">></text>
      </view>
      <view class="menu-row" @click="contactService">
        <text class="menu-title">联系景区人工客服</text>
        <text class="menu-arrow">></text>
      </view>
      <view class="menu-row danger" @click="logout">
        <text class="menu-title">退出登录</text>
        <text class="menu-arrow">></text>
      </view>
    </view>

    <text class="version">灵山胜境 AI导览 v1.0.0</text>

    <FeedbackModal 
      ref="feedbackModal" 
      @submit="handleFeedbackSubmit"
    />
  </view>
</template>

<script>
import { get } from '@/utils/request'
import { promptForFeedback } from '@/utils/feedback'
import FeedbackModal from '@/components/FeedbackModal'

export default {
  components: {
    FeedbackModal
  },
  data() {
    return {
      userId: '',
      nickname: '灵山游客',
      signature: '愿今日山水有好风',
      userProfile: {},
      activePreferenceKey: '',
      lastPreferenceTapAt: 0,
      preferenceChartSize: 160,
      preferenceChartRect: null,
      footprints: [],
      footprintMapRect: null,
      isPageActive: true
    }
  },
  computed: {
    shortUserId() {
      return this.userId ? String(this.userId).slice(-8) : 'guest'
    },
    footprintSegments() {
      return this.footprints.slice(1).map((item, index) => {
        const previous = this.footprints[index]
        const width = this.footprintMapRect?.width || 0
        const height = this.footprintMapRect?.height || 0
        if (!width || !height) return null
        const x1 = previous.svgX / 100 * width
        const y1 = previous.svgY / 100 * height
        const x2 = item.svgX / 100 * width
        const y2 = item.svgY / 100 * height
        const dx = x2 - x1
        const dy = y2 - y1
        const length = Math.sqrt(dx * dx + dy * dy)
        const angle = Math.atan2(dy, dx) * 180 / Math.PI
        return {
          style: {
            left: x1 + 'px',
            top: y1 + 'px',
            width: length + 'px',
            transform: `rotate(${angle}deg)`
          }
        }
      }).filter(Boolean)
    },
    preferenceChartItems() {
      const entries = Object.entries(this.userProfile || {})
        .map(([key, value]) => ({
          key,
          label: this.getTagLabel(key),
          rawValue: Math.max(0, Number(value) || 0),
          color: this.getTagColor(key)
        }))
        .filter(item => item.rawValue > 0)
        .sort((a, b) => b.rawValue - a.rawValue)
      const total = entries.reduce((sum, item) => sum + item.rawValue, 0)
      if (!total) return []
      let cursor = -Math.PI / 2
      return entries.map(item => {
        const percentValue = item.rawValue / total
        const startAngle = cursor
        const endAngle = cursor + percentValue * Math.PI * 2
        cursor = endAngle
        return {
          ...item,
          percent: Math.round(percentValue * 100),
          startAngle,
          endAngle,
          midAngle: (startAngle + endAngle) / 2
        }
      })
    },
    activePreferenceItem() {
      return this.preferenceChartItems.find(item => item.key === this.activePreferenceKey) ||
        this.preferenceChartItems[0] ||
        { label: '暂无偏好', percent: 0 }
    }
  },
  onLoad() {
    this.syncPreferenceChartSize()
    this.userId = String(uni.getStorageSync('userId') || 'guest')
    const saved = uni.getStorageSync('visitorProfile')
    if (saved) {
      this.nickname = saved.nickname || this.nickname
      this.signature = saved.signature || this.signature
    }
    this.loadUserProfile()
    this.loadFootprints()
  },
  onReady() {
    this.syncPreferenceChartSize()
    this.measurePreferenceChart()
    this.measureFootprintMap()
    this.$nextTick(() => this.drawPreferenceChart())
  },
  methods: {
    rpxToPx(rpx) {
      const info = uni.getSystemInfoSync()
      return (Number(rpx) || 0) * info.windowWidth / 750
    },
    syncPreferenceChartSize() {
      const info = uni.getSystemInfoSync()
      this.preferenceChartSize = this.rpxToPx(info.windowWidth <= 380 ? 280 : 320)
    },
    measurePreferenceChart() {
      const query = uni.createSelectorQuery().in(this)
      query.select('#preferenceChart').boundingClientRect(rect => {
        this.preferenceChartRect = rect || null
      }).exec()
    },
    measureFootprintMap() {
      const query = uni.createSelectorQuery().in(this)
      query.select('#footprintMap').boundingClientRect(rect => {
        this.footprintMapRect = rect || null
      }).exec()
    },
    async loadUserProfile() {
      try {
        const res = await get('/recommendation', { user_id: this.userId })
        this.userProfile = res.user_profile || {}
      } catch (e) {
        this.userProfile = {
          'zen_culture': 0.75,
          'architecture_art': 0.62,
          'buddha_history': 0.45,
          'lake_scenery': 0.38
        }
      }
      this.ensureActivePreference()
      this.$nextTick(() => this.drawPreferenceChart())
    },
    ensureActivePreference() {
      const items = this.preferenceChartItems
      if (!items.length) {
        this.activePreferenceKey = ''
        return
      }
      if (!items.some(item => item.key === this.activePreferenceKey)) {
        this.activePreferenceKey = items[0].key
      }
    },
    selectPreferenceSlice(key) {
      const previousKey = this.activePreferenceKey
      this.activePreferenceKey = key
      this.$nextTick(() => {
        this.drawPreferenceChart()
        setTimeout(() => this.drawPreferenceChart(), 0)
      })
    },
    drawPreferenceChart() {
      const items = this.preferenceChartItems
      if (!items.length) return
      this.syncPreferenceChartSize()
      this.measurePreferenceChart()
      const { size, center, outerRadius, innerRadius, activeOffset } = this.preferenceChartMetrics()
      const ctx = uni.createCanvasContext('preferenceChart', this)

      ctx.clearRect(0, 0, size, size)
      items.forEach(item => {
        const active = item.key === this.activePreferenceKey
        const offset = active ? activeOffset : 0
        const offsetX = Math.cos(item.midAngle) * offset
        const offsetY = Math.sin(item.midAngle) * offset
        const cx = center + offsetX
        const cy = center + offsetY

        ctx.beginPath()
        ctx.moveTo(
          cx + Math.cos(item.startAngle) * innerRadius,
          cy + Math.sin(item.startAngle) * innerRadius
        )
        ctx.arc(cx, cy, outerRadius, item.startAngle, item.endAngle)
        ctx.lineTo(
          cx + Math.cos(item.endAngle) * innerRadius,
          cy + Math.sin(item.endAngle) * innerRadius
        )
        ctx.arc(cx, cy, innerRadius, item.endAngle, item.startAngle, true)
        ctx.closePath()
        ctx.setFillStyle(item.color)
        ctx.fill()
      })
      ctx.draw()
    },
    preferenceChartMetrics() {
      const size = this.preferenceChartSize
      const outerRadius = size * 0.38
      const innerRadius = size * 0.235
      return {
        size,
        center: size / 2,
        outerRadius,
        innerRadius,
        hitPadding: size * 0.025,
        looseInnerRadius: size * 0.06,
        looseOuterRadius: size * 0.5,
        activeOffset: size * 0.035
      }
    },
    normalizePreferenceAngle(angle) {
      const base = -Math.PI / 2
      const full = Math.PI * 2
      let value = angle
      while (value < base) value += full
      while (value >= base + full) value -= full
      return value
    },
    isPointInPreferenceSlice(point, item) {
      const { center, outerRadius, innerRadius, hitPadding, activeOffset } = this.preferenceChartMetrics()
      const offset = item.key === this.activePreferenceKey ? activeOffset : 0
      const cx = center + Math.cos(item.midAngle) * offset
      const cy = center + Math.sin(item.midAngle) * offset
      const dx = point.x - cx
      const dy = point.y - cy
      const distance = Math.sqrt(dx * dx + dy * dy)
      if (distance < innerRadius - hitPadding || distance > outerRadius + hitPadding) return false
      const angle = this.normalizePreferenceAngle(Math.atan2(dy, dx))
      return angle >= item.startAngle && angle < item.endAngle
    },
    findPreferenceSliceByAngle(point) {
      const { center, looseInnerRadius, looseOuterRadius } = this.preferenceChartMetrics()
      const dx = point.x - center
      const dy = point.y - center
      const distance = Math.sqrt(dx * dx + dy * dy)
      if (distance < looseInnerRadius || distance > looseOuterRadius) return null
      const angle = this.normalizePreferenceAngle(Math.atan2(dy, dx))
      return this.preferenceChartItems.find(item => angle >= item.startAngle && angle < item.endAngle) || null
    },
    resolvePreferenceTapPoints(event) {
      const source = event.changedTouches?.[0] || event.touches?.[0] || event.detail || event || {}
      const points = []
      const directX = Number(source.x ?? source.offsetX)
      const directY = Number(source.y ?? source.offsetY)
      if (Number.isFinite(directX) && Number.isFinite(directY)) {
        points.push({ x: directX, y: directY })
      }

      const clientX = Number(source.clientX ?? source.pageX)
      const clientY = Number(source.clientY ?? source.pageY)
      const rect = this.preferenceChartRect
      if (Number.isFinite(clientX) && Number.isFinite(clientY) && rect) {
        const localX = clientX - rect.left
        const localY = clientY - rect.top
        const scaleX = rect.width ? this.preferenceChartSize / rect.width : 1
        const scaleY = rect.height ? this.preferenceChartSize / rect.height : 1
        points.push({
          x: localX * scaleX,
          y: localY * scaleY
        })
      }

      if (Number.isFinite(directX) && Number.isFinite(directY) && rect) {
        const localX = directX - rect.left
        const localY = directY - rect.top
        const scaleX = rect.width ? this.preferenceChartSize / rect.width : 1
        const scaleY = rect.height ? this.preferenceChartSize / rect.height : 1
        points.push({
          x: localX * scaleX,
          y: localY * scaleY
        })
      }
      return points
    },
    handlePreferenceChartTap(event) {
      const now = Date.now()
      const points = this.resolvePreferenceTapPoints(event)
      if (!points.length) {
        return
      }
      if (now - this.lastPreferenceTapAt < 80) return
      this.lastPreferenceTapAt = now

      for (const point of points) {
        const x = Number(point?.x)
        const y = Number(point?.y)
        if (!Number.isFinite(x) || !Number.isFinite(y)) continue

        const hitPoint = { x, y }
        const candidates = this.preferenceChartItems.filter(item => this.isPointInPreferenceSlice(hitPoint, item))
        if (!candidates.length) {
          const looseTarget = this.findPreferenceSliceByAngle(hitPoint)
          if (looseTarget) {
            this.selectPreferenceSlice(looseTarget.key)
            return
          }
          continue
        }
        const target = candidates.find(item => item.key !== this.activePreferenceKey) || candidates[0]
        if (target) {
          this.selectPreferenceSlice(target.key)
          return
        }
      }
    },
    async loadFootprints() {
      try {
        console.log('[profile][footprints] request', { userId: this.userId })
        const res = await get('/footprints', { user_id: this.userId })
        const data = res.footprints || []
        console.log('[profile][footprints] response', {
          userId: this.userId,
          status: res.status,
          count: res.count,
          rawCount: data.length,
          sample: data.slice(0, 3)
        })
        this.footprints = this.convertCoords(data)
        this.$nextTick(() => this.measureFootprintMap())
        console.log('[profile][footprints] rendered', { userId: this.userId, renderedCount: this.footprints.length })
      } catch (e) {
        console.warn('[profile][footprints] load failed', { userId: this.userId, error: e })
        this.footprints = []
      }
    },
    convertCoords(data) {
      const points = data.map(item => ({
        ...item,
        lat: parseFloat(item.latitude) || 0,
        lon: parseFloat(item.longitude) || 0
      }))
      const validPoints = points.filter(item => item.lat && item.lon)
      const latValues = validPoints.map(item => item.lat)
      const lonValues = validPoints.map(item => item.lon)
      const minLat = Math.min(...latValues, 31.426)
      const maxLat = Math.max(...latValues, 31.434)
      const minLon = Math.min(...lonValues, 120.094)
      const maxLon = Math.max(...lonValues, 120.105)
      const latRange = Math.max(maxLat - minLat, 0.0001)
      const lonRange = Math.max(maxLon - minLon, 0.0001)
      
      return points.map((item, index) => {
        let svgX = 50
        let svgY = 50
        
        if (item.lat && item.lon) {
          svgX = ((item.lon - minLon) / lonRange) * 78 + 11
          svgY = ((maxLat - item.lat) / latRange) * 70 + 15
        } else {
          svgX = 18 + (index % 5) * 16
          svgY = 24 + Math.floor(index / 5) * 18
        }
        
        return {
          ...item,
          svgX: Math.round(svgX * 10) / 10,
          svgY: Math.round(svgY * 10) / 10
        }
      })
    },
    saveProfile() {
      uni.setStorageSync('visitorProfile', {
        nickname: this.nickname || '灵山游客',
        signature: this.signature || '愿今日山水有好风'
      })
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
    },
    goToFeedback() {
      uni.navigateTo({
        url: '/pages/feedback/index?feedback_type=app&target_type=app&target_id=app&target_name=App%E4%BD%BF%E7%94%A8%E4%BD%93%E9%AA%8C&source=profile'
      })
    },
    maybePromptAppFeedback() {
      if (!this.isPageActive) return
      const launchCount = Number(uni.getStorageSync('appLaunchCount') || 0)
      if (launchCount < 3) return
      this.$refs.feedbackModal.open({
        title: '评价',
        content: '如果你愿意，花几秒钟告诉我们 App 哪些地方好用、哪些地方还需要改进。',
        params: {
          feedback_type: 'app',
          target_type: 'app',
          target_id: 'app',
          target_name: 'App 使用体验',
          source: 'profile'
        }
      })
    },
    handleFeedbackSubmit(data) {
      this.$refs.feedbackModal.close()
    },
    onHide() {
      this.isPageActive = false
      this.$refs.feedbackModal?.close()
    },
    onUnload() {
      this.isPageActive = false
      this.$refs.feedbackModal?.close()
    },
    onShow() {
      this.isPageActive = true
      this.userId = String(uni.getStorageSync('userId') || 'guest')
      this.loadFootprints()
      this.maybePromptAppFeedback()
    },
    contactService() {
      uni.navigateTo({ url: '/pages/customer-service/index' })
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '确定要退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            uni.removeStorageSync('access_token')
            uni.removeStorageSync('refresh_token')
            uni.removeStorageSync('user_info')
            const userId = 'visitor_' + Date.now()
            uni.setStorageSync('userId', userId)
            this.userId = userId
            uni.redirectTo({ url: '/pages/login/index' })
          }
        }
      })
    },
    getTagLabel(tag) {
      const labels = {
        'zen_culture': '禅意文化',
        'buddha_history': '佛教历史',
        'architecture_art': '建筑艺术',
        'buddha_performance': '佛教表演',
        'lake_scenery': '湖景风光',
        'parent_child': '亲子互动',
        'ancient_temple': '古寺文化',
        'leisure_service': '休闲服务'
      }
      return labels[tag] || tag
    },
    getTagColor(tag) {
      const colors = {
        'zen_culture': '#8c3228',
        'buddha_history': '#a65c3e',
        'architecture_art': '#37251a',
        'buddha_performance': '#5a4a3a',
        'lake_scenery': '#2d5a4a',
        'parent_child': '#b8860b',
        'ancient_temple': '#4a3728',
        'leisure_service': '#6b4423'
      }
      return colors[tag] || '#8c3228'
    }
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 52rpx;
  background:
    radial-gradient(circle at 90% 0, rgba(191, 139, 65, 0.18), transparent 30%),
    linear-gradient(180deg, #f6ecd9, #efe0c8 52%, #f8f1e7);
  color: #39281d;
}

.profile-hero {
  display: flex;
  align-items: center;
  min-height: 220rpx;
  padding: 30rpx;
  border-radius: 12rpx;
  background:
    linear-gradient(135deg, rgba(126, 48, 39, 0.96), rgba(196, 145, 75, 0.9)),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.08) 0 3rpx, transparent 3rpx 22rpx);
  color: #fff8e8;
  box-shadow: 0 18rpx 40rpx rgba(83, 47, 24, 0.16);
}

.avatar-ring {
  width: 132rpx;
  height: 132rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 26rpx;
  border: 4rpx solid rgba(255, 248, 232, 0.64);
  border-radius: 50%;
  background: rgba(255, 248, 232, 0.16);
}

.avatar-text {
  font-size: 48rpx;
  font-weight: 900;
}

.hero-info {
  flex: 1;
  min-width: 0;
}

.name-input,
.sign-input,
.user-id {
  display: block;
  width: 100%;
  color: #fff8e8;
}

.name-input {
  height: 56rpx;
  font-size: 36rpx;
  font-weight: 900;
}

.sign-input {
  height: 48rpx;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: rgba(255, 248, 232, 0.82);
}

.user-id {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(255, 248, 232, 0.66);
}

.section-card {
  margin-top: 22rpx;
  margin-bottom: 22rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.88);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.section-title {
  font-size: 31rpx;
  font-weight: 900;
  color: #4b2c1f;
}

.section-sub {
  color: #9b7448;
  font-size: 22rpx;
}

.preference-chart-wrap {
  position: relative;
  width: 320rpx;
  height: 320rpx;
  margin: 6rpx auto 4rpx;
}

.preference-canvas {
  width: 320rpx;
  height: 320rpx;
}

.preference-center {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 200rpx;
  height: 200rpx;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 251, 242, 0.94);
  box-shadow: inset 0 0 0 1rpx rgba(121, 74, 38, 0.1);
  pointer-events: none;
}

.preference-center-label,
.preference-center-value {
  display: block;
}

.preference-center-label {
  max-width: 140rpx;
  color: #6c432b;
  font-size: 24rpx;
  font-weight: 800;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preference-center-value {
  margin-top: 6rpx;
  color: #8c3228;
  font-size: 42rpx;
  font-weight: 950;
}

.menu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.menu-row:last-child {
  border-bottom: none;
}

.menu-title {
  color: #3f2b20;
  font-size: 27rpx;
  font-weight: 800;
}

.menu-arrow {
  flex-shrink: 0;
  color: #9b7448;
  font-size: 26rpx;
}

.footprint-map {
  position: relative;
  height: 330rpx;
  overflow: hidden;
  border-radius: 10rpx;
  background:
    radial-gradient(circle at 18% 28%, rgba(140, 50, 40, 0.18), transparent 16%),
    radial-gradient(circle at 70% 62%, rgba(47, 91, 104, 0.16), transparent 18%),
    linear-gradient(135deg, #ead9b9, #d8be86);
}

.map-line-segment {
  position: absolute;
  height: 4rpx;
  border-radius: 999rpx;
  background: rgba(140, 50, 40, 0.45);
  border-top: 2rpx dashed rgba(140, 50, 40, 0.72);
  transform-origin: 0 50%;
  z-index: 1;
}

.map-dot {
  position: absolute;
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  background: #a65c3e;
  border: 4rpx solid rgba(255, 248, 232, 0.92);
  box-shadow: 0 4rpx 12rpx rgba(75, 43, 24, 0.18);
  transform: translate(-50%, -50%);
  z-index: 2;
}

.map-dot.start {
  background: #2d5a4a;
}

.map-dot.end {
  background: #8c3228;
}

.map-pin {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.92);
  box-shadow: 0 4rpx 12rpx rgba(75, 43, 24, 0.12);
  transform: translate(10rpx, -50%);
  white-space: nowrap;
  z-index: 3;
}

.pin-name {
  font-size: 24rpx;
  color: #4b2c1f;
  font-weight: 600;
}

.empty-footprint {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0;
}

.empty-icon {
  font-size: 60rpx;
  margin-bottom: 16rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #37251a;
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: 24rpx;
  color: #8b7355;
}

.pin-name {
  max-width: 150rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #4d3221;
  font-size: 22rpx;
  font-weight: 800;
}

.danger .menu-title {
  color: #8c3228;
}

.version {
  display: block;
  margin-top: 32rpx;
  text-align: center;
  color: #b39a7a;
  font-size: 22rpx;
}

@media screen and (max-width: 380px) {
  .preference-chart-wrap,
  .preference-canvas {
    width: 280rpx;
    height: 280rpx;
  }

  .preference-center {
    width: 176rpx;
    height: 176rpx;
  }

  .preference-center-label,
  .pin-name {
    max-width: 120rpx;
  }

  .menu-row {
    gap: 12rpx;
  }

  .footprint-map {
    height: 280rpx;
  }
}
</style>
