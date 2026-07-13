<template>
  <view class="service-page">
    <view class="service-hero">
      <view class="hero-icon">📞</view>
      <text class="hero-title">客服中心</text>
      <text class="hero-sub">我们随时为您服务</text>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">客服热线</text>
      </view>
      <view class="phone-card" @click="makeCall">
        <text class="phone-icon">📱</text>
        <view class="phone-info">
          <text class="phone-number">{{ serviceInfo.phone }}</text>
          <text class="phone-hint">点击拨打</text>
        </view>
        <text class="phone-arrow">></text>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">营业时间</text>
      </view>
      <view class="hours-list">
        <view class="hours-item">
          <text class="hours-label">工作日</text>
          <text class="hours-value">{{ serviceInfo.business_hours }}</text>
        </view>
        <view class="hours-item">
          <text class="hours-label">节假日</text>
          <text class="hours-value">{{ serviceInfo.holiday_hours }}</text>
        </view>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">常见问题</text>
      </view>
      <view class="faq-list">
        <view 
          class="faq-item" 
          v-for="(faq, index) in serviceInfo.faqs" 
          :key="index"
          @click="toggleFaq(index)"
        >
          <view class="faq-header">
            <text class="faq-question">{{ faq.question }}</text>
            <text class="faq-arrow" :class="{ expanded: expandedIndex === index }">▼</text>
          </view>
          <view class="faq-answer" v-show="expandedIndex === index">
            <text class="answer-text">{{ faq.answer }}</text>
          </view>
        </view>
      </view>
    </view>

    <text class="version">灵山胜境 AI导览 v1.0.0</text>
  </view>
</template>

<script>
import { get } from '@/utils/request'

export default {
  data() {
    return {
      serviceInfo: {
        phone: '',
        business_hours: '',
        holiday_hours: '',
        faqs: []
      },
      expandedIndex: -1
    }
  },
  onLoad() {
    this.loadServiceInfo()
  },
  methods: {
    async loadServiceInfo() {
      try {
        const res = await get('/customer-service')
        this.serviceInfo = res
      } catch (e) {
        this.serviceInfo = {
          phone: '400-828-8888',
          business_hours: '08:00 - 17:30',
          holiday_hours: '08:00 - 18:00',
          faqs: [
            { question: '门票有效期是多久？', answer: '门票当日有效，入园后可全天游览。' },
            { question: '景区内可以使用无人机吗？', answer: '为保障游客安全及文物保护，景区内禁止使用无人机等飞行设备。' },
            { question: '景区提供行李寄存服务吗？', answer: '游客中心设有行李寄存处，提供免费寄存服务。' }
          ]
        }
      }
    },
    makeCall() {
      uni.makePhoneCall({
        phoneNumber: this.serviceInfo.phone,
        fail: () => {
          uni.showToast({ title: '无法拨打', icon: 'none' })
        }
      })
    },
    toggleFaq(index) {
      this.expandedIndex = this.expandedIndex === index ? -1 : index
    }
  }
}
</script>

<style lang="scss" scoped>
.service-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 52rpx;
  background:
    radial-gradient(circle at 90% 0, rgba(191, 139, 65, 0.18), transparent 30%),
    linear-gradient(180deg, #f6ecd9, #efe0c8 52%, #f8f1e7);
  color: #39281d;
}

.service-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 30rpx;
  border-radius: 12rpx;
  background:
    linear-gradient(135deg, rgba(126, 48, 39, 0.96), rgba(196, 145, 75, 0.9)),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.08) 0 3rpx, transparent 3rpx 22rpx);
  color: #fff8e8;
  box-shadow: 0 18rpx 40rpx rgba(83, 47, 24, 0.16);
}

.hero-icon {
  font-size: 72rpx;
  margin-bottom: 16rpx;
}

.hero-title {
  font-size: 40rpx;
  font-weight: 900;
}

.hero-sub {
  margin-top: 8rpx;
  font-size: 26rpx;
  opacity: 0.85;
}

.section-card {
  margin-top: 22rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.88);
}

.section-head {
  margin-bottom: 18rpx;
}

.section-title {
  font-size: 31rpx;
  font-weight: 900;
  color: #4b2c1f;
}

.phone-card {
  display: flex;
  align-items: center;
  padding: 24rpx;
  border-radius: 10rpx;
  background: linear-gradient(135deg, rgba(140, 50, 40, 0.08), rgba(196, 145, 75, 0.06));
}

.phone-icon {
  font-size: 48rpx;
  margin-right: 20rpx;
}

.phone-info {
  flex: 1;
}

.phone-number {
  display: block;
  font-size: 34rpx;
  font-weight: 900;
  color: #8c3228;
}

.phone-hint {
  display: block;
  margin-top: 4rpx;
  font-size: 22rpx;
  color: #9b7448;
}

.phone-arrow {
  font-size: 26rpx;
  color: #9b7448;
}

.hours-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.hours-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.hours-item:last-child {
  border-bottom: none;
}

.hours-label {
  font-size: 28rpx;
  color: #4b2c1f;
}

.hours-value {
  font-size: 28rpx;
  font-weight: 800;
  color: #8c3228;
}

.faq-list {
  display: flex;
  flex-direction: column;
  gap: 12rpx;
}

.faq-item {
  border-radius: 8rpx;
  background: rgba(140, 50, 40, 0.04);
  overflow: hidden;
}

.faq-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20rpx 20rpx;
}

.faq-question {
  flex: 1;
  font-size: 28rpx;
  font-weight: 800;
  color: #4b2c1f;
  line-height: 1.4;
}

.faq-arrow {
  flex-shrink: 0;
  margin-left: 16rpx;
  font-size: 20rpx;
  color: #9b7448;
  transition: transform 0.3s;
}

.faq-arrow.expanded {
  transform: rotate(180deg);
}

.faq-answer {
  padding: 0 20rpx 20rpx;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.answer-text {
  font-size: 26rpx;
  color: #6b5344;
  line-height: 1.6;
}

.version {
  display: block;
  margin-top: 32rpx;
  text-align: center;
  color: #b39a7a;
  font-size: 22rpx;
}
</style>