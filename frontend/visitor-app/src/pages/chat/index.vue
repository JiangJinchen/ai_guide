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
          <image class="history-icon" src="/static/icons/history.png" mode="aspectFit"></image>
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
        :speaking="speechPlaybackActive"
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
import { get, post, BASE_URL } from '@/utils/request'
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
      speechPlaybackActive: false,
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
    this.speechPlaybackActive = false
    if (this.status === 'speak') this.status = 'idle'
    this.$nextTick(() => {
      if (this.$refs.digitalHuman) {
        this.$refs.digitalHuman.ensureLive2D()
        this.$refs.digitalHuman.stopSpeaking()
      }
    })
    if (uni.getStorageSync('openChatHistory')) {
      uni.removeStorageSync('openChatHistory')
      this.loadHistory()
    }
  },
  onHide() {
    const keepPendingReply = this.status === 'think'
    console.log('[chat] onHide', {
      status: this.status,
      keepPendingReply,
      activeReplySeq: this.activeReplySeq,
      hasSseClient: !!this.currentSseClient
    })
    this.isPageActive = false
    if (!keepPendingReply) {
      this.activeReplySeq += 1
      this.closeSseConnection()
      this.stopCurrentSpeech()
      this.status = 'idle'
      this.speechPlaybackActive = false
    }
    this.showFeedbackModal = false
    if (this.$refs.digitalHuman) {
      this.$refs.digitalHuman.stopSpeaking()
      this.$refs.digitalHuman.pauseRendering()
    }
  },
  onUnload() {
    this.isPageActive = false
    this.activeReplySeq += 1
    uni.removeStorageSync('chatSession')
    this.cleanupH5Recording()
    this.stopCurrentSpeech(false)
    this.showFeedbackModal = false
    this.closeSseConnection()
    if (this.$refs.digitalHuman) {
      this.$refs.digitalHuman.destroyLive2D({ releaseAudioGraph: false })
      this.digitalReady = false
    }
  },  methods: {
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
      console.log('[chat] digital human ready', { digitalReady: this.digitalReady })
    },
    onDigitalError(error) {
      const message = error && error.message ? error.message : '数字人模型加载失败'
      const transient = /document unavailable|stage unavailable|querySelector|appendChild|Cannot read property/i.test(message)
      console.warn('[chat] digital human error received', { message, transient, digitalReady: this.digitalReady })
      if (transient || this.digitalReady) {
        console.warn('[chat] ignore digital human error', { message, transient, digitalReady: this.digitalReady })
        return
      }
      this.digitalReady = false
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
      console.log('[chat] service action click', { action, action_type: actionType })

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

      if (!action.path) {
        console.warn('[chat] service action missing path', { action, action_type: actionType })
        return
      }
      let url = action.path
      if (action.params && Object.keys(action.params).length > 0) {
        const params = Object.keys(action.params)
          .filter(key => action.params[key] !== undefined && action.params[key] !== null)
          .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(String(action.params[key])))
          .join('&')
        if (params) url = url + '?' + params
      }

      if (actionType === 'switch_tab') {
        console.log('[chat] service action switchTab', { url: action.path, action })
        uni.switchTab({
          url: action.path,
          success: () => console.log('[chat] service action switchTab success', { url: action.path }),
          fail: (error) => console.warn('[chat] service action switchTab failed', { url: action.path, error })
        })
        return
      }
      console.log('[chat] service action navigateTo', { url, action })
      uni.navigateTo({
        url,
        success: () => console.log('[chat] service action navigateTo success', { url }),
        fail: (error) => console.warn('[chat] service action navigateTo failed', { url, error })
      })
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
      if (!this.shouldAttachLocation(text)) {
        console.log('[chat] getCurrentLocationForChat skip', { text })
        return Promise.resolve({})
      }
      console.log('[chat] getCurrentLocationForChat start', { text })
      return this.resolveCurrentLocation(false).then((location) => {
        console.log('[chat] getCurrentLocationForChat resolved', { text, hasLocation: !!location, location })
        if (!location) return {}
        this.notifyLocationFeedback(location)
        return {
          latitude: location.latitude,
          longitude: location.longitude
        }
      })
    },
    async askQuestion(text, options = {}) {
      console.log('[chat] askQuestion start', {
        text,
        options,
        status: this.status,
        digitalReady: this.digitalReady,
      })
      const replySeq = this.activeReplySeq + 1
      this.activeReplySeq = replySeq
      this.stopCurrentSpeech()

      const userId = uni.getStorageSync('userId') || 'guest'
      const sessionId = this.ensureChatSession()
      this.messages.push({ role: 'user', text: options.displayText || text })
      this.scrollToBottom()
      this.status = 'think'
      console.log('[chat] askQuestion status set', { text, status: this.status, activeReplySeq: this.activeReplySeq })
      this.emotion = 'neutral'

      try {
        console.log('[chat] askQuestion location payload', { text, options, status: this.status })
        const locationPayload = options.location ? {
          latitude: options.location.latitude,
          longitude: options.location.longitude
        } : await this.getCurrentLocationForChat(text)
        console.log('[chat] askQuestion location resolved', { text, locationPayload, status: this.status })
        this.touchChatSession()
        console.log('[chat] askQuestion after touchChatSession', { text, status: this.status, sessionId })

        const assistantMsgIndex = this.messages.length
        this.messages.push({ role: 'assistant', text: '', service_actions: [], debug_info: {} })

        let speechText = ''
        let replyId = String(replySeq)
        let userEmotion = 'neutral'
        let digitalHumanConfig = {}
        let leadSpeechText = ''
        let leadSpeechPromise = null
        let speechStartPromise = null
        let streamFailed = false

        const onMessage = (data) => {
          console.log('[chat] sse message received', {
            type: data && data.type,
            reply_id: data && data.reply_id,
            text_length: data && data.text ? String(data.text).length : 0,
            has_service_actions: !!(data && data.service_actions && data.service_actions.length),
          })
          if (replySeq !== this.activeReplySeq) return

          if (data.type === 'content') {
            this.messages[assistantMsgIndex].text = data.text
            replyId = data.reply_id || replyId
            this.status = 'think'
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
              action: data.digital_human_action === 'speak' ? undefined : data.digital_human_action,
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
                speaking: false
              })
            }
          }
        }

        const onError = (error) => {
          console.error('[chat] stream error callback', { replySeq, activeReplySeq: this.activeReplySeq, error })
          if (replySeq !== this.activeReplySeq) return
          if (streamFailed) return
          streamFailed = true
          console.error('Streaming error:', error)
          this.messages[assistantMsgIndex].text = '当前网络不稳定，您可以稍后再问我。'
          this.status = 'idle'
          this.scrollToBottom()
        }

        const onClose = async () => {
          console.log('[chat] stream close callback', { replySeq, activeReplySeq: this.activeReplySeq, speechTextLength: speechText.length, leadSpeechTextLength: leadSpeechText.length, status: this.status })
          if (replySeq !== this.activeReplySeq) return
          if (speechStartPromise) {
            await speechStartPromise
            if (replySeq !== this.activeReplySeq) return
            this.chatQuestionCount += 1
            this.maybePromptChatFeedback(sessionId)
            return
          }
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

        console.log('[chat] askQuestion before streamChat', {
          text,
          locationPayload,
          userId,
          sessionId,
        })
        console.log('[chat] askQuestion streamChat request sending', { text, locationPayload, userId, sessionId, status: this.status })
        this.currentSseClient = await streamChat({ text, user_id: userId, session_id: sessionId, ...locationPayload }, onMessage, onError, onClose)
        console.log('[chat] askQuestion streamChat attached', {
          text,
          locationPayload,
          status: this.status,
        })
      } catch (e) {
        console.error('[chat] askQuestion failed', { text, error: e && e.message ? e.message : e, stack: e && e.stack ? e.stack : '' })
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
      const audio = this.audioElement
      console.log('[chat] stopCurrentSpeech', {
        has_audio: !!audio,
        audio_type: audio && audio.constructor ? audio.constructor.name : typeof audio,
        has_pause: !!(audio && typeof audio.pause === 'function'),
        has_stop: !!(audio && typeof audio.stop === 'function'),
        has_destroy: !!(audio && typeof audio.destroy === 'function')
      })
      this.audioElement = null
      this.speechPlaybackActive = false
      if (this.status === 'speak') this.status = 'idle'
      if (audio) {
        if (typeof audio.onplay !== 'undefined') audio.onplay = null
        if (typeof audio.onended !== 'undefined') audio.onended = null
        if (typeof audio.onerror !== 'undefined') audio.onerror = null
        if (typeof audio.destroy === 'function') {
          try {
            audio.destroy()
          } catch (error) {
            console.warn('[chat] audio destroy failed', error)
          }
        } else if (typeof audio.stop === 'function') {
          try {
            audio.stop()
          } catch (error) {
            console.warn('[chat] audio stop failed', error)
          }
        } else if (typeof audio.pause === 'function') {
          try {
            audio.pause()
          } catch (error) {
            console.warn('[chat] audio pause failed', error)
          }
        }
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
    getAudioDataParts(audioData) {
      const source = String(audioData || '').trim()
      const match = source.match(/^data:(audio\/[^;]+);base64,(.+)$/)
      if (!match) {
        return { mime: 'audio/mpeg', base64: source.replace(/\s/g, ''), isDataUri: false }
      }
      return { mime: match[1], base64: String(match[2] || '').replace(/\s/g, ''), isDataUri: true }
    },
    getAudioExtension(mime = '') {
      if (mime.includes('wav')) return 'wav'
      if (mime.includes('mpeg') || mime.includes('mp3')) return 'mp3'
      if (mime.includes('aac')) return 'aac'
      return 'mp3'
    },
    resolveAudioSource(src) {
      const value = String(src || '').trim()
      if (!value) return ''
      if (/^(https?:|file:|data:|blob:)/i.test(value)) return value
      if (value.startsWith('/api/')) {
        return BASE_URL.replace(/\/api\/?$/, '') + value
      }
      if (value.startsWith('/')) {
        return BASE_URL.replace(/\/api\/?$/, '') + value
      }
      return value
    },
    writeAppAudioFileWithAndroid(base64, fileName) {
      try {
        if (typeof plus === 'undefined' || !plus.android || !plus.io) return ''
        const localUrl = `_doc/${fileName}`
        const fullPath = plus.io.convertLocalFileSystemURL(localUrl)
        const Base64 = plus.android.importClass('android.util.Base64')
        const FileOutputStream = plus.android.importClass('java.io.FileOutputStream')
        const cleanBase64 = String(base64 || '').replace(/\s/g, '')
        const bytes = Base64.decode(cleanBase64, Base64.DEFAULT)
        if (!bytes) {
          console.error('[chat] android audio decode returned empty bytes', {
            file_name: fileName,
            base64_length: cleanBase64.length
          })
          return ''
        }
        const stream = new FileOutputStream(fullPath)
        stream.write(bytes)
        stream.flush()
        stream.close()
        console.log('[chat] android audio file ready', { local_url: localUrl, full_path: fullPath })
        return fullPath || localUrl
      } catch (error) {
        console.error('[chat] android audio write failed', error)
        return ''
      }
    },
    writeAppAudioFileWithPlusFs(base64, fileName, mime = 'audio/wav') {
      return new Promise((resolve, reject) => {
        if (typeof plus === 'undefined' || !plus.io || typeof plus.io.resolveLocalFileSystemURL !== 'function') {
          reject(new Error('plus file system unavailable'))
          return
        }
        const cleanBase64 = String(base64 || '').replace(/\s/g, '')
        const localUrl = `_doc/${fileName}`
        const makeBlob = () => {
          if (typeof Blob !== 'function') {
            throw new Error('blob unavailable')
          }
          if (typeof uni !== 'undefined' && typeof uni.base64ToArrayBuffer === 'function') {
            return new Blob([uni.base64ToArrayBuffer(cleanBase64)], { type: mime || 'audio/wav' })
          }
          if (typeof atob === 'function') {
            const binary = atob(cleanBase64)
            const buffer = new Uint8Array(binary.length)
            for (let i = 0; i < binary.length; i++) {
              buffer[i] = binary.charCodeAt(i)
            }
            return new Blob([buffer], { type: mime || 'audio/wav' })
          }
          throw new Error('no base64 decoder available')
        }
        plus.io.resolveLocalFileSystemURL('_doc/', (dirEntry) => {
          dirEntry.getFile(fileName, { create: true }, (fileEntry) => {
            fileEntry.createWriter((writer) => {
              const startAt = Date.now()
              writer.onerror = (error) => {
                console.error('[chat] plus fs audio write failed', error)
                reject(error)
              }
              writer.onwriteend = () => {
                const fullPath = typeof fileEntry.toLocalURL === 'function' ? fileEntry.toLocalURL() : localUrl
                console.log('[chat] plus fs audio file ready', { local_url: localUrl, full_path: fullPath, cost_ms: Date.now() - startAt })
                resolve(fullPath || localUrl)
              }
              writer.write(makeBlob())
            }, reject)
          }, reject)
        }, reject)
      })
    },
    writeAppAudioFile(audioData) {
      return new Promise((resolve, reject) => {
        let settled = false
        let writeTimeout = null
        const finish = (callback, value) => {
          if (settled) return
          settled = true
          if (writeTimeout) {
            clearTimeout(writeTimeout)
            writeTimeout = null
          }
          callback(value)
        }
        const parts = this.getAudioDataParts(audioData)
        if (!parts.base64) {
          finish(reject, new Error('empty audio data'))
          return
        }
        const ext = this.getAudioExtension(parts.mime)
        const fileName = `tts_${Date.now()}_${Math.random().toString(36).slice(2, 8)}.${ext}`
        const fsAvailable = typeof uni.getFileSystemManager === 'function' && uni.env && uni.env.USER_DATA_PATH
        const plusFsAvailable = typeof plus !== 'undefined' && plus.io && typeof plus.io.resolveLocalFileSystemURL === 'function'
        const androidAvailable = typeof plus !== 'undefined' && plus.android && plus.io
        console.log('[chat] write app audio file', {
          file_name: fileName,
          mime: parts.mime,
          base64_length: parts.base64.length,
          has_uni_fs: !!fsAvailable,
          has_plus_fs: !!plusFsAvailable,
          has_android: !!androidAvailable
        })
        writeTimeout = setTimeout(() => {
          finish(reject, new Error('app audio write timeout'))
        }, 5000)

        if (fsAvailable) {
          const writeStartAt = Date.now()
          const filePath = `${uni.env.USER_DATA_PATH}/${fileName}`
          uni.getFileSystemManager().writeFile({
            filePath,
            data: parts.base64,
            encoding: 'base64',
            success: () => {
              console.log('[chat] write app audio file done', { strategy: 'uni-fs', cost_ms: Date.now() - writeStartAt })
              finish(resolve, filePath)
            },
            fail: (error) => {
              console.warn('[chat] uni-fs write failed, fallback to plus fs', error)
              if (plusFsAvailable) {
                const plusWriteStartAt = Date.now()
                this.writeAppAudioFileWithPlusFs(parts.base64, fileName, parts.mime)
                  .then((audioPath) => {
                    console.log('[chat] write app audio file done', { strategy: 'plus-fs', cost_ms: Date.now() - plusWriteStartAt })
                    finish(resolve, audioPath)
                  })
                  .catch((plusError) => {
                    console.warn('[chat] plus fs write failed, fallback to android bridge', plusError)
                    if (androidAvailable) {
                      const audioPath = this.writeAppAudioFileWithAndroid(parts.base64, fileName)
                      if (audioPath) {
                        finish(resolve, audioPath)
                      } else {
                        finish(reject, new Error('android audio write failed'))
                      }
                    } else {
                      finish(reject, plusError)
                    }
                  })
              } else if (androidAvailable) {
                const audioPath = this.writeAppAudioFileWithAndroid(parts.base64, fileName)
                if (audioPath) {
                  finish(resolve, audioPath)
                } else {
                  finish(reject, new Error('android audio write failed'))
                }
              } else {
                finish(reject, error)
              }
            }
          })
          return
        }

        if (plusFsAvailable) {
          const writeStartAt = Date.now()
          this.writeAppAudioFileWithPlusFs(parts.base64, fileName, parts.mime)
            .then((audioPath) => {
              console.log('[chat] write app audio file done', { strategy: 'plus-fs', cost_ms: Date.now() - writeStartAt })
              finish(resolve, audioPath)
            })
            .catch((error) => {
              console.warn('[chat] plus fs write failed, fallback to android bridge', error)
              if (androidAvailable) {
                const audioPath = this.writeAppAudioFileWithAndroid(parts.base64, fileName)
                if (audioPath) {
                  finish(resolve, audioPath)
                } else {
                  finish(reject, new Error('android audio write failed'))
                }
              } else {
                finish(reject, error)
              }
            })
          return
        }

        if (androidAvailable) {
          const writeStartAt = Date.now()
          const audioPath = this.writeAppAudioFileWithAndroid(parts.base64, fileName)
          if (audioPath) {
            console.log('[chat] write app audio file done', { strategy: 'plus-android', cost_ms: Date.now() - writeStartAt })
            finish(resolve, audioPath)
          } else {
            finish(reject, new Error('android audio write failed'))
          }
          return
        }

        finish(reject, new Error('no app file writer available'))
      })
    },
    playSpeechAudio(audioInput, replySeq) {
      return new Promise((resolve) => {
        if (replySeq !== this.activeReplySeq) {
          resolve(false)
          return
        }

        const payload = audioInput && typeof audioInput === 'object' && !Array.isArray(audioInput)
          ? audioInput
          : { audio_data: audioInput }
        const audioUrl = this.resolveAudioSource(payload.audio_url || payload.audioUrl || '')
        const audioData = String(payload.audio_data || '').trim()
        if (!audioUrl && !audioData) {
          resolve(false)
          return
        }

        console.log('[chat] playSpeechAudio', {
          platform: process.env.UNI_PLATFORM,
          has_inner_audio: typeof uni.createInnerAudioContext === 'function',
          has_audio_url: !!audioUrl,
          has_audio_data: !!audioData,
          audio_url: audioUrl,
          data_uri: String(audioData).startsWith('data:audio/'),
          audio_length: audioData.length
        })

        const markAudioStarted = (sourceType, audioSrc) => {
          if (replySeq !== this.activeReplySeq) return false
          this.speechPlaybackActive = true
          this.status = 'speak'
          console.log('[chat] app audio play', { source_type: sourceType, src: audioSrc })
          if (this.$refs.digitalHuman) {
            this.$refs.digitalHuman.startSpeaking({ motion: 'Tap' })
          }
          return true
        }

        let playbackSettled = false
        const cleanupAudio = (audio, ok, sourceType, audioSrc, error) => {
          if (playbackSettled) return
          playbackSettled = true
          if (error) {
            console.error('[chat] app audio error', { source_type: sourceType, src: audioSrc, error })
          } else {
            console.log('[chat] app audio ended', { source_type: sourceType, src: audioSrc })
          }
          this.speechPlaybackActive = false
          if (this.audioElement === audio) this.audioElement = null
          try {
            if (audio && typeof audio.destroy === 'function') audio.destroy()
          } catch (e) {}
          resolve(ok)
        }

        const playWithPlusAudio = (audioSrc, sourceType = 'plus-audio-file') => {
          if (typeof plus === 'undefined' || !plus.audio || typeof plus.audio.createPlayer !== 'function') {
            return false
          }
          try {
            const player = plus.audio.createPlayer(audioSrc)
            if (!player) return false
            const audioHandle = {
              _player: player,
              stop() {
                if (player && typeof player.stop === 'function') player.stop()
              },
              destroy() {
                try { if (player && typeof player.stop === 'function') player.stop() } catch (e) {}
                try { if (player && typeof player.close === 'function') player.close() } catch (e) {}
              }
            }
            this.audioElement = audioHandle
            let started = false
            let playTimer = null
            const onStarted = () => {
              if (started) return
              started = true
              if (playTimer) {
                clearTimeout(playTimer)
                playTimer = null
              }
              markAudioStarted(sourceType, audioSrc)
            }
            const onEnded = () => cleanupAudio(audioHandle, true, sourceType, audioSrc, null)
            const onError = (error) => cleanupAudio(audioHandle, false, sourceType, audioSrc, error)
            playTimer = setTimeout(() => {
              cleanupAudio(audioHandle, false, sourceType, audioSrc, new Error('app audio play timeout'))
            }, 8000)
            if (typeof player.addEventListener === 'function') {
              player.addEventListener('play', onStarted)
              player.addEventListener('ended', onEnded)
              player.addEventListener('error', onError)
            }
            player.play(() => {
              onStarted()
            }, (error) => {
              onError(error)
            })
            return true
          } catch (error) {
            console.error('[chat] plus audio play failed', error)
            return false
          }
        }

        const playWithInnerAudio = (audioSrc, sourceType = 'inner-audio-file') => {
          if (typeof uni.createInnerAudioContext !== 'function') return false
          const innerAudio = uni.createInnerAudioContext()
          this.audioElement = innerAudio
          innerAudio.autoplay = false
          innerAudio.volume = 1
          innerAudio.src = audioSrc
          let playTimer = setTimeout(() => {
            cleanupAudio(innerAudio, false, sourceType, audioSrc, new Error('app audio play timeout'))
          }, 8000)
          innerAudio.onPlay(() => {
            if (playTimer) {
              clearTimeout(playTimer)
              playTimer = null
            }
            markAudioStarted(sourceType, audioSrc)
          })
          innerAudio.onEnded(() => cleanupAudio(innerAudio, true, sourceType, audioSrc, null))
          innerAudio.onError((error) => cleanupAudio(innerAudio, false, sourceType, audioSrc, error))
          innerAudio.play()
          return true
        }

        if (process.env.UNI_PLATFORM !== 'h5') {
          if (audioUrl) {
            console.log('[chat] app audio direct source', { src: audioUrl })
            if (playWithInnerAudio(audioUrl, 'remote-audio-url') || playWithPlusAudio(audioUrl, 'remote-audio-url')) {
              return
            }
          }
          this.writeAppAudioFile(audioData)
            .then((audioSrc) => {
              console.log('[chat] app audio file ready', { src: audioSrc })
              if (!playWithInnerAudio(audioSrc, 'inner-audio-file') && !playWithPlusAudio(audioSrc, 'plus-audio-file')) {
                resolve(false)
              }
            })
            .catch((error) => {
              console.error('[chat] write app audio failed', error)
              resolve(false)
            })
          return
        }

        this.audioElement = new Audio(audioUrl || audioData)
        this.audioElement.onplay = () => {
          if (replySeq !== this.activeReplySeq) return
          this.speechPlaybackActive = true
          this.status = 'speak'
          if (this.$refs.digitalHuman) {
            this.$refs.digitalHuman.startRealLipSync(this.audioElement)
          }
        }
        this.audioElement.onended = () => {
          this.speechPlaybackActive = false
          if (this.audioElement) {
            this.audioElement.onplay = null
            this.audioElement.onended = null
            this.audioElement.onerror = null
            this.audioElement = null
          }
          resolve(true)
        }
        this.audioElement.onerror = () => {
          this.speechPlaybackActive = false
          if (this.audioElement) {
            this.audioElement.onplay = null
            this.audioElement.onended = null
            this.audioElement.onerror = null
            this.audioElement = null
          }
          resolve(false)
        }

        this.audioElement.play().catch((error) => {
          console.error('[chat] h5 audio play failed', error)
          this.speechPlaybackActive = false
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
            this.speechPlaybackActive = true
            this.status = 'speak'
            this.$refs.digitalHuman.startSpeaking({ motion: 'Tap' })
          }
        }
        utterance.onend = () => {
          this.speechPlaybackActive = false
          resolve(true)
        }
        utterance.onerror = () => {
          this.speechPlaybackActive = false
          resolve(false)
        }
        window.speechSynthesis.speak(utterance)
      })
    },
    async trySpeak(text, replySeq = this.activeReplySeq, replyId = String(replySeq)) {
      try {
        console.log('[chat] trySpeak start', {
          reply_id: replyId,
          text_length: String(text || '').length,
          platform: process.env.UNI_PLATFORM
        })
        const speechChunks = this.splitSpeechText(text)
        if (speechChunks.length > 1) {
          this.stopCurrentSpeech(false)
          const speechTasks = speechChunks.map((chunk, index) => post('/ai/tts', {
            text: chunk,
            voice: this.digitalHumanVoice,
            reply_id: `${replyId}_${index + 1}`
          }))
          for (let i = 0; i < speechTasks.length; i++) {
            if (replySeq !== this.activeReplySeq) return
            const audio = await speechTasks[i]
            if (replySeq !== this.activeReplySeq) return
            console.log('[chat] tts response chunk', {
              reply_id: `${replyId}_${i + 1}`,
              has_audio: !!(audio && audio.audio_data),
              audio_length: audio && audio.audio_data ? String(audio.audio_data).length : 0,
              note: audio && audio.note
            })
            if (!audio || (!audio.audio_url && !audio.audio_data)) {
              continue
            }
            const played = await this.playSpeechAudio(audio, replySeq)
            if (!played) {
              console.warn('[chat] tts chunk playback failed', { reply_id: `${replyId}_${i + 1}` })
              this.finishSpeaking(replySeq)
              return
            }
          }
          this.finishSpeaking(replySeq)
          return
        }

        const audio = await post('/ai/tts', { text, voice: this.digitalHumanVoice, reply_id: replyId })
        if (replySeq !== this.activeReplySeq) return
        console.log('[chat] tts response', {
          reply_id: replyId,
          has_audio: !!(audio && audio.audio_data),
          audio_length: audio && audio.audio_data ? String(audio.audio_data).length : 0,
          note: audio && audio.note
        })

        if (audio && (audio.audio_url || audio.audio_data)) {
          this.stopCurrentSpeech(false)
          const played = await this.playSpeechAudio(audio, replySeq)
          if (played) {
            this.finishSpeaking(replySeq)
            return
          }
          console.warn('[chat] tts audio playback failed', { reply_id: replyId })
          this.finishSpeaking(replySeq)
          return
        }

        const played = await this.playBrowserSpeech(text, replySeq)
        if (played) {
          this.finishSpeaking(replySeq)
          return
        }
        console.warn('[chat] browser speech playback failed', { reply_id: replyId })
      } catch (e) {
        console.error('[chat] trySpeak failed', { reply_id: replyId, error: e && (e.message || e.errMsg || e) })
      }

      if (replySeq !== this.activeReplySeq) return
      this.finishSpeaking(replySeq)
    },
    finishSpeaking(replySeq = this.activeReplySeq) {
      if (replySeq !== this.activeReplySeq) return
      this.status = 'idle'
      this.speechPlaybackActive = false
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

.history-icon {
  width: 32rpx;
  height: 32rpx;
  display: block;
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
