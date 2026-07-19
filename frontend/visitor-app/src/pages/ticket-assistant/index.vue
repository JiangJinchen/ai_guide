<template>
  <view class="ticket-page">
    <view class="summary-band">
      <view>
        <text class="eyebrow">票务助手</text>
        <text class="title">门票与观光车信息</text>
        <text class="desc">{{ assistant.positioning }}</text>
      </view>
    </view>

    <view class="tabs">
      <text
        class="tab"
        :class="{ active: activeType === item.value }"
        v-for="item in ticketTypes"
        :key="item.value"
        @click="activeType = item.value"
      >
        {{ item.label }}
      </text>
    </view>

    <view class="ticket-list">
      <view class="ticket-card" v-for="ticket in filteredProducts" :key="ticket.id">
        <view class="ticket-head">
          <view>
            <text class="ticket-name">{{ ticket.name }}</text>
          </view>
          <view class="price-block">
            <text class="price">{{ formatPrice(ticket.price) }}</text>
          </view>
        </view>

        <view class="policy" v-if="ticket.official_notice">
          <text>{{ ticket.official_notice }}</text>
        </view>
      </view>
    </view>

    <view class="empty-state" v-if="!loading && !filteredProducts.length">
      <text>暂无该类票务信息</text>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">售票与乘车点</text>
      </view>
      <view class="location-list">
        <view class="location-row" v-for="location in filteredLocations" :key="location.id">
          <view class="location-copy">
            <text class="location-name">{{ location.name }}</text>
          </view>
          <view class="icon-button nav-button" @click="openLocation(location)">
            <image class="icon-symbol" src="/static/icons/导航.png" mode="aspectFit"></image>
          </view>
        </view>
      </view>
    </view>

  </view>
</template>

<script>
import { get } from '@/utils/request'

const fallbackAssistant = {
  positioning: '票务助手只提供门票、观光车票、套票信息，不承接支付、出票、退票和核销。',
  products: [],
  service_locations: []
}

export default {
  data() {
    return {
      loading: false,
      activeType: 'all',
      assistant: fallbackAssistant,
      ticketTypes: [
        { label: '全部', value: 'all' },
        { label: '景区门票', value: 'scenic_ticket' },
        { label: '观光车', value: 'sightseeing_bus' },
        { label: '套票', value: 'package' }
      ]
    }
  },
  computed: {
    filteredProducts() {
      const products = this.assistant.products || []
      if (this.activeType === 'all') return products
      return products.filter(item => item.ticket_type === this.activeType)
    },
    filteredLocations() {
      const locations = this.assistant.service_locations || []
      return locations.filter(loc => {
        const name = (loc.name || '').toLowerCase()
        return name.includes('售票处') || name.includes('售票点')
      })
    }
  },
  onLoad() {
    this.loadTickets()
  },
  methods: {
    async loadTickets() {
      this.loading = true
      try {
        const data = await get('/ticket-assistant')
        this.assistant = {
          ...fallbackAssistant,
          ...data,
          products: data.products || [],
          service_locations: data.service_locations || []
        }
      } catch (error) {
        this.assistant = fallbackAssistant
        uni.showToast({ title: '票务信息暂不可用', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    formatPrice(price) {
      const value = Number(price)
      if (!Number.isFinite(value) || value < 0) return '以公告为准'
      return `￥${value.toFixed(value % 1 === 0 ? 0 : 2)}`
    },
    openLocation(location) {
      uni.openLocation({
        latitude: Number(location.latitude),
        longitude: Number(location.longitude),
        name: location.name,
        address: location.desc || '灵山胜境景区内'
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.ticket-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 54rpx;
  background: linear-gradient(180deg, #f6ecd9 0%, #efe0c8 50%, #f8f1e7 100%);
  color: #3b2a1f;
}

.summary-band {
  min-height: 220rpx;
  display: flex;
  justify-content: space-between;
  padding: 34rpx;
  border-radius: 10rpx;
  background:
    linear-gradient(135deg, rgba(132, 45, 36, 0.96), rgba(194, 143, 74, 0.9)),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.08) 0 3rpx, transparent 3rpx 22rpx);
  color: #fff8e8;
  box-shadow: 0 18rpx 42rpx rgba(83, 47, 24, 0.16);
}

.eyebrow,
.title,
.desc {
  display: block;
}

.eyebrow {
  font-size: 23rpx;
  color: rgba(255, 248, 232, 0.78);
}

.title {
  margin-top: 18rpx;
  font-size: 46rpx;
  font-weight: 900;
  letter-spacing: 0;
}

.desc {
  margin-top: 18rpx;
  max-width: 560rpx;
  font-size: 25rpx;
  line-height: 1.55;
}

.tabs {
  display: flex;
  gap: 14rpx;
  margin-top: 22rpx;
  margin-bottom: 22rpx;
  overflow-x: auto;
}

.tab {
  flex-shrink: 0;
  min-width: 130rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 58rpx;
  padding: 0 18rpx;
  border-radius: 8rpx;
  background: rgba(255, 251, 242, 0.9);
  color: #7c5838;
  font-size: 23rpx;
}

.tab.active {
  background: #8c3228;
  color: #fff8e8;
}

.ticket-card,
.section,
.risk-box {
  padding: 24rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.9);
}

.ticket-card {
  margin-bottom: 18rpx;
}

.ticket-head {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
}

.ticket-name,
.price,
.policy,
.location-name,
.location-desc {
  display: block;
}

.ticket-name {
  font-size: 32rpx;
  font-weight: 900;
  color: #3f2b20;
}

.price-block {
  min-width: 170rpx;
  text-align: right;
}

.price {
  color: #8c3228;
  font-size: 32rpx;
  font-weight: 900;
}

.policy {
  margin-top: 16rpx;
  color: #5f4a37;
  font-size: 23rpx;
  line-height: 1.5;
}

.policy.muted {
  color: #9a8063;
}

button {
  margin: 0;
}

.mini-btn {
  height: 68rpx;
  padding: 0 26rpx;
  border-radius: 8rpx;
  font-size: 24rpx;
  line-height: 68rpx;
  background: #efe0bd;
  color: #6a4b2f;
}

.empty-state {
  padding: 46rpx 0;
  text-align: center;
  color: #a68a68;
  font-size: 25rpx;
}

.section {
  margin-top: 26rpx;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12rpx;
}

.section-title {
  font-size: 31rpx;
  font-weight: 900;
}

.section-note {
  color: #9b7448;
  font-size: 22rpx;
}

.location-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.location-row:last-child {
  border-bottom: none;
}

.location-copy {
  flex: 1;
  min-width: 0;
}

.location-name {
  color: #3f2b20;
  font-size: 27rpx;
  font-weight: 800;
}

.location-desc {
  margin-top: 8rpx;
  color: #806b55;
  font-size: 23rpx;
}

.icon-button {
  width: 58rpx;
  height: 58rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #efe0bd;
  color: #814b00;
}

.icon-button:active {
  background: #e3cea4;
}

.icon-symbol {
  width: 32rpx;
  height: 32rpx;
  display: block;
}
</style>
