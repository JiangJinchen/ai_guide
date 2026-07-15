<template>
  <view class="recommendation-page">
    <view class="page-head">
      <view>
        <text class="page-title">个性化推荐</text>
        <text class="page-subtitle">基于您的游览偏好和行为记录</text>
      </view>
    </view>

    <view class="section-block empty-block" v-if="recommendations.length === 0">
      <view class="section-head">
        <text class="section-title">推荐景点</text>
      </view>
      <view class="empty-state">
        <view class="empty-illustration">
          <text>推</text>
        </view>
        <text class="empty-title">暂无推荐内容</text>
        <text class="empty-desc">开始浏览景点，获取个性化推荐</text>
      </view>
    </view>

    <view 
      class="section-block rec-card-block"
      v-for="(item, index) in recommendations"
      :key="item.spot_id"
      @click="goToGuide(item.spot_id)"
    >
      <image 
        class="rec-bg" 
        :src="getSpotImage(item.spot_name)" 
        mode="aspectFill"
        @error="onImageError($event)"
      />
      <view class="rec-overlay"></view>
      <view class="rec-rank" :class="'rank-' + (index + 1)">{{ index + 1 }}</view>
      <view class="rec-content">
        <text class="rec-name">{{ item.spot_name }}</text>
        <text class="rec-reason">{{ item.reason }}</text>
      </view>
      <view class="rec-arrow">›</view>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'
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

const SPOT_IMAGES = {
  '灵山大佛': imgLingshandaf,
  '灵山梵宫': imgLingshanfangong,
  '九龙灌浴': imgJiulongguanyu,
  '五印坛城': imgWuyintancheng,
  '百子戏弥勒': imgBaiziximile,
  '祥符禅寺': imgXiangfuchensi,
  '阿育王柱': imgAyuwangzhu,
  '五明桥': imgLingshanshengjing,
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

const DEFAULT_IMAGE = imgLingshanshengjing

export default {
  data() {
    return {
      recommendations: []
    }
  },
  onShow() {
    this.loadRecommendations()
  },
  methods: {
    async loadRecommendations() {
      try {
        const userId = uni.getStorageSync('userId') || 'guest'
        const res = await get('/recommendation', { user_id: userId })
        const list = res.recommendations || res || []
        this.recommendations = list.map(item => ({
          spot_id: item.spot_id || item.id,
          spot_name: item.spot_name || item.name,
          reason: item.reason || '根据您的浏览偏好推荐'
        }))
      } catch (e) {
        this.recommendations = [
          { spot_id: 1, spot_name: '灵山大佛', reason: '热门景点推荐' },
          { spot_id: 2, spot_name: '灵山梵宫', reason: '建筑艺术殿堂' },
          { spot_id: 3, spot_name: '九龙灌浴', reason: '动态表演场景' },
          { spot_id: 4, spot_name: '五印坛城', reason: '藏传佛教文化' }
        ]
      }
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
    },
    onImageError(e) {
      if (e.target && e.target.style) {
        e.target.style.display = 'none'
      }
    },
    getSpotImage(name) {
      return SPOT_IMAGES[name] || DEFAULT_IMAGE
    },
  }
}
</script>

<style lang="scss" scoped>
.recommendation-page {
  min-height: 100vh;
  padding-bottom: 48rpx;
  background: linear-gradient(180deg, #fdf8f0 0%, #f5efe3 100%);
  color: #37251a;
}

.page-head {
  padding: 56rpx 30rpx 44rpx;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  color: #fff8e8;
}

.page-title {
  display: block;
  font-size: 44rpx;
  font-weight: 900;
}

.page-subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: rgba(255, 248, 232, 0.8);
}

.section-block {
  margin: -28rpx 30rpx 24rpx;
  border-radius: 16rpx;
  background: rgba(255, 248, 232, 0.95);
  box-shadow: 0 4rpx 20rpx rgba(55, 37, 26, 0.08);
  overflow: hidden;
}

.rec-card-block {
  position: relative;
  margin: 10rpx 30rpx 24rpx;
  min-height: 280rpx;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24rpx 30rpx;
}

.section-title {
  font-size: 32rpx;
  font-weight: bold;
  color: #37251a;
}

.empty-block {
  margin: -28rpx 30rpx 24rpx;
}

.rec-bg {
  width: 100%;
  height: 280rpx;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
}

.rec-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(transparent 30%, rgba(55, 37, 26, 0.7));
}

.rec-rank {
  position: absolute;
  top: 20rpx;
  left: 20rpx;
  width: 48rpx;
  height: 48rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24rpx;
  font-weight: bold;
  color: #fff8e8;
}

.rank-1 {
  background: linear-gradient(135deg, #f2ca70, #d4a84b);
}

.rank-2 {
  background: linear-gradient(135deg, #c0c0c0, #a0a0a0);
}

.rank-3 {
  background: linear-gradient(135deg, #cd7f32, #b87333);
}

.rec-content {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24rpx 80rpx 24rpx 24rpx;
}

.rec-name {
  display: block;
  font-size: 32rpx;
  font-weight: bold;
  color: #fff8e8;
  margin-bottom: 12rpx;
  text-shadow: 0 2rpx 4rpx rgba(0, 0, 0, 0.3);
}

.rec-reason {
  display: block;
  font-size: 26rpx;
  color: rgba(255, 248, 232, 0.9);
  line-height: 1.5;
}

.rec-arrow {
  position: absolute;
  top: 50%;
  right: 24rpx;
  transform: translateY(-50%);
  font-size: 40rpx;
  color: rgba(255, 248, 232, 0.9);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60rpx 0;
}

.empty-illustration {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: linear-gradient(135deg, #8c3228, #a65c3e);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 30rpx;
  
  text {
    font-size: 50rpx;
    font-weight: bold;
    color: #fff8e8;
  }
}

.empty-title {
  font-size: 32rpx;
  color: #37251a;
  margin-bottom: 16rpx;
}

.empty-desc {
  font-size: 26rpx;
  color: #8b7355;
}
</style>
