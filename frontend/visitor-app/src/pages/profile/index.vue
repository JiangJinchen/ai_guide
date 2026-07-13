<template>
  <view class="profile-page">
    <view class="profile-hero">
      <view class="avatar-ring">
        <text class="avatar-text">{{ nickname.slice(0, 1) }}</text>
      </view>
      <view class="hero-info">
        <input class="name-input" v-model="nickname" @blur="saveProfile" />
        <input class="sign-input" v-model="signature" @blur="saveProfile" />
        <text class="user-id">ID {{ shortUserId }}</text>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的游览偏好</text>
        <text class="section-sub">基于游览行为分析</text>
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

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的游览足迹</text>
        <text class="section-sub">{{ footprints.length }} 个景点</text>
      </view>
      <view class="footprint-map" v-if="footprints.length > 0">
        <svg class="map-svg" viewBox="0 0 400 200">
          <polyline
            v-if="footprints.length > 1"
            :points="svgPathPoints"
            fill="none"
            stroke="#8c3228"
            stroke-width="2"
            stroke-dasharray="5,3"
            opacity="0.6"
          />
          <circle
            v-for="(item, index) in footprints"
            :key="'circle-' + item.spot_name"
            :cx="item.svgX"
            :cy="item.svgY"
            r="8"
            :fill="index === 0 ? '#2d5a4a' : index === footprints.length - 1 ? '#8c3228' : '#a65c3e'"
          />
        </svg>
        <view
          v-for="(item, index) in footprints"
          :key="'label-' + item.spot_name"
          class="map-pin"
          :style="{ left: (item.svgX / 4) + '%', top: (item.svgY / 2) + '%' }"
          @click="goToGuide(item.spot_id)"
        >
          <text class="pin-name">{{ item.spot_name }}</text>
        </view>
      </view>
      <view class="empty-footprint" v-else>
        <text class="empty-icon">👣</text>
        <text class="empty-text">暂无游览记录</text>
        <text class="empty-hint">使用导航前往景点后将记录足迹</text>
      </view>
    </view>

    <view class="section-card">
      <view class="menu-row" @click="goToFeedback">
        <text class="menu-title">评价与反馈</text>
        <text class="menu-arrow">></text>
      </view>
      <view class="menu-row" @click="contactService">
        <text class="menu-title">联系景区人工客服</text>
        <text class="menu-arrow">></text>
      </view>
      <view class="menu-row danger" @click="logout">
        <text class="menu-title">退出登录</text>
        <text class="menu-arrow">></text>
      </view>
    </view>

    <text class="version">灵山胜境 AI导览 v1.0.0</text>

    <FeedbackModal 
      ref="feedbackModal" 
      @submit="handleFeedbackSubmit"
    />
  </view>
</template>

<script>
import { get } from '@/utils/request'
import { promptForFeedback } from '@/utils/feedback'
import FeedbackModal from '@/components/FeedbackModal'

export default {
  components: {
    FeedbackModal
  },
  data() {
    return {
      userId: '',
      nickname: '灵山游客',
      signature: '愿今日山水有好风',
      userProfile: {},
      footprints: [],
      isPageActive: true
    }
  },
  computed: {
    shortUserId() {
      return this.userId ? this.userId.slice(-8) : 'guest'
    },
    svgPathPoints() {
      return this.footprints.map(item => `${item.svgX},${item.svgY}`).join(' ')
    }
  },
  onLoad() {
    this.userId = uni.getStorageSync('userId') || 'guest'
    const saved = uni.getStorageSync('visitorProfile')
    if (saved) {
      this.nickname = saved.nickname || this.nickname
      this.signature = saved.signature || this.signature
    }
    this.loadUserProfile()
  },
  methods: {
    async loadUserProfile() {
      try {
        const res = await get('/recommendation', { user_id: this.userId })
        this.userProfile = res.user_profile || {}
      } catch (e) {
        this.userProfile = {
          'zen_culture': 0.75,
          'architecture_art': 0.62,
          'buddha_history': 0.45,
          'lake_scenery': 0.38
        }
      }
    },
    async loadFootprints() {
      try {
        const res = await get('/footprints', { user_id: this.userId })
        const data = res.footprints || []
        this.footprints = this.convertCoords(data)
      } catch (e) {
        this.footprints = []
      }
    },
    convertCoords(data) {
      const minLat = 31.426
      const maxLat = 31.434
      const minLon = 120.094
      const maxLon = 120.105
      
      return data.map(item => {
        const lat = parseFloat(item.latitude) || 0
        const lon = parseFloat(item.longitude) || 0
        
        let svgX = 50
        let svgY = 100
        
        if (lat && lon) {
          svgX = ((lon - minLon) / (maxLon - minLon)) * 320 + 40
          svgY = ((maxLat - lat) / (maxLat - minLat)) * 160 + 20
        } else {
          svgX = 40 + Math.random() * 320
          svgY = 20 + Math.random() * 160
        }
        
        return {
          ...item,
          svgX: Math.round(svgX),
          svgY: Math.round(svgY)
        }
      })
    },
    saveProfile() {
      uni.setStorageSync('visitorProfile', {
        nickname: this.nickname || '灵山游客',
        signature: this.signature || '愿今日山水有好风'
      })
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    },
    goToFeedback() {
      uni.navigateTo({
        url: '/pages/feedback/index?feedback_type=app&target_type=app&target_id=app&target_name=App%E4%BD%BF%E7%94%A8%E4%BD%93%E9%AA%8C&source=profile'
      })
    },
    maybePromptAppFeedback() {
      if (!this.isPageActive) return
      const launchCount = Number(uni.getStorageSync('appLaunchCount') || 0)
      if (launchCount < 3) return
      this.$refs.feedbackModal.open({
        title: '评价',
        content: '如果你愿意，花几秒钟告诉我们 App 哪些地方好用、哪些地方还需要改进。',
        params: {
          feedback_type: 'app',
          target_type: 'app',
          target_id: 'app',
          target_name: 'App 使用体验',
          source: 'profile'
        }
      })
    },
    handleFeedbackSubmit(data) {
      this.$refs.feedbackModal.close()
    },
    onHide() {
      this.isPageActive = false
      this.$refs.feedbackModal?.close()
    },
    onUnload() {
      this.isPageActive = false
      this.$refs.feedbackModal?.close()
    },
    onShow() {
      this.isPageActive = true
      this.loadFootprints()
      this.maybePromptAppFeedback()
    },
    contactService() {
      uni.navigateTo({ url: '/pages/customer-service/index' })
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '这将清除当前游客身份并生成新的访客ID。',
        success: (res) => {
          if (res.confirm) {
            const userId = 'visitor_' + Date.now()
            uni.setStorageSync('userId', userId)
            this.userId = userId
            uni.showToast({ title: '已退出', icon: 'success' })
          }
        }
      })
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
.profile-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 52rpx;
  background:
    radial-gradient(circle at 90% 0, rgba(191, 139, 65, 0.18), transparent 30%),
    linear-gradient(180deg, #f6ecd9, #efe0c8 52%, #f8f1e7);
  color: #39281d;
}

.profile-hero {
  display: flex;
  align-items: center;
  min-height: 220rpx;
  padding: 30rpx;
  border-radius: 12rpx;
  background:
    linear-gradient(135deg, rgba(126, 48, 39, 0.96), rgba(196, 145, 75, 0.9)),
    repeating-linear-gradient(115deg, rgba(255,255,255,0.08) 0 3rpx, transparent 3rpx 22rpx);
  color: #fff8e8;
  box-shadow: 0 18rpx 40rpx rgba(83, 47, 24, 0.16);
}

.avatar-ring {
  width: 132rpx;
  height: 132rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 26rpx;
  border: 4rpx solid rgba(255, 248, 232, 0.64);
  border-radius: 50%;
  background: rgba(255, 248, 232, 0.16);
}

.avatar-text {
  font-size: 48rpx;
  font-weight: 900;
}

.hero-info {
  flex: 1;
  min-width: 0;
}

.name-input,
.sign-input,
.user-id {
  display: block;
  width: 100%;
  color: #fff8e8;
}

.name-input {
  height: 56rpx;
  font-size: 36rpx;
  font-weight: 900;
}

.sign-input {
  height: 48rpx;
  margin-top: 6rpx;
  font-size: 24rpx;
  color: rgba(255, 248, 232, 0.82);
}

.user-id {
  margin-top: 10rpx;
  font-size: 22rpx;
  color: rgba(255, 248, 232, 0.66);
}

.section-card {
  margin-top: 22rpx;
  margin-bottom: 22rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.88);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.section-title {
  font-size: 31rpx;
  font-weight: 900;
  color: #4b2c1f;
}

.section-sub {
  color: #9b7448;
  font-size: 22rpx;
}

.profile-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
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

.menu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.menu-row:last-child {
  border-bottom: none;
}

.menu-title {
  color: #3f2b20;
  font-size: 27rpx;
  font-weight: 800;
}

.menu-arrow {
  flex-shrink: 0;
  color: #9b7448;
  font-size: 26rpx;
}

.footprint-map {
  position: relative;
  height: 330rpx;
  overflow: hidden;
  border-radius: 10rpx;
  background:
    radial-gradient(circle at 18% 28%, rgba(140, 50, 40, 0.18), transparent 16%),
    radial-gradient(circle at 70% 62%, rgba(47, 91, 104, 0.16), transparent 18%),
    linear-gradient(135deg, #ead9b9, #d8be86);
}

.map-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.map-pin {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 6rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.92);
  box-shadow: 0 4rpx 12rpx rgba(75, 43, 24, 0.12);
  transform: translate(-10rpx, -50%);
  white-space: nowrap;
}

.pin-name {
  font-size: 24rpx;
  color: #4b2c1f;
  font-weight: 600;
}

.empty-footprint {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0;
}

.empty-icon {
  font-size: 60rpx;
  margin-bottom: 16rpx;
}

.empty-text {
  font-size: 28rpx;
  color: #37251a;
  margin-bottom: 8rpx;
}

.empty-hint {
  font-size: 24rpx;
  color: #8b7355;
}

.pin-name {
  max-width: 150rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #4d3221;
  font-size: 22rpx;
  font-weight: 800;
}

.danger .menu-title {
  color: #8c3228;
}

.version {
  display: block;
  margin-top: 32rpx;
  text-align: center;
  color: #b39a7a;
  font-size: 22rpx;
}
</style>
