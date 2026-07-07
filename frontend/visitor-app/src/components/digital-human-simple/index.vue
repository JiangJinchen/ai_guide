<template>
  <view class="digital-human">
    <view class="live2d-stage" ref="stageRef">
      <view v-if="!isReady" class="live2d-mask">
        <view class="live2d-placeholder">
          <text class="placeholder-title">{{ loadText }}</text>
          <text class="placeholder-subtitle">{{ loadSubText }}</text>
        </view>
      </view>
    </view>
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
      mediaElementSource: null
    }
  },
  computed: {
    loadText() {
      return this.loadError ? 'Live2D 加载失败' : 'Live2D 加载中'
    },
    loadSubText() {
      return this.loadError || '正在准备数字人模型'
    }
  },
  watch: {
    status(newStatus) {
      if (this.isReady) {
        const motionOptions = this.resolveStatusMotion(newStatus)
        this.playMotion(motionOptions.motion, motionOptions.motionIndex, {
          force: motionOptions.force
        })
      }
    },
    emotion(newEmotion) {
      if (this.isReady) {
        const expression = EMOTION_MAP[newEmotion] || 'Normal'
        this.setExpression(expression)
      }
    },
    speaking(newVal) {
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
    this.initLive2D()
  },
  beforeUnmount() {
    this.destroyLive2D()
  },
  methods: {
    async initLive2D() {
      try {
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
          resolution: window.devicePixelRatio || 1
        })
        this.app.view.style.width = '100%'
        this.app.view.style.height = '100%'
        this.stageEl.appendChild(this.app.view)

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
        this.loadError = error.message || '加载失败'
        this.$emit('error', error)
      }
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
        const existing = document.querySelector(`script[src="${src}"]`)
        if (existing) {
          setTimeout(resolve, 100)
          return
        }
        const script = document.createElement('script')
        script.src = src
        script.onload = resolve
        script.onerror = () => reject(new Error(`脚本加载失败: ${src}`))
        document.head.appendChild(script)
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
      this.stopLipSync()
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
      this.stopLipSync()
      this.isSpeakingNow = true
      try {
        if (!window.AudioContext && !window.webkitAudioContext) {
          this.startLipSync()
          return
        }
        
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
        this.analyser = this.audioContext.createAnalyser()
        this.analyser.fftSize = 256
        const bufferLength = this.analyser.frequencyBinCount
        this.dataArray = new Uint8Array(bufferLength)
        
        this.mediaElementSource = this.audioContext.createMediaElementSource(audioElement)
        this.mediaElementSource.connect(this.analyser)
        this.analyser.connect(this.audioContext.destination)
        
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
    stopLipSync() {
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
      if (this.audioContext) {
        this.audioContext.close()
        this.audioContext = null
        this.analyser = null
        this.dataArray = null
        this.mediaElementSource = null
      }
      this.mouthOpenValue = 0
    },
    startSpeaking(options = {}) {
      if (!this.isReady) return
      this.setExpression(options.expression || EMOTION_MAP[this.emotion] || 'Normal')
      const speakMotion = this.resolveStatusMotion('speak')
      this.playMotion(options.motion || speakMotion.motion, options.motionIndex ?? speakMotion.motionIndex, {
        force: true
      })
      this.startLipSync()
    },
    stopSpeaking() {
      this.stopLipSync()
      this.playMotion('Idle', undefined, { force: true })
      this.setExpression('Normal')
    },
    applyDigitalHuman(options) {
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
      if (options.action) {
        if (options.action === 'speak') {
          this.startLipSync()
        } else {
          this.stopLipSync()
        }
      }
      if (options.speaking !== undefined) {
        if (options.speaking) {
          this.startLipSync()
        } else {
          this.stopLipSync()
        }
      }
    },
    destroyLive2D() {
      this.stopLipSync()
      this.unbindMouthUpdate()
      this.unbindLive2DTicker()
      if (this.app) {
        this.app.destroy(true, { children: true, texture: true, baseTexture: true })
        this.app = null
      }
      this.model = null
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
