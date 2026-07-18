<template>
  <view class="digital-page">
    <view class="sky-layer"></view>

    <view class="top-bar">
      <view>
        <text class="page-title">灵山数字人</text>
        <text class="page-subtitle">{{ statusText }}</text>
      </view>
      <view class="top-actions">
        <button class="history-button" @click="openHistory">
          <svg t="1784360750105" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="5336" width="200" height="200"><path d="M516.693333 19.2a495.36 495.36 0 1 0 495.36 495.36A495.786667 495.786667 0 0 0 516.693333 19.2z m0 926.72a431.36 431.36 0 1 1 431.36-431.36 431.786667 431.786667 0 0 1-431.36 431.786667z" fill="#ffffff" p-id="5337"></path><path d="M548.693333 501.333333V227.84a32 32 0 0 0-64 0v287.146667a31.573333 31.573333 0 0 0 9.813334 22.613333l235.946666 227.413333a32 32 0 1 0 42.666667-46.08z" fill="#ffffff" p-id="5338"></path></svg>
        </button>
      </view>
    </view>

    <view class="stage">
      <view class="halo"></view>
      <DigitalHuman
        :key="digitalHumanModelPath"
        ref="digitalHuman"
        class="stage-human"
        :status="status"
        :emotion="emotion"
        :model-path="digitalHumanModelPath"
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
          <view class="service-actions" v-if="msg.service_actions && msg.service_actions.length > 0">
            <view 
              class="service-action-item" 
              v-for="(action, actionIndex) in msg.service_actions" 
              :key="actionIndex"
              @click="navigateToService(action)"
            >
              <text class="service-action-icon">{{ action.icon }}</text>
              <text class="service-action-name">{{ serviceActionLabel(action) }}</text>
            </view>
          </view>
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
        <view class="input-tools">
          <view class="emoji-trigger" @click="toggleEmojiPanel">
            <text class="emoji-icon">😊</text>
          </view>
          <input
            class="text-input"
            v-model="inputText"
            :disabled="status === 'listen' || status === 'recognizing' || status === 'think'"
            :placeholder="status === 'listen' ? '正在聆听，请说话...' : status === 'recognizing' ? '正在识别语音...' : status === 'think' ? '请稍候，正在思考中...' : '也可以输入文字询问'"
            confirm-type="send"
            @confirm="sendText"
          />
          <button class="send-button" :disabled="status === 'listen' || status === 'recognizing' || status === 'think' || !inputText.trim()" @click="sendText">发送</button>
        </view>
        
        <view class="emoji-panel" v-if="showEmojiPanel">
          <view class="emoji-grid">
            <view 
              class="emoji-item" 
              v-for="(item, index) in emojiList" 
              :key="index" 
              @click="selectEmoji(item)"
            >
              <text class="emoji-char">{{ item.emoji }}</text>
              <text class="emoji-label">{{ item.label }}</text>
            </view>
          </view>
        </view>
      </view>
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

    <view class="history-mask" v-if="showHistoryPanel" @click="closeHistoryPanel">
      <view class="history-sheet" @click.stop>
        <view class="history-head">
          <text class="history-title-main">近期会话</text>
          <button class="history-close" @click="closeHistoryPanel">×</button>
        </view>
        <scroll-view class="history-list" scroll-y>
          <view class="history-empty" v-if="historyLoading">正在加载...</view>
          <view class="history-empty" v-else-if="historySessions.length === 0">暂无历史会话</view>
          <view
            class="history-session"
            :class="{ active: item.session_id === chatSessionId }"
            v-for="item in historySessions"
            :key="item.session_id"
            @click="selectHistorySession(item)"
          >
            <view class="history-session-top">
              <text class="history-session-title">{{ item.title || '未命名会话' }}</text>
              <text class="history-session-time">{{ formatHistoryTime(item.latest_message_at || item.updated_at) }}</text>
            </view>
            <text class="history-session-preview">{{ item.preview || '点击查看完整对话' }}</text>
            <text class="history-session-count">{{ item.turn_count || 0 }} 轮对话</text>
          </view>
        </scroll-view>
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
import FeedbackModal from '@/components/FeedbackModal/index.vue'
import { get, post } from '@/utils/request'
import { requestCurrentLocation, getLocationErrorMessage } from '@/utils/location'
import { promptForFeedback, markFeedbackPrompt, openFeedbackPage } from '@/utils/feedback'
import { streamChat } from '@/utils/sse'

export default {
  components: {
    DigitalHuman,
    FeedbackModal
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
      digitalHumanModelPath: '/static/live2d/epsilon_ja/epsilon_free/runtime/Epsilon_free.model3.json',
      digitalHumanVoice: 'female',
      digitalHumanName: '灵山数字导游',
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
      currentSseClient: null,
      chatSessionId: '',
      chatQuestionCount: 0,
      chatSessionTimeoutMs: 20 * 60 * 1000,
      showHistoryPanel: false,
      historyLoading: false,
      historySessions: [],
      isPageActive: true,
      showFeedbackModal: false,
      feedbackModalConfig: {
        title: '',
        content: '',
        params: {},
        type: '',
        targetKey: ''
      },
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
      ],
      showEmojiPanel: false,
      emojiList: [
        { emoji: '😊', label: '开心', emotion: 'positive' },
        { emoji: '👍', label: '点赞', emotion: 'positive' },
        { emoji: '❤️', label: '感谢', emotion: 'positive' },
        { emoji: '🙏', label: '祈福', emotion: 'positive' },
        { emoji: '🎉', label: '庆祝', emotion: 'positive' },
        { emoji: '😊', label: '微笑', emotion: 'positive' },
        { emoji: '😁', label: '大笑', emotion: 'positive' },
        { emoji: '🤗', label: '拥抱', emotion: 'positive' },
        { emoji: '🤔', label: '疑惑', emotion: 'neutral' },
        { emoji: '😲', label: '惊讶', emotion: 'surprised' },
        { emoji: '😳', label: '害羞', emotion: 'shy' },
        { emoji: '😭', label: '难过', emotion: 'negative' },
        { emoji: '😢', label: '伤心', emotion: 'negative' },
        { emoji: '😩', label: '疲惫', emotion: 'negative' },
        { emoji: '😵‍💫', label: '晕', emotion: 'negative' },
        { emoji: '😞', label: '失望', emotion: 'negative' },
        { emoji: '😠', label: '生气', emotion: 'angry' },
        { emoji: '☹️', label: '不满', emotion: 'angry' }
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
    this.ensureChatSession()
    this.loadDigitalHumanConfig()
    if (options && options.history === 'true') this.loadHistory()
    this.initRecorder()
  },
  onShow() {
    this.isPageActive = true
    this.$nextTick(() => {
      if (this.$refs.digitalHuman) this.$refs.digitalHuman.ensureLive2D()
    })
    if (uni.getStorageSync('openChatHistory')) {
      uni.removeStorageSync('openChatHistory')
      this.loadHistory()
    }
  },
  onHide() {
    this.isPageActive = false
    if (this.$refs.digitalHuman) {
      this.$refs.digitalHuman.destroyLive2D({ releaseAudioGraph: false })
      this.digitalReady = false
    }
    this.showFeedbackModal = false
    this.closeSseConnection()
    this.stopCurrentSpeech()
  },
  onUnload() {
    this.isPageActive = false
    uni.removeStorageSync('chatSession')
    this.cleanupH5Recording()
    this.stopCurrentSpeech(false)
    this.showFeedbackModal = false
    this.closeSseConnection()
    if (this.$refs.digitalHuman) {
      this.$refs.digitalHuman.destroyLive2D({ releaseAudioGraph: false })
      this.digitalReady = false
    }
  },
  methods: {
    async loadDigitalHumanConfig() {
      try {
        const config = await get('/digital-human/config')
        if (!config) return
        if (config.model) this.digitalHumanModelPath = config.model
        if (config.voice === 'male' || config.voice === 'female') this.digitalHumanVoice = config.voice
        if (config.name) this.digitalHumanName = config.name
        if (this.messages[0] && this.messages[0].role === 'assistant') {
          this.messages[0].text = `您好，我是${this.digitalHumanName}。您可以按住说话，也可以输入文字，询问景点、路线、演出或祈福活动。`
        }
      } catch (error) {
        // Keep the bundled model and default voice when the service is unavailable.
      }
    },
    createChatSessionId() {
      return `chat_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
    },
    ensureChatSession(forceNew = false) {
      const now = Date.now()
      const stored = uni.getStorageSync('chatSession') || {}
      const expired = !stored.lastActiveAt || now - Number(stored.lastActiveAt) > this.chatSessionTimeoutMs
      if (forceNew || !stored.sessionId || expired) {
        const next = {
          sessionId: this.createChatSessionId(),
          lastActiveAt: now
        }
        uni.setStorageSync('chatSession', next)
        this.chatSessionId = next.sessionId
        this.chatQuestionCount = 0
        return this.chatSessionId
      }
      stored.lastActiveAt = now
      uni.setStorageSync('chatSession', stored)
      this.chatSessionId = stored.sessionId
      return this.chatSessionId
    },
    touchChatSession() {
      const sessionId = this.chatSessionId || this.ensureChatSession()
      uni.setStorageSync('chatSession', {
        sessionId,
        lastActiveAt: Date.now()
      })
    },
    activateChatSession(sessionId) {
      if (!sessionId) return this.ensureChatSession()
      this.chatSessionId = sessionId
      this.chatQuestionCount = 0
      uni.setStorageSync('chatSession', {
        sessionId,
        lastActiveAt: Date.now()
      })
      return sessionId
    },
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
    async loadChatSessions() {
      try {
        this.historyLoading = true
        const userId = uni.getStorageSync('userId') || 'guest'
        const sessions = await get('/chat/sessions', { user_id: userId, limit: 20 })
        this.historySessions = Array.isArray(sessions) ? sessions : []
      } catch (e) {
        this.historySessions = []
      } finally {
        this.historyLoading = false
      }
    },
    formatHistoryTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    },
    closeHistoryPanel() {
      this.showHistoryPanel = false
    },
    async loadHistory(sessionId) {
      try {
        const userId = uni.getStorageSync('userId') || 'guest'
        const activeSessionId = this.activateChatSession(sessionId || this.ensureChatSession())
        const history = await get('/chat/history', { user_id: userId, session_id: activeSessionId })
        if (Array.isArray(history) && history.length) {
          const nextMessages = []
          history.reverse().forEach((item) => {
            if (item.content) {
              nextMessages.push({ role: 'user', text: item.content })
            }
            if (item.reply_text) {
              nextMessages.push({ role: 'assistant', text: item.reply_text })
            }
          })
          this.messages = nextMessages.length ? nextMessages : this.messages
          this.scrollToBottom()
          this.activateChatSession(activeSessionId)
        }
      } catch (e) {}
    },
    async openHistory() {
      this.showHistoryPanel = true
      await this.loadChatSessions()
    },
    async selectHistorySession(session) {
      if (!session || !session.session_id) return
      this.stopCurrentSpeech()
      await this.loadHistory(session.session_id)
      this.showHistoryPanel = false
      uni.showToast({ title: '已切换到历史会话', icon: 'none' })
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
    serviceActionLabel(action = {}) {
      const actionType = action.action_type || 'navigate_to'
      if (actionType !== 'open_location') return action.name || ''
      return '开始导航'
    },
    async navigateToService(action) {
      const actionType = action.action_type || 'navigate_to'

      if (actionType === 'open_location') {
        const payload = action.payload || {}
        const latitude = Number(payload.latitude)
        const longitude = Number(payload.longitude)
        if (!latitude || !longitude) {
          uni.showToast({ title: '暂无可导航位置', icon: 'none' })
          return
        }
        uni.openLocation({
          latitude,
          longitude,
          name: payload.name || action.name || '目的地',
          address: payload.address || ''
        })
        return
      }

      if (actionType === 'request_location') {
        const location = await this.resolveCurrentLocation(true)
        if (location) {
          await this.askQuestion('我在当前位置附近', {
            location,
            displayText: '已获取当前位置，请继续查询附近设施'
          })
        }
        return
      }

      if (!action.path) return
      let url = action.path
      if (action.params && Object.keys(action.params).length > 0) {
        const params = new URLSearchParams(action.params).toString()
        url = `${url}?${params}`
      }

      if (actionType === 'switch_tab') {
        uni.switchTab({ url: action.path })
        return
      }
      uni.navigateTo({ url })
    },
    toggleEmojiPanel() {
      this.showEmojiPanel = !this.showEmojiPanel
    },
    selectEmoji(item) {
      this.inputText += item.emoji
      this.showEmojiPanel = false
    },
    sendText() {
      const text = this.inputText.trim()
      if (!text) return
      this.inputText = ''
      this.showEmojiPanel = false
      this.askQuestion(text)
    },
    shouldAttachLocation(text) {
      return ['附近', '周围', '旁边', '最近', '迷路', '怎么走', '导航', '带我去', '我想去', '想去', '前往', '天气好热', '避暑', '走不动', '休息', '吃饭', '餐厅', '厕所'].some(word => text.includes(word))
    },
    notifyLocationFeedback(location) {
      if (!location) return
      const label = location.isFallback ? '默认起点' : location.isCached ? '上次位置' : '当前位置'
      uni.showToast({ title: `已获取${label}`, icon: 'none' })
    },
    async resolveCurrentLocation(showFeedback = false) {
      try {
        const location = await requestCurrentLocation({ allowCache: true, allowFallback: false })
        if (showFeedback) {
          this.notifyLocationFeedback(location)
        }
        return location
      } catch (error) {
        if (showFeedback) {
          uni.showToast({ title: getLocationErrorMessage(error), icon: 'none' })
        }
        return null
      }
    },
    getCurrentLocationForChat(text) {
      if (!this.shouldAttachLocation(text)) return Promise.resolve({})
      return this.resolveCurrentLocation(false).then((location) => {
        if (!location) return {}
        this.notifyLocationFeedback(location)
        return {
          latitude: location.latitude,
          longitude: location.longitude
        }
      })
    },
    async askQuestion(text, options = {}) {
      const replySeq = this.activeReplySeq + 1
      this.activeReplySeq = replySeq
      this.stopCurrentSpeech()

      const userId = uni.getStorageSync('userId') || 'guest'
      const sessionId = this.ensureChatSession()
      this.messages.push({ role: 'user', text: options.displayText || text })
      this.scrollToBottom()
      this.status = 'think'
      this.emotion = 'neutral'

      try {
        const locationPayload = options.location ? {
          latitude: options.location.latitude,
          longitude: options.location.longitude
        } : await this.getCurrentLocationForChat(text)
        this.touchChatSession()

        const assistantMsgIndex = this.messages.length
        this.messages.push({ role: 'assistant', text: '', service_actions: [], debug_info: {} })

        let speechText = ''
        let replyId = String(replySeq)
        let userEmotion = 'neutral'
        let digitalHumanConfig = {}
        let leadSpeechText = ''
        let leadSpeechPromise = null

        const onMessage = (data) => {
          if (replySeq !== this.activeReplySeq) return

          if (data.type === 'content') {
            this.messages[assistantMsgIndex].text = data.text
            replyId = data.reply_id || replyId
            this.status = 'speak'
            this.scrollToBottom()
          } else if (data.type === 'speech') {
            const nextLeadText = String(data.text || '').trim()
            if (nextLeadText && !leadSpeechPromise) {
              leadSpeechText = nextLeadText
              replyId = data.reply_id || replyId
              leadSpeechPromise = this.trySpeak(
                leadSpeechText,
                replySeq,
                `${replyId}_lead`
              )
            }
          } else if (data.type === 'metadata') {
            speechText = data.speech_text || this.messages[assistantMsgIndex].text
            replyId = data.reply_id || replyId
            userEmotion = data.emotion || userEmotion
            this.emotion = userEmotion

            const emotionExpression = this.getExpressionForEmotion(userEmotion)
            digitalHumanConfig = {
              action: data.digital_human_action,
              expression: data.digital_human_expression || emotionExpression,
              motion: data.digital_human_motion
            }

            if (data.service_actions) {
              this.messages[assistantMsgIndex].service_actions = data.service_actions
            }
            if (data.debug) {
              this.messages[assistantMsgIndex].debug_info = data.debug
            }

            if (this.$refs.digitalHuman) {
              this.$refs.digitalHuman.applyDigitalHuman({
                ...digitalHumanConfig,
                emotion: userEmotion,
                speaking: !!leadSpeechPromise
              })
            }
          }
        }

        const onError = (error) => {
          if (replySeq !== this.activeReplySeq) return
          console.error('Streaming error:', error)
          this.messages[assistantMsgIndex].text = '当前网络不稳定，您可以稍后再问我。'
          this.status = 'idle'
          this.scrollToBottom()
        }

        const onClose = async () => {
          if (replySeq !== this.activeReplySeq) return
          if (leadSpeechPromise) {
            await leadSpeechPromise
            if (replySeq !== this.activeReplySeq) return
          }

          let remainingSpeechText = speechText
          if (leadSpeechText && remainingSpeechText.startsWith(leadSpeechText)) {
            remainingSpeechText = remainingSpeechText.slice(leadSpeechText.length).trim()
          }
          if (remainingSpeechText) {
            await this.trySpeak(remainingSpeechText, replySeq, `${replyId}_tail`)
          }
          this.chatQuestionCount += 1
          this.maybePromptChatFeedback(sessionId)
        }

        this.currentSseClient = await streamChat({ text, user_id: userId, session_id: sessionId, ...locationPayload }, onMessage, onError, onClose)
      } catch (e) {
        if (replySeq !== this.activeReplySeq) return
        this.messages.push({ role: 'assistant', text: '当前网络不稳定，您可以稍后再问我。' })
        this.status = 'idle'
        this.scrollToBottom()
      }
    },
    /*
    maybePromptChatFeedback(sessionId) {
      if (this.chatQuestionCount < 3) return
      const targetKey = sessionId || this.chatSessionId
      promptForFeedback({
        type: 'chat',
        targetKey,
        title: '评价',
        content: '你已经和数字人连续交流了几轮，愿意花几秒钟评价这次问答体验吗？',
        params: {
          feedback_type: 'chat',
          target_type: 'chat',
          target_id: targetKey,
          target_name: 'AI 对话',
          source: 'chat',
          session_id: targetKey
        }
      })
    },
    */
    async maybePromptChatFeedback(sessionId) {
      if (!this.isPageActive) return
      if (this.chatQuestionCount < 3) return
      const targetKey = sessionId || this.chatSessionId
      const result = await promptForFeedback({
        type: 'chat',
        targetKey,
        title: '评价',
        content: '你已经和数字人连续交流了几轮，愿意花几秒钟评价这次问答体验吗？',
        params: {
          feedback_type: 'chat',
          target_type: 'chat',
          target_id: targetKey,
          target_name: 'AI 对话',
          source: 'chat',
          session_id: targetKey
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
      this.closeSseConnection()
      this.stopCurrentSpeech()
      if (this.feedbackModalConfig.params) {
        openFeedbackPage(this.feedbackModalConfig.params)
      }
    },
    closeSseConnection() {
      if (this.currentSseClient) {
        try {
          this.currentSseClient.close()
        } catch (e) {}
        this.currentSseClient = null
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
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel()
      }
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
    splitSpeechText(text, maxLen = 220) {
      const normalized = String(text || '').replace(/\s+/g, ' ').trim()
      if (!normalized) return []

      const rawParts = normalized.split(/([。！？!?；;])/)
      const sentences = []
      for (let i = 0; i < rawParts.length; i += 2) {
        const left = rawParts[i] || ''
        const right = rawParts[i + 1] || ''
        const sentence = `${left}${right}`.trim()
        if (sentence) sentences.push(sentence)
      }
      const chunks = []
      let buffer = ''
      const softBreakChars = ['，', ',', '、', '；', ';']

      const pushBuffer = () => {
        const trimmed = buffer.trim()
        if (trimmed) chunks.push(trimmed)
        buffer = ''
      }

      const pushLongSentence = (sentence) => {
        let rest = sentence.trim()
        while (rest.length > maxLen) {
          let cutIndex = -1
          for (const ch of softBreakChars) {
            const idx = rest.lastIndexOf(ch, maxLen)
            if (idx > cutIndex) cutIndex = idx
          }
          if (cutIndex < Math.floor(maxLen * 0.5)) {
            cutIndex = maxLen
          } else {
            cutIndex += 1
          }
          chunks.push(rest.slice(0, cutIndex).trim())
          rest = rest.slice(cutIndex).trim()
        }
        if (rest) buffer = rest
      }

      for (const sentence of sentences) {
        if (!sentence) continue
        if ((buffer + sentence).length <= maxLen) {
          buffer += sentence
          continue
        }

        pushBuffer()

        if (sentence.length <= maxLen) {
          buffer = sentence
          continue
        }

        pushLongSentence(sentence)
      }

      pushBuffer()
      return chunks.length ? chunks : [normalized]
    },
    playSpeechAudio(audioData, replySeq) {
      return new Promise((resolve) => {
        if (!audioData || replySeq !== this.activeReplySeq) {
          resolve(false)
          return
        }

        this.audioElement = new Audio(audioData)
        this.audioElement.onplay = () => {
          if (replySeq !== this.activeReplySeq) return
          if (this.$refs.digitalHuman) {
            this.$refs.digitalHuman.startRealLipSync(this.audioElement)
          }
        }
        this.audioElement.onended = () => {
          if (this.audioElement) {
            this.audioElement.onplay = null
            this.audioElement.onended = null
            this.audioElement.onerror = null
            this.audioElement = null
          }
          resolve(true)
        }
        this.audioElement.onerror = () => {
          if (this.audioElement) {
            this.audioElement.onplay = null
            this.audioElement.onended = null
            this.audioElement.onerror = null
            this.audioElement = null
          }
          resolve(false)
        }

        this.audioElement.play().catch(() => {
          if (this.audioElement) {
            this.audioElement.onplay = null
            this.audioElement.onended = null
            this.audioElement.onerror = null
            this.audioElement = null
          }
          resolve(false)
        })
      })
    },
    playBrowserSpeech(text, replySeq) {
      return new Promise((resolve) => {
        if (
          !text ||
          replySeq !== this.activeReplySeq ||
          typeof window === 'undefined' ||
          !window.speechSynthesis ||
          typeof window.SpeechSynthesisUtterance !== 'function'
        ) {
          resolve(false)
          return
        }

        const utterance = new window.SpeechSynthesisUtterance(text)
        utterance.lang = 'zh-CN'
        utterance.rate = 1
        utterance.pitch = 1
        utterance.onstart = () => {
          if (replySeq === this.activeReplySeq && this.$refs.digitalHuman) {
            this.$refs.digitalHuman.startSpeaking({ motion: 'Tap' })
          }
        }
        utterance.onend = () => resolve(true)
        utterance.onerror = () => resolve(false)
        window.speechSynthesis.speak(utterance)
      })
    },
    async trySpeak(text, replySeq = this.activeReplySeq, replyId = String(replySeq)) {
      try {
        const speechChunks = this.splitSpeechText(text)
        if (speechChunks.length > 1) {
          this.stopCurrentSpeech(false)
          for (let i = 0; i < speechChunks.length; i++) {
            if (replySeq !== this.activeReplySeq) return
            const audio = await post('/ai/tts', {
              text: speechChunks[i],
              voice: this.digitalHumanVoice,
              reply_id: `${replyId}_${i + 1}`
            })
            if (replySeq !== this.activeReplySeq) return
            if (!audio || !audio.audio_data) {
              continue
            }
            const played = audio && audio.audio_data
              ? await this.playSpeechAudio(audio.audio_data, replySeq)
              : await this.playBrowserSpeech(speechChunks[i], replySeq)
            if (!played) return
          }
          this.finishSpeaking(replySeq)
          return
        }

        const audio = await post('/ai/tts', { text, voice: this.digitalHumanVoice, reply_id: replyId })
        if (replySeq !== this.activeReplySeq) return

        if (audio && audio.audio_data) {
          this.stopCurrentSpeech(false)
          const played = await this.playSpeechAudio(audio.audio_data, replySeq)
          if (played) {
            this.finishSpeaking(replySeq)
            return
          }
        } else {
          const played = await this.playBrowserSpeech(text, replySeq)
          if (played) {
            this.finishSpeaking(replySeq)
            return
          }
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
  display: flex;
  flex-direction: column;
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
  flex: 0 0 40vh;
  min-height: 360rpx;
  max-height: 520rpx;
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
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.message-scroll {
  flex: 1;
  min-height: 0;
  height: auto;
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

.service-actions {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
  flex-wrap: wrap;
}

.service-action-item {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: rgba(140, 50, 40, 0.15);
  border: 1rpx solid rgba(140, 50, 40, 0.3);
}

.service-action-item:active {
  background: rgba(140, 50, 40, 0.25);
}

.service-action-icon {
  font-size: 24rpx;
}

.service-action-name {
  font-size: 22rpx;
  color: #8c3228;
}

.quick-row {
  display: flex;
  gap: 12rpx;
  overflow-x: auto;
  padding: 12rpx 0;
  white-space: nowrap;
  flex-shrink: 0;
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
  flex-direction: column;
  gap: 12rpx;
  flex-shrink: 0;
}

.history-mask {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  align-items: flex-end;
  background: rgba(0, 0, 0, 0.38);
}

.history-sheet {
  width: 100%;
  max-height: 70vh;
  padding: 24rpx;
  border-radius: 18rpx 18rpx 0 0;
  background: #fff8e8;
  color: #37251a;
}

.history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.history-title-main {
  font-size: 30rpx;
  font-weight: 800;
}

.history-close {
  width: 52rpx;
  height: 52rpx;
  padding: 0;
  border-radius: 50%;
  background: #f0dfbd;
  color: #6d4b2d;
  font-size: 34rpx;
  line-height: 52rpx;
}

.history-list {
  max-height: 58vh;
}

.history-empty {
  padding: 48rpx 0;
  text-align: center;
  color: #8b7357;
  font-size: 26rpx;
}

.history-session {
  padding: 18rpx;
  margin-bottom: 14rpx;
  border: 1rpx solid rgba(140, 50, 40, 0.12);
  border-radius: 10rpx;
  background: #f3e3c4;
}

.history-session.active {
  border-color: rgba(140, 50, 40, 0.45);
  background: #efd8ad;
}

.history-session-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.history-session-title {
  flex: 1;
  font-size: 28rpx;
  font-weight: 700;
  color: #37251a;
}

.history-session-time {
  flex-shrink: 0;
  color: #8b7357;
  font-size: 22rpx;
}

.history-session-preview {
  display: block;
  margin-top: 8rpx;
  color: #6d4b2d;
  font-size: 24rpx;
  line-height: 1.45;
}

.history-session-count {
  display: block;
  margin-top: 8rpx;
  color: #9a7b54;
  font-size: 22rpx;
}

.input-tools {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.emoji-trigger {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8rpx;
  background: #fffaf0;
}

.emoji-icon {
  font-size: 36rpx;
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

.emoji-panel {
  padding: 16rpx;
  border-radius: 10rpx;
  background: #fffaf0;
}

.emoji-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.emoji-item {
  width: 88rpx;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6rpx;
  padding: 10rpx;
  border-radius: 8rpx;
  background: #f3e3c4;
}

.emoji-item:active {
  background: #e8d4a8;
}

.emoji-char {
  font-size: 36rpx;
}

.emoji-label {
  font-size: 20rpx;
  color: #6d4b2d;
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
