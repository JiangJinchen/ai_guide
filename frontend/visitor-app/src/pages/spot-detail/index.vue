<template>
  <view class="spot-page">
    <view v-if="spotDetail" class="detail">
      <view class="cover">
        <image class="cover-image" :src="coverImage" mode="aspectFill" />
        <view class="cover-shade"></view>
        <view class="cover-note">
          <text class="cover-title">{{ spotName }}</text>
        </view>
      </view>

      <view class="content">
        <view class="audio-card">
          <view class="audio-head">
            <view>
              <text class="audio-title">语音讲解</text>
            </view>
            <text class="audio-time">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</text>
          </view>
          <view class="audio-control-row">
            <slider
              class="audio-slider"
              :disabled="!canPlayAudio || duration <= 0"
              :value="playbackPercent"
              min="0"
              max="100"
              block-size="16"
              activeColor="#8c3228"
              backgroundColor="rgba(140, 50, 40, 0.16)"
              @change="seekAudio"
            />
            <button v-if="canPlayAudio" class="audio-toggle" @click="toggleGuidePlayback">
              {{ isPlaying ? '暂停' : '播放' }}
            </button>
            <text v-else class="audio-empty-note">!</text>
          </view>
          <text v-if="audioHint" class="audio-subtitle">{{ audioHint }}</text>
        </view>

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
          <text class="section-title">打卡亮点</text>
          <view class="highlight-list">
            <text class="highlight-item" v-for="item in highlights" :key="item">{{ item }}</text>
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
          <view class="nearby-row" v-for="item in nearbyItems" :key="item.type + item.id" @click="openNearby(item)">
            <view class="nearby-main">
              <text class="nearby-name">{{ item.name }}</text>
              <text class="nearby-desc">{{ item.desc }}</text>
            </view>
            <text class="nearby-action">{{ item.action }}</text>
          </view>
        </view>

      </view>

      <view class="floating-human" v-if="showDigitalHuman">
        <DigitalHuman
          ref="digitalHuman"
          class="human-frame"
          :compact="true"
          :status="humanStatus"
          :emotion="humanEmotion"
          @ready="onDigitalReady"
          @error="onDigitalError"
        />
      </view>
    </view>

    <view class="loading" v-else-if="isLoading">
      <text>正在展开景点详情...</text>
    </view>

    <view class="error-state" v-else>
      <text class="error-title">景点详情加载失败</text>
      <text class="error-desc">请返回景点列表后重新选择</text>
      <button class="error-action" @click="backToGuide">返回景点列表</button>
    </view>

    <FeedbackModal
      :visible="showFeedbackModal"
      :title="feedbackModalConfig.title"
      :content="feedbackModalConfig.content"
      :params="feedbackModalConfig.params"
      :type="feedbackModalConfig.type"
      :target-key="feedbackModalConfig.targetKey"
      @close="showFeedbackModal = false"
      @later="handleFeedbackLater"
      @submit="handleFeedbackSubmit"
    />
  </view>
</template>

<script>
import DigitalHuman from '@/components/digital-human-simple/index.vue'
import FeedbackModal from '@/components/FeedbackModal/index.vue'
import { get, post } from '@/utils/request'
import { promptForFeedback, markFeedbackPrompt, openFeedbackPage } from '@/utils/feedback'
import { getSpotImage } from '@/utils/spot-images'

const GUIDE_FEEDBACK_DWELL_MS = 60 * 1000

const fallbackGuide = {
  content: '这里是灵山胜境的重要景点，适合放慢脚步慢慢感受。',
  culture: '这里融合了佛教文化、建筑艺术和景观表达，形成了独特的游览体验。',
  highlights: '建筑细节、文化内涵、拍照视角',
  open_info: '请以景区当日公告为准。'
}

export default {
  components: {
    DigitalHuman,
    FeedbackModal
  },
  data() {
    return {
      spotId: null,
      spotDetail: null,
      guideContent: null,
      guideAsset: null,
      audioElement: null,
      audioUrl: '',
      nearbyData: null,
      popularityData: null,
      isLoading: false,
      startTime: 0,
      guideFeedbackTimer: null,
      behaviorId: null,
      audioReady: false,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      playbackPercent: 0,
      digitalReady: false,
      isPageActive: true,
      showFeedbackModal: false,
      feedbackModalConfig: {
        title: '',
        content: '',
        params: {},
        type: '',
        targetKey: ''
      }
    }
  },
  computed: {
    spotName() {
      return this.spotDetail?.spot_name || this.spotDetail?.name || '灵山景点'
    },
    coverImage() {
      return getSpotImage(this.spotName)
    },
    guideText() {
      return this.guideContent?.content || this.spotDetail?.description || fallbackGuide.content
    },
    cultureText() {
      return this.guideContent?.culture || this.spotDetail?.culture_connotation || fallbackGuide.culture
    },
    highlights() {
      const raw = this.guideContent?.highlights || this.spotDetail?.highlights || fallbackGuide.highlights
      return String(raw)
        .split(/[，,；;。/、\n]+/)
        .map(item => item.trim())
        .filter(Boolean)
        .slice(0, 5)
    },
    crowdLevel() {
      if (this.popularityData?.popularity_level) {
        return `人流量 ${this.popularityData.popularity_level}`
      }
      const levels = ['舒适', '适中', '热门']
      return `人流量 ${levels[(this.spotDetail?.id || 0) % levels.length]}`
    },
    keyInfo() {
      return [
        { label: '开放', value: this.spotDetail?.open_info || fallbackGuide.open_info },
      ]
    },
    nearbyItems() {
      const items = []
      const pushGroup = (list = [], type, action) => {
        list.forEach(item => {
          items.push({
            type,
            id: item.id,
            name: item.name,
            desc: `${item.distance_text || item.walk_time || ''}${item.desc ? ` · ${item.desc}` : ''}`.trim(),
            latitude: item.latitude,
            longitude: item.longitude,
            action
          })
        })
      }

      if (this.nearbyData) {
        pushGroup(this.nearbyData.nearby_spots, 'spot', '详情')
        pushGroup(this.nearbyData.food, 'food', '导航')
        pushGroup(this.nearbyData.hotel, 'hotel', '导航')
        pushGroup(this.nearbyData.services, 'service', '导航')
      }

      return items.slice(0, 6)
    },
    
    audioHint() {
      if (!this.canPlayAudio) return '讲解音频暂未生成'
      return this.isPlaying ? '正在播放中' : '点击播放即可开始'
    },
    canPlayAudio() {
      return Boolean(this.audioUrl)
    },
    humanStatus() {
      return this.isPlaying ? 'speak' : 'idle'
    },
    humanEmotion() {
      return 'neutral'
    },
    showDigitalHuman() {
      return Boolean(this.spotDetail)
    }
  },
  onLoad(options) {
    this.startTime = Date.now()
    const spotId = Number(options?.spot_id)
    if (Number.isFinite(spotId) && spotId > 0) {
      this.loadSpot(spotId)
    } else {
      this.isLoading = false
    }
  },
  onShow() {
    this.isPageActive = true
    if (this.spotId && !this.behaviorId && this.spotDetail) {
      this.recordViewBehavior()
    }
    this.scheduleGuideFeedbackPrompt()
  },
  onHide() {
    this.isPageActive = false
    this.clearGuideFeedbackTimer()
    this.dismissFeedbackModal()
  },
  onUnload() {
    this.isPageActive = false
    this.clearGuideFeedbackTimer()
    this.dismissFeedbackModal()
    if (this.spotId && this.spotDetail) {
      const duration = Math.floor((Date.now() - this.startTime) / 1000)
      if (this.behaviorId) {
        this.updateBehaviorDuration(duration)
      } else {
        this.recordViewBehavior(duration)
      }
    }
    this.destroyAudio()
  },
  methods: {
    onDigitalReady() {
      this.digitalReady = true
      if (this.isPlaying && this.audioElement && this.$refs.digitalHuman) {
        this.$refs.digitalHuman.startRealLipSync(this.audioElement)
      }
    },
    onDigitalError(error) {
      this.digitalReady = false
      const message = error && error.message ? error.message : '数字人加载失败'
      uni.showToast({ title: message, icon: 'none' })
    },
    recordViewBehavior(duration = null) {
      const data = {
        behavior_type: 'view',
        spot_id: this.spotId,
        spot_name: this.spotDetail.spot_name || this.spotDetail.name,
        duration
      }
      post('/behavior', data).then(res => {
        if (res.id) this.behaviorId = res.id
      }).catch(() => {})
    },
    updateBehaviorDuration(duration) {
      post(`/behavior/${this.behaviorId}/duration?duration=${duration}`).catch(() => {
        this.recordViewBehavior(duration)
      })
    },
    clearGuideFeedbackTimer() {
      if (!this.guideFeedbackTimer) return
      clearTimeout(this.guideFeedbackTimer)
      this.guideFeedbackTimer = null
    },
    scheduleGuideFeedbackPrompt() {
      this.clearGuideFeedbackTimer()
      if (!this.spotId || !this.spotDetail) return
      const elapsed = Date.now() - this.startTime
      const remaining = Math.max(GUIDE_FEEDBACK_DWELL_MS - elapsed, 0)
      this.guideFeedbackTimer = setTimeout(() => {
        this.guideFeedbackTimer = null
        this.maybePromptGuideFeedback()
      }, remaining)
    },
    /*
    maybePromptGuideFeedback() {
      if (!this.spotId || !this.spotDetail) return
      promptForFeedback({
        type: 'guide',
        targetKey: this.spotId,
        title: '评价',
        content: `你已经在「${this.spotName}」停留了一会儿，愿意评价这次讲解体验吗？`,
        params: {
          feedback_type: 'guide',
          target_type: 'spot',
          target_id: this.spotId,
          target_name: this.spotName,
          source: 'guide'
        }
      })
    },
    */
    async maybePromptGuideFeedback() {
      if (!this.isPageActive) return
      if (!this.spotId || !this.spotDetail) return
      const result = await promptForFeedback({
        type: 'guide',
        targetKey: this.spotId,
        title: '评价',
        content: `你已经在「${this.spotName}」停留了一会儿，愿意评价这次讲解体验吗？`,
        params: {
          feedback_type: 'guide',
          target_type: 'spot',
          target_id: this.spotId,
          target_name: this.spotName,
          source: 'guide'
        },
        useCustomModal: true
      })
      if (result && result.shouldShow) {
        this.feedbackModalConfig = {
          title: result.title,
          content: result.content,
          params: result.params,
          type: result.type,
          targetKey: result.targetKey
        }
        this.showFeedbackModal = true
      }
    },
    handleFeedbackLater() {
      if (this.feedbackModalConfig.type && this.feedbackModalConfig.targetKey) {
        markFeedbackPrompt(this.feedbackModalConfig.type, this.feedbackModalConfig.targetKey, 'dismissed')
      }
    },
    handleFeedbackSubmit() {
      if (this.feedbackModalConfig.params) {
        openFeedbackPage(this.feedbackModalConfig.params)
      }
    },
    dismissFeedbackModal() {
      this.showFeedbackModal = false
    },
    async loadSpot(id) {
      this.isLoading = true
      this.startTime = Date.now()
      this.clearGuideFeedbackTimer()
      this.spotId = id
      this.spotDetail = null
      this.nearbyData = null
      this.popularityData = null
      this.guideContent = null
      this.guideAsset = null
      this.audioUrl = ''
      this.destroyAudio()
      this.behaviorId = null

      try {
        const spot = await get(`/spots/${id}`)
        this.spotDetail = spot
        const [guideResult, nearbyResult, popularityResult] = await Promise.allSettled([
          get(`/guide/${id}`),
          get(`/spots/${id}/nearby`),
          get(`/spots/${id}/popularity`)
        ])

        if (guideResult.status === 'fulfilled') {
          const guide = guideResult.value
          this.guideContent = guide || null
          this.guideAsset = guide?.guide_asset || null
          this.audioUrl = guide?.audio_url || guide?.guide_asset?.audio_url || ''
          console.log('[AUDIO DEBUG] guide data:', JSON.stringify({ audio_url: guide?.audio_url, guide_asset_audio_url: guide?.guide_asset?.audio_url }, null, 2))
          console.log('[AUDIO DEBUG] final audioUrl:', this.audioUrl)
          this.prepareAudio()
        } else {
          this.guideContent = null
          this.guideAsset = null
          this.audioUrl = ''
        }

        this.nearbyData = nearbyResult.status === 'fulfilled' ? nearbyResult.value : null
        this.popularityData = popularityResult.status === 'fulfilled' ? popularityResult.value : null
      } catch (e) {
        this.spotDetail = null
        uni.showToast({ title: '景点详情加载失败', icon: 'none' })
      } finally {
        this.isLoading = false
        if (!this.behaviorId && this.spotDetail) {
          this.recordViewBehavior()
        }
        this.scheduleGuideFeedbackPrompt()
      }
    },
    prepareAudio() {
      this.currentTime = 0
      this.duration = 0
      this.playbackPercent = 0
      this.isPlaying = false
      if (!this.audioUrl) {
        console.log('[AUDIO DEBUG] prepareAudio: audioUrl is empty')
        return
      }

      console.log('[AUDIO DEBUG] Creating Audio element with URL:', this.audioUrl)
      this.audioElement = new Audio(this.audioUrl)
      this.audioElement.preload = 'auto'
      this.audioElement.onloadedmetadata = () => {
        this.duration = Number.isFinite(this.audioElement.duration) ? this.audioElement.duration : 0
        console.log('[AUDIO DEBUG] onloadedmetadata: duration =', this.duration)
      }
      this.audioElement.ontimeupdate = () => {
        if (!this.audioElement) return
        this.currentTime = this.audioElement.currentTime || 0
        this.duration = Number.isFinite(this.audioElement.duration) ? this.audioElement.duration : this.duration
        this.playbackPercent = this.duration > 0 ? Math.min(100, Math.max(0, Math.round((this.currentTime / this.duration) * 100))) : 0
      }
      this.audioElement.onplay = () => {
        this.isPlaying = true
        if (this.$refs.digitalHuman && this.digitalReady) {
          this.$refs.digitalHuman.startRealLipSync(this.audioElement)
        }
      }
      this.audioElement.onpause = () => {
        this.isPlaying = false
        if (this.$refs.digitalHuman) {
          this.$refs.digitalHuman.stopSpeaking()
        }
      }
      this.audioElement.onended = () => {
        this.isPlaying = false
        this.currentTime = 0
        this.playbackPercent = 0
        if (this.$refs.digitalHuman) {
          this.$refs.digitalHuman.stopSpeaking()
        }
      }
      this.audioElement.onerror = (e) => {
        this.isPlaying = false
        this.audioUrl = ''
        console.error('[AUDIO DEBUG] Audio error:', e)
        console.error('[AUDIO DEBUG] Audio error details:', {
          error: this.audioElement?.error?.message,
          code: this.audioElement?.error?.code,
          url: this.audioUrl
        })
        uni.showToast({ title: '讲解音频加载失败', icon: 'none' })
        if (this.$refs.digitalHuman) {
          this.$refs.digitalHuman.stopSpeaking()
        }
      }
    },
    destroyAudio() {
      if (!this.audioElement) return
      this.audioElement.onloadedmetadata = null
      this.audioElement.ontimeupdate = null
      this.audioElement.onplay = null
      this.audioElement.onpause = null
      this.audioElement.onended = null
      this.audioElement.onerror = null
      this.audioElement.pause()
      this.audioElement = null
      this.isPlaying = false
      this.currentTime = 0
      this.duration = 0
      this.playbackPercent = 0
      if (this.$refs.digitalHuman) {
        this.$refs.digitalHuman.stopSpeaking()
      }
    },
    async toggleGuidePlayback() {
      console.log('[AUDIO DEBUG] toggleGuidePlayback called')
      console.log('[AUDIO DEBUG] canPlayAudio:', this.canPlayAudio)
      console.log('[AUDIO DEBUG] audioUrl:', this.audioUrl)
      console.log('[AUDIO DEBUG] audioElement exists:', !!this.audioElement)
      if (!this.canPlayAudio) {
        uni.showToast({ title: '讲解音频尚未生成', icon: 'none' })
        return
      }
      if (!this.audioElement) {
        console.log('[AUDIO DEBUG] audioElement is null, calling prepareAudio')
        this.prepareAudio()
      }
      if (!this.audioElement) return

      try {
        if (this.audioElement.paused) {
          console.log('[AUDIO DEBUG] Calling play()')
          await this.audioElement.play()
          console.log('[AUDIO DEBUG] play() succeeded')
        } else {
          console.log('[AUDIO DEBUG] Calling pause()')
          this.audioElement.pause()
        }
      } catch (e) {
        console.error('[AUDIO DEBUG] Playback error:', e)
        uni.showToast({ title: '无法播放讲解音频', icon: 'none' })
      }
    },
    seekAudio(event) {
      if (!this.audioElement || !this.duration) return
      const value = Number(event.detail.value || 0)
      this.playbackPercent = value
      this.currentTime = (this.duration * value) / 100
      this.audioElement.currentTime = this.currentTime
    },
    formatTime(seconds) {
      const value = Math.max(0, Math.floor(Number(seconds) || 0))
      const mins = String(Math.floor(value / 60)).padStart(2, '0')
      const secs = String(value % 60).padStart(2, '0')
      return `${mins}:${secs}`
    },
    openNavigation() {
      const lat = Number(this.spotDetail?.latitude)
      const lon = Number(this.spotDetail?.longitude)
      if (lat && lon) {
        this.recordNavigateBehavior()
        uni.openLocation({
          latitude: lat,
          longitude: lon,
          name: this.spotName,
          address: this.spotDetail.location || '灵山胜境景区内'
        })
      } else {
        uni.showToast({ title: '后续补充地图导航', icon: 'none' })
      }
    },
    recordNavigateBehavior() {
      const data = {
        behavior_type: 'navigate',
        spot_id: this.spotId,
        spot_name: this.spotDetail.spot_name || this.spotDetail.name || this.spotName
      }
      post('/behavior', data).catch(() => {})
    },
    openNearby(item) {
      if (item.type === 'spot') {
        uni.redirectTo({ url: `/pages/spot-detail/index?spot_id=${item.id}` })
        return
      }
      const lat = Number(item.latitude)
      const lon = Number(item.longitude)
      if (lat && lon) {
        uni.openLocation({
          latitude: lat,
          longitude: lon,
          name: item.name,
          address: item.desc || '灵山胜境周边'
        })
      } else {
        uni.showToast({ title: '位置信息暂不可用', icon: 'none' })
      }
    },
    backToGuide() {
      uni.redirectTo({ url: '/pages/guide/index' })
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

.cover-title,
.audio-title,
.audio-subtitle,
.audio-time,
.block-title,
.section-title,
.paragraph,
.info-label,
.info-value,
.highlight-item,
.show-time,
.show-name,
.nearby-name,
.nearby-desc,
.review-name,
.review-text {
  display: block;
}

.cover {
  position: relative;
  height: 540rpx;
  overflow: hidden;
}

.cover-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.cover-shade {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(30, 21, 15, 0.06), rgba(30, 21, 15, 0.58));
}

.cover-note {
  position: absolute;
  left: 34rpx;
  right: 34rpx;
  bottom: 110rpx;
  color: #fff8e8;
}

.cover-title {
  font-size: 58rpx;
  font-weight: 900;
}

.cover-badge-row {
  position: absolute;
  left: 34rpx;
  right: 34rpx;
  bottom: 34rpx;
  display: flex;
  gap: 14rpx;
  flex-wrap: wrap;
}

.cover-badge {
  padding: 10rpx 18rpx;
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.86);
  color: #7d3026;
  font-size: 22rpx;
}

.content {
  padding: 26rpx;
  padding-bottom: 80rpx;
}

.audio-card,
.intro-block,
.section-card {
  margin-bottom: 22rpx;
  padding: 28rpx;
  border: 1rpx solid rgba(121, 74, 38, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.92);
}

.audio-head,
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
}

.audio-title,
.section-title,
.block-title {
  font-size: 32rpx;
  font-weight: 850;
  color: #4b2c1f;
}

.audio-subtitle,
.audio-time {
  margin-top: 8rpx;
  color: #8b745b;
  font-size: 24rpx;
}

.audio-slider {
  flex: 1;
  margin: 0;
}

.audio-control-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  margin: 22rpx 0 10rpx;
}

.audio-toggle {
  flex-shrink: 0;
  min-width: 98rpx;
  min-height: 66rpx;
  padding: 0 18rpx;
  border-radius: 10rpx;
  background: #8c3228;
  color: #fff8e8;
  font-size: 24rpx;
}

.audio-empty-note {
  flex-shrink: 0;
  color: #8b745b;
  font-size: 22rpx;
  line-height: 1;
}

.audio-actions {
  display: flex;
  gap: 14rpx;
}

.audio-btn {
  flex: 1;
  min-height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10rpx;
  background: #f3e3c4;
  color: #8a3328;
  font-size: 26rpx;
}

.audio-btn.primary {
  background: #8c3228;
  color: #fff8e8;
}

.audio-btn[disabled] {
  opacity: 0.5;
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
  margin-top: 18rpx;
  color: #66513f;
  font-size: 27rpx;
  line-height: 1.75;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr;
  margin-bottom: 22rpx;
}

.info-cell {
  min-height: 118rpx;
  padding: 22rpx;
  border-radius: 10rpx;
  background: #7c3028;
  color: #fff7e6;
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

.show-row,
.nearby-row,
.review-row {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
  padding: 18rpx 0;
  border-bottom: 1rpx solid rgba(121, 74, 38, 0.1);
}

.show-row:last-child,
.nearby-row:last-child,
.review-row:last-child {
  border-bottom: none;
}

.show-time,
.nearby-action,
.review-name {
  flex-shrink: 0;
  color: #8a3328;
  font-weight: 800;
  font-size: 25rpx;
}

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

.nearby-main {
  flex: 1;
  min-width: 0;
}

.nearby-name {
  color: #3f2b20;
  font-size: 27rpx;
}

.nearby-desc {
  margin-top: 8rpx;
  color: #806b55;
  font-size: 23rpx;
  line-height: 1.45;
}

.loading {
  padding-top: 220rpx;
  text-align: center;
  color: #8a3328;
  font-size: 28rpx;
}

.error-state {
  min-height: 70vh;
  padding: 220rpx 40rpx 0;
  color: #806b55;
  text-align: center;
}

.error-title,
.error-desc {
  display: block;
}

.error-title {
  color: #4b2c1f;
  font-size: 32rpx;
  font-weight: 800;
}

.error-desc {
  margin-top: 14rpx;
  font-size: 25rpx;
}

.error-action {
  width: 240rpx;
  min-height: 72rpx;
  margin-top: 32rpx;
  background: #8c3228;
  color: #fff8e8;
  font-size: 26rpx;
}

.floating-human {
  position: fixed;
  right: 18rpx;
  bottom: calc(110rpx + env(safe-area-inset-bottom));
  z-index: 40;
  width: 180rpx;
  height: 230rpx;
  pointer-events: none;
}

.human-frame {
  width: 100%;
  height: 100%;
}
</style>
