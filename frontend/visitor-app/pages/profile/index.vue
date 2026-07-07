<template>
  <view class="profile">
    <view class="profile-header">
      <view class="avatar">👤</view>
      <view class="user-info">
        <text class="user-name">游客 {{ shortUserId }}</text>
        <text class="user-id">ID: {{ userId }}</text>
      </view>
    </view>

    <view class="menu-section">
      <view class="menu-item" @click="goToChatHistory">
        <text class="menu-icon">💬</text>
        <text class="menu-text">对话历史</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @click="goToFeedback">
        <text class="menu-icon">⭐</text>
        <text class="menu-text">服务评价</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item" @click="goToRecommendation">
        <text class="menu-icon">🎯</text>
        <text class="menu-text">我的推荐</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <view class="menu-section">
      <view class="menu-item">
        <text class="menu-icon">ℹ️</text>
        <text class="menu-text">关于我们</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-item">
        <text class="menu-icon">📖</text>
        <text class="menu-text">使用帮助</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <view class="version">
      <text>灵山胜境 AI导览 v1.0.0</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      userId: ''
    }
  },
  computed: {
    shortUserId() {
      return this.userId ? this.userId.slice(-6) : '------'
    }
  },
  onLoad() {
    this.userId = uni.getStorageSync('userId') || 'guest'
  },
  methods: {
    goToChatHistory() {
      uni.navigateTo({ url: '/pages/chat/index?history=true' })
    },
    goToFeedback() {
      uni.navigateTo({ url: '/pages/feedback/index' })
    },
    goToRecommendation() {
      uni.navigateTo({ url: '/pages/recommendation/index' })
    }
  }
}
</script>

<style lang="scss" scoped>
.profile {
  min-height: 100vh;
  background: #f5f5f5;
}

.profile-header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 60rpx 30rpx;
  display: flex;
  align-items: center;
}

.avatar {
  width: 120rpx;
  height: 120rpx;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 60rpx;
  margin-right: 30rpx;
}

.user-info {
  color: #fff;
}

.user-name {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
  margin-bottom: 10rpx;
}

.user-id {
  display: block;
  font-size: 24rpx;
  opacity: 0.8;
}

.menu-section {
  background: #fff;
  margin: 20rpx 30rpx;
  border-radius: 16rpx;
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 30rpx;
  border-bottom: 1rpx solid #f0f0f0;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-icon {
  font-size: 40rpx;
  margin-right: 20rpx;
}

.menu-text {
  flex: 1;
  font-size: 28rpx;
  color: #333;
}

.menu-arrow {
  font-size: 32rpx;
  color: #ccc;
}

.version {
  text-align: center;
  padding: 40rpx;
  font-size: 24rpx;
  color: #ccc;
}
</style>