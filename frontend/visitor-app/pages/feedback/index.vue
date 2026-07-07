<template>
  <view class="feedback-page">
    <view class="feedback-header">
      <text class="header-title">服务评价</text>
      <text class="header-subtitle">您的反馈对我们很重要</text>
    </view>

    <view class="feedback-content">
      <view class="rating-section">
        <text class="section-title">服务评分</text>
        <view class="stars">
          <text 
            class="star" 
            :class="{ active: star <= rating }"
            v-for="star in 5"
            :key="star"
            @click="setRating(star)"
          >★</text>
        </view>
        <text class="rating-text">{{ ratingText }}</text>
      </view>

      <view class="comment-section">
        <text class="section-title">评价内容</text>
        <textarea 
          class="comment-input"
          v-model="comment"
          placeholder="请输入您的评价..."
          :maxlength="500"
        />
        <text class="word-count">{{ comment.length }}/500</text>
      </view>

      <view class="tags-section">
        <text class="section-title">评价标签</text>
        <view class="tags">
          <text 
            class="tag" 
            :class="{ active: selectedTags.includes(tag) }"
            v-for="tag in tags"
            :key="tag"
            @click="toggleTag(tag)"
          >{{ tag }}</text>
        </view>
      </view>
    </view>

    <view class="submit-section">
      <button class="submit-btn" @click="submitFeedback" :disabled="!canSubmit">
        提交评价
      </button>
    </view>
  </view>
</template>

<script>
import { post } from '@/utils/request'

export default {
  data() {
    return {
      rating: 0,
      comment: '',
      tags: ['服务态度好', '讲解详细', '推荐路线', '景点美丽', '导航准确', '其他'],
      selectedTags: []
    }
  },
  computed: {
    ratingText() {
      const texts = ['', '非常不满意', '不满意', '一般', '满意', '非常满意']
      return texts[this.rating] || ''
    },
    canSubmit() {
      return this.rating > 0 && this.comment.trim().length > 0
    }
  },
  methods: {
    setRating(star) {
      this.rating = star
    },
    toggleTag(tag) {
      const index = this.selectedTags.indexOf(tag)
      if (index > -1) {
        this.selectedTags.splice(index, 1)
      } else {
        this.selectedTags.push(tag)
      }
    },
    async submitFeedback() {
      if (!this.canSubmit) {
        uni.showToast({ title: '请填写评分和评价', icon: 'none' })
        return
      }
      
      uni.showLoading({ title: '提交中...' })
      
      try {
        const res = await post('/feedback', {
          rating: this.rating,
          comment: this.comment,
          tags: this.selectedTags.join(',')
        })
        
        uni.hideLoading()
        uni.showToast({ title: '评价成功', icon: 'success' })
        
        setTimeout(() => {
          uni.navigateBack()
        }, 1500)
      } catch (e) {
        uni.hideLoading()
        uni.showToast({ title: '提交失败', icon: 'none' })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.feedback-page {
  min-height: 100vh;
  background: #f5f5f5;
  display: flex;
  flex-direction: column;
}

.feedback-header {
  background: linear-gradient(135deg, #667eea, #764ba2);
  padding: 40rpx 30rpx;
  text-align: center;
  color: #fff;
}

.header-title {
  display: block;
  font-size: 36rpx;
  font-weight: bold;
}

.header-subtitle {
  display: block;
  font-size: 24rpx;
  opacity: 0.9;
  margin-top: 10rpx;
}

.feedback-content {
  flex: 1;
  padding: 30rpx;
}

.rating-section {
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

.stars {
  display: flex;
  justify-content: center;
}

.star {
  font-size: 60rpx;
  color: #ddd;
  margin: 0 10rpx;
}

.star.active {
  color: #ffd700;
}

.rating-text {
  display: block;
  text-align: center;
  font-size: 26rpx;
  color: #999;
  margin-top: 16rpx;
}

.comment-section {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
}

.comment-input {
  width: 100%;
  height: 300rpx;
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 20rpx;
  font-size: 28rpx;
}

.word-count {
  display: block;
  text-align: right;
  font-size: 24rpx;
  color: #999;
  margin-top: 10rpx;
}

.tags-section {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
}

.tags {
  display: flex;
  flex-wrap: wrap;
}

.tag {
  background: #f5f5f5;
  padding: 16rpx 30rpx;
  border-radius: 30rpx;
  font-size: 26rpx;
  color: #666;
  margin-right: 20rpx;
  margin-bottom: 16rpx;
}

.tag.active {
  background: #667eea;
  color: #fff;
}

.submit-section {
  padding: 30rpx;
  padding-bottom: calc(30rpx + env(safe-area-inset-bottom));
}

.submit-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-radius: 50rpx;
  font-size: 32rpx;
  padding: 28rpx 0;
}

.submit-btn[disabled] {
  background: #ccc;
}
</style>