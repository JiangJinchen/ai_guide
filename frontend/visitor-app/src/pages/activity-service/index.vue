<template>
  <view class="activity-page">
    <view class="hero-band">
      <text class="eyebrow">{{ pageTitle }}</text>
      <text class="title">{{ pageSubtitle }}</text>
      <text class="desc">{{ pageDesc }}</text>
    </view>

    <view class="activity-list">
      <view
        class="activity-card"
        v-for="activity in activities"
        :key="activity.id"
      >
        <view class="card-head">
          <text class="activity-name">{{ activity.name }}</text>
          <view @click="openLocation(activity)">
            <svg viewBox="0 0 1024 1024" width="24" height="24" fill="#814b00ff">
              <path d="M906.000638 1023.99996a99.290887 99.290887 0 0 1-57.16748-18.052889L483.763632 746.186063l-55.161604 221.649355a40.11753 40.11753 0 0 1-39.114592 30.088147 40.11753 40.11753 0 0 1-39.114592-31.091086l-82.240937-352.031328a20.058765 20.058765 0 0 0-11.032321-14.041135L50.494306 504.477943l-5.014692-3.008815a100.293826 100.293826 0 0 1 18.052889-176.517133L886.944811 7.020568a100.293826 100.293826 0 0 1 136.399603 101.296764l-17.04995 821.406432v3.008815a99.290887 99.290887 0 0 1-58.170419 81.237998 100.293826 100.293826 0 0 1-42.123407 10.029383z m-11.03232-84.246814a20.058765 20.058765 0 0 0 31.091085-13.038197l17.049951-821.406432v-3.008815a20.058765 20.058765 0 0 0-27.079333-21.061703L92.617712 399.169426a20.058765 20.058765 0 0 0-6.017629 34.099901l203.596466 94.276196a99.290887 99.290887 0 0 1 55.161604 68.199801l45.132222 190.558269 29.085209-117.343776a40.11753 40.11753 0 0 1 62.182172-23.06758z"></path>
              <path d="M389.487436 997.923565a40.11753 40.11753 0 0 1-27.079333-69.202739l191.561207-176.517134a40.11753 40.11753 0 0 1 54.158666 59.173358L416.566769 986.891244a40.11753 40.11753 0 0 1-27.079333 11.032321zM462.701929 714.092039a40.11753 40.11753 0 0 1-31.091086-65.190987L917.032959 42.123407a40.11753 40.11753 0 1 1 62.182172 50.146913L493.793015 699.047965a40.11753 40.11753 0 0 1-31.091086 15.044074z"></path>
            </svg>
          </view>
        </view>
        
        <text class="activity-location">{{ activity.location }}</text>
        
        <view class="time-row" v-if="activity.schedule_times && activity.schedule_times.length">
          <text class="time-chip" v-for="time in activity.schedule_times" :key="activity.id + '-' + time">
            {{ time }}
          </text>
        </view>
        
        <view class="content-section">
          <text class="content-text">{{ activity.content }}</text>
          <text class="significance-text" v-if="activity.significance">{{ activity.significance }}</text>
        </view>
        
        <view class="card-footer">
          <text class="duration" v-if="activity.duration_minutes">{{ activity.duration_minutes }}分钟</text>
        </view>
      </view>
      
      <view class="empty-state" v-if="!loading && !activities.length">
        <text>暂无活动信息</text>
      </view>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'

export default {
  data() {
    return {
      loading: false,
      activityType: 'performance',
      activities: []
    }
  },
  computed: {
    pageTitle() {
      return '活动服务'
    },
    pageSubtitle() {
      return this.activityType === 'performance' ? '演出时间' : '文化体验'
    },
    pageDesc() {
      return this.activityType === 'performance' 
        ? '查看景区当日演出场次，提前规划游览路线' 
        : '了解禅修体验内容，感受心灵洗礼'
    }
  },
  async onLoad(options = {}) {
    if (options.type) this.activityType = options.type
    await this.loadActivities()
  },
  methods: {
    async loadActivities() {
      this.loading = true
      try {
        const data = await get('/activities', { activity_type: this.activityType })
        this.activities = data.items || []
      } catch (error) {
        this.activities = []
        uni.showToast({ title: '活动信息暂不可用', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
    openLocation(activity) {
      const latitude = Number(activity.latitude)
      const longitude = Number(activity.longitude)
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        uni.showToast({ title: '暂无可导航位置', icon: 'none' })
        return
      }
      uni.openLocation({
        latitude,
        longitude,
        name: activity.name,
        address: activity.location || '灵山胜境景区内'
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.activity-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 54rpx;
  background: linear-gradient(180deg, #f6ecd9 0%, #efe0c8 50%, #f8f1e7 100%);
  color: #3b2a1f;
}

.hero-band {
  min-height: 180rpx;
  padding: 34rpx;
  border-radius: 10rpx;
  background:
    linear-gradient(135deg, rgba(132, 45, 36, 0.96), rgba(46, 92, 115, 0.88)),
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
  margin-top: 12rpx;
  font-size: 40rpx;
  font-weight: 900;
}

.desc {
  margin-top: 12rpx;
  font-size: 24rpx;
  line-height: 1.5;
}

.activity-list {
  margin-top: 24rpx;
}

.activity-card {
  margin-bottom: 20rpx;
  padding: 28rpx;
  border-radius: 12rpx;
  background: rgba(255, 251, 242, 0.95);
  border: 1rpx solid rgba(121, 74, 38, 0.12);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16rpx;
}

.activity-name {
  flex: 1;
  font-size: 34rpx;
  font-weight: 900;
  color: #3f2b20;
}

.activity-location {
  display: block;
  margin-top: 8rpx;
  font-size: 24rpx;
  color: #8c765e;
}

.time-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12rpx;
  margin-top: 20rpx;
}

.time-chip {
  flex-shrink: 0;
  min-height: 52rpx;
  padding: 0 24rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 26rpx;
  background: #efe0bd;
  color: #7c5838;
  font-size: 24rpx;
}

.content-section {
  margin-top: 20rpx;
  padding-top: 20rpx;
  border-top: 1rpx dashed rgba(121, 74, 38, 0.15);
}

.content-text {
  display: block;
  font-size: 26rpx;
  color: #5f4a37;
  line-height: 1.6;
}

.significance-text {
  display: block;
  margin-top: 12rpx;
  font-size: 24rpx;
  color: #856f58;
  line-height: 1.6;
  font-style: italic;
}

.card-footer {
  margin-top: 16rpx;
  display: flex;
  justify-content: flex-end;
}

.duration {
  font-size: 22rpx;
  color: #a68a68;
}

.empty-state {
  padding: 60rpx 0;
  text-align: center;
  color: #a68a68;
  font-size: 26rpx;
}
</style>