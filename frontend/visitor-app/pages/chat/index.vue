<template>
  <view class="chat-page">
    <scroll-view 
      class="chat-content" 
      scroll-y 
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
    >
      <view 
        class="message-item" 
        :class="{ user: msg.isUser }"
        v-for="(msg, index) in messages"
        :key="index"
      >
        <view class="avatar">{{ msg.isUser ? '👤' : '🤖' }}</view>
        <view class="message-bubble">
          <text class="message-text">{{ msg.content }}</text>
          <text class="message-time">{{ msg.time }}</text>
        </view>
      </view>
      <view v-if="isLoading" class="loading">
        <text class="loading-text">AI思考中...</text>
      </view>
    </scroll-view>

    <view class="input-area">
      <view class="input-row">
        <view class="voice-btn" @click="toggleVoice">
          <text>{{ isVoiceMode ? '✓' : '🎤' }}</text>
        </view>
        <input 
          class="input-box" 
          v-model="inputText"
          placeholder="输入问题..."
          @confirm="sendMessage"
          :disabled="isVoiceMode"
        />
        <view class="send-btn" @click="sendMessage" :class="{ active: inputText.trim() }">
          <text>发送</text>
        </view>
      </view>
      <view class="quick-questions" v-if="!isVoiceMode">
        <text 
          class="quick-item" 
          v-for="(q, i) in quickQuestions" 
          :key="i"
          @click="sendQuickQuestion(q)"
        >{{ q }}</text>
      </view>
    </view>
  </view>
</template>

<script>
import { get, post } from '@/utils/request'

export default {
  data() {
    return {
      messages: [],
      inputText: '',
      scrollTop: 0,
      isLoading: false,
      isVoiceMode: false,
      quickQuestions: ['梵宫在哪里？', '今天有表演吗？', '推荐游玩路线', '附近有餐厅吗？']
    }
  },
  onLoad(options) {
    if (options && options.history === 'true') {
      this.loadHistory()
    } else {
      this.messages.push({
        isUser: false,
        content: '您好！我是灵山胜境的AI导览助手，请问有什么可以帮助您的？',
        time: new Date().toLocaleTimeString()
      })
    }
  },
  methods: {
    async loadHistory() {
      try {
        const history = await get('/chat/history')
        if (history && history.length > 0) {
          this.messages = history.map(item => ({
            isUser: item.role === 'user',
            content: item.content,
            time: item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : ''
          }))
        }
      } catch (e) {
        console.error('加载历史失败', e)
      }
    },
    async sendMessage() {
      if (!this.inputText.trim() || this.isLoading) return
      
      const text = this.inputText.trim()
      this.inputText = ''
      
      this.messages.push({
        isUser: true,
        content: text,
        time: new Date().toLocaleTimeString()
      })
      
      this.scrollToBottom()
      this.isLoading = true
      
      try {
        const res = await post('/chat', { text })
        this.messages.push({
          isUser: false,
          content: res.response || res.answer || '抱歉，我暂时无法回答这个问题',
          time: new Date().toLocaleTimeString()
        })
      } catch (e) {
        this.messages.push({
          isUser: false,
          content: '网络请求失败，请稍后重试',
          time: new Date().toLocaleTimeString()
        })
      }
      
      this.isLoading = false
      this.scrollToBottom()
    },
    sendQuickQuestion(q) {
      this.inputText = q
      this.sendMessage()
    },
    toggleVoice() {
      this.isVoiceMode = !this.isVoiceMode
      if (this.isVoiceMode) {
        uni.showToast({ title: '语音模式', icon: 'none' })
      }
    },
    scrollToBottom() {
      setTimeout(() => {
        this.scrollTop = 99999
      }, 100)
    }
  }
}
</script>

<style lang="scss" scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

.chat-content {
  flex: 1;
  padding: 20rpx;
}

.message-item {
  display: flex;
  margin-bottom: 30rpx;
}

.message-item.user {
  flex-direction: row-reverse;
}

.avatar {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  flex-shrink: 0;
}

.message-item.user .avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.message-bubble {
  max-width: 70%;
  margin: 0 20rpx;
}

.message-item.user .message-bubble {
  text-align: right;
}

.message-text {
  display: inline-block;
  background: #fff;
  padding: 24rpx 30rpx;
  border-radius: 24rpx;
  font-size: 28rpx;
  line-height: 1.6;
  color: #333;
  max-width: 100%;
  word-break: break-all;
}

.message-item.user .message-text {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  border-radius: 24rpx;
}

.message-time {
  display: block;
  font-size: 20rpx;
  color: #999;
  margin-top: 10rpx;
}

.loading {
  text-align: center;
  padding: 20rpx;
}

.loading-text {
  font-size: 26rpx;
  color: #999;
}

.input-area {
  background: #fff;
  padding: 20rpx 30rpx;
  padding-bottom: calc(20rpx + env(safe-area-inset-bottom));
}

.input-row {
  display: flex;
  align-items: center;
}

.voice-btn {
  width: 80rpx;
  height: 80rpx;
  border-radius: 50%;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36rpx;
  margin-right: 20rpx;
}

.input-box {
  flex: 1;
  height: 80rpx;
  background: #f5f5f5;
  border-radius: 40rpx;
  padding: 0 30rpx;
  font-size: 28rpx;
}

.send-btn {
  width: 120rpx;
  height: 80rpx;
  background: #e0e0e0;
  border-radius: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: 20rpx;
  font-size: 28rpx;
  color: #999;
}

.send-btn.active {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.quick-questions {
  display: flex;
  flex-wrap: wrap;
  margin-top: 20rpx;
}

.quick-item {
  background: #f5f5f5;
  padding: 16rpx 28rpx;
  border-radius: 30rpx;
  font-size: 24rpx;
  color: #666;
  margin-right: 20rpx;
  margin-bottom: 10rpx;
}
</style>