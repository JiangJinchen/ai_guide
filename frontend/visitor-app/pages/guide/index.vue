<template>
  <view class="guide-page">
    <view class="guide-header" v-if="spotDetail">
      <text class="spot-name">{{ spotDetail.spot_name }}</text>
      <text class="spot-subtitle">{{ spotDetail.description }}</text>
    </view>

    <scroll-view class="guide-content" scroll-y v-if="guideContent">
      <view class="guide-section">
        <text class="section-title">📖 景点介绍</text>
        <text class="section-content">{{ guideContent.guide_text || guideContent.content }}</text>
      </view>

      <view class="guide-section" v-if="guideContent.culture_highlights">
        <text class="section-title">✨ 文化亮点</text>
        <text class="section-content">{{ guideContent.culture_highlights }}</text>
      </view>

      <view class="guide-section" v-if="guideContent.open_info">
        <text class="section-title">⏰ 开放信息</text>
        <text class="section-content">{{ guideContent.open_info }}</text>
      </view>

      <view class="guide-section">
        <view class="play-button" @click="playGuide">
          <text class="play-icon">▶</text>
          <text class="play-text">{{ isPlaying ? '停止播放' : '语音讲解' }}</text>
        </view>
      </view>
    </scroll-view>

    <view class="spots-list" v-if="!spotDetail">
      <text class="list-title">选择景点</text>
      <view 
        class="spot-item" 
        v-for="spot in spots" 
        :key="spot.id"
        @click="loadGuide(spot.id)"
      >
        <view class="spot-thumb">
          <text class="thumb-placeholder">🖼️</text>
        </view>
        <view class="spot-info">
          <text class="spot-name">{{ spot.spot_name }}</text>
          <text class="spot-desc">{{ spot.description }}</text>
        </view>
        <text class="spot-arrow">›</text>
      </view>
    </view>

    <view class="loading" v-if="isLoading">
      <text>加载中...</text>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

export default {
  data() {
    return {
      spotId: null,
      spotDetail: null,
      guideContent: null,
      spots: [],
      isLoading: false,
      isPlaying: false
    }
  },
  onLoad(options) {
    if (options && options.spot_id) {
      this.spotId = parseInt(options.spot_id)
      this.loadGuide(this.spotId)
    } else {
      this.loadSpotsList()
    }
  },
  methods: {
    async loadSpotsList() {
      try {
        this.spots = await get('/spots')
      } catch (e) {
        console.error('加载景点失败', e)
        this.spots = [
          { id: 1, spot_name: '梵宫', description: '宏伟的佛教艺术殿堂' },
          { id: 2, spot_name: '灵山大佛', description: '世界最高的佛像之一' },
          { id: 3, spot_name: '五印坛城', description: '藏传佛教文化圣地' }
        ]
      }
    },
    async loadGuide(id) {
      this.isLoading = true
      this.spotId = id
      
      try {
        const [spot, guide] = await Promise.all([
          get(`/spots/${id}`),
          get(`/guide/${id}`)
        ])
        
        this.spotDetail = spot
        this.guideContent = guide
        
        if (!this.guideContent.guide_text) {
          this.guideContent.guide_text = '欢迎来到' + (spot.spot_name || '') + '，这里有着深厚的文化底蕴和美丽的风景。'
        }
      } catch (e) {
        console.error('加载讲解失败', e)
        this.spotDetail = { spot_name: '景点详情', description: '' }
        this.guideContent = { guide_text: '暂无详细讲解内容' }
      }
      
      this.isLoading = false
    },
    playGuide() {
      this.isPlaying = !this.isPlaying
      if (this.isPlaying) {
        uni.showToast({ title: '开始播放', icon: 'none' })
      } else {
        uni.showToast({ title: '已停止', icon: 'none' })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.guide-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.guide-header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 40rpx 30rpx;
  color: #fff;
}

.spot-name {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
}

.spot-subtitle {
  display: block;
  font-size: 26rpx;
  opacity: 0.9;
  margin-top: 10rpx;
}

.guide-content {
  padding: 30rpx;
  height: calc(100vh - 180rpx);
}

.guide-section {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.section-title {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

.section-content {
  display: block;
  font-size: 28rpx;
  color: #666;
  line-height: 1.8;
}

.play-button {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-radius: 50rpx;
  padding: 28rpx;
}

.play-icon {
  font-size: 36rpx;
  margin-right: 16rpx;
}

.play-text {
  font-size: 30rpx;
}

.spots-list {
  padding: 30rpx;
}

.list-title {
  display: block;
  font-size: 32rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 20rpx;
}

.spot-item {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
}

.spot-thumb {
  width: 120rpx;
  height: 120rpx;
  background: #f0f0f0;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.thumb-placeholder {
  font-size: 48rpx;
}

.spot-info {
  flex: 1;
}

.spot-name {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}

.spot-desc {
  display: block;
  font-size: 24rpx;
  color: #999;
}

.spot-arrow {
  font-size: 40rpx;
  color: #ccc;
}

.loading {
  text-align: center;
  padding: 100rpx;
  font-size: 28rpx;
  color: #999;
}
</style>