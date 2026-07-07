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
        <text class="section-title">偏好设置</text>
        <text class="section-sub">本地保存</text>
      </view>
      <view class="setting-row">
        <text class="setting-label">主题</text>
        <view class="segmented">
          <text
            class="segment"
            :class="{ active: preference.theme === item.value }"
            v-for="item in themes"
            :key="item.value"
            @click="setPreference('theme', item.value)"
          >
            {{ item.label }}
          </text>
        </view>
      </view>
      <view class="setting-row">
        <text class="setting-label">数字人</text>
        <view class="segmented">
          <text
            class="segment"
            :class="{ active: preference.figure === item.value }"
            v-for="item in figures"
            :key="item.value"
            @click="setPreference('figure', item.value)"
          >
            {{ item.label }}
          </text>
        </view>
      </view>
      <view class="setting-row">
        <text class="setting-label">声音</text>
        <view class="segmented">
          <text
            class="segment"
            :class="{ active: preference.voice === item.value }"
            v-for="item in voices"
            :key="item.value"
            @click="setPreference('voice', item.value)"
          >
            {{ item.label }}
          </text>
        </view>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的预约</text>
        <text class="section-sub">待接入预约码</text>
      </view>
      <view class="reservation-row" v-for="item in reservations" :key="item.name">
        <view>
          <text class="row-title">{{ item.name }}</text>
          <text class="row-desc">{{ item.time }} · {{ item.status }}</text>
        </view>
        <text class="row-action">查看</text>
      </view>
    </view>

    <view class="section-card">
      <view class="section-head">
        <text class="section-title">我的游览足迹</text>
        <text class="section-sub">地图视图预留</text>
      </view>
      <view class="footprint-map">
        <view class="map-road road-a"></view>
        <view class="map-road road-b"></view>
        <view class="map-road road-c"></view>
        <view
          class="map-pin"
          v-for="(item, index) in footprints"
          :key="item.name"
          :class="'pin-' + index"
          @click="goToGuide(item.id)"
        >
          <text class="pin-dot"></text>
          <text class="pin-name">{{ item.name }}</text>
        </view>
      </view>
    </view>

    <view class="section-card">
      <view class="menu-row" @click="goToFeedback">
        <text class="menu-title">服务评价</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-row" @click="contactService">
        <text class="menu-title">联系景区人工客服</text>
        <text class="menu-arrow">›</text>
      </view>
      <view class="menu-row danger" @click="logout">
        <text class="menu-title">退出登录</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <text class="version">灵山胜境 AI导览 v1.0.0</text>
  </view>
</template>

<script>
export default {
  data() {
    return {
      userId: '',
      nickname: '灵山游客',
      signature: '愿今日山水有好风',
      preference: {
        theme: 'classic',
        figure: 'gentle',
        voice: '女声'
      },
      themes: [
        { label: '古风', value: 'classic' },
        { label: '清雅', value: 'fresh' },
        { label: '夜游', value: 'night' }
      ],
      figures: [
        { label: '温雅', value: 'gentle' },
        { label: '活泼', value: 'bright' },
        { label: '沉稳', value: 'calm' }
      ],
      voices: [
        { label: '女声', value: '女声' },
        { label: '男声', value: '男声' }
      ],
      reservations: [
        { name: '禅修体验', time: '今日 14:00', status: '待确认' },
        { name: '祈福点灯', time: '明日 10:30', status: '可生成预约码' }
      ],
      footprints: [
        { id: 1, name: '灵山大佛', date: '今日' },
        { id: 2, name: '灵山梵宫', date: '昨日' },
        { id: 3, name: '九龙灌浴', date: '本周' }
      ]
    }
  },
  computed: {
    shortUserId() {
      return this.userId ? this.userId.slice(-8) : 'guest'
    }
  },
  onLoad() {
    this.userId = uni.getStorageSync('userId') || 'guest'
    const saved = uni.getStorageSync('visitorProfile')
    if (saved) {
      this.nickname = saved.nickname || this.nickname
      this.signature = saved.signature || this.signature
      this.preference = saved.preference || this.preference
    }
  },
  methods: {
    saveProfile() {
      uni.setStorageSync('visitorProfile', {
        nickname: this.nickname || '灵山游客',
        signature: this.signature || '愿今日山水有好风',
        preference: this.preference
      })
    },
    setPreference(key, value) {
      this.preference = { ...this.preference, [key]: value }
      this.saveProfile()
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/guide/index?spot_id=${id}` })
    },
    goToFeedback() {
      uni.navigateTo({ url: '/pages/feedback/index' })
    },
    contactService() {
      uni.showModal({
        title: '人工客服',
        content: '后续可接入景区客服电话、在线客服或小程序客服能力。',
        showCancel: false
      })
    },
    logout() {
      uni.showModal({
        title: '退出登录',
        content: '将清除当前游客身份并生成新的游客ID。',
        success: (res) => {
          if (res.confirm) {
            const userId = 'visitor_' + Date.now()
            uni.setStorageSync('userId', userId)
            this.userId = userId
            uni.showToast({ title: '已退出', icon: 'success' })
          }
        }
      })
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

.setting-row {
  padding: 16rpx 0;
}

.setting-label {
  display: block;
  margin-bottom: 14rpx;
  color: #6d5542;
  font-size: 24rpx;
}

.segmented {
  display: flex;
  gap: 12rpx;
}

.segment {
  flex: 1;
  height: 62rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #efe0bd;
  color: #6a4b2f;
  font-size: 24rpx;
}

.segment.active {
  background: #8c3228;
  color: #fff8e8;
}

.reservation-row,
.menu-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  padding: 20rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.reservation-row:last-child,
.menu-row:last-child {
  border-bottom: none;
}

.row-title,
.row-desc {
  display: block;
}

.row-title,
.menu-title {
  color: #3f2b20;
  font-size: 27rpx;
  font-weight: 800;
}

.row-desc {
  margin-top: 8rpx;
  color: #806b55;
  font-size: 23rpx;
}

.row-action,
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

.map-road {
  position: absolute;
  background: rgba(115, 77, 43, 0.2);
  border-radius: 999rpx;
}

.road-a {
  left: -40rpx;
  right: 60rpx;
  top: 150rpx;
  height: 10rpx;
  transform: rotate(-12deg);
}

.road-b {
  left: 250rpx;
  top: -30rpx;
  width: 10rpx;
  height: 420rpx;
  transform: rotate(24deg);
}

.road-c {
  left: 80rpx;
  right: -60rpx;
  top: 238rpx;
  height: 8rpx;
  transform: rotate(16deg);
}

.map-pin {
  position: absolute;
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 12rpx;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.88);
  box-shadow: 0 8rpx 18rpx rgba(75, 43, 24, 0.14);
}

.pin-0 {
  left: 68rpx;
  top: 92rpx;
}

.pin-1 {
  right: 80rpx;
  top: 150rpx;
}

.pin-2 {
  left: 210rpx;
  bottom: 54rpx;
}

.pin-dot {
  width: 18rpx;
  height: 18rpx;
  border-radius: 50%;
  background: #8c3228;
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
