<template>
  <view class="digital-human" :class="{ compact }" :style="containerStyle">
    <!-- #ifdef APP-PLUS -->
    <view
      class="live2d-stage"
      ref="stageRef"
      :id="stageId"
      :style="stageStyle"
      :live2d-state="renderState"
      :change:live2d-state="live2dRender.updateState"
    >
      <view v-if="!isReady" class="live2d-mask">
        <view class="live2d-placeholder">
          <text class="placeholder-title">{{ loadText }}</text>
          <text class="placeholder-subtitle">{{ loadSubText }}</text>
        </view>
      </view>
    </view>
    <!-- #endif -->
    <!-- #ifndef APP-PLUS -->
    <view class="live2d-stage" ref="stageRef" :style="stageStyle">
      <view v-if="!isReady" class="live2d-mask">
        <view class="live2d-placeholder">
          <text class="placeholder-title">{{ loadText }}</text>
          <text class="placeholder-subtitle">{{ loadSubText }}</text>
        </view>
      </view>
    </view>
    <!-- #endif -->
  </view>
</template>

<script>
const PIXI_PATH = '/static/vendor/pixi.min.js'
const CUBISM_CORE_PATH = '/static/vendor/live2dcubismcore.min.js'
const LIVE2D_PLUGIN_PATH = '/static/vendor/pixi-live2d-cubism4.min.js'
const DEFAULT_MODEL_PATH = '/static/live2d/epsilon_ja/epsilon_free/runtime/Epsilon_free.model3.json'
const MOUTH_PARAM_ID = 'PARAM_MOUTH_OPEN_Y'

const EMOTION_MAP = {
  neutral: 'Normal',
  positive: 'Smile',
  negative: 'Sad',
  angry: 'Angry',
  shy: 'Blushing',
  surprised: 'Surprised'
}

const STATUS_MAP = {
  idle: 'Idle',
  listen: 'FlickUp',
  think: 'Flick',
  speak: 'Tap'
}

const STATUS_MOTION_OPTIONS = {
  idle: { motion: 'Idle' },
  listen: { motion: 'FlickUp' },
  think: { motion: 'Flick' },
  speak: { motion: 'Tap', motionIndex: 3, force: true }
}

export default {
  name: 'DigitalHumanSimple',
  props: {
    modelPath: {
      type: String,
      default: DEFAULT_MODEL_PATH
    },
    status: {
      type: String,
      default: 'idle'
    },
    emotion: {
      type: String,
      default: 'neutral'
    },
    speaking: {
      type: Boolean,
      default: false
    },
    compact: {
      type: Boolean,
      default: false
    }
  },
  emits: ['ready', 'error'],
  data() {
    return {
      isReady: false,
      loadError: '',
      app: null,
      model: null,
      stageEl: null,
      lipSyncTimer: null,
      lipSyncTimerType: '',
      audioContext: null,
      analyser: null,
      dataArray: null,
      currentExpression: '',
      currentMotion: '',
      mouthOpenValue: 0,
      isSpeakingNow: false,
      coreModelCache: null,
      mouthUpdateHandler: null,
      tickerMouthHandler: null,
      live2dTickerHandler: null,
      mediaElementSource: null,
      sourceAudioElement: null,
      contextLost: false,
      recovering: false,
      initializing: false,
      recoveryTimer: null,
      contextLostHandler: null,
      contextRestoredHandler: null,
      renderActionSeq: 0,
      renderAction: null,
      renderErrorCount: 0,
      stageId: `live2d-stage-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    }
  },
  computed: {
    loadText() {
      return this.loadError ? 'Live2D 加载失败' : 'Live2D 加载中'
    },
    loadSubText() {
      return this.loadError || '正在准备数字人模型'
    },
    compactMinHeight() {
      return this.compact ? '220rpx' : '420rpx'
    },
    containerStyle() {
      return {
        minHeight: this.compactMinHeight
      }
    },
    stageStyle() {
      return {
        minHeight: this.compactMinHeight
      }
    },
    renderState() {
      return {
        modelPath: this.modelPath,
        status: this.status,
        emotion: this.emotion,
        speaking: this.speaking,
        compact: this.compact,
        stageId: this.stageId,
        action: this.renderAction
      }
    }
  },
  watch: {
    modelPath(newPath, oldPath) {
      if (!newPath || newPath === oldPath) return
      if (this.isAppRenderMode()) {
        this.sendRenderAction('reload')
        return
      }
      if (this.isReady) {
        this.recoverLive2D()
      }
    },
    status(newStatus) {
      if (this.isAppRenderMode()) return
      if (this.isReady) {
        const motionOptions = this.resolveStatusMotion(newStatus)
        this.playMotion(motionOptions.motion, motionOptions.motionIndex, {
          force: motionOptions.force
        })
      }
    },
    emotion(newEmotion) {
      if (this.isAppRenderMode()) return
      if (this.isReady) {
        const expression = EMOTION_MAP[newEmotion] || 'Normal'
        this.setExpression(expression)
      }
    },
    speaking(newVal) {
      if (this.isAppRenderMode()) return
      if (this.isReady) {
        if (newVal) {
          this.startLipSync()
        } else {
          this.stopLipSync()
        }
      }
    }
  },
  mounted() {
    if (this.isAppRenderMode()) return
    this.initLive2D()
  },
  beforeUnmount() {
    if (this.recoveryTimer) {
      clearTimeout(this.recoveryTimer)
      this.recoveryTimer = null
    }
    this.destroyLive2D()
  },
  methods: {
    isAppRenderMode() {
      return process.env.UNI_PLATFORM === 'app-plus'
    },
    sendRenderAction(type, payload = {}) {
      this.renderAction = {
        seq: ++this.renderActionSeq,
        type,
        payload
      }
    },
    onRenderReady() {
      this.renderErrorCount = 0
      this.loadError = ''
      this.isReady = true
      console.log('[digital-human] app renderjs ready')
      this.$emit('ready')
    },
    onRenderError(error) {
      const message = error && (error.message || error.errMsg || error.error) ? (error.message || error.errMsg || error.error) : '加载失败'
      console.error('[digital-human] app renderjs error', error)
      if (this.isAppRenderMode()) {
        if (this.isReady) return
        this.renderErrorCount += 1
        const transient = /document unavailable|stage unavailable|querySelector|appendChild|Cannot read property/i.test(message)
        if (transient && this.renderErrorCount <= 30) {
          this.loadError = ''
          const delay = Math.min(1200, 200 + this.renderErrorCount * 100)
          setTimeout(() => this.sendRenderAction('reload'), delay)
          return
        }
        if (this.renderErrorCount <= 5) {
          this.loadError = ''
          setTimeout(() => this.sendRenderAction('reload'), 500)
          return
        }
      }
      this.isReady = false
      this.loadError = message
      this.$emit('error', new Error(message))
    },
    async initLive2D() {
      if (this.initializing) return
      this.initializing = true
      try {
        this.loadError = ''
        await this.loadScript(CUBISM_CORE_PATH)
        await this.loadScript(PIXI_PATH)
        await this.loadScript(LIVE2D_PLUGIN_PATH)

        const PIXI = window.PIXI
        if (!PIXI || !PIXI.live2d) {
          throw new Error('Live2D 库加载失败')
        }

        PIXI.live2d.Live2DModel.registerTicker(PIXI.Ticker)

        this.stageEl = this.$refs.stageRef.$el || this.$refs.stageRef
        if (!this.stageEl) {
          throw new Error('未找到挂载节点')
        }

        const width = this.stageEl.offsetWidth || 300
        const height = this.stageEl.offsetHeight || 500

        this.app = new PIXI.Application({
          width,
          height,
          backgroundAlpha: 0,
          antialias: true,
          autoDensity: true,
          resolution: Math.min(window.devicePixelRatio || 1, 2)
        })
        this.app.view.style.width = '100%'
        this.app.view.style.height = '100%'
        this.stageEl.appendChild(this.app.view)
        this.bindCanvasContextEvents()

        const model = await Promise.race([
          PIXI.live2d.Live2DModel.from(this.modelPath, {
            autoInteract: false,
            autoUpdate: false,
            motionPreload: PIXI.live2d.MotionPreloadStrategy.NONE,
            idleMotionGroup: 'Idle'
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('模型加载超时')), 20000))
        ])

        this.model = model
        this.app.stage.addChild(model)

        const scale = Math.min(width / model.width, height / model.height) * 0.95
        model.scale.set(scale)
        model.anchor.set(0.5, 1)
        model.x = width / 2
        model.y = height

        this.isReady = true
        this.contextLost = false
        this.coreModelCache = this.getCoreModel()
        
        this.setExpression(EMOTION_MAP[this.emotion])
        const motionOptions = this.resolveStatusMotion(this.status)
        this.playMotion(motionOptions.motion, motionOptions.motionIndex, {
          force: motionOptions.force
        })
        
        this.bindMouthUpdate()
        this.bindLive2DTicker()
        
        this.$emit('ready')
      } catch (error) {
        this.isReady = false
        this.loadError = error.message || '加载失败'
        if (this.app) {
          this.destroyLive2D()
        }
        this.$emit('error', error)
      } finally {
        this.initializing = false
      }
    },
    bindCanvasContextEvents() {
      this.unbindCanvasContextEvents()
      const canvas = this.app && this.app.view
      if (!canvas || typeof canvas.addEventListener !== 'function') return

      this.contextLostHandler = (event) => {
        if (event && typeof event.preventDefault === 'function') event.preventDefault()
        this.contextLost = true
        this.isReady = false
        if (this.app && typeof this.app.stop === 'function') this.app.stop()
        this.scheduleLive2DRecovery()
      }
      this.contextRestoredHandler = () => {
        this.scheduleLive2DRecovery(0)
      }
      canvas.addEventListener('webglcontextlost', this.contextLostHandler, false)
      canvas.addEventListener('webglcontextrestored', this.contextRestoredHandler, false)
    },
    unbindCanvasContextEvents() {
      const canvas = this.app && this.app.view
      if (canvas && typeof canvas.removeEventListener === 'function') {
        if (this.contextLostHandler) {
          canvas.removeEventListener('webglcontextlost', this.contextLostHandler, false)
        }
        if (this.contextRestoredHandler) {
          canvas.removeEventListener('webglcontextrestored', this.contextRestoredHandler, false)
        }
      }
      this.contextLostHandler = null
      this.contextRestoredHandler = null
    },
    scheduleLive2DRecovery(delay = 800) {
      if (this.recoveryTimer) clearTimeout(this.recoveryTimer)
      this.recoveryTimer = setTimeout(() => {
        this.recoveryTimer = null
        this.recoverLive2D()
      }, delay)
    },
    async recoverLive2D() {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('reload')
        return
      }
      if (this.recovering) return
      if (this.initializing) return
      this.recovering = true
      try {
        this.destroyLive2D({ releaseAudioGraph: false })
        await this.$nextTick()
        await this.initLive2D()
      } finally {
        this.recovering = false
      }
    },
    async ensureLive2D() {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('ensure')
        return
      }
      const canvas = this.app && this.app.view
      const gl = this.app && this.app.renderer && this.app.renderer.gl
      const isLost = this.contextLost || (gl && typeof gl.isContextLost === 'function' && gl.isContextLost())
      if (!this.isReady || !canvas || canvas.isConnected === false || isLost) {
        await this.recoverLive2D()
        return
      }
      if (this.app && typeof this.app.start === 'function') this.app.start()
    },
    pauseRendering() {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('pause')
        return
      }
      if (this.app && typeof this.app.stop === 'function') this.app.stop()
    },
    getCoreModel() {
      return this.model &&
        this.model.internalModel &&
        this.model.internalModel.coreModel
        ? this.model.internalModel.coreModel
        : null
    },
    bindMouthUpdate() {
      this.unbindMouthUpdate()

      this.mouthUpdateHandler = () => {
        this.applyMouthOpen()
      }

      const internalModel = this.model && this.model.internalModel
      if (internalModel && typeof internalModel.on === 'function') {
        internalModel.on('beforeModelUpdate', this.mouthUpdateHandler)
      }

      if (this.app && this.app.ticker) {
        this.tickerMouthHandler = () => {
          this.applyMouthOpen()
        }
        this.app.ticker.add(this.tickerMouthHandler)
      }
    },
    bindLive2DTicker() {
      this.unbindLive2DTicker()

      if (!this.app || !this.app.ticker || !this.model) {
        return
      }

      this.live2dTickerHandler = () => {
        if (!this.model || this.model.destroyed || this.model._destroyed) return
        const deltaMS = this.app.ticker.deltaMS || 16.6667
        this.model.update(deltaMS)
      }
      this.app.ticker.add(this.live2dTickerHandler)
    },
    unbindLive2DTicker() {
      if (this.app && this.app.ticker && this.live2dTickerHandler) {
        this.app.ticker.remove(this.live2dTickerHandler)
      }
      this.live2dTickerHandler = null
    },
    unbindMouthUpdate() {
      const internalModel = this.model && this.model.internalModel
      if (internalModel && this.mouthUpdateHandler) {
        if (typeof internalModel.off === 'function') {
          internalModel.off('beforeModelUpdate', this.mouthUpdateHandler)
        } else if (typeof internalModel.removeListener === 'function') {
          internalModel.removeListener('beforeModelUpdate', this.mouthUpdateHandler)
        }
      }

      if (this.app && this.app.ticker && this.tickerMouthHandler) {
        this.app.ticker.remove(this.tickerMouthHandler)
      }

      this.mouthUpdateHandler = null
      this.tickerMouthHandler = null
    },
    loadScript(src) {
      return new Promise((resolve, reject) => {
        const doc = typeof document !== 'undefined' ? document : null
        if (!doc || typeof doc.querySelector !== 'function' || typeof doc.createElement !== 'function' || !doc.head) {
          reject(new Error('renderjs document unavailable'))
          return
        }
        const existing = doc.querySelector(`script[src="${src}"]`)
        if (existing) {
          setTimeout(resolve, 100)
          return
        }
        const script = doc.createElement('script')
        script.src = src
        script.onload = resolve
        script.onerror = () => reject(new Error(`脚本加载失败: ${src}`))
        doc.head.appendChild(script)
      })
    },
    async setExpression(expression) {
      if (!this.model || !expression) return
      if (expression === this.currentExpression) return
      try {
        await this.model.expression(expression)
        this.currentExpression = expression
      } catch (e) {}
    },
    resolveStatusMotion(status) {
      return STATUS_MOTION_OPTIONS[status] || STATUS_MOTION_OPTIONS.idle
    },
    getMotionPriority(force = false) {
      const priority = window.PIXI && window.PIXI.live2d && window.PIXI.live2d.MotionPriority
      if (!priority) return undefined
      return force ? priority.FORCE : priority.NORMAL
    },
    async playMotion(motion, motionIndex, options = {}) {
      if (!this.model || !motion) return
      const motionKey = `${motion}:${motionIndex === undefined ? 'random' : motionIndex}`
      if (!options.force && motionKey === this.currentMotion) return
      try {
        const priority = this.getMotionPriority(!!options.force)
        if (priority !== undefined) {
          await this.model.motion(motion, motionIndex, priority)
        } else {
          await this.model.motion(motion, motionIndex)
        }
        this.currentMotion = motionKey
      } catch (e) {}
    },
    startLipSync() {
      this.stopLipSync({ keepAudioGraph: true })
      this.isSpeakingNow = true
      this.lipSyncTimerType = 'interval'
      this.lipSyncTimer = setInterval(() => {
        if (!this.isSpeakingNow) return
        let open = 0.25 + Math.sin(Date.now() / 150) * 0.4 + Math.random() * 0.15
        open = Math.max(0, Math.min(1, open))
        this.mouthOpenValue = open
      }, 50)
    },
    async startRealLipSync(audioElement) {
      this.stopLipSync({ keepAudioGraph: true })
      this.isSpeakingNow = true
      try {
        if (!window.AudioContext && !window.webkitAudioContext) {
          this.startLipSync()
          return
        }

        const canReuseAudioGraph = this.audioContext &&
          this.audioContext.state !== 'closed' &&
          this.analyser &&
          this.mediaElementSource &&
          this.sourceAudioElement === audioElement

        if (!canReuseAudioGraph) {
          this.releaseAudioGraph()
          this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
          this.analyser = this.audioContext.createAnalyser()
          this.analyser.fftSize = 256
          const bufferLength = this.analyser.frequencyBinCount
          this.dataArray = new Uint8Array(bufferLength)

          this.mediaElementSource = this.audioContext.createMediaElementSource(audioElement)
          this.mediaElementSource.connect(this.analyser)
          this.analyser.connect(this.audioContext.destination)
          this.sourceAudioElement = audioElement
        }

        if (this.audioContext && this.audioContext.state === 'suspended') {
          await this.audioContext.resume()
        }
        
        const updateMouth = () => {
          if (!this.isSpeakingNow || !this.analyser) return
          
          this.analyser.getByteFrequencyData(this.dataArray)
          
          let sum = 0
          for (let i = 0; i < this.dataArray.length; i++) {
            sum += this.dataArray[i]
          }
          const average = sum / this.dataArray.length
          const normalized = Math.min(1, average / 128)
          
          this.mouthOpenValue = Math.max(0, Math.min(1, normalized * 0.9 + 0.05))
          
          this.lipSyncTimerType = 'animationFrame'
          this.lipSyncTimer = requestAnimationFrame(updateMouth)
        }
        
        updateMouth()
      } catch (e) {
        this.startLipSync()
      }
    },
    applyMouthOpen() {
      const coreModel = this.coreModelCache || this.getCoreModel()
      if (!coreModel) return

      const value = Math.max(0, Math.min(1, Number(this.mouthOpenValue) || 0))

      if (typeof coreModel.setParameterValueById === 'function') {
        coreModel.setParameterValueById(MOUTH_PARAM_ID, value, 1)
      } else if (typeof coreModel.setParamFloat === 'function') {
        coreModel.setParamFloat(MOUTH_PARAM_ID, value)
      } else if (typeof coreModel.addParameterValueById === 'function') {
        coreModel.addParameterValueById(MOUTH_PARAM_ID, value, 1)
      }
    },
    stopLipSync(options = {}) {
      this.isSpeakingNow = false
      if (this.lipSyncTimer) {
        if (this.lipSyncTimerType === 'animationFrame') {
          cancelAnimationFrame(this.lipSyncTimer)
        } else {
          clearInterval(this.lipSyncTimer)
        }
        this.lipSyncTimer = null
        this.lipSyncTimerType = ''
      }
      if (options.releaseAudioGraph) {
        this.releaseAudioGraph()
      }
      this.mouthOpenValue = 0
    },
    releaseAudioGraph() {
      if (this.audioContext) {
        this.audioContext.close()
        this.audioContext = null
      }
      this.analyser = null
      this.dataArray = null
      this.mediaElementSource = null
      this.sourceAudioElement = null
    },
    startSpeaking(options = {}) {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('startSpeaking', options)
        return
      }
      if (!this.isReady) return
      this.setExpression(options.expression || EMOTION_MAP[this.emotion] || 'Normal')
      const speakMotion = this.resolveStatusMotion('speak')
      this.playMotion(options.motion || speakMotion.motion, options.motionIndex ?? speakMotion.motionIndex, {
        force: true
      })
      this.startLipSync()
    },
    stopSpeaking() {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('stopSpeaking')
        return
      }
      this.stopLipSync()
      this.playMotion('Idle', undefined, { force: true })
      this.setExpression('Normal')
    },
    applyDigitalHuman(options = {}) {
      if (this.isAppRenderMode()) {
        this.sendRenderAction('applyDigitalHuman', options)
        return
      }
      if (!this.isReady) return
      if (options.emotion) {
        const expression = EMOTION_MAP[options.emotion] || options.emotion
        this.setExpression(expression)
      }
      if (options.motion) {
        this.playMotion(options.motion, options.motionIndex, { force: true })
      }
      if (options.expression) {
        this.setExpression(options.expression)
      }
      if (options.action && options.action !== 'speak') {
        this.stopLipSync()
      }
      if (options.speaking !== undefined) {
        if (options.speaking) {
          this.startLipSync()
        } else {
          this.stopLipSync()
        }
      }
    },
    destroyLive2D(options = {}) {
      if (this.isAppRenderMode()) {
        this.isReady = false
        this.sendRenderAction('destroy')
        return
      }
      this.stopLipSync({ releaseAudioGraph: options.releaseAudioGraph !== false })
      this.unbindMouthUpdate()
      this.unbindLive2DTicker()
      this.unbindCanvasContextEvents()
      if (this.app) {
        try {
          this.app.destroy(true, { children: true, texture: true, baseTexture: true })
        } catch (e) {}
        this.app = null
      }
      this.model = null
      this.coreModelCache = null
      this.currentExpression = ''
      this.currentMotion = ''
      this.contextLost = false
      this.isReady = false
    }
  }
}
</script>

<script module="live2dRender" lang="renderjs">
const PIXI_PATH = '/static/vendor/pixi.min.js'
const CUBISM_CORE_PATH = '/static/vendor/live2dcubismcore.min.js'
const LIVE2D_PLUGIN_PATH = '/static/vendor/pixi-live2d-cubism4.min.js'
const DEFAULT_MODEL_PATH = '/static/live2d/epsilon_ja/epsilon_free/runtime/Epsilon_free.model3.json'
const MOUTH_PARAM_ID = 'PARAM_MOUTH_OPEN_Y'
const EMOTION_MAP = { neutral: 'Normal', positive: 'Smile', negative: 'Sad', angry: 'Angry', shy: 'Blushing', surprised: 'Surprised' }
const STATUS_MOTION_OPTIONS = { idle: { motion: 'Idle' }, listen: { motion: 'FlickUp' }, think: { motion: 'Flick' }, speak: { motion: 'Tap', motionIndex: 3, force: true } }

export default {
  data() {
    return { app: null, model: null, initialized: false, initializing: false, lastState: null, lastActionSeq: 0, currentExpression: '', currentMotion: '', mouthOpenValue: 0, lipSyncTimer: null, isSpeakingNow: false, coreModelCache: null, mouthUpdateHandler: null, tickerMouthHandler: null, live2dTickerHandler: null, initRetryTimer: null, initRetryCount: 0, initRetryReason: '', initGeneration: 0 }
  },
  mounted() { this.initFromCurrentState() },
  beforeDestroy() { this.clearInitRetry(); this.destroyLive2D() },
  methods: {
    clearInitRetry() {
      if (this.initRetryTimer) {
        clearTimeout(this.initRetryTimer)
        this.initRetryTimer = null
      }
      this.initRetryReason = ''
    },
    scheduleInitRetry(reason, delay = 120) {
      if (this.initialized) return
      this.clearInitRetry()
      this.initRetryReason = reason || ''
      this.initRetryCount += 1
      const nextDelay = Math.min(3000, delay + Math.min(this.initRetryCount * 80, 1200))
      console.log('[digital-human][renderjs] init retry', { reason: this.initRetryReason, count: this.initRetryCount, delay: nextDelay })
      this.initRetryTimer = setTimeout(() => {
        this.initRetryTimer = null
        this.initFromCurrentState()
      }, nextDelay)
    },
    isTransientInitError(error) {
      const message = error && (error.message || error.errMsg || error.error) ? String(error.message || error.errMsg || error.error) : String(error || '')
      return /document unavailable|stage unavailable|querySelector|appendChild|Cannot read property|Cannot read properties|renderjs document unavailable|renderjs stage unavailable/i.test(message)
    },
    resolveResourcePath(src) {
      const value = String(src || '')
      if (!value || /^(https?:|data:|file:)/.test(value)) return value
      if (typeof plus !== 'undefined' && plus.io && typeof plus.io.convertLocalFileSystemURL === 'function') {
        const localValue = value.indexOf('/static/') === 0 ? `_www${value}` : value
        const converted = plus.io.convertLocalFileSystemURL(localValue)
        if (converted) return converted
      }
      if (value.indexOf('/static/') === 0) return `.${value}`
      return value
    },
    loadScript(src) {
      const candidates = []
      const resolved = this.resolveResourcePath(src)
      candidates.push(resolved)
      if (resolved && resolved !== src) candidates.push(src)
      const clean = String(src || '').replace(/^\//, '')
      candidates.push(`./${clean}`)
      candidates.push(`/_www/${clean}`)
      const urls = Array.from(new Set(candidates.filter(Boolean)))
      return new Promise((resolve, reject) => {
        const waitForDocument = (attempt = 0) => {
          const doc = typeof document !== 'undefined' ? document : null
          if (!doc || typeof doc.querySelector !== 'function' || typeof doc.createElement !== 'function' || !doc.head) {
            if (attempt < 50) {
              setTimeout(() => waitForDocument(attempt + 1), 100)
              return
            }
            reject(new Error('renderjs document unavailable'))
            return
          }
          const next = (index) => {
            if (index >= urls.length) {
              reject(new Error(`renderjs script load failed: ${src}`))
              return
            }
            const url = urls[index]
            const existing = doc.querySelector(`script[src="${url}"]`)
            if (existing) return setTimeout(resolve, 50)
            const script = doc.createElement('script')
            script.src = url
            script.onload = resolve
            script.onerror = () => next(index + 1)
            doc.head.appendChild(script)
          }
          next(0)
        }
        waitForDocument()
      })
    },
    waitForStage(stageId, attempt = 0) {
      return new Promise((resolve, reject) => {
        const stageEl = this.getStageElement(stageId)
        if (stageEl) {
          resolve(stageEl)
          return
        }
        if (attempt >= 50) {
          reject(new Error('renderjs stage unavailable'))
          return
        }
        setTimeout(() => {
          this.waitForStage(stageId, attempt + 1).then(resolve).catch(reject)
        }, 100)
      })
    },
    initFromCurrentState() {
      if (this.initializing || this.initialized) return
      const state = this.lastState || {}
      if (!state.stageId) {
        console.log('[digital-human][renderjs] wait for state', { initialized: this.initialized, initializing: this.initializing, has_state: !!this.lastState })
        this.scheduleInitRetry('missing-stage-id', 80)
        return
      }
      this.initLive2D(state)
    },
    updateState(newState) {
      this.lastState = newState || this.lastState || {}
      console.log('[digital-human][renderjs] state update', { status: this.lastState.status, emotion: this.lastState.emotion, speaking: this.lastState.speaking, action: this.lastState.action && this.lastState.action.type, seq: this.lastState.action && this.lastState.action.seq })
      if (!this.initialized) {
        this.initFromCurrentState()
        return
      }
      this.applyState(this.lastState)
      this.applyAction(this.lastState.action)
    },
    async initLive2D(state = {}) {
      if (this.initializing) return
      this.initializing = true
      const generation = ++this.initGeneration
      try {
        console.log('[digital-human][renderjs] init start', { model_path: state.modelPath || DEFAULT_MODEL_PATH, stage_id: state.stageId })
        if (!state.stageId) throw new Error('renderjs stage unavailable')
        const stageEl = await this.waitForStage(state.stageId)
        if (!stageEl || typeof stageEl.appendChild !== 'function') throw new Error('renderjs stage unavailable')
        this.stageEl = stageEl
        await this.loadScript(CUBISM_CORE_PATH)
        await this.loadScript(PIXI_PATH)
        await this.loadScript(LIVE2D_PLUGIN_PATH)
        const PIXI = window.PIXI
        if (!PIXI || !PIXI.live2d) throw new Error('renderjs Live2D library unavailable')
        PIXI.live2d.Live2DModel.registerTicker(PIXI.Ticker)
        console.log('[digital-human][renderjs] stage element', { stage_id: state.stageId, node_type: stageEl.nodeType, node_name: stageEl.nodeName, can_append: typeof stageEl.appendChild === 'function' })
        if (typeof stageEl.appendChild !== 'function') throw new Error(`renderjs stage cannot append canvas: ${stageEl.nodeName || stageEl.nodeType}`)
        const width = stageEl.offsetWidth || 300
        const height = stageEl.offsetHeight || 500
        this.app = new PIXI.Application({ width, height, backgroundAlpha: 0, antialias: true, autoDensity: true, resolution: Math.min(window.devicePixelRatio || 1, 2) })
        this.app.view.style.width = '100%'
        this.app.view.style.height = '100%'
        stageEl.appendChild(this.app.view)
        const modelPath = this.resolveResourcePath(state.modelPath || DEFAULT_MODEL_PATH)
        const model = await Promise.race([
          PIXI.live2d.Live2DModel.from(modelPath, { autoInteract: false, autoUpdate: false, motionPreload: PIXI.live2d.MotionPreloadStrategy.NONE, idleMotionGroup: 'Idle' }),
          new Promise((_, reject) => setTimeout(() => reject(new Error('renderjs model load timeout')), 20000))
        ])
        this.model = model
        this.app.stage.addChild(model)
        this.fitModel(width, height)
        this.coreModelCache = this.getCoreModel()
        this.bindMouthUpdate()
        this.bindLive2DTicker()
        if (generation !== this.initGeneration) {
          this.destroyLive2D()
          return
        }
        this.initialized = true
        this.applyState(state)
        console.log('[digital-human][renderjs] ready')
        this.notifyOwner('onRenderReady')
      } catch (error) {
        if (generation !== this.initGeneration) {
          return
        }
        if (this.isTransientInitError(error) && this.initRetryCount < 60) {
          console.warn('[digital-human][renderjs] transient renderjs init issue', {
            reason: this.initRetryReason || (error && error.message ? error.message : String(error || '')),
            count: this.initRetryCount,
            message: error && error.message ? error.message : String(error || '')
          })
          this.loadError = ''
          this.destroyLive2D()
          this.scheduleInitRetry(error && error.message ? error.message : 'transient-render-error')
          return
        }
        console.error('[digital-human][renderjs] init failed', error)
        this.isReady = false
        this.loadError = error.message || '加载失败'
        if (this.app) {
          this.destroyLive2D()
        }
        this.notifyOwner('onRenderError', { message: error && error.message ? error.message : String(error || 'renderjs load failed') })
      } finally {
        if (generation === this.initGeneration) {
          this.initializing = false
        }
      }
    },
    getStageElement(stageId) {
      const isAppendable = (node) => node && node.nodeType === 1 && typeof node.appendChild === 'function'
      const doc = typeof document !== 'undefined' ? document : null
      const candidates = []
      if (stageId && doc && typeof doc.getElementById === 'function') {
        candidates.push(doc.getElementById(stageId))
      }
      candidates.push(this.$el)
      if (this.$el && typeof this.$el.querySelector === 'function') {
        candidates.push(this.$el.querySelector('.live2d-stage'))
        candidates.push(this.$el.querySelector('div'))
      }
      if (doc && typeof doc.querySelector === 'function') {
        candidates.push(doc.querySelector(`#${stageId}`))
        candidates.push(doc.querySelector('.live2d-stage'))
      }
      for (let i = 0; i < candidates.length; i++) {
        let node = candidates[i]
        while (node) {
          if (isAppendable(node)) return node
          node = node.parentElement
        }
      }
      console.error('[digital-human][renderjs] no appendable stage', candidates.map((node) => node ? { node_type: node.nodeType, node_name: node.nodeName, can_append: typeof node.appendChild === 'function' } : null))
      return null
    },
    notifyOwner(method, payload) {
      if (this.$ownerInstance && typeof this.$ownerInstance.callMethod === 'function') this.$ownerInstance.callMethod(method, payload)
    },
    fitModel(width, height) {
      if (!this.model) return
      const scale = Math.min((width || 300) / this.model.width, (height || 500) / this.model.height) * 0.95
      this.model.scale.set(scale)
      this.model.anchor.set(0.5, 1)
      this.model.x = (width || 300) / 2
      this.model.y = height || 500
    },
    applyState(state = {}) {
      if (!this.model) return
      this.setExpression(EMOTION_MAP[state.emotion] || 'Normal')
      const motionOptions = this.resolveStatusMotion(state.status)
      this.playMotion(motionOptions.motion, motionOptions.motionIndex, { force: motionOptions.force })
      state.speaking ? this.startLipSync() : this.stopLipSync()
    },
    applyAction(action) {
      if (!action || !action.seq || action.seq === this.lastActionSeq) return
      this.lastActionSeq = action.seq
      const payload = action.payload || {}
      console.log('[digital-human][renderjs] action', { type: action.type, seq: action.seq })
      if (action.type === 'reload') return this.reload()
      if (action.type === 'ensure') {
        if (this.app && this.model) {
          if (this.app.start) this.app.start()
          this.notifyOwner('onRenderReady')
        } else {
          this.initFromCurrentState()
        }
        return
      }
      if (action.type === 'pause') return this.app && this.app.stop && this.app.stop()
      if (action.type === 'destroy') return this.destroyLive2D()
      if (action.type === 'startSpeaking') return this.startSpeaking(payload)
      if (action.type === 'stopSpeaking') return this.stopSpeaking()
      if (action.type === 'applyDigitalHuman') this.applyDigitalHuman(payload)
    },
    async reload() { this.destroyLive2D(); await this.initLive2D(this.lastState || {}) },
    resolveStatusMotion(status) { return STATUS_MOTION_OPTIONS[status] || STATUS_MOTION_OPTIONS.idle },
    getMotionPriority(force = false) {
      const priority = window.PIXI && window.PIXI.live2d && window.PIXI.live2d.MotionPriority
      if (!priority) return undefined
      return force ? priority.FORCE : priority.NORMAL
    },
    async playMotion(motion, motionIndex, options = {}) {
      if (!this.model || !motion) return
      const motionKey = `${motion}:${motionIndex === undefined ? 'random' : motionIndex}`
      if (!options.force && motionKey === this.currentMotion) return
      try {
        const priority = this.getMotionPriority(!!options.force)
        priority !== undefined ? await this.model.motion(motion, motionIndex, priority) : await this.model.motion(motion, motionIndex)
        this.currentMotion = motionKey
      } catch (error) { console.error('[digital-human][renderjs] play motion failed', error) }
    },
    async setExpression(expression) {
      if (!this.model || !expression || expression === this.currentExpression) return
      try { await this.model.expression(expression); this.currentExpression = expression } catch (error) { console.error('[digital-human][renderjs] set expression failed', error) }
    },
    getCoreModel() { return this.model && this.model.internalModel && this.model.internalModel.coreModel ? this.model.internalModel.coreModel : null },
    bindMouthUpdate() {
      this.unbindMouthUpdate()
      this.mouthUpdateHandler = () => this.applyMouthOpen()
      const internalModel = this.model && this.model.internalModel
      if (internalModel && typeof internalModel.on === 'function') internalModel.on('beforeModelUpdate', this.mouthUpdateHandler)
      if (this.app && this.app.ticker) { this.tickerMouthHandler = () => this.applyMouthOpen(); this.app.ticker.add(this.tickerMouthHandler) }
    },
    bindLive2DTicker() {
      this.unbindLive2DTicker()
      if (!this.app || !this.app.ticker || !this.model) return
      this.live2dTickerHandler = () => { if (!this.model || this.model.destroyed || this.model._destroyed) return; this.model.update(this.app.ticker.deltaMS || 16.6667) }
      this.app.ticker.add(this.live2dTickerHandler)
    },
    unbindLive2DTicker() { if (this.app && this.app.ticker && this.live2dTickerHandler) this.app.ticker.remove(this.live2dTickerHandler); this.live2dTickerHandler = null },
    unbindMouthUpdate() {
      const internalModel = this.model && this.model.internalModel
      if (internalModel && this.mouthUpdateHandler) {
        if (typeof internalModel.off === 'function') internalModel.off('beforeModelUpdate', this.mouthUpdateHandler)
        else if (typeof internalModel.removeListener === 'function') internalModel.removeListener('beforeModelUpdate', this.mouthUpdateHandler)
      }
      if (this.app && this.app.ticker && this.tickerMouthHandler) this.app.ticker.remove(this.tickerMouthHandler)
      this.mouthUpdateHandler = null
      this.tickerMouthHandler = null
    },
    startLipSync() {
      this.stopLipSync()
      this.isSpeakingNow = true
      this.lipSyncTimer = setInterval(() => {
        if (!this.isSpeakingNow) return
        let open = 0.25 + Math.sin(Date.now() / 150) * 0.4 + Math.random() * 0.15
        this.mouthOpenValue = Math.max(0, Math.min(1, open))
      }, 50)
    },
    applyMouthOpen() {
      const coreModel = this.coreModelCache || this.getCoreModel()
      if (!coreModel) return
      const value = Math.max(0, Math.min(1, Number(this.mouthOpenValue) || 0))
      if (typeof coreModel.setParameterValueById === 'function') coreModel.setParameterValueById(MOUTH_PARAM_ID, value, 1)
      else if (typeof coreModel.setParamFloat === 'function') coreModel.setParamFloat(MOUTH_PARAM_ID, value)
      else if (typeof coreModel.addParameterValueById === 'function') coreModel.addParameterValueById(MOUTH_PARAM_ID, value, 1)
    },
    stopLipSync() { this.isSpeakingNow = false; if (this.lipSyncTimer) clearInterval(this.lipSyncTimer); this.lipSyncTimer = null; this.mouthOpenValue = 0 },
    startSpeaking(options = {}) {
      if (!this.model) return
      this.setExpression(options.expression || EMOTION_MAP[(this.lastState || {}).emotion] || 'Normal')
      const speakMotion = this.resolveStatusMotion('speak')
      this.playMotion(options.motion || speakMotion.motion, options.motionIndex ?? speakMotion.motionIndex, { force: true })
      this.startLipSync()
    },
    stopSpeaking() { this.stopLipSync(); this.playMotion('Idle', undefined, { force: true }); this.setExpression('Normal') },
    applyDigitalHuman(options = {}) {
      if (!this.model) return
      if (options.emotion) this.setExpression(EMOTION_MAP[options.emotion] || options.emotion)
      if (options.motion) this.playMotion(options.motion, options.motionIndex, { force: true })
      if (options.expression) this.setExpression(options.expression)
      if (options.action && options.action !== 'speak') this.stopLipSync()
      if (options.speaking !== undefined) options.speaking ? this.startLipSync() : this.stopLipSync()
    },
    destroyLive2D() {
      this.stopLipSync()
      this.unbindMouthUpdate()
      this.unbindLive2DTicker()
      this.clearInitRetry()
      if (this.app) { try { this.app.destroy(true, { children: true, texture: true, baseTexture: true }) } catch (error) {}; this.app = null }
      this.model = null
      this.coreModelCache = null
      this.currentExpression = ''
      this.currentMotion = ''
      this.initialized = false
      this.initializing = false
    }
  }
}
</script>
<style lang="scss" scoped>
.digital-human {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 420rpx;
}

.live2d-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 420rpx;
  overflow: hidden;
}

.live2d-mask {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 1;
}

.live2d-placeholder {
  min-width: 260rpx;
  padding: 20rpx 24rpx;
  border: 1rpx solid rgba(255, 248, 232, 0.28);
  border-radius: 8rpx;
  background: rgba(20, 22, 24, 0.28);
  text-align: center;
  color: #fff8e8;
}

.placeholder-title {
  display: block;
  font-size: 26rpx;
  font-weight: 700;
}

.placeholder-subtitle {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  opacity: 0.72;
}
</style>
