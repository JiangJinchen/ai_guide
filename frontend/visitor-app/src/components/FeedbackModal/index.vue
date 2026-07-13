<template>
  <view class="feedback-modal-mask" v-if="visible" @click="handleClose">
    <view class="feedback-modal" @click.stop>
      <view class="modal-header">
        <text class="modal-title">{{ title }}</text>
        <button class="modal-close" @click="handleClose">×</button>
      </view>
      <view class="modal-content">
        <text class="modal-desc">{{ content }}</text>
      </view>
      <view class="modal-actions">
        <button class="modal-btn modal-btn-secondary" @click="handleLater">稍后</button>
        <button class="modal-btn modal-btn-primary" @click="handleSubmit">去评价</button>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'FeedbackModal',
  props: {
    visible: {
      type: Boolean,
      default: false
    },
    title: {
      type: String,
      default: '评价服务'
    },
    content: {
      type: String,
      default: '感谢您使用我们的服务，是否愿意给我们一个评价？'
    },
    params: {
      type: Object,
      default: () => ({})
    },
    type: {
      type: String,
      default: ''
    },
    targetKey: {
      type: String,
      default: ''
    }
  },
  emits: ['close', 'submit', 'later'],
  methods: {
    handleClose() {
      this.$emit('close')
    },
    handleLater() {
      this.$emit('later')
      this.$emit('close')
    },
    handleSubmit() {
      this.$emit('submit')
      this.$emit('close')
    }
  }
}
</script>

<style lang="scss" scoped>
.feedback-modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.feedback-modal {
  width: 600rpx;
  background: linear-gradient(180deg, #fffbf7 0%, #fff7e6 100%);
  border-radius: 20rpx;
  overflow: hidden;
  box-shadow: 0 24rpx 60rpx rgba(64, 36, 20, 0.3);
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from { 
    opacity: 0;
    transform: translateY(40rpx);
  }
  to { 
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx 32rpx 24rpx;
  position: relative;
}

.modal-icon {
  width: 80rpx;
  height: 80rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #8b2d22, #b84a38);
  border-radius: 50%;
  color: #fff7e6;
  font-size: 40rpx;
  margin-right: 20rpx;
  box-shadow: 0 8rpx 20rpx rgba(139, 45, 34, 0.3);
}

.modal-title {
  font-size: 36rpx;
  font-weight: 800;
  color: #33251b;
}

.modal-close {
  position: absolute;
  right: 24rpx;
  top: 24rpx;
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(139, 45, 34, 0.1);
  border-radius: 50%;
  color: #8b2d22;
  font-size: 36rpx;
  padding: 0;
  margin: 0;
  border: none;
}

.modal-content {
  padding: 0 40rpx 32rpx;
  text-align: center;
}

.modal-desc {
  font-size: 28rpx;
  color: #5c493a;
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  border-top: 1rpx solid rgba(139, 45, 34, 0.1);
}

.modal-btn {
  flex: 1;
  height: 96rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30rpx;
  font-weight: 700;
  border-radius: 0;
  margin: 0;
  padding: 0;
  border: none;
}

.modal-btn-secondary {
  background: transparent;
  color: #8c7a66;
}

.modal-btn-primary {
  background: linear-gradient(135deg, #8b2d22, #a63f2e);
  color: #fff7e6;
}
</style>