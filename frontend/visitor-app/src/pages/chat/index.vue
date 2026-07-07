<template>
  <view class="digital-page">
    <view class="sky-layer"></view>

    <view class="top-bar">
      <view>
        <text class="page-title">灵山数字人</text>
        <text class="page-subtitle">{{ statusText }}</text>
      </view>
      <view class="top-actions">
        <button class="history-button" @click="openHistory">史</button>
      </view>
    </view>

    <view class="stage">
      <view class="halo"></view>
      <DigitalHuman
        ref="digitalHuman"
        class="stage-human"
        :status="status"
        :emotion="emotion"
        @ready="onDigitalReady"
        @error="onDigitalError"
      />
      <view class="shadow"></view>
    </view>

    <view class="dialog-panel">
      <scroll-view class="message-scroll" scroll-y :scroll-top="scrollTop">
        <view
          class="message"
          v-for="(msg, index) in messages"
          :key="index"
          :class="{ user: msg.role === 'user' }"
        >
          <text class="message-role">{{ msg.role === 'user' ? '游客' : '数字人' }}</text>
          <text class="message-text">{{ msg.text }}</text>
        </view>
      </scroll-view>

      <view class="quick-row">
        <text class="quick-chip" v-for="item in quickQuestions" :key="item" @click="askQuick(item)">
          {{ item }}
        </text>
      </view>

      <view class="input-row">
        <view class="thinking-indicator" v-if="status === 'listen' || status === 'recognizing' || status === 'think'">
          <view class="thinking-dots">
            <view class="dot"></view>
            <view class="dot"></view>
            <view class="dot"></view>
          </view>
          <text class="thinking-text">
            {{ status === 'listen' ? '正在聆听中' : status === 'recognizing' ? '正在识别中' : '正在思考中' }}
          </text>
        </view>
        <input
          class="text-input"
          :disabled="status === 'listen' || status === 'recognizing' || status === 'think'"
          :placeholder="status === 'listen' ? '正在聆听，请说话...' : status === 'recognizing' ? '正在识别语音...' : status === 'think' ? '请稍候，正在思考中...' : '也可以输入文字询问'"
          confirm-type="send"
          @confirm="sendText"
        />
        <button class="send-button" :disabled="status === 'listen' || status === 'recognizing' || status === 'think'" @click="sendText">发送</button>
      </view>
    </view>

    <view class="voice-control">
      <button
        class="voice-button"
        :class="{ recording: isRecording, disabled: status === 'think' }"
        :disabled="status === 'think'"
        @touchstart="startVoice"
        @touchend="stopVoice"
        @mousedown="startVoice"
        @mouseup="stopVoice"
      >
        <text class="voice-main">{{ isRecording ? '松开发送' : '按住说话' }}</text>
      </button>
    </view>
  </view>
</template>

<script>
import DigitalHuman from '@/components/digital-human-simple/index.vue'
import { get, post } from '@/utils/request'

export default {
  components: {
    DigitalHuman
  },
  data() {
    return {
      inputText: '',
      isRecording: false,
      recorder: null,
      status: 'idle',
      emotion: 'neutral',
      scrollTop: 0,
      digitalReady: false,
      audioElement: null,
      activeReplySeq: 0,
      isRecognizing: false,
      h5RecorderSupported: false,
      h5MediaStream: null,
      h5AudioContext: null,
      h5SourceNode: null,
      h5ProcessorNode: null,
      h5AudioChunks: [],
      h5InputSampleRate: 44100,
      voiceStartAt: 0,
      messages: [
        {
          role: 'assistant',
          text: '您好，我是灵山胜境数字导游。您可以按住说话，也可以输入文字，询问景点、路线、演出或祈福活动。'
        }
      ],
      quickQuestions: [
        '梵宫今天有演出吗',
        '推荐一条游览路线',
        '灵山大佛有什么故事'
      ]
    }
  },
  computed: {
    statusText() {
      const map = {
        idle: '待命中，随时为您讲解',
        listen: '正在聆听您的问题',
        recognizing: '正在识别语音',
        think: '正在检索知识库并生成回答',
        speak: '正在语音讲解'
      }
      return map[this.status] || map.idle
    },
    emotionLabel() {
      const map = {
        neutral: '平和',
        positive: '愉悦',
        negative: '安抚',
        surprised: '惊喜',
        shy: '害羞',
        angry: '生气'
      }
      return `情绪 ${map[this.emotion] || map.neutral}`
    },
    voiceHint() {
      return ''
    }
  },
  onLoad(options) {
    if (options && options.history === 'true') this.loadHistory()
    this.initRecorder()
  },
  onShow() {
    if (uni.getStorageSync('openChatHistory')) {
      uni.removeStorageSync('openChatHistory')
      this.loadHistory()
    }
  },
  onUnload() {
    this.cleanupH5Recording()
    this.stopCurrentSpeech(false)
  },
  methods: {
    onDigitalReady() {
      this.digitalReady = true
    },
    onDigitalError(error) {
      this.digitalReady = false
      const message = error && error.message ? error.message : '数字人模型加载失败'
      uni.showToast({ title: message, icon: 'none' })
    },
    initRecorder() {
      if (process.env.UNI_PLATFORM === 'h5') {
        this.h5RecorderSupported = !!(
          typeof navigator !== 'undefined' &&
          navigator.mediaDevices &&
          typeof navigator.mediaDevices.getUserMedia === 'function' &&
          (window.AudioContext || window.webkitAudioContext)
        )
        this.recorder = null
        return
      }

      if (typeof uni.getRecorderManager !== 'function') {
        this.recorder = null
        return
      }

      try {
        const recorder = uni.getRecorderManager()
        if (!recorder || typeof recorder.onStop !== 'function' || typeof recorder.onError !== 'function') {
          this.recorder = null
          return
        }

        this.recorder = recorder
        this.recorder.onStop((res) => this.handleVoiceFile(res))
        this.recorder.onError(() => {
          this.isRecording = false
          this.status = 'idle'
          uni.showToast({ title: '录音不可用，请输入文字', icon: 'none' })
        })
      } catch (e) {
        this.recorder = null
      }
    },
    async loadHistory() {
      try {
        const userId = uni.getStorageSync('userId') || 'guest'
        const history = await get('/chat/history', { user_id: userId })
        if (Array.isArray(history) && history.length) {
          this.messages = history.reverse().map(item => ({
            role: 'user',
            text: item.content || ''
          }))
        }
      } catch (e) {}
    },
    async openHistory() {
      await this.loadHistory()
      uni.showToast({ title: '已加载对话历史', icon: 'none' })
    },
    async startVoice(event) {
      if (event && typeof event.preventDefault === 'function') {
        event.preventDefault()
      }
      if (this.isRecording) return
      if (this.isRecognizing) return
      this.isRecording = true
      this.voiceStartAt = Date.now()
      this.status = 'listen'
      if (this.recorder) {
        this.recorder.start({ duration: 15000, sampleRate: 16000, numberOfChannels: 1, format: 'wav' })
      } else if (process.env.UNI_PLATFORM === 'h5') {
        await this.startH5Recording()
      } else {
        this.isRecording = false
        this.status = 'idle'
        uni.showToast({ title: '当前环境不支持录音，请输入文字', icon: 'none' })
      }
    },
    stopVoice(event) {
      if (event && typeof event.preventDefault === 'function') {
        event.preventDefault()
      }
      if (!this.isRecording) return
      this.isRecording = false
      if (this.recorder) {
        this.recorder.stop()
      } else if (process.env.UNI_PLATFORM === 'h5') {
        this.stopH5Recording()
      } else {
        this.status = 'idle'
      }
    },
    async startH5Recording() {
      if (!this.h5RecorderSupported) {
        this.isRecording = false
        this.status = 'idle'
        uni.showToast({ title: '浏览器不支持录音，请输入文字', icon: 'none' })
        return
      }

      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext
        this.h5AudioChunks = []
        this.h5MediaStream = await navigator.mediaDevices.getUserMedia({ audio: true })
        this.h5AudioContext = new AudioContext()
        this.h5InputSampleRate = this.h5AudioContext.sampleRate
        this.h5SourceNode = this.h5AudioContext.createMediaStreamSource(this.h5MediaStream)
        this.h5ProcessorNode = this.h5AudioContext.createScriptProcessor(4096, 1, 1)

        this.h5ProcessorNode.onaudioprocess = (audioEvent) => {
          if (!this.isRecording) return
          const input = audioEvent.inputBuffer.getChannelData(0)
          this.h5AudioChunks.push(new Float32Array(input))
        }

        this.h5SourceNode.connect(this.h5ProcessorNode)
        this.h5ProcessorNode.connect(this.h5AudioContext.destination)
      } catch (e) {
        this.cleanupH5Recording()
        this.isRecording = false
        this.status = 'idle'
        uni.showToast({ title: '无法访问麦克风，请检查权限', icon: 'none' })
      }
    },
    stopH5Recording() {
      const duration = Date.now() - this.voiceStartAt
      const chunks = this.h5AudioChunks.slice()
      const inputSampleRate = this.h5InputSampleRate
      this.cleanupH5Recording()

      if (duration < 300 || !chunks.length) {
        this.status = 'idle'
        uni.showToast({ title: '说话时间太短', icon: 'none' })
        return
      }

      const merged = this.mergeAudioChunks(chunks)
      const pcm16 = this.floatTo16BitPCM(this.downsampleBuffer(merged, inputSampleRate, 16000))
      const audioData = this.arrayBufferToBase64(pcm16.buffer)
      this.handleVoiceAudio({ audioData, format: 'pcm' })
    },
    cleanupH5Recording() {
      if (this.h5ProcessorNode) {
        this.h5ProcessorNode.disconnect()
        this.h5ProcessorNode.onaudioprocess = null
      }
      if (this.h5SourceNode) {
        this.h5SourceNode.disconnect()
      }
      if (this.h5MediaStream) {
        this.h5MediaStream.getTracks().forEach(track => track.stop())
      }
      if (this.h5AudioContext) {
        this.h5AudioContext.close()
      }
      this.h5ProcessorNode = null
      this.h5SourceNode = null
      this.h5MediaStream = null
      this.h5AudioContext = null
      this.h5AudioChunks = []
    },
    mergeAudioChunks(chunks) {
      const length = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
      const result = new Float32Array(length)
      let offset = 0
      chunks.forEach((chunk) => {
        result.set(chunk, offset)
        offset += chunk.length
      })
      return result
    },
    downsampleBuffer(buffer, inputSampleRate, outputSampleRate) {
      if (outputSampleRate === inputSampleRate) return buffer
      const ratio = inputSampleRate / outputSampleRate
      const newLength = Math.round(buffer.length / ratio)
      const result = new Float32Array(newLength)
      let offsetResult = 0
      let offsetBuffer = 0

      while (offsetResult < result.length) {
        const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
        let sum = 0
        let count = 0
        for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
          sum += buffer[i]
          count += 1
        }
        result[offsetResult] = count ? sum / count : 0
        offsetResult += 1
        offsetBuffer = nextOffsetBuffer
      }

      return result
    },
    floatTo16BitPCM(floatBuffer) {
      const pcm = new Int16Array(floatBuffer.length)
      for (let i = 0; i < floatBuffer.length; i++) {
        const sample = Math.max(-1, Math.min(1, floatBuffer[i]))
        pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
      }
      return pcm
    },
    arrayBufferToBase64(buffer) {
      const bytes = new Uint8Array(buffer)
      let binary = ''
      const chunkSize = 0x8000
      for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize))
      }
      return btoa(binary)
    },
    async handleVoiceFile(res = {}) {
      const duration = Date.now() - this.voiceStartAt
      if (duration < 300) {
        this.status = 'idle'
        uni.showToast({ title: '说话时间太短', icon: 'none' })
        return
      }

      try {
        const audioData = await this.readTempFileAsBase64(res.tempFilePath)
        await this.handleVoiceAudio({ audioData, format: 'wav' })
      } catch (e) {
        this.status = 'idle'
        uni.showToast({ title: '录音读取失败，请输入文字', icon: 'none' })
      }
    },
    readTempFileAsBase64(tempFilePath) {
      return new Promise((resolve, reject) => {
        if (!tempFilePath || typeof uni.getFileSystemManager !== 'function') {
          reject(new Error('录音文件不可用'))
          return
        }

        uni.getFileSystemManager().readFile({
          filePath: tempFilePath,
          encoding: 'base64',
          success: (res) => resolve(res.data),
          fail: reject
        })
      })
    },
    async handleVoiceAudio({ audioData, format }) {
      this.status = 'recognizing'
      this.isRecognizing = true
      try {
        const asr = await post('/ai/asr', { audio_data: audioData, format })
        const text = (asr && asr.text ? asr.text : '').trim()
        console.log('[Voice] ASR result', { text, format })
        if (!text || text === '无法识别') {
          this.status = 'idle'
          uni.showToast({ title: '没有识别到有效语音', icon: 'none' })
          return
        }
        await this.askQuestion(text)
      } catch (e) {
        this.status = 'idle'
        uni.showToast({ title: '语音识别失败，请输入文字', icon: 'none' })
      } finally {
        this.isRecognizing = false
      }
    },
    askQuick(text) {
      this.askQuestion(text)
    },
    sendText() {
      const text = this.inputText.trim()
      if (!text) return
      this.inputText = ''
      this.askQuestion(text)
    },
    async askQuestion(text) {
      const replySeq = this.activeReplySeq + 1
      this.activeReplySeq = replySeq
      this.stopCurrentSpeech()

      const userId = uni.getStorageSync('userId') || 'guest'
      this.messages.push({ role: 'user', text })
      this.scrollToBottom()
      this.status = 'think'
      this.emotion = 'neutral'

      try {
        const res = await post('/chat', { text, user_id: userId })
        if (replySeq !== this.activeReplySeq) return
        
        const answer = res.text || res.response || res.answer || '抱歉，我暂时没有检索到合适的讲解。'
        const speechText = res.speech_text || answer
        const replyId = res.reply_id || String(replySeq)
        const userEmotion = res.emotion || this.emotion

        const emotionExpression = this.getExpressionForEmotion(userEmotion)

        const digitalHuman = res.digital_human || {
          action: res.digital_human_action,
          expression: res.digital_human_expression || emotionExpression
        }

        this.messages.push({ role: 'assistant', text: answer })
        this.emotion = userEmotion
        this.status = 'speak'
        this.scrollToBottom()

        if (this.$refs.digitalHuman) {
          this.$refs.digitalHuman.applyDigitalHuman({
            ...digitalHuman,
            emotion: userEmotion,
            speaking: false
          })
        }
        this.trySpeak(speechText, replySeq, replyId)
      } catch (e) {
        if (replySeq !== this.activeReplySeq) return
        this.messages.push({ role: 'assistant', text: '当前网络不稳定，您可以稍后再问我。' })
        this.status = 'idle'
        this.scrollToBottom()
      }
    },
    getExpressionForEmotion(emotion) {
      const emotionMap = {
        positive: 'Smile',
        negative: 'Sad',
        surprised: 'Surprised',
        shy: 'Blushing',
        angry: 'Angry',
        neutral: 'Normal'
      }
      return emotionMap[emotion] || 'Normal'
    },
    stopCurrentSpeech(resetDigital = true) {
      if (this.audioElement) {
        this.audioElement.onplay = null
        this.audioElement.onended = null
        this.audioElement.onerror = null
        this.audioElement.pause()
        this.audioElement = null
      }

      if (resetDigital && this.$refs.digitalHuman) {
        this.$refs.digitalHuman.stopSpeaking()
      }
    },
    async trySpeak(text, replySeq = this.activeReplySeq, replyId = String(replySeq)) {
      try {
        const audio = await post('/ai/tts', { text, voice: 'female', reply_id: replyId })
        if (replySeq !== this.activeReplySeq) return

        if (audio && audio.audio_data) {
          this.stopCurrentSpeech(false)
          
          this.audioElement = new Audio(audio.audio_data)
          
          this.audioElement.onplay = () => {
            if (replySeq !== this.activeReplySeq) return
            if (this.$refs.digitalHuman) {
              this.$refs.digitalHuman.startRealLipSync(this.audioElement)
            }
          }
          this.audioElement.onended = () => this.finishSpeaking(replySeq)
          this.audioElement.onerror = () => this.finishSpeaking(replySeq)
          
          await this.audioElement.play()
          return
        }
      } catch (e) {}

      if (replySeq !== this.activeReplySeq) return
      if (this.$refs.digitalHuman) {
        this.$refs.digitalHuman.startSpeaking({
          expression: this.getExpressionForEmotion(this.emotion),
          motion: 'Tap'
        })
      }
      setTimeout(() => {
        this.finishSpeaking(replySeq)
      }, Math.min(5200, Math.max(1800, text.length * 80)))
    },
    finishSpeaking(replySeq = this.activeReplySeq) {
      if (replySeq !== this.activeReplySeq) return
      this.status = 'idle'
      if (this.$refs.digitalHuman) {
        this.$refs.digitalHuman.stopSpeaking()
      }
    },
    scrollToBottom() {
      setTimeout(() => {
        this.scrollTop = 99999
      }, 80)
    }
  }
}
</script>

<style lang="scss" scoped>
.digital-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 28%, rgba(231, 190, 104, 0.32), transparent 22%),
    linear-gradient(180deg, #1f3f3d 0%, #583025 55%, #201611 100%);
  color: #fff8e8;
}

.sky-layer {
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(115deg, rgba(255, 255, 255, 0.05) 0 2rpx, transparent 2rpx 26rpx),
    radial-gradient(circle at 20% 12%, rgba(255, 238, 180, 0.14), transparent 18%);
}

.top-bar {
  position: relative;
  z-index: 4;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 40rpx 30rpx 0;
}

.page-title,
.page-subtitle {
  display: block;
}

.page-title {
  font-size: 42rpx;
  font-weight: 900;
}

.page-subtitle {
  margin-top: 8rpx;
  color: rgba(255, 248, 232, 0.72);
  font-size: 24rpx;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.history-button {
  width: 58rpx;
  height: 58rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1rpx solid rgba(255, 248, 232, 0.35);
  border-radius: 50%;
  background: rgba(255, 248, 232, 0.12);
  color: #fff8e8;
  font-size: 24rpx;
  line-height: 1;
}

.emotion-pill {
  padding: 10rpx 18rpx;
  border: 1rpx solid rgba(255, 248, 232, 0.35);
  border-radius: 999rpx;
  background: rgba(255, 248, 232, 0.12);
  font-size: 22rpx;
}

.stage {
  position: relative;
  z-index: 2;
  height: 700rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.halo {
  position: absolute;
  width: 430rpx;
  height: 430rpx;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(242, 202, 112, 0.48), rgba(242, 202, 112, 0.08) 58%, transparent 70%);
  animation: breathe 4s ease-in-out infinite;
}

.stage-human {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
}

.shadow {
  position: absolute;
  bottom: 42rpx;
  width: 260rpx;
  height: 38rpx;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.28);
  filter: blur(4rpx);
}

.dialog-panel {
  position: relative;
  z-index: 5;
  margin: -10rpx 24rpx 0;
  padding: 20rpx;
  border: 1rpx solid rgba(255, 248, 232, 0.18);
  border-radius: 12rpx;
  background: rgba(255, 248, 232, 0.9);
  color: #37251a;
}

.message-scroll {
  height: 290rpx;
}

.message {
  max-width: 84%;
  margin-bottom: 18rpx;
  padding: 16rpx 18rpx;
  border-radius: 10rpx;
  background: #f3e3c4;
}

.message.user {
  margin-left: auto;
  background: #8c3228;
  color: #fff8e8;
}

.message-role,
.message-text {
  display: block;
}

.message-role {
  margin-bottom: 8rpx;
  font-size: 20rpx;
  opacity: 0.72;
}

.message-text {
  font-size: 26rpx;
  line-height: 1.55;
}

.quick-row {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
  padding: 12rpx 0;
  white-space: nowrap;
}

.quick-chip {
  display: inline-flex;
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #6d4b2d;
  font-size: 22rpx;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.text-input {
  flex: 1;
  height: 72rpx;
  padding: 0 20rpx;
  border-radius: 8rpx;
  background: #fffaf0;
  font-size: 26rpx;
}

.send-button {
  width: 112rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #8c3228;
  color: #fff8e8;
  font-size: 26rpx;
}

.send-button[disabled] {
  background: #666;
  opacity: 0.6;
}

.text-input[disabled] {
  opacity: 0.6;
}

.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(140, 50, 40, 0.8);
  color: #fff8e8;
  font-size: 22rpx;
}

.thinking-dots {
  display: flex;
  align-items: center;
  gap: 6rpx;
}

.thinking-dots .dot {
  width: 8rpx;
  height: 8rpx;
  border-radius: 50%;
  background: #fff8e8;
  animation: dot-bounce 1.4s infinite ease-in-out both;
}

.thinking-dots .dot:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: -0.16s;
}

.thinking-dots .dot:nth-child(3) {
  animation-delay: 0s;
}

@keyframes dot-bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.voice-control {
  position: relative;
  z-index: 6;
  padding: 22rpx 42rpx calc(30rpx + env(safe-area-inset-bottom));
}

.voice-button {
  width: 100%;
  min-height: 112rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #c1924f, #8d3228);
  color: #fff8e8;
  box-shadow: 0 16rpx 36rpx rgba(0, 0, 0, 0.22);
}

.voice-button.recording {
  background: linear-gradient(135deg, #2f6570, #9b3a2d);
}

.voice-button.disabled {
  background: #555;
  box-shadow: none;
  opacity: 0.6;
}

.voice-main,
.voice-sub {
  display: block;
}

.voice-main {
  font-size: 32rpx;
  font-weight: 900;
}

.voice-sub {
  margin-top: 6rpx;
  font-size: 22rpx;
  opacity: 0.78;
}

@keyframes breathe {
  0%, 100% {
    transform: scale(0.96);
    opacity: 0.72;
  }

  50% {
    transform: scale(1.06);
    opacity: 1;
  }
}
</style>
