<template>
  <view class="home-page">
    <view class="top-search">
      <view class="search-box">
        <svg t="1784372367736" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2788" width="32" height="32"><path d="M843.093333 863.573333L723.626667 716.8c47.786667-47.786667 85.333333-116.053333 92.16-191.146667 20.48-177.493333-105.813333-337.92-286.72-354.986666S194.56 276.48 177.493333 453.973333s105.813333 337.92 286.72 354.986667c75.093333 6.826667 150.186667-10.24 208.213334-47.786667l116.053333 146.773334c6.826667 6.826667 17.066667 13.653333 23.893333 13.653333s17.066667 0 27.306667-6.826667c13.653333-13.653333 13.653333-37.546667 3.413333-51.2z m-372.053333-126.293333c-139.946667-13.653333-238.933333-136.533333-221.866667-276.48 13.653333-139.946667 136.533333-238.933333 276.48-221.866667s238.933333 136.533333 221.866667 276.48-139.946667 238.933333-276.48 221.866667z" fill="#707070" p-id="2789"></path></svg>
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
            <image class="hero-banner-img" :src="slide.img" mode="aspectFill"></image>
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
        <text class="section-more" @click="goToGuideList">更多</text>
      </view>
      <view class="hot-grid">
        <view
          class="hot-card"
          v-for="(spot, index) in hotSpots"
          :key="spot.id"
          @click="goToGuide(spot.id)"
        >
          <image class="hot-image" :src="spotImages[spot.name] || defaultImage" mode="aspectFill" />
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
        <text class="section-title">今日演出</text>
        <text class="section-more" @click="openActivityList('performance')">更多</text>
      </view>
      <view class="notice-list">
        <view
          class="notice-row"
          v-for="notice in notices"
          :key="notice.id + '-' + notice.event_time"
          @click="openActivityDetail(notice)"
        >
          <text class="notice-time">{{ notice.display_time || notice.event_time }}</text>
          <view class="notice-body">
            <text class="notice-title">{{ notice.name }}</text>
            <text class="notice-desc">{{ formatActivityDesc(notice) }}</text>
          </view>
        </view>
        <view class="notice-empty" v-if="!notices.length">
          <text>今日暂无演出安排</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { get, post } from '@/utils/request'

const fallbackSpots = [
  { id: 1, name: '灵山大佛', summary: '江南之花的地标佛像，适合祈福与远眺。' },
  { id: 2, name: '灵山梵宫', summary: '佛教文化艺术殿堂，建筑、壁画与演出的完美融合。' },
  { id: 3, name: '九龙灌浴', summary: '经典动态表演景观，适合亲子和初次游客。' },
  { id: 4, name: '五印坛城', summary: '藏传佛教文化空间，色彩绚丽，适合游览打卡。' }
]

import imgLingshandaf from '@/static/images/灵山大佛.jpg'
import imgLingshanfangong from '@/static/images/灵山梵宫.jpg'
import imgJiulongguanyu from '@/static/images/九龙灌浴.jpg'
import imgWuyintancheng from '@/static/images/五印坛城.jpg'
import imgBaiziximile from '@/static/images/百子戏弥勒.jpg'
import imgXiangfuchensi from '@/static/images/祥符禅寺.jpg'
import imgAyuwangzhu from '@/static/images/阿育王柱.jpg'
import imgWuzhimen from '@/static/images/五智门.jpg'
import imgFoztan from '@/static/images/佛足坛.jpg'
import imgPutiAvenue from '@/static/images/菩提大道.jpg'
import imgXiangmofudiao from '@/static/images/降魔浮雕.jpg'
import imgNianhuaguangchang from '@/static/images/拈花广场.jpg'
import imgFantianhuahai from '@/static/images/梵天花海.jpg'
import imgWudengHu from '@/static/images/五灯湖.jpg'
import imgLumingGu from '@/static/images/鹿鸣谷.jpg'
import imgManfeilongta from '@/static/images/曼飞龙塔.jpg'
import imgLingshanshengjing from '@/static/images/灵山胜境.jpg'
import imgFojiawenhua from '@/static/images/佛教文化博览馆.jpg'
import imgWujiyizhai from '@/static/images/无尽意斋.jpg'
import imgYoukezhongxin from '@/static/images/游客中心.jpg'
import imgLingshandaZhaoBi from '@/static/images/灵山大照壁.jpg'
import imgXiangyueHuajie from '@/static/images/香月花街.jpg'
import imgNianhuatang from '@/static/images/拈花堂.jpg'

import imgBanner1 from '@/static/images/banner1.jpg'
import imgBanner2 from '@/static/images/banner2.jpg'
import imgBanner3 from '@/static/images/banner3.jpg'

const SPOT_IMAGES = {
  '灵山大佛': imgLingshandaf,
  '灵山梵宫': imgLingshanfangong,
  '九龙灌浴': imgJiulongguanyu,
  '五印坛城': imgWuyintancheng,
  '百子戏弥勒': imgBaiziximile,
  '祥符禅寺': imgXiangfuchensi,
  '阿育王柱': imgAyuwangzhu,
  '五智门': imgWuzhimen,
  '佛足坛': imgFoztan,
  '菩提大道': imgPutiAvenue,
  '降魔浮雕': imgXiangmofudiao,
  '拈花广场': imgNianhuaguangchang,
  '梵天花海': imgFantianhuahai,
  '五灯湖': imgWudengHu,
  '鹿鸣谷': imgLumingGu,
  '曼飞龙塔': imgManfeilongta,
  '灵山胜境': imgLingshanshengjing,
  '佛教文化博览馆': imgFojiawenhua,
  '无尽意斋': imgWujiyizhai,
  '灵山胜境游客中心': imgYoukezhongxin,
  '灵山大照壁': imgLingshandaZhaoBi,
  '香月花街': imgXiangyueHuajie,
  '拈花堂': imgNianhuatang
}

export default {
  data() {
    return {
      keyword: '',
      activeHero: 0,
      activeService: 'student',
      spots: fallbackSpots,
      spotImages: SPOT_IMAGES,
      defaultImage: imgLingshanshengjing,
      heroSlides: [
        {
          kicker: '无锡 灵山 胜境',
          title: '一日入胜境',
          desc: '灵山秀水、佛像与梵音，尽享悠然。',
          img: imgBanner1
        },
        {
          kicker: '梵宫华章',
          title: '见建筑如诗',
          desc: '在艺术、壁画与光影之间感受佛教文化。',
          img: imgBanner2
        },
        {
          kicker: '祈福朝圣',
          title: '闻一声晨钟',
          desc: '从六度桥到灵山大佛，步步皆有故事。',
          img: imgBanner3
        }
      ],
      serviceGroups: [
        {
          key: 'student',
          name: '导览服务',
          subtitle: '从问答到讲解，把景区故事交给智能导游',
          icon: '导',
          summary: 'AI问答、景点讲解和路线规划。',
          items: [
            { name: 'AI数字人', url: '/pages/chat/index', tab: true, desc: '语音问答与智能导览' },
            { name: '景点讲解', url: '/pages/guide/index', desc: '查看景点详情' },
            { name: '路线规划', url: '/pages/route-planning/index', desc: '定制游览顺序' }
          ]
        },
        {
          key: 'teacher',
          name: '游玩服务',
          subtitle: '安排更顺畅的游玩体验',
          icon: '游',
          summary: '附近景点、票务信息和个性化推荐。',
          items: [
            { name: '附近景点', url: '/pages/nearby-spots/index', desc: '基于位置推荐' },
            { name: '票务助手', url: '/pages/ticket-assistant/index', desc: '门票与观光车信息' },
            { name: '个性推荐', url: '/pages/recommendation/index', desc: '按偏好推荐景点' }
          ]
        },
        {
          key: 'education',
          name: '活动服务',
          subtitle: '演出时间与体验提醒',
          icon: '活',
          summary: '演出时间和体验介绍。',
          items: [
            { name: '演出时间', url: '/pages/activity-service/index?type=performance', desc: '查看即将开场场次' },
            { name: '禅修体验', url: '/pages/activity-service/index?type=zen', desc: '体验介绍与现场指引' }
          ]
        },
        {
          key: 'alumni',
          name: '游客服务',
          subtitle: '管理个人信息',
          icon: '服',
          summary: '个人中心和客服入口。',
          items: [
            { name: '个人中心', url: '/pages/profile/index', tab: true, desc: '偏好与足迹' },
            { name: '联系客服', url: '/pages/customer-service/index', desc: '人工客服入口' }
          ]
        }
      ],
      notices: [],
      todayRefreshTimer: null
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
    this.loadUpcomingActivities()
  },
  onShow() {
    this.loadUpcomingActivities()
    this.startTodayRefresh()
  },
  onHide() {
    this.stopTodayRefresh()
  },
  onUnload() {
    this.stopTodayRefresh()
  },
  methods: {
    async loadSpots() {
      try {
        const list = await get('/spots')
        if (Array.isArray(list) && list.length) {
          this.spots = list.map(item => ({
            id: item.id,
            name: item.spot_name || item.name,
            summary: item.description || item.culture_connotation || '热门景点'
          }))
        }
      } catch (e) {
        this.spots = fallbackSpots
      }
    },
    async loadUpcomingActivities() {
      try {
        const data = await get('/activities/upcoming', { limit: 4 })
        this.notices = data.items || []
      } catch (e) {
        this.notices = []
      }
    },
    startTodayRefresh() {
      this.stopTodayRefresh()
      this.todayRefreshTimer = setInterval(() => {
        this.loadUpcomingActivities()
      }, 5 * 60 * 1000)
    },
    stopTodayRefresh() {
      if (this.todayRefreshTimer) {
        clearInterval(this.todayRefreshTimer)
        this.todayRefreshTimer = null
      }
    },
    formatActivityDesc(activity) {
      const place = activity.location ? `地点：${activity.location}` : '地点以现场公告为准'
      const note = activity.schedule_note || '具体以景区当日公告为准'
      return `${place} · ${note}`
    },
    handleSearch() {
      if (this.keyword.trim()) {
        const behaviorData = { behavior_type: 'search', keyword: this.keyword.trim() }
        post('/behavior', behaviorData).catch(() => {})
      }
    },
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
        uni.showToast({ title: '宸蹭负鎮ㄥ畾浣嶅埌浠婃棩鐏靛北', icon: 'none' })
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
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
    },
    openActivityList(type = 'performance') {
      uni.navigateTo({ url: `/pages/activity-service/index?type=${type}` })
    },
    openActivityDetail(activity) {
      uni.navigateTo({
        url: `/pages/activity-service/index?id=${activity.id}&type=${activity.activity_type || 'performance'}&time=${activity.event_time || ''}`
      })
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

.hero-banner-img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transform: scale(1);
  animation: bannerZoom 4.2s linear infinite;
}

@keyframes bannerZoom {
  0% {
    transform: scale(1);
  }
  100% {
    transform: scale(1.2);
  }
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
  box-shadow: 0 16rpx 34rpx rgba(68, 39, 22, 0.14);
}

.hot-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
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

.notice-empty {
  padding: 34rpx 22rpx;
  color: #9b8266;
  font-size: 24rpx;
  text-align: center;
}
</style>

