<template>
  <view class="preview-page">
    <view class="preview-header">
      <view>
        <text class="preview-title">{{ displayName }}</text>
        <text class="preview-meta">{{ clothes || '默认服装' }}</text>
      </view>
      <text class="preview-state" :class="{ ready: modelReady, failed: loadError }">{{ stateText }}</text>
    </view>

    <view class="preview-stage">
      <DigitalHuman
        :key="modelPath"
        ref="digitalHuman"
        :model-path="modelPath"
        :status="status"
        :emotion="emotion"
        :speaking="status === 'speak'"
        @ready="handleReady"
        @error="handleError"
      />
    </view>

    <view class="preview-controls">
      <view class="segmented-control">
        <text v-for="item in statuses" :key="item.value" class="segment" :class="{ active: status === item.value }" @click="status = item.value">{{ item.label }}</text>
      </view>
      <view class="segmented-control emotion-control">
        <text v-for="item in emotions" :key="item.value" class="segment" :class="{ active: emotion === item.value }" @click="emotion = item.value">{{ item.label }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import DigitalHuman from '@/components/digital-human-simple/index.vue'

const DEFAULT_MODEL = '/static/live2d/epsilon_ja/epsilon_free/runtime/Epsilon_free.model3.json'

export default {
  components: { DigitalHuman },
  data() {
    return {
      displayName: '灵山数字导游',
      clothes: '',
      modelPath: DEFAULT_MODEL,
      status: 'idle',
      emotion: 'neutral',
      modelReady: false,
      loadError: '',
      statuses: [
        { value: 'idle', label: '待机' },
        { value: 'listen', label: '聆听' },
        { value: 'think', label: '思考' },
        { value: 'speak', label: '说话' }
      ],
      emotions: [
        { value: 'neutral', label: '平和' },
        { value: 'positive', label: '微笑' },
        { value: 'negative', label: '安抚' },
        { value: 'surprised', label: '惊喜' }
      ]
    }
  },
  computed: {
    stateText() {
      if (this.loadError) return '加载失败'
      return this.modelReady ? '模型正常' : '加载中'
    }
  },
  onLoad(options = {}) {
    this.displayName = this.decodeOption(options.name) || this.displayName
    this.clothes = this.decodeOption(options.clothes)
    this.modelPath = this.decodeOption(options.model) || DEFAULT_MODEL
  },
  methods: {
    decodeOption(value) {
      if (!value) return ''
      try {
        return decodeURIComponent(value)
      } catch (error) {
        return value
      }
    },
    handleReady() {
      this.modelReady = true
      this.loadError = ''
    },
    handleError(error) {
      this.modelReady = false
      this.loadError = error?.message || '模型加载失败'
    }
  }
}
</script>

<style lang="scss" scoped>
.preview-page {
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto minmax(420px, 1fr) auto;
  background: #1f272b;
  color: #ffffff;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  padding: 24rpx 30rpx;
  border-bottom: 1rpx solid rgba(255, 255, 255, 0.12);
}

.preview-title,
.preview-meta {
  display: block;
}

.preview-title {
  font-size: 30rpx;
  font-weight: 700;
}

.preview-meta {
  margin-top: 6rpx;
  color: rgba(255, 255, 255, 0.65);
  font-size: 22rpx;
}

.preview-state {
  color: #fbbf24;
  font-size: 22rpx;
}

.preview-state.ready {
  color: #4ade80;
}

.preview-state.failed {
  color: #f87171;
}

.preview-stage {
  min-height: 420px;
  overflow: hidden;
}

.preview-controls {
  display: grid;
  gap: 14rpx;
  padding: 20rpx 24rpx 30rpx;
  border-top: 1rpx solid rgba(255, 255, 255, 0.12);
  background: #172024;
}

.segmented-control {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1rpx solid rgba(255, 255, 255, 0.2);
  border-radius: 6rpx;
  overflow: hidden;
}

.segment {
  min-width: 0;
  padding: 16rpx 8rpx;
  border-right: 1rpx solid rgba(255, 255, 255, 0.16);
  color: rgba(255, 255, 255, 0.72);
  text-align: center;
  font-size: 22rpx;
}

.segment:last-child {
  border-right: 0;
}

.segment.active {
  background: #f4c35b;
  color: #172024;
  font-weight: 700;
}

@media screen and (max-width: 380px) {
  .preview-page {
    grid-template-rows: auto minmax(360px, 1fr) auto;
  }

  .preview-header {
    gap: 12rpx;
    padding: 22rpx 20rpx;
  }

  .preview-stage {
    min-height: 360px;
  }

  .preview-controls {
    padding: 18rpx 18rpx 24rpx;
  }

  .segmented-control {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
