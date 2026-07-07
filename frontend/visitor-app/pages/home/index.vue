<template>
  <view class="home">
    <view class="header">
      <text class="title">灵山胜境</text>
      <text class="subtitle">AI数字人智慧导览</text>
    </view>

    <view class="search-bar" @click="goToGuideList">
      <text class="search-icon">🔍</text>
      <text class="search-hint">搜索景点...</text>
    </view>

    <view class="quick-actions">
      <view class="action-item" @click="goToChat">
        <view class="action-icon">💬</view>
        <text class="action-text">AI对话</text>
      </view>
      <view class="action-item" @click="goToRecommendation">
        <view class="action-icon">🎯</view>
        <text class="action-text">个性推荐</text>
      </view>
      <view class="action-item" @click="goToRoutePlanning">
        <view class="action-icon">🗺️</view>
        <text class="action-text">路线规划</text>
      </view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">热门景点</text>
        <text class="section-more" @click="goToGuideList">查看全部 ›</text>
      </view>
      <scroll-view class="spot-scroll" scroll-x>
        <view class="spot-card" v-for="spot in hotSpots" :key="spot.id" @click="goToGuide(spot.id)">
          <view class="spot-image">
            <text class="image-placeholder">🖼️</text>
          </view>
          <text class="spot-name">{{ spot.name }}</text>
        </view>
      </scroll-view>
    </view>

    <view class="section">
      <view class="section-header">
        <text class="section-title">AI智能导览</text>
      </view>
      <view class="ai-banner" @click="goToChat">
        <view class="ai-avatar">🤖</view>
        <view class="ai-info">
          <text class="ai-title">有问题尽管问我</text>
          <text class="ai-desc">景点、文化、路线...我都能解答</text>
        </view>
        <text class="ai-arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      hotSpots: [
        { id: 1, name: '梵宫' },
        { id: 2, name: '灵山大佛' },
        { id: 3, name: '灵山胜境' },
        { id: 4, name: '五印坛城' },
        { id: 5, name: '灵山梵宫' }
      ]
    }
  },
  methods: {
    goToChat() {
      uni.navigateTo({ url: '/pages/chat/index' })
    },
    goToRecommendation() {
      uni.navigateTo({ url: '/pages/recommendation/index' })
    },
    goToRoutePlanning() {
      uni.navigateTo({ url: '/pages/route-planning/index' })
    },
    goToGuideList() {
      uni.navigateTo({ url: '/pages/guide/index' })
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.home {
  min-height: 100vh;
  background: #f5f5f5;
}

.header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 60rpx 30rpx 40rpx;
  text-align: center;
  color: #fff;
}

.title {
  display: block;
  font-size: 44rpx;
  font-weight: bold;
}

.subtitle {
  display: block;
  font-size: 26rpx;
  opacity: 0.9;
  margin-top: 10rpx;
}

.search-bar {
  display: flex;
  align-items: center;
  margin: -30rpx 30rpx 30rpx;
  background: #fff;
  border-radius: 50rpx;
  padding: 24rpx 30rpx;
  box-shadow: 0 4rpx 20rpx rgba(0, 0, 0, 0.08);
}

.search-icon {
  font-size: 36rpx;
  margin-right: 16rpx;
}

.search-hint {
  font-size: 28rpx;
  color: #999;
}

.quick-actions {
  display: flex;
  justify-content: space-around;
  padding: 30rpx;
  background: #fff;
  margin: 0 30rpx;
  border-radius: 20rpx;
}

.action-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.action-icon {
  width: 100rpx;
  height: 100rpx;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
  margin-bottom: 16rpx;
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.action-text {
  font-size: 26rpx;
  color: #666;
}

.section {
  margin: 30rpx;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
}

.section-more {
  font-size: 26rpx;
  color: #999;
}

.spot-scroll {
  white-space: nowrap;
}

.spot-card {
  display: inline-block;
  width: 240rpx;
  margin-right: 20rpx;
  background: #fff;
  border-radius: 16rpx;
  overflow: hidden;
}

.spot-image {
  width: 240rpx;
  height: 160rpx;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-placeholder {
  font-size: 60rpx;
}

.spot-name {
  display: block;
  padding: 20rpx;
  font-size: 26rpx;
  color: #333;
  text-align: center;
}

.ai-banner {
  display: flex;
  align-items: center;
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 20rpx;
  padding: 30rpx;
  color: #fff;
}

.ai-avatar {
  font-size: 60rpx;
  margin-right: 20rpx;
}

.ai-info {
  flex: 1;
}

.ai-title {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  margin-bottom: 8rpx;
}

.ai-desc {
  display: block;
  font-size: 24rpx;
  opacity: 0.9;
}

.ai-arrow {
  font-size: 40rpx;
  opacity: 0.7;
}
</style>
