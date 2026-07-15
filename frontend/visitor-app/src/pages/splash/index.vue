<template>
  <view class="splash-container">
    <view class="splash-content">
      <view class="logo-wrapper">
        <view class="logo-circle">
          <text class="logo-text">灵</text>
        </view>
        <text class="logo-title">灵山胜境</text>
        <text class="logo-subtitle">AI智慧导览</text>
      </view>
      <view class="loading-bar">
        <view class="loading-progress" :style="{ width: progress + '%' }"></view>
      </view>
      <text class="loading-text">{{ loadingText }}</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      progress: 0,
      loadingText: '正在启动...',
      timer: null,
      loadingSteps: ['正在加载资源...', '正在初始化服务...', '即将进入...']
    }
  },
  mounted() {
    this.startAnimation()
  },
  beforeUnmount() {
    if (this.timer) {
      clearInterval(this.timer)
    }
  },
  methods: {
    startAnimation() {
      let stepIndex = 0
      this.timer = setInterval(() => {
        this.progress += Math.random() * 15 + 5
        if (stepIndex < this.loadingSteps.length && this.progress > (stepIndex + 1) * 30) {
          this.loadingText = this.loadingSteps[stepIndex]
          stepIndex++
        }
        if (this.progress >= 100) {
          this.progress = 100
          this.loadingText = '正在进入...'
          clearInterval(this.timer)
          setTimeout(() => {
            this.jumpToMain()
          }, 500)
        }
      }, 150)
    },
    jumpToMain() {
      const hasToken = uni.getStorageSync('access_token')
      if (hasToken) {
        uni.switchTab({ url: '/pages/home/index' })
      } else {
        uni.redirectTo({ url: '/pages/login/index' })
      }
    }
  }
}
</script>

<style>
.splash-container {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #743327 0%, #9b4a34 40%, #d8ad64 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.splash-content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  animation: fadeInUp 0.8s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.logo-circle {
  width: 160rpx;
  height: 160rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  border: 4rpx solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30rpx;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

.logo-text {
  font-size: 72rpx;
  font-weight: bold;
  color: #fff;
}

.logo-title {
  font-size: 48rpx;
  font-weight: bold;
  color: #fff;
  margin-bottom: 10rpx;
}

.logo-subtitle {
  font-size: 28rpx;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 80rpx;
}

.loading-bar {
  width: 300rpx;
  height: 8rpx;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4rpx;
  overflow: hidden;
  margin-bottom: 20rpx;
}

.loading-progress {
  height: 100%;
  background: linear-gradient(90deg, #fff, #ffd700);
  border-radius: 4rpx;
  transition: width 0.15s ease-out;
}

.loading-text {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}
</style>