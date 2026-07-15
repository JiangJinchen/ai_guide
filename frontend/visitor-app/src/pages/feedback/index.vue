<template>
  <view class="feedback-page">
    <view class="feedback-header">
      <text class="header-title">{{ pageTitle }}</text>
      <text class="header-subtitle">{{ pageSubtitle }}</text>
    </view>

    <view class="feedback-content">
      <view class="target-card" v-if="targetLabel">
        <text class="target-label">{{ modeLabel }}</text>
        <text class="target-name">{{ targetLabel }}</text>
      </view>

      <view class="rating-section">
        <text class="section-title">{{ ratingTitle }}</text>
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

      <view class="tags-section">
        <text class="section-title">可以补充选择</text>
        <view class="tags">
          <text
            class="tag"
            :class="{ active: selectedTags.includes(tag) }"
            v-for="tag in activeTags"
            :key="tag"
            @click="toggleTag(tag)"
          >{{ tag }}</text>
        </view>
      </view>

      <view class="comment-section">
        <text class="section-title">具体反馈</text>
        <textarea
          class="comment-input"
          v-model="comment"
          :placeholder="commentPlaceholder"
          :maxlength="500"
        />
        <text class="word-count">{{ comment.length }}/500</text>
      </view>
    </view>

    <view class="submit-section">
      <button class="submit-btn" @click="submitFeedback" :disabled="!canSubmit">
        {{ isSubmitting ? '提交中...' : '提交反馈' }}
      </button>
    </view>

    <view class="records-section">
      <view class="records-head">
        <text class="section-title">评价记录</text>
        <text class="records-count">{{ records.length }} 条</text>
      </view>
      <view class="record-card" v-for="record in records" :key="record.id">
        <view class="record-top">
          <text class="record-type">{{ recordTypeLabel(record.feedback_type) }}</text>
          <text class="record-score">{{ record.score || '-' }} 分</text>
        </view>
        <text class="record-target">{{ record.target_name || 'App 使用体验' }}</text>
        <text class="record-comment" v-if="record.comment">{{ record.comment }}</text>
        <view class="record-tags" v-if="record.tags && record.tags.length">
          <text class="record-tag" v-for="tag in record.tags" :key="record.id + tag">{{ tag }}</text>
        </view>
        <text class="record-time">{{ formatRecordTime(record.created_at) }}</text>
      </view>
      <view class="empty-records" v-if="!records.length">
        <text>暂无评价记录</text>
      </view>
    </view>
  </view>
</template>

<script>
import { get, post } from '@/utils/request'
import { markFeedbackSubmitted } from '@/utils/feedback'

const FEEDBACK_CONFIG = {
  app: {
    label: 'App 使用体验',
    title: '评价与反馈',
    subtitle: '告诉我们 App 整体哪里好用、哪里还可以改进',
    ratingTitle: 'App 使用体验评分',
    placeholder: '可以写下页面体验、功能建议、定位或加载问题等。',
    tags: ['页面清晰', '操作顺畅', '功能有帮助', '定位不准', '加载较慢', '信息不清楚']
  },
  chat: {
    label: 'AI 对话',
    title: '评价',
    subtitle: '这几轮问答是否解决了你的问题？',
    ratingTitle: 'AI 回答体验评分',
    placeholder: '例如：回答是否准确、是否有帮助、是否理解了你的问题。',
    tags: ['回答准确', '很有帮助', '回复自然', '没有答到重点', '信息不准确', '等待较久']
  },
  guide: {
    label: '景点讲解',
    title: '评价',
    subtitle: '这段讲解内容对你有帮助吗？',
    ratingTitle: '讲解体验评分',
    placeholder: '例如：内容是否清楚、是否有趣、讲解语音是否舒服。',
    tags: ['讲解清楚', '内容有趣', '语音舒服', '内容太少', '不够准确', '节奏不合适']
  },
  route: {
    label: '路线规划',
    title: '评价',
    subtitle: '这条路线是否帮你顺利完成游览？',
    ratingTitle: '路线导航评分',
    placeholder: '例如：路线是否合理、是否绕路、导航指引是否清楚。',
    tags: ['路线合理', '指引清楚', '节省时间', '有点绕路', '定位不稳', '不符合偏好']
  }
}

export default {
  data() {
    return {
      feedbackType: 'app',
      targetType: 'app',
      targetId: 'app',
      targetName: '',
      source: 'profile',
      sessionId: '',
      rating: 0,
      comment: '',
      selectedTags: [],
      records: [],
      isSubmitting: false
    }
  },
  computed: {
    modeConfig() {
      return FEEDBACK_CONFIG[this.feedbackType] || FEEDBACK_CONFIG.app
    },
    pageTitle() {
      return this.modeConfig.title
    },
    pageSubtitle() {
      return this.modeConfig.subtitle
    },
    modeLabel() {
      return this.modeConfig.label
    },
    targetLabel() {
      if (this.feedbackType === 'app') return ''
      return this.targetName || this.modeConfig.label
    },
    ratingTitle() {
      return this.modeConfig.ratingTitle
    },
    commentPlaceholder() {
      return this.modeConfig.placeholder
    },
    activeTags() {
      return this.modeConfig.tags
    },
    ratingText() {
      const texts = ['', '非常不满意', '不满意', '一般', '满意', '非常满意']
      return texts[this.rating] || '点击星星评分'
    },
    canSubmit() {
      return this.rating > 0 && !this.isSubmitting
    },
    targetKey() {
      return this.targetId || this.targetName || this.feedbackType
    }
  },
  onLoad(options = {}) {
    this.feedbackType = this.decodeOption(options.feedback_type) || this.decodeOption(options.mode) || 'app'
    this.targetType = this.decodeOption(options.target_type) || (this.feedbackType === 'app' ? 'app' : this.feedbackType)
    this.targetId = this.decodeOption(options.target_id) || (this.feedbackType === 'app' ? 'app' : '')
    this.targetName = this.decodeOption(options.target_name) || ''
    this.source = this.decodeOption(options.source) || 'profile'
    this.sessionId = this.decodeOption(options.session_id) || ''
    this.loadFeedbackRecords()
  },
  onShow() {
    this.loadFeedbackRecords()
  },
  methods: {
    decodeOption(value) {
      if (!value) return ''
      try {
        return decodeURIComponent(String(value))
      } catch (e) {
        return String(value)
      }
    },
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
    parseTags(rawTags) {
      if (!rawTags) return []
      if (typeof rawTags === 'string') {
        try {
          const parsed = JSON.parse(rawTags)
          return Array.isArray(parsed) ? parsed : []
        } catch (e) {
          return rawTags.split(',').map(t => t.trim().replace(/['"]/g, ''))
        }
      }
      if (Array.isArray(rawTags)) {
        const firstTag = String(rawTags[0] || '')
        if (firstTag.startsWith('[')) {
          try {
            const joined = rawTags.join(',')
            const parsed = JSON.parse(joined)
            return Array.isArray(parsed) ? parsed : []
          } catch (e) {
            return rawTags.map(t => String(t).replace(/['"\[\]]/g, '').trim()).filter(Boolean)
          }
        }
        return rawTags.map(t => String(t).replace(/['"\[\]]/g, '').trim()).filter(Boolean)
      }
      return []
    },
    async loadFeedbackRecords() {
      try {
        const userId = uni.getStorageSync('userId') || 'guest'
        const data = await get('/feedback/records', { user_id: userId, limit: 20 })
        this.records = (Array.isArray(data) ? data : []).map(r => ({
          ...r,
          tags: this.parseTags(r.tags)
        }))
      } catch (e) {
        this.records = []
      }
    },
    async submitFeedback() {
      if (!this.canSubmit) {
        uni.showToast({ title: '请先选择评分', icon: 'none' })
        return
      }
      this.isSubmitting = true
      uni.showLoading({ title: '提交中...' })
      try {
        const userId = uni.getStorageSync('userId') || 'guest'
        const res = await post('/feedback/submit', {
          user_id: userId,
          feedback_type: this.feedbackType,
          target_type: this.targetType,
          target_id: this.targetId,
          target_name: this.targetName,
          source: this.source,
          session_id: this.sessionId,
          satisfaction_score: this.rating,
          comment: this.comment.trim(),
          tags: this.selectedTags
        })
        markFeedbackSubmitted(this.feedbackType, this.targetKey)
        if (res && res.record) {
          const record = {
            ...res.record,
            tags: this.parseTags(res.record.tags)
          }
          this.records = [record, ...this.records.filter(item => item.id !== res.record.id)]
        }
        this.rating = 0
        this.comment = ''
        this.selectedTags = []
        uni.showToast({ title: '反馈已提交', icon: 'success' })
        if (this.feedbackType !== 'app') {
          setTimeout(() => uni.navigateBack(), 1000)
        }
      } catch (e) {
        uni.showToast({ title: '提交失败，请稍后重试', icon: 'none' })
      } finally {
        uni.hideLoading()
        this.isSubmitting = false
      }
    },
    recordTypeLabel(type) {
      return (FEEDBACK_CONFIG[type] || FEEDBACK_CONFIG.app).label
    },
    formatRecordTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      const pad = num => String(num).padStart(2, '0')
      return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
    }
  }
}
</script>

<style lang="scss" scoped>
.feedback-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f6ecd9 0%, #efe0c8 52%, #f8f1e7 100%);
  color: #39281d;
  padding-bottom: 44rpx;
}

.feedback-header {
  padding: 44rpx 30rpx 36rpx;
  background: linear-gradient(135deg, #8c3228, #c19148);
  color: #fff8e8;
}

.header-title,
.header-subtitle,
.section-title,
.target-label,
.target-name,
.rating-text,
.record-type,
.record-score,
.record-target,
.record-comment,
.record-time {
  display: block;
}

.header-title {
  font-size: 38rpx;
  font-weight: 900;
}

.header-subtitle {
  margin-top: 10rpx;
  font-size: 24rpx;
  line-height: 1.5;
  opacity: 0.86;
}

.feedback-content,
.records-section {
  padding: 24rpx;
}

.target-card,
.rating-section,
.tags-section,
.comment-section,
.record-card {
  margin-bottom: 20rpx;
  padding: 26rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.92);
}

.target-label {
  color: #8c3228;
  font-size: 22rpx;
  font-weight: 800;
}

.target-name {
  margin-top: 8rpx;
  font-size: 30rpx;
  font-weight: 900;
}

.section-title {
  margin-bottom: 20rpx;
  color: #4b2c1f;
  font-size: 30rpx;
  font-weight: 900;
}

.stars {
  display: flex;
  justify-content: center;
  gap: 14rpx;
}

.star {
  color: #d8c7ab;
  font-size: 58rpx;
  line-height: 1;
}

.star.active {
  color: #c19148;
}

.rating-text {
  margin-top: 16rpx;
  text-align: center;
  color: #8c765e;
  font-size: 25rpx;
}

.tags,
.record-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.tag,
.record-tag {
  min-height: 52rpx;
  display: flex;
  align-items: center;
  padding: 0 20rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #6d4b2d;
  font-size: 23rpx;
}

.tag.active {
  background: #8c3228;
  color: #fff8e8;
}

.comment-input {
  box-sizing: border-box;
  width: 100%;
  min-height: 230rpx;
  padding: 20rpx;
  border-radius: 10rpx;
  background: #fff8e8;
  color: #3f2b20;
  font-size: 26rpx;
  line-height: 1.5;
}

.word-count {
  display: block;
  margin-top: 10rpx;
  text-align: right;
  color: #9b8266;
  font-size: 22rpx;
}

.submit-section {
  padding: 0 24rpx 24rpx;
}

.submit-btn {
  width: 100%;
  min-height: 84rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
  font-size: 30rpx;
  font-weight: 900;
}

.submit-btn[disabled] {
  background: #cbbba3;
  color: rgba(255, 248, 232, 0.8);
}

.records-section {
  padding-top: 0;
}

.records-head,
.record-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.records-count {
  color: #9b7448;
  font-size: 22rpx;
}

.record-type {
  color: #8c3228;
  font-size: 22rpx;
  font-weight: 800;
}

.record-score {
  color: #c19148;
  font-size: 24rpx;
  font-weight: 900;
}

.record-target {
  margin-top: 8rpx;
  font-size: 28rpx;
  font-weight: 800;
}

.record-comment {
  margin-top: 10rpx;
  color: #66513f;
  font-size: 24rpx;
  line-height: 1.5;
}

.record-tags {
  margin-top: 12rpx;
}

.record-tag {
  min-height: 42rpx;
  font-size: 20rpx;
}

.record-time {
  margin-top: 12rpx;
  color: #9b8266;
  font-size: 21rpx;
}

.empty-records {
  padding: 46rpx 0;
  text-align: center;
  color: #9b8266;
  font-size: 24rpx;
}
</style>
