<template>
  <view class="home-page">
    <view class="top-search">
      <view class="search-box">
        <text class="search-mark">搜</text>
        <input
          class="search-input"
          v-model="keyword"
          placeholder="搜索服务 / 景点"
          confirm-type="search"
          @input="handleSearch"
          @confirm="openFirstResult"
        />
        <text v-if="keyword" class="clear" @click="clearSearch">清</text>
      </view>

      <view class="search-results" v-if="keyword && filteredResults.length">
        <view
          class="result-row"
          v-for="item in filteredResults"
          :key="item.type + '-' + item.id"
          @click="openResult(item)"
        >
          <text class="result-type">{{ item.type === 'service' ? '服务' : '景点' }}</text>
          <view class="result-main">
            <text class="result-title">{{ item.name }}</text>
            <text class="result-desc">{{ item.desc }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="hero">
      <swiper
        class="hero-swiper"
        circular
        autoplay
        :interval="4200"
        :duration="900"
        @change="onHeroChange"
      >
        <swiper-item v-for="(slide, index) in heroSlides" :key="slide.title">
          <view class="hero-slide" :class="['hero-' + index, { active: activeHero === index }]">
            <view class="hero-shade"></view>
            <view class="hero-copy">
              <text class="hero-kicker">{{ slide.kicker }}</text>
              <text class="hero-title">{{ slide.title }}</text>
              <text class="hero-desc">{{ slide.desc }}</text>
            </view>
          </view>
        </swiper-item>
      </swiper>

      <view class="service-dock">
        <view
          class="service-group"
          v-for="group in serviceGroups"
          :key="group.key"
          :class="{ active: activeService === group.key }"
          @click="activeService = group.key"
        >
          <view class="group-tab">
            <text class="group-icon">{{ group.icon }}</text>
            <text class="group-name">{{ group.name }}</text>
          </view>
          <view class="group-services" v-if="activeService === group.key">
            <text class="group-summary">{{ group.summary }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="service-panel">
      <view class="service-panel-head">
        <view>
          <text class="service-panel-title">{{ activeGroup.name }}</text>
          <text class="service-panel-subtitle">{{ activeGroup.subtitle }}</text>
        </view>
        <text class="service-panel-mark">{{ activeGroup.icon }}</text>
      </view>
      <view class="service-grid">
        <view
          class="service-item"
          v-for="service in activeGroup.items"
          :key="service.name"
          @click="goToService(service)"
        >
          <text class="service-item-name">{{ service.name }}</text>
          <text class="service-item-desc">{{ service.desc }}</text>
        </view>
      </view>
    </view>

    <view class="section">
      <view class="section-head">
        <text class="section-title">热门景点</text>
        <text class="section-more" @click="goToGuideList">全部景点</text>
      </view>
      <view class="hot-grid">
        <view
          class="hot-card"
          v-for="(spot, index) in hotSpots"
          :key="spot.id"
          :class="'spot-tone-' + (index % 4)"
          @click="goToGuide(spot.id)"
        >
          <view class="hot-overlay"></view>
          <view class="hot-content">
            <text class="hot-name">{{ spot.name }}</text>
            <text class="hot-summary">{{ spot.summary }}</text>
          </view>
        </view>
      </view>
    </view>

    <view class="section today-section">
      <view class="section-head">
        <text class="section-title">今日灵山</text>
        <text class="section-more">实时提醒</text>
      </view>
      <view class="notice-list">
        <view class="notice-row" v-for="notice in notices" :key="notice.title">
          <text class="notice-time">{{ notice.time }}</text>
          <view class="notice-body">
            <text class="notice-title">{{ notice.title }}</text>
            <text class="notice-desc">{{ notice.desc }}</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

const fallbackSpots = [
  { id: 1, name: '灵山大佛', summary: '太湖之滨的地标佛像，适合祈福与远眺。' },
  { id: 2, name: '灵山梵宫', summary: '佛教艺术殿堂，建筑、壁画与演出皆值得停留。' },
  { id: 3, name: '九龙灌浴', summary: '经典动态表演场景，适合亲子和初到游客。' },
  { id: 4, name: '五印坛城', summary: '藏传佛教文化空间，色彩浓烈，适合拍照打卡。' }
]

export default {
  data() {
    return {
      keyword: '',
      activeHero: 0,
      activeService: 'student',
      spots: fallbackSpots,
      heroSlides: [
        { kicker: '无锡 太湖 灵山', title: '一日入胜境', desc: '沿山水、佛光与梵音，慢游灵山。' },
        { kicker: '梵宫华彩', title: '见建筑如诗', desc: '在穹顶、壁画与光影之间感受佛教艺术。' },
        { kicker: '礼佛祈福', title: '听一场晨钟', desc: '从九龙灌浴到灵山大佛，步步皆有故事。' }
      ],
      serviceGroups: [
        {
          key: 'student',
          name: '导览服务',
          subtitle: '从问答到讲解，把景区故事交给智能导游',
          icon: '游',
          summary: '从问答到讲解，把景区故事交给智能导游。',
          items: [
            { name: 'AI数字人', url: '/pages/chat/index', tab: true, desc: '语音问答与智能讲解' },
            { name: '景点讲解', url: '/pages/guide/index', desc: '查看景点详情' },
            { name: '路线规划', url: '/pages/route-planning/index', desc: '定制游览顺序' }
          ]
        },
        {
          key: 'teacher',
          name: '游玩服务',
          subtitle: '安排更顺路的游览体验',
          icon: '行',
          summary: '安排更顺路的游览体验。',
          items: [
            { name: '附近景点', url: '/pages/nearby-spots/index', desc: '基于定位推荐' },
            { name: '个性推荐', url: '/pages/recommendation/index', desc: '按偏好推荐景点' },
            { name: '服务评价', url: '/pages/feedback/index', desc: '提交体验反馈' }
          ]
        },
        {
          key: 'education',
          name: '活动服务',
          subtitle: '今日演出、禅修与祈福活动',
          icon: '禅',
          summary: '聚合今日演出、禅修体验与祈福活动提醒。',
          items: [
            { name: '今日灵山', anchor: 'today', desc: '演出与活动提醒' },
            { name: '禅修体验', anchor: 'today', desc: '预约体验预告' },
            { name: '祈福点灯', anchor: 'today', desc: '活动信息' }
          ]
        },
        {
          key: 'alumni',
          name: '游客服务',
          subtitle: '管理个人信息与预约',
          icon: '客',
          summary: '管理个人信息入口。',
          items: [
            { name: '个人中心', url: '/pages/profile/index', tab: true, desc: '偏好和足迹' },
            { name: '我的预约', url: '/pages/profile/index', tab: true, desc: '查看预约记录' },
            { name: '联系客服', url: '/pages/profile/index', tab: true, desc: '人工客服入口' }
          ]
        }
      ],
      notices: [
        { time: '09:30', title: '梵宫吉祥颂', desc: '上午场即将开始，建议提前二十分钟入场。' },
        { time: '10:00', title: '九龙灌浴', desc: '今日正常演出，雨天以现场通知为准。' },
        { time: '14:00', title: '禅修体验', desc: '体验名额有限，可在服务台咨询预约。' },
        { time: '全天', title: '祈福点灯', desc: '灵山大佛广场周边开放祈福服务。' }
      ]
    }
  },
  computed: {
    hotSpots() {
      return this.spots.slice(0, 4)
    },
    allServices() {
      return this.serviceGroups.flatMap(group =>
        group.items.map(item => ({
          ...item,
          id: `${group.key}-${item.name}`,
          type: 'service'
        }))
      )
    },
    activeGroup() {
      return this.serviceGroups.find(group => group.key === this.activeService) || this.serviceGroups[0]
    },
    filteredResults() {
      const word = this.keyword.trim().toLowerCase()
      if (!word) return []
      const serviceResults = this.allServices
        .filter(item => item.name.includes(word) || item.desc.includes(word))
        .map(item => ({ ...item, type: 'service' }))
      const spotResults = this.spots
        .filter(item => item.name.includes(word) || item.summary.includes(word))
        .map(item => ({ ...item, type: 'spot', desc: item.summary }))
      return [...serviceResults, ...spotResults].slice(0, 8)
    }
  },
  onLoad() {
    this.loadSpots()
  },
  methods: {
    async loadSpots() {
      try {
        const list = await get('/spots')
        if (Array.isArray(list) && list.length) {
          this.spots = list.map(item => ({
            id: item.id,
            name: item.spot_name || item.name,
            summary: item.description || item.culture_connotation || '灵山胜境人气景点。'
          }))
        }
      } catch (e) {
        this.spots = fallbackSpots
      }
    },
    handleSearch() {},
    clearSearch() {
      this.keyword = ''
    },
    openFirstResult() {
      if (this.filteredResults.length) this.openResult(this.filteredResults[0])
    },
    openResult(item) {
      if (item.type === 'spot') {
        this.goToGuide(item.id)
        return
      }
      this.goToService(item)
    },
    goToService(service) {
      if (service.anchor === 'today') {
        this.keyword = ''
        uni.showToast({ title: '已为您定位到今日灵山', icon: 'none' })
        return
      }
      if (service.tab) {
        uni.switchTab({ url: service.url })
      } else if (service.url) {
        uni.navigateTo({ url: service.url })
      }
    },
    onHeroChange(e) {
      this.activeHero = e.detail.current
    },
    goToGuideList() {
      uni.navigateTo({ url: '/pages/guide/index' })
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.home-page {
  min-height: 100vh;
  padding: 24rpx 24rpx 48rpx;
  background:
    radial-gradient(circle at 8% 4%, rgba(188, 65, 48, 0.16), transparent 34%),
    linear-gradient(180deg, #f5ead8 0%, #efe1ca 45%, #f7f1e7 100%);
  color: #33251b;
}

.top-search {
  position: relative;
  z-index: 20;
}

.search-box {
  display: flex;
  align-items: center;
  height: 86rpx;
  padding: 0 26rpx;
  border: 2rpx solid rgba(127, 73, 37, 0.2);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.94);
  box-shadow: 0 14rpx 40rpx rgba(73, 45, 24, 0.1);
}

.search-mark,
.clear {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #8b2d22;
  color: #fff7e6;
  font-size: 24rpx;
}

.clear {
  background: #b89155;
}

.search-input {
  flex: 1;
  height: 84rpx;
  padding: 0 18rpx;
  font-size: 28rpx;
  color: #33251b;
}

.search-results {
  position: absolute;
  left: 0;
  right: 0;
  top: 100rpx;
  padding: 12rpx;
  border-radius: 10rpx;
  background: rgba(255, 252, 245, 0.98);
  box-shadow: 0 18rpx 46rpx rgba(50, 32, 18, 0.18);
}

.result-row {
  display: flex;
  align-items: center;
  padding: 18rpx;
  border-bottom: 1rpx solid rgba(139, 45, 34, 0.08);
}

.result-row:last-child {
  border-bottom: none;
}

.result-type {
  width: 72rpx;
  height: 42rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 18rpx;
  border-radius: 6rpx;
  background: #efe0bd;
  color: #7d3429;
  font-size: 22rpx;
}

.result-main {
  flex: 1;
  min-width: 0;
}

.result-title,
.result-desc {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-title {
  font-size: 28rpx;
  font-weight: 700;
}

.result-desc {
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #8c7a66;
}

.hero {
  position: relative;
  height: 500rpx;
  margin-top: 24rpx;
  overflow: hidden;
  border-radius: 12rpx;
  box-shadow: 0 24rpx 60rpx rgba(64, 36, 20, 0.18);
}

.hero-swiper,
.hero-slide {
  height: 100%;
}

.hero-slide {
  position: relative;
  overflow: hidden;
}

.hero-slide::before {
  content: '';
  position: absolute;
  inset: 0;
  transform: scale(1);
  transition: transform 4.2s linear;
  background-size: cover;
  background-position: center;
}

.hero-slide.active::before {
  transform: scale(1.2);
}

.hero-0::before {
  background:
    linear-gradient(105deg, rgba(112, 29, 23, 0.84), rgba(112, 29, 23, 0.18) 48%, rgba(17, 44, 43, 0.38)),
    radial-gradient(circle at 82% 18%, rgba(236, 202, 115, 0.52), transparent 24%),
    linear-gradient(135deg, #8d3228, #d5a85f 52%, #35534b);
}

.hero-1::before {
  background:
    linear-gradient(105deg, rgba(60, 40, 28, 0.82), rgba(72, 32, 24, 0.28)),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.16) 0 4rpx, transparent 4rpx 22rpx),
    linear-gradient(135deg, #61321f, #b28445 55%, #203f3c);
}

.hero-2::before {
  background:
    linear-gradient(105deg, rgba(50, 72, 64, 0.76), rgba(127, 48, 34, 0.32)),
    radial-gradient(circle at 72% 40%, rgba(247, 220, 138, 0.5), transparent 26%),
    linear-gradient(135deg, #274a42, #b05a38 58%, #ead092);
}

.hero-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(25, 18, 14, 0.04), rgba(25, 18, 14, 0.36));
}

.hero-copy {
  position: absolute;
  left: 38rpx;
  right: 38rpx;
  top: 58rpx;
  color: #fff7e6;
}

.hero-kicker,
.hero-title,
.hero-desc {
  display: block;
}

.hero-kicker {
  width: fit-content;
  padding: 8rpx 16rpx;
  border: 1rpx solid rgba(255, 247, 230, 0.55);
  font-size: 22rpx;
}

.hero-title {
  margin-top: 26rpx;
  font-size: 58rpx;
  font-weight: 800;
  letter-spacing: 0;
}

.hero-desc {
  margin-top: 14rpx;
  max-width: 470rpx;
  font-size: 26rpx;
  line-height: 1.6;
}

.service-dock {
  position: absolute;
  left: 28rpx;
  right: 28rpx;
  bottom: 0;
  height: 148rpx;
  display: flex;
  align-items: stretch;
  background: rgba(255, 250, 240, 0.86);
  backdrop-filter: blur(8rpx);
}

.service-group {
  display: flex;
  width: 116rpx;
  min-width: 116rpx;
  overflow: hidden;
  transition: width 0.25s ease;
}

.service-group.active {
  width: 400rpx;
  flex: 1;
}

.group-tab {
  width: 116rpx;
  min-width: 116rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff7e6;
  background: #8f3026;
}

.service-group:nth-child(2) .group-tab {
  background: #c19148;
}

.service-group:nth-child(3) .group-tab {
  background: #2e5c73;
}

.service-group:nth-child(4) .group-tab {
  background: #c7654e;
}

.group-icon {
  width: 38rpx;
  height: 38rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10rpx;
  border: 1rpx solid rgba(255,255,255,0.7);
  border-radius: 50%;
  font-size: 22rpx;
}

.group-name {
  font-size: 24rpx;
  font-weight: 700;
}

.group-services {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 18rpx 24rpx;
}

.group-summary {
  display: block;
  width: 100%;
  color: #5c493a;
  font-size: 23rpx;
  line-height: 1.45;
  word-break: normal;
}

.service-panel {
  margin-top: 24rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(120, 72, 37, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.9);
  box-shadow: 0 12rpx 30rpx rgba(70, 41, 22, 0.08);
}

.service-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.service-panel-title,
.service-panel-subtitle {
  display: block;
}

.service-panel-title {
  color: #4b2b1f;
  font-size: 32rpx;
  font-weight: 850;
}

.service-panel-subtitle {
  margin-top: 6rpx;
  color: #8c765e;
  font-size: 22rpx;
}

.service-panel-mark {
  width: 58rpx;
  height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #8b2d22;
  color: #fff7e6;
  font-size: 26rpx;
}

.service-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
}

.service-item {
  min-height: 118rpx;
  padding: 20rpx;
  border-radius: 8rpx;
  background: #f2e2c2;
}

.service-item:nth-child(2n) {
  background: #ead5ad;
}

.service-item-name,
.service-item-desc {
  display: block;
}

.service-item-name {
  color: #4c3020;
  font-size: 27rpx;
  font-weight: 850;
}

.service-item-desc {
  margin-top: 8rpx;
  color: #80694f;
  font-size: 22rpx;
  line-height: 1.35;
}

.section {
  margin-top: 34rpx;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20rpx;
}

.section-title {
  font-size: 36rpx;
  font-weight: 800;
  color: #4b2b1f;
}

.section-more {
  font-size: 24rpx;
  color: #9b6b38;
}

.hot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20rpx;
}

.hot-card {
  position: relative;
  min-height: 250rpx;
  overflow: hidden;
  border-radius: 10rpx;
  background-size: cover;
  background-position: center;
  box-shadow: 0 16rpx 34rpx rgba(68, 39, 22, 0.14);
}

.spot-tone-0 {
  background:
    linear-gradient(140deg, rgba(75, 33, 24, 0.1), rgba(15, 50, 44, 0.35)),
    linear-gradient(135deg, #743327, #d8ad64);
}

.spot-tone-1 {
  background:
    linear-gradient(140deg, rgba(42, 31, 23, 0.18), rgba(133, 40, 32, 0.26)),
    linear-gradient(135deg, #34483f, #c99455);
}

.spot-tone-2 {
  background:
    linear-gradient(140deg, rgba(80, 27, 24, 0.1), rgba(33, 65, 75, 0.38)),
    linear-gradient(135deg, #884433, #e2c17a);
}

.spot-tone-3 {
  background:
    linear-gradient(140deg, rgba(32, 51, 51, 0.14), rgba(98, 43, 30, 0.32)),
    linear-gradient(135deg, #285263, #d4a04f);
}

.hot-overlay {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(0,0,0,0.04), rgba(0,0,0,0.58)),
    repeating-linear-gradient(90deg, rgba(255,255,255,0.07) 0 2rpx, transparent 2rpx 18rpx);
}

.hot-content {
  position: absolute;
  left: 22rpx;
  right: 22rpx;
  bottom: 22rpx;
  color: #fff7e6;
}

.hot-name,
.hot-summary {
  display: block;
}

.hot-name {
  font-size: 32rpx;
  font-weight: 800;
}

.hot-summary {
  margin-top: 10rpx;
  font-size: 23rpx;
  line-height: 1.45;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.notice-list {
  overflow: hidden;
  border: 1rpx solid rgba(120, 72, 37, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.84);
}

.notice-row {
  display: flex;
  padding: 22rpx;
  border-bottom: 1rpx solid rgba(120, 72, 37, 0.1);
}

.notice-row:last-child {
  border-bottom: none;
}

.notice-time {
  width: 86rpx;
  color: #8d2f25;
  font-size: 24rpx;
  font-weight: 800;
}

.notice-body {
  flex: 1;
  min-width: 0;
}

.notice-title,
.notice-desc {
  display: block;
}

.notice-title {
  font-size: 28rpx;
  color: #3f2c20;
  font-weight: 700;
}

.notice-desc {
  margin-top: 6rpx;
  color: #7c6a57;
  font-size: 23rpx;
  line-height: 1.45;
}
</style>
