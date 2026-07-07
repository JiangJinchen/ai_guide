<template>
  <view class="spot-page">
    <view v-if="!spotDetail && !isLoading" class="spot-picker">
      <view class="picker-head">
        <text class="picker-title">景点讲解</text>
        <text class="picker-subtitle">择一处胜景，听一段缘起</text>
      </view>
      <view
        class="picker-row"
        v-for="(spot, index) in spots"
        :key="spot.id"
        :class="'tone-' + (index % 4)"
        @click="loadSpot(spot.id)"
      >
        <view class="picker-image"></view>
        <view class="picker-info">
          <text class="picker-name">{{ spot.spot_name || spot.name }}</text>
          <text class="picker-desc">{{ spot.description }}</text>
        </view>
        <text class="picker-arrow">›</text>
      </view>
    </view>

    <view v-if="spotDetail" class="detail">
      <view class="cover" :class="'cover-tone-' + (spotDetail.id % 4)">
        <view class="cover-shade"></view>
        <view class="cover-note">
          <text class="cover-kicker">灵山胜境</text>
          <text class="cover-title">{{ spotName }}</text>
          <text class="cover-subtitle">{{ shortDescription }}</text>
        </view>
        <view class="panorama-tip">AR / VR 全景导览预留</view>
      </view>

      <view class="content">
        <view class="intro-block">
          <view class="title-row">
            <text class="block-title">{{ spotName }}</text>
            <text class="crowd-tag">{{ crowdLevel }}</text>
          </view>
          <text class="paragraph">{{ guideText }}</text>
        </view>

        <view class="info-grid">
          <view class="info-cell" v-for="item in keyInfo" :key="item.label">
            <text class="info-label">{{ item.label }}</text>
            <text class="info-value">{{ item.value }}</text>
          </view>
        </view>

        <view class="section-card">
          <text class="section-title">历史由来</text>
          <text class="paragraph">{{ cultureText }}</text>
        </view>

        <view class="section-card">
          <text class="section-title">打卡点与游览亮点</text>
          <view class="highlight-list">
            <text class="highlight-item" v-for="item in highlights" :key="item">{{ item }}</text>
          </view>
        </view>

        <view class="section-card">
          <text class="section-title">票务与预约</text>
          <view class="plain-row">
            <text class="plain-label">门票</text>
            <text class="plain-value">{{ ticketInfo }}</text>
          </view>
          <view class="plain-row">
            <text class="plain-label">预约</text>
            <text class="plain-value">{{ reserveInfo }}</text>
          </view>
        </view>

        <view class="section-card" v-if="performances.length">
          <view class="title-row">
            <text class="section-title">演出日程</text>
            <text class="next-show">最近 {{ performances[0].time }}</text>
          </view>
          <view class="show-row" v-for="show in performances" :key="show.time + show.name">
            <text class="show-time">{{ show.time }}</text>
            <text class="show-name">{{ show.name }}</text>
          </view>
        </view>

        <view class="section-card">
          <view class="title-row">
            <text class="section-title">地理位置</text>
            <text class="map-link" @click="openNavigation">去导航</text>
          </view>
          <view class="map-card" @click="openNavigation">
            <view class="map-line horizontal"></view>
            <view class="map-line vertical"></view>
            <view class="map-pin">{{ spotName.slice(0, 2) }}</view>
            <text class="map-address">{{ spotDetail.location || '灵山胜境景区内' }}</text>
          </view>
        </view>

        <view class="section-card">
          <text class="section-title">周边信息</text>
          <view class="nearby-row" v-for="item in nearbyItems" :key="item.name" @click="openNearby(item)">
            <view>
              <text class="nearby-name">{{ item.name }}</text>
              <text class="nearby-desc">{{ item.desc }}</text>
            </view>
            <text class="nearby-action">{{ item.type === 'spot' ? '详情' : '导航' }}</text>
          </view>
        </view>

        <view class="section-card">
          <text class="section-title">游客评价</text>
          <view class="review-row" v-for="review in reviews" :key="review.name">
            <text class="review-name">{{ review.name }}</text>
            <text class="review-text">{{ review.text }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="loading" v-if="isLoading">
      <text>正在展开景点卷轴...</text>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

const fallbackSpots = [
  { id: 1, spot_name: '灵山大佛', description: '太湖之滨的祈福地标。' },
  { id: 2, spot_name: '灵山梵宫', description: '集建筑、壁画、演艺于一体的佛教艺术殿堂。' },
  { id: 3, spot_name: '九龙灌浴', description: '以佛陀诞生为主题的动态景观。' },
  { id: 4, spot_name: '五印坛城', description: '藏传佛教文化体验空间。' }
]

export default {
  data() {
    return {
      spotId: null,
      spotDetail: null,
      guideContent: null,
      spots: fallbackSpots,
      isLoading: false
    }
  },
  computed: {
    spotName() {
      return this.spotDetail?.spot_name || this.spotDetail?.name || '灵山景点'
    },
    shortDescription() {
      const text = this.spotDetail?.description || '灵山胜境代表性景点。'
      return text.length > 42 ? text.slice(0, 42) + '...' : text
    },
    guideText() {
      return this.guideContent?.content || this.spotDetail?.description || '这里有深厚的文化底蕴，适合停下脚步慢慢游览。'
    },
    cultureText() {
      return this.guideContent?.culture || this.spotDetail?.culture_connotation || '该景点承载了灵山胜境的文化叙事，将建筑、礼佛、山水与游览体验融合在一起。'
    },
    highlights() {
      const raw = this.guideContent?.highlights || this.spotDetail?.highlights
      if (raw) return String(raw).split(/[、,，；;]/).filter(Boolean).slice(0, 5)
      return ['代表性视角拍照', '听取文化讲解', '参与祈福体验', '留意建筑细节']
    },
    crowdLevel() {
      const levels = ['舒适', '适中', '较热闹']
      return `人流 ${levels[(this.spotDetail?.id || 0) % levels.length]}`
    },
    keyInfo() {
      return [
        { label: '开放', value: this.spotDetail?.open_info || '以景区当日公告为准' },
        { label: '建议停留', value: this.spotName.includes('梵宫') ? '45-70分钟' : '25-45分钟' },
        { label: '适合', value: this.spotName.includes('九龙') ? '亲子 / 表演' : '祈福 / 拍照' },
        { label: '热度', value: this.crowdLevel.replace('人流 ', '') }
      ]
    },
    ticketInfo() {
      return this.spotName.includes('梵宫') ? '含在景区门票内，特殊演出以现场票务为准' : '通常随景区门票入园'
    },
    reserveInfo() {
      return this.spotName.includes('体验') ? '建议提前预约' : '当前无需单独预约，后续可接入预约码'
    },
    performances() {
      if (this.spotName.includes('梵宫')) {
        return [
          { time: '09:30', name: '吉祥颂上午场' },
          { time: '14:00', name: '吉祥颂下午场' }
        ]
      }
      if (this.spotName.includes('九龙')) {
        return [
          { time: '10:00', name: '九龙灌浴' },
          { time: '15:00', name: '九龙灌浴' }
        ]
      }
      return []
    },
    nearbyItems() {
      const otherSpots = this.spots
        .filter(item => item.id !== this.spotDetail?.id)
        .slice(0, 2)
        .map(item => ({
          type: 'spot',
          id: item.id,
          name: item.spot_name || item.name,
          desc: '附近景点，可继续查看详情'
        }))
      return [
        ...otherSpots,
        { type: 'food', name: '香月花街素食', desc: '步行可达，适合午间休憩' },
        { type: 'hotel', name: '景区周边旅宿', desc: '可跳转导航，后续接入预订' }
      ]
    },
    reviews() {
      return [
        { name: '游客甲', text: '讲解内容很清楚，适合第一次来灵山的人。' },
        { name: '游客乙', text: '下午光线很好，拍照和慢游都很舒服。' }
      ]
    }
  },
  onLoad(options) {
    if (options && options.spot_id) {
      this.loadSpot(Number(options.spot_id))
    } else {
      this.loadSpotsList()
    }
  },
  methods: {
    async loadSpotsList() {
      try {
        const list = await get('/spots')
        if (Array.isArray(list) && list.length) this.spots = list
      } catch (e) {
        this.spots = fallbackSpots
      }
    },
    async loadSpot(id) {
      this.isLoading = true
      this.spotId = id
      if (!this.spots.length) await this.loadSpotsList()

      try {
        const [spot, guide] = await Promise.all([
          get(`/spots/${id}`),
          get(`/guide/${id}`)
        ])
        this.spotDetail = spot
        this.guideContent = guide
      } catch (e) {
        const fallback = fallbackSpots.find(item => item.id === id) || fallbackSpots[0]
        this.spotDetail = fallback
        this.guideContent = {
          content: fallback.description,
          culture: '这里是灵山胜境的重要游览节点，适合结合智能导览了解历史、礼仪与建筑细节。'
        }
      } finally {
        this.isLoading = false
      }
    },
    openNavigation() {
      const lat = Number(this.spotDetail?.latitude)
      const lon = Number(this.spotDetail?.longitude)
      if (lat && lon) {
        uni.openLocation({
          latitude: lat,
          longitude: lon,
          name: this.spotName,
          address: this.spotDetail.location || '灵山胜境景区内'
        })
      } else {
        uni.showToast({ title: '后续接入地图导航', icon: 'none' })
      }
    },
    openNearby(item) {
      if (item.type === 'spot') {
        this.loadSpot(item.id)
        uni.pageScrollTo({ scrollTop: 0, duration: 200 })
      } else {
        uni.showToast({ title: '后续接入导航', icon: 'none' })
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.spot-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at 88% 0, rgba(183, 128, 54, 0.18), transparent 32%),
    linear-gradient(180deg, #f7eddd, #efe0c6);
  color: #36271c;
}

.spot-picker {
  padding: 28rpx;
}

.picker-head {
  padding: 36rpx 8rpx 28rpx;
}

.picker-title,
.picker-subtitle {
  display: block;
}

.picker-title {
  font-size: 46rpx;
  font-weight: 800;
  color: #783126;
}

.picker-subtitle {
  margin-top: 10rpx;
  color: #8b745b;
  font-size: 26rpx;
}

.picker-row {
  display: flex;
  align-items: center;
  min-height: 172rpx;
  margin-bottom: 20rpx;
  padding: 18rpx;
  border-radius: 10rpx;
  background: rgba(255, 251, 241, 0.88);
  box-shadow: 0 14rpx 34rpx rgba(75, 43, 24, 0.1);
}

.picker-image {
  width: 150rpx;
  height: 120rpx;
  margin-right: 22rpx;
  border-radius: 8rpx;
  background: linear-gradient(135deg, #7b3026, #d7a656);
}

.tone-1 .picker-image { background: linear-gradient(135deg, #2f5969, #c08a43); }
.tone-2 .picker-image { background: linear-gradient(135deg, #355447, #c96545); }
.tone-3 .picker-image { background: linear-gradient(135deg, #824632, #e0bf76); }

.picker-info {
  flex: 1;
  min-width: 0;
}

.picker-name,
.picker-desc {
  display: block;
}

.picker-name {
  font-size: 31rpx;
  font-weight: 800;
}

.picker-desc {
  margin-top: 10rpx;
  color: #806b55;
  font-size: 24rpx;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.picker-arrow {
  margin-left: 16rpx;
  color: #b28a56;
  font-size: 46rpx;
}

.cover {
  position: relative;
  height: 540rpx;
  overflow: hidden;
  background-size: cover;
}

.cover::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(110deg, rgba(255,255,255,0.08) 0 3rpx, transparent 3rpx 20rpx),
    linear-gradient(135deg, #713127, #d7a65c 58%, #294c44);
}

.cover-tone-1::before { background: linear-gradient(135deg, #743127, #d9b469 52%, #203f3d); }
.cover-tone-2::before { background: linear-gradient(135deg, #294f63, #b65b3c 54%, #e0c27e); }
.cover-tone-3::before { background: linear-gradient(135deg, #334f44, #c89550 54%, #7b3027); }

.cover-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(30, 21, 15, 0.06), rgba(30, 21, 15, 0.58));
}

.cover-note {
  position: absolute;
  left: 34rpx;
  right: 34rpx;
  bottom: 70rpx;
  color: #fff8e8;
}

.cover-kicker,
.cover-title,
.cover-subtitle {
  display: block;
}

.cover-kicker {
  width: fit-content;
  padding: 8rpx 16rpx;
  border: 1rpx solid rgba(255, 248, 232, 0.55);
  font-size: 22rpx;
}

.cover-title {
  margin-top: 18rpx;
  font-size: 58rpx;
  font-weight: 900;
}

.cover-subtitle {
  margin-top: 12rpx;
  font-size: 26rpx;
  line-height: 1.55;
}

.panorama-tip {
  position: absolute;
  right: 24rpx;
  top: 28rpx;
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.86);
  color: #7d3026;
  font-size: 22rpx;
}

.content {
  padding: 26rpx;
}

.intro-block,
.section-card {
  margin-bottom: 22rpx;
  padding: 28rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.86);
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.block-title,
.section-title {
  display: block;
  font-size: 32rpx;
  font-weight: 850;
  color: #4b2c1f;
}

.crowd-tag,
.next-show,
.map-link {
  flex-shrink: 0;
  padding: 8rpx 14rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #843429;
  font-size: 22rpx;
}

.paragraph {
  display: block;
  margin-top: 18rpx;
  color: #66513f;
  font-size: 27rpx;
  line-height: 1.75;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-bottom: 22rpx;
}

.info-cell {
  min-height: 118rpx;
  padding: 22rpx;
  border-radius: 10rpx;
  background: #7c3028;
  color: #fff7e6;
}

.info-cell:nth-child(2) { background: #b38648; }
.info-cell:nth-child(3) { background: #2f5b68; }
.info-cell:nth-child(4) { background: #415646; }

.info-label,
.info-value {
  display: block;
}

.info-label {
  font-size: 22rpx;
  opacity: 0.82;
}

.info-value {
  margin-top: 10rpx;
  font-size: 26rpx;
  font-weight: 800;
  line-height: 1.35;
}

.highlight-list {
  margin-top: 20rpx;
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.highlight-item {
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #6c4a2d;
  font-size: 24rpx;
}

.plain-row,
.show-row,
.nearby-row,
.review-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.plain-row:last-child,
.show-row:last-child,
.nearby-row:last-child,
.review-row:last-child {
  border-bottom: none;
}

.plain-label,
.show-time,
.nearby-action,
.review-name {
  flex-shrink: 0;
  color: #8a3328;
  font-weight: 800;
  font-size: 25rpx;
}

.plain-value,
.show-name,
.review-text {
  flex: 1;
  color: #67523f;
  font-size: 25rpx;
  line-height: 1.45;
  text-align: right;
}

.map-card {
  position: relative;
  height: 250rpx;
  margin-top: 22rpx;
  overflow: hidden;
  border-radius: 10rpx;
  background:
    radial-gradient(circle at 44% 46%, rgba(132, 52, 41, 0.3), transparent 14%),
    linear-gradient(135deg, #eadbbf, #d5bd8a);
}

.map-line {
  position: absolute;
  background: rgba(121, 74, 38, 0.18);
}

.map-line.horizontal {
  left: 0;
  right: 0;
  top: 50%;
  height: 8rpx;
  transform: rotate(-12deg);
}

.map-line.vertical {
  top: 0;
  bottom: 0;
  left: 55%;
  width: 8rpx;
  transform: rotate(18deg);
}

.map-pin {
  position: absolute;
  left: 50%;
  top: 44%;
  transform: translate(-50%, -50%);
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #8a3328;
  color: #fff8e8;
  font-size: 22rpx;
  font-weight: 800;
}

.map-address {
  position: absolute;
  left: 24rpx;
  right: 24rpx;
  bottom: 20rpx;
  color: #5f4835;
  font-size: 24rpx;
}

.nearby-row {
  align-items: center;
}

.nearby-name,
.nearby-desc {
  display: block;
}

.nearby-name {
  color: #3f2b20;
  font-size: 27rpx;
  font-weight: 800;
}

.nearby-desc {
  margin-top: 8rpx;
  color: #806b55;
  font-size: 23rpx;
}

.loading {
  padding-top: 220rpx;
  text-align: center;
  color: #8a3328;
  font-size: 28rpx;
}
</style>
