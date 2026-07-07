<template>
  <view class="recommendation">
    <view class="rec-header">
      <text class="rec-title">为您推荐</text>
      <text class="rec-subtitle">基于您的偏好和历史记录</text>
    </view>

    <view class="recommend-list">
      <view 
        class="recommend-card" 
        v-for="(item, index) in recommendations" 
        :key="index"
        @click="goToGuide(item.spot_id)"
      >
        <view class="card-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</view>
        <view class="card-image">
          <text class="image-placeholder">🖼️</text>
        </view>
        <view class="card-info">
          <text class="card-name">{{ item.spot_name }}</text>
          <text class="card-desc">{{ item.reason }}</text>
          <view class="card-tags">
            <text class="tag" v-for="(tag, i) in item.tags" :key="i">{{ tag }}</text>
          </view>
        </view>
        <view class="card-action">
          <text>查看 ›</text>
        </view>
      </view>
    </view>

    <view class="empty-tip" v-if="recommendations.length === 0">
      <text class="empty-icon">🎯</text>
      <text class="empty-text">暂无推荐内容</text>
      <text class="empty-hint">开始与AI对话，获取个性化推荐</text>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

export default {
  data() {
    return {
      recommendations: []
    }
  },
  onLoad() {
    this.loadRecommendations()
  },
  methods: {
    async loadRecommendations() {
      try {
        const res = await get('/recommendation')
        this.recommendations = res.recommendations || res || []
      } catch (e) {
        console.error('加载推荐失败', e)
        this.recommendations = [
          { spot_id: 1, spot_name: '梵宫', reason: '您之前询问过文化景点', tags: ['文化', '建筑', '必看'] },
          { spot_id: 2, spot_name: '灵山大佛', reason: '热门景点推荐', tags: ['地标', '祈福', '拍照'] },
          { spot_id: 3, spot_name: '五印坛城', reason: '藏传佛教文化体验', tags: ['文化', '艺术'] }
        ]
      }
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.recommendation {
  min-height: 100vh;
  background: #f5f5f5;
}

.rec-header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 40rpx 30rpx;
  text-align: center;
  color: #fff;
}

.rec-title {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
}

.rec-subtitle {
  display: block;
  font-size: 24rpx;
  opacity: 0.9;
  margin-top: 10rpx;
}

.recommend-list {
  padding: 30rpx;
}

.recommend-card {
  display: flex;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 20rpx;
  align-items: center;
}

.card-rank {
  width: 60rpx;
  height: 60rpx;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28rpx;
  font-weight: bold;
  color: #999;
  margin-right: 20rpx;
}

.rank-1 {
  background: linear-gradient(135deg, #ffd700, #ffb700);
  color: #fff;
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #a0a0a0);
  color: #fff;
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #b87333);
  color: #fff;
}

.card-image {
  width: 160rpx;
  height: 160rpx;
  background: #f0f0f0;
  border-radius: 12rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20rpx;
}

.image-placeholder {
  font-size: 50rpx;
}

.card-info {
  flex: 1;
}

.card-name {
  display: block;
  font-size: 30rpx;
  font-weight: bold;
  color: #333;
  margin-bottom: 8rpx;
}

.card-desc {
  display: block;
  font-size: 24rpx;
  color: #999;
  margin-bottom: 12rpx;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
}

.tag {
  background: #f5f5f5;
  padding: 6rpx 16rpx;
  border-radius: 16rpx;
  font-size: 22rpx;
  color: #666;
  margin-right: 12rpx;
}

.card-action {
  color: #667eea;
  font-size: 26rpx;
}

.empty-tip {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100rpx 30rpx;
}

.empty-icon {
  font-size: 100rpx;
  margin-bottom: 30rpx;
}

.empty-text {
  font-size: 32rpx;
  color: #333;
  margin-bottom: 16rpx;
}

.empty-hint {
  font-size: 26rpx;
  color: #999;
}
</style>