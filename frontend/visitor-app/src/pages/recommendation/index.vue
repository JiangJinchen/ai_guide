<template>
  <view class="recommendation-page">
    <view class="page-head">
      <view>
        <text class="page-title">个性化推荐</text>
        <text class="page-subtitle">基于您的游览偏好和行为记录</text>
      </view>
    </view>

    <view class="section-block" v-if="Object.keys(userProfile).length > 0">
      <view class="section-head">
        <text class="section-title">您的游览偏好</text>
      </view>
      <view class="profile-tags">
        <view 
          class="profile-tag" 
          v-for="(score, tag) in userProfile" 
          :key="tag"
          :style="{ opacity: score, backgroundColor: getTagColor(tag) }"
        >
          <text class="tag-name">{{ getTagLabel(tag) }}</text>
          <text class="tag-score">{{ (score * 100).toFixed(0) }}%</text>
        </view>
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

const SPOT_IMAGES = {
  '灵山大佛': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Grand%20bronze%20Buddha%20statue%20on%20mountain%20scenic%20spot%20with%20blue%20sky&image_size=landscape_16_9',
  '灵山梵宫': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Magnificent%20Buddhist%20palace%20architecture%20with%20golden%20roof%20and%20intricate%20designs&image_size=landscape_16_9',
  '九龙灌浴': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Dynamic%20fountain%20show%20with%20nine%20dragons%20spraying%20water%20on%20Buddha%20statue&image_size=landscape_16_9',
  '五印坛城': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Tibetan%20Buddhist%20mandala%20temple%20with%20colorful%20paintings%20and%20golden%20decoration&image_size=landscape_16_9',
  '百子戏弥勒': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Bronze%20sculpture%20of%20Maitreya%20Buddha%20with%20hundreds%20of%20children%20playing%20around&image_size=landscape_16_9',
  '祥符禅寺': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Ancient%20Buddhist%20temple%20with%20traditional%20Chinese%20architecture%20and%20incense&image_size=landscape_16_9',
  '阿育王柱': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Ancient%20stone%20pillar%20with%20Buddhist%20carvings%20in%20scenic%20area&image_size=landscape_16_9',
  '五明桥': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Traditional%20Chinese%20five%20arches%20bridge%20over%20lake%20with%20beautiful%20scenery&image_size=landscape_16_9',
  '五智门': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Magnificent%20Chinese%20traditional%20gateway%20with%20carvings%20in%20Buddhist%20temple&image_size=landscape_16_9',
  '佛足坛': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Buddhist%20footprint%20stones%20sculpture%20in%20temple%20garden&image_size=landscape_16_9',
  '菩提大道': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Long%20avenue%20lined%20with%20bodhi%20trees%20leading%20to%20Buddhist%20temple&image_size=landscape_16_9',
  '降魔浮雕': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Relief%20sculpture%20depicting%20Buddha%20overcoming%20demons%20in%20temple&image_size=landscape_16_9',
  '拈花广场': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Beautiful%20square%20with%20flower%20sculpture%20in%20Buddhist%20scenic%20area&image_size=landscape_16_9',
  '梵天花海': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Beautiful%20flower%20sea%20garden%20with%20colorful%20flowers%20near%20Buddhist%20temple&image_size=landscape_16_9',
  '五灯湖': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Serene%20lake%20with%20lanterns%20in%20Chinese%20garden%20scenic%20spot&image_size=landscape_16_9',
  '鹿鸣谷': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Peaceful%20valley%20with%20deer%20statues%20in%20mountain%20scenic%20area&image_size=landscape_16_9',
  '曼飞龙塔': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Stupa%20pagoda%20with%20multiple%20spires%20in%20Buddhist%20scenic%20spot&image_size=landscape_16_9',
  '灵山胜境': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Panoramic%20view%20of%20Lingshan%20Buddhist%20scenic%20area%20with%20mountains%20and%20lake&image_size=landscape_16_9',
  '佛教文化博览馆': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Modern%20museum%20exhibiting%20Buddhist%20culture%20artifacts%20and%20history&image_size=landscape_16_9',
  '无尽意斋': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Traditional%20Chinese%20tea%20house%20and%20meditation%20room%20in%20temple&image_size=landscape_16_9',
  '灵山胜境游客中心': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Modern%20visitor%20center%20building%20in%20scenic%20area%20with%20glass%20facade&image_size=landscape_16_9',
  '灵山大照壁': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Large%20traditional%20Chinese%20screen%20wall%20with%20Buddhist%20paintings&image_size=landscape_16_9',
  '香月花街': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Traditional%20Chinese%20street%20with%20shops%20and%20flowers%20at%20night&image_size=landscape_16_9',
  '拈花堂': 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Zen%20meditation%20hall%20with%20traditional%20Chinese%20architecture&image_size=landscape_16_9'
}

const DEFAULT_IMAGE = 'https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image?prompt=Beautiful%20Buddhist%20scenic%20spot%20landscape%20with%20mountains%20and%20temples&image_size=landscape_16_9'

export default {
  data() {
    return {
      recommendations: [],
      userProfile: {},
      preferredTags: []
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
        this.userProfile = res.user_profile || {}
        this.preferredTags = res.user_preferred_tags || []
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
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    },
    onImageError(e) {
      e.target.style.display = 'none'
    },
    getSpotImage(name) {
      return SPOT_IMAGES[name] || DEFAULT_IMAGE
    },
    getTagLabel(tag) {
      const labels = {
        'zen_culture': '禅意文化',
        'buddha_history': '佛教历史',
        'architecture_art': '建筑艺术',
        'buddha_performance': '佛教表演',
        'lake_scenery': '湖景风光',
        'parent_child': '亲子互动',
        'ancient_temple': '古寺文化',
        'leisure_service': '休闲服务'
      }
      return labels[tag] || tag
    },
    getTagColor(tag) {
      const colors = {
        'zen_culture': '#8c3228',
        'buddha_history': '#a65c3e',
        'architecture_art': '#37251a',
        'buddha_performance': '#5a4a3a',
        'lake_scenery': '#2d5a4a',
        'parent_child': '#b8860b',
        'ancient_temple': '#4a3728',
        'leisure_service': '#6b4423'
      }
      return colors[tag] || '#8c3228'
    }
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
  margin: 0 30rpx 24rpx;
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

.section-count {
  font-size: 26rpx;
  color: #8b7355;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
  padding: 0 30rpx 24rpx;
}

.profile-tag {
  display: flex;
  align-items: center;
  padding: 12rpx 24rpx;
  border-radius: 24rpx;
  color: #fff8e8;
}

.tag-name {
  font-size: 26rpx;
  margin-right: 8rpx;
}

.tag-score {
  font-size: 24rpx;
  opacity: 0.9;
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
