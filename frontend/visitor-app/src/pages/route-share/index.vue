<template>
  <view class="share-page">
    <view class="share-header">
      <view class="logo-area">
        <text class="logo-text">🗺️</text>
      </view>
      <text class="app-name">灵山胜境 AI导览</text>
    </view>

    <view class="route-card" v-if="routeData">
      <view class="route-header">
        <text class="route-name">{{ routeData.route_name }}</text>
        <view class="route-badge">
          <text>{{ routeData.total_duration }}分钟</text>
        </view>
      </view>

      <view class="route-info">
        <view class="info-row">
          <text class="info-icon">📍</text>
          <text class="info-text">{{ routeData.total_spots }}个景点</text>
        </view>
        <view class="info-row">
          <text class="info-icon">🚶</text>
          <text class="info-text">{{ formatDistance(routeData.total_distance) }}</text>
        </view>
      </view>

      <view class="route-spots">
        <text class="spots-title">游览顺序</text>
        <view 
          class="spot-item" 
          v-for="(spot, index) in routeData.route" 
          :key="index"
        >
          <view class="spot-number">{{ index + 1 }}</view>
          <view class="spot-info">
            <text class="spot-name">{{ spot.name || spot.spot_name }}</text>
            <text class="spot-time">停留{{ spot.stay_minutes }}分钟</text>
          </view>
        </view>
      </view>

      <view class="route-desc">
        <text>{{ routeData.description }}</text>
      </view>
    </view>

    <view class="empty-state" v-else>
      <text class="empty-icon">🔗</text>
      <text class="empty-title">路线链接无效</text>
      <text class="empty-desc">该路线链接可能已过期或不存在</text>
    </view>

    <view class="action-area">
      <button class="primary-btn" @click="openInApp">
        <text class="btn-icon">📱</text>
        <text class="btn-text">在APP中打开</text>
      </button>
      <button class="secondary-btn" @click="copyRouteData">
        <text class="btn-icon">📋</text>
        <text class="btn-text">复制路线信息</text>
      </button>
    </view>

    <view class="footer">
      <text class="footer-text">灵山胜境 AI导览 · 智能路线规划</text>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

export default {
  data() {
    return {
      routeData: null,
      shareId: ''
    }
  },
  onLoad(options = {}) {
    this.shareId = options.share_id || options.shareId
    if (this.shareId) {
      this.loadRouteData()
    }
  },
  methods: {
    async loadRouteData() {
      try {
        const res = await get(`/routes/share/${encodeURIComponent(this.shareId)}`)
        this.routeData = res.route || res
      } catch (e) {
        console.error('Failed to load route data:', e)
      }
    },
    formatDistance(distance) {
      const value = Number(distance || 0)
      if (value < 1000) return `${Math.round(value)}米`
      return `${(value / 1000).toFixed(1)}公里`
    },
    openInApp() {
      const scheme = `lingshan://route-detail?share_id=${this.shareId}`
      // #ifdef H5
      const downloadUrl = 'https://your-app-download-url.com'
      window.location.href = downloadUrl
      // #endif
      // #ifdef APP-PLUS
      plus.runtime.openURL(scheme)
      // #endif
    },
    copyRouteData() {
      if (!this.routeData) return
      const names = this.routeData.route
        .map((spot, index) => `${index + 1}. ${spot.name || spot.spot_name}`)
        .join('\n')
      const text = [
        `${this.routeData.route_name}`,
        `预计用时：${this.routeData.total_duration}分钟`,
        `预计距离：${this.formatDistance(this.routeData.total_distance)}`,
        `游览顺序：`,
        names
      ].join('\n')
      uni.setClipboardData({
        data: text,
        success: () => uni.showToast({ title: '路线信息已复制', icon: 'none' })
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.share-page {
  min-height: 100vh;
  padding: 32rpx 24rpx;
  background:
    radial-gradient(circle at 90% 0, rgba(191, 139, 65, 0.18), transparent 30%),
    linear-gradient(180deg, #f6ecd9, #efe0c8 52%, #f8f1e7);
}

.share-header {
  text-align: center;
  padding: 40rpx 0;
}

.logo-area {
  width: 100rpx;
  height: 100rpx;
  margin: 0 auto 20rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #8c3228, #c4914b);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-text {
  font-size: 48rpx;
}

.app-name {
  font-size: 36rpx;
  font-weight: 900;
  color: #4b2c1f;
}

.route-card {
  background: rgba(255, 251, 242, 0.95);
  border-radius: 16rpx;
  padding: 32rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  box-shadow: 0 8rpx 30rpx rgba(83, 47, 24, 0.08);
}

.route-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24rpx;
}

.route-name {
  font-size: 36rpx;
  font-weight: 900;
  color: #8c3228;
}

.route-badge {
  background: linear-gradient(135deg, #8c3228, #c4914b);
  color: #fff;
  padding: 8rpx 16rpx;
  border-radius: 20rpx;
  font-size: 22rpx;
  font-weight: 800;
}

.route-info {
  display: flex;
  gap: 32rpx;
  margin-bottom: 28rpx;
  padding-bottom: 28rpx;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.info-row {
  display: flex;
  align-items: center;
}

.info-icon {
  font-size: 28rpx;
  margin-right: 8rpx;
}

.info-text {
  font-size: 26rpx;
  color: #6b5344;
}

.route-spots {
  margin-bottom: 28rpx;
}

.spots-title {
  display: block;
  font-size: 28rpx;
  font-weight: 900;
  color: #4b2c1f;
  margin-bottom: 16rpx;
}

.spot-item {
  display: flex;
  align-items: center;
  padding: 16rpx 0;
}

.spot-number {
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: rgba(140, 50, 40, 0.1);
  color: #8c3228;
  font-size: 24rpx;
  font-weight: 900;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16rpx;
}

.spot-info {
  flex: 1;
}

.spot-name {
  display: block;
  font-size: 28rpx;
  font-weight: 800;
  color: #4b2c1f;
}

.spot-time {
  display: block;
  font-size: 22rpx;
  color: #9b7448;
  margin-top: 4rpx;
}

.route-desc {
  padding: 20rpx;
  background: rgba(140, 50, 40, 0.04);
  border-radius: 12rpx;
}

.route-desc text {
  font-size: 24rpx;
  color: #6b5344;
  line-height: 1.6;
}

.empty-state {
  text-align: center;
  padding: 100rpx 0;
}

.empty-icon {
  font-size: 80rpx;
  display: block;
  margin-bottom: 24rpx;
}

.empty-title {
  font-size: 32rpx;
  font-weight: 900;
  color: #4b2c1f;
  display: block;
  margin-bottom: 12rpx;
}

.empty-desc {
  font-size: 26rpx;
  color: #9b7448;
}

.action-area {
  margin-top: 32rpx;
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.primary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #8c3228, #c4914b);
  color: #fff;
  padding: 28rpx;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 900;
  border: none;
}

.btn-icon {
  font-size: 32rpx;
  margin-right: 12rpx;
}

.btn-text {
  font-size: 30rpx;
}

.secondary-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.8);
  color: #8c3228;
  padding: 28rpx;
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 900;
  border: 2rpx solid #8c3228;
}

.footer {
  text-align: center;
  margin-top: 40rpx;
}

.footer-text {
  font-size: 22rpx;
  color: #b39a7a;
}
</style>