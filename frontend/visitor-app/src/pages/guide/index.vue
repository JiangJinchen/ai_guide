<template>
  <view class="guide-page">
    <view class="page-head">
      <text class="page-title">景点讲解</text>
      <text class="page-subtitle">选择景点，查看介绍并收听语音讲解</text>
    </view>

    <view v-if="isLoading" class="state-block">
      <text>正在加载景点...</text>
    </view>

    <view v-else class="spot-list">
      <view
        v-for="spot in spots"
        :key="spot.id"
        class="spot-row"
        @click="openSpotDetail(spot.id)"
      >
        <image
          class="spot-image"
          :src="getSpotImage(spot.spot_name || spot.name)"
          mode="aspectFill"
        />
        <view class="spot-info">
          <text class="spot-name">{{ spot.spot_name || spot.name }}</text>
          <text class="spot-desc">{{ spot.description || '查看景点详情与语音讲解' }}</text>
        </view>
        <text class="spot-arrow">›</text>
      </view>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'
import { getSpotImage } from '@/utils/spot-images'

const FALLBACK_SPOTS = [
  { id: 1, spot_name: '灵山大佛', description: '太湖之滨的祈福地标。' },
  { id: 2, spot_name: '灵山梵宫', description: '集建筑、壁画、演艺于一体的佛教艺术殿堂。' },
  { id: 3, spot_name: '九龙灌浴', description: '以佛陀诞生为主题的动态景观。' },
  { id: 4, spot_name: '五印坛城', description: '藏传佛教风格的文化体验空间。' }
]

export default {
  data() {
    return {
      spots: [],
      isLoading: true
    }
  },
  onLoad(options) {
    const spotId = Number(options?.spot_id)
    if (Number.isFinite(spotId) && spotId > 0) {
      uni.redirectTo({ url: `/pages/spot-detail/index?spot_id=${spotId}` })
      return
    }
    this.loadSpotsList()
  },
  methods: {
    getSpotImage,
    async loadSpotsList() {
      this.isLoading = true
      try {
        const list = await get('/spots')
        this.spots = Array.isArray(list) && list.length ? list : FALLBACK_SPOTS
      } catch (error) {
        this.spots = FALLBACK_SPOTS
      } finally {
        this.isLoading = false
      }
    },
    openSpotDetail(id) {
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.guide-page {
  min-height: 100vh;
  padding-bottom: 48rpx;
  background: linear-gradient(180deg, #f7eddd, #efe0c6);
  color: #36271c;
}

.page-head {
  padding: 64rpx 36rpx 34rpx;
}

.page-title,
.page-subtitle,
.spot-name,
.spot-desc {
  display: block;
}

.page-title {
  color: #783126;
  font-size: 46rpx;
  font-weight: 800;
}

.page-subtitle {
  margin-top: 10rpx;
  color: #806b55;
  font-size: 26rpx;
}

.spot-list {
  padding: 0 28rpx;
}

.spot-row {
  display: flex;
  align-items: center;
  min-height: 156rpx;
  margin-bottom: 20rpx;
  padding: 18rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.1);
  border-radius: 8rpx;
  background: rgba(255, 251, 241, 0.92);
  box-shadow: 0 12rpx 28rpx rgba(75, 43, 24, 0.08);
}

.spot-image {
  width: 150rpx;
  height: 120rpx;
  flex-shrink: 0;
  margin-right: 22rpx;
  border-radius: 8rpx;
}

.spot-info {
  flex: 1;
  min-width: 0;
}

.spot-name {
  font-size: 31rpx;
  font-weight: 800;
}

.spot-desc {
  display: -webkit-box;
  margin-top: 10rpx;
  overflow: hidden;
  color: #806b55;
  font-size: 24rpx;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.spot-arrow {
  margin-left: 16rpx;
  color: #a8753e;
  font-size: 46rpx;
}

.state-block {
  min-height: 360rpx;
  padding-top: 120rpx;
  color: #806b55;
  font-size: 27rpx;
  text-align: center;
}
</style>
