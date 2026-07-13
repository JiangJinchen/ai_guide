const PROMPT_STATE_KEY = 'feedbackPromptState'
const DAY_MS = 24 * 60 * 60 * 1000

export const FEEDBACK_COOLDOWN = {
  app: 7 * DAY_MS,
  chat: 7 * DAY_MS,
  guide: 7 * DAY_MS,
  route: 7 * DAY_MS
}

const readPromptState = () => {
  const state = uni.getStorageSync(PROMPT_STATE_KEY)
  return state && typeof state === 'object' ? state : {}
}

const writePromptState = (state) => {
  uni.setStorageSync(PROMPT_STATE_KEY, state || {})
}

const normalizeKey = (value) => String(value || 'default')

const ensureBucket = (state, type) => {
  const bucket = state[type] || {}
  bucket.targets = bucket.targets || {}
  state[type] = bucket
  return bucket
}

export const canPromptFeedback = (type, targetKey, cooldownMs = FEEDBACK_COOLDOWN[type] || FEEDBACK_COOLDOWN.app) => {
  const state = readPromptState()
  const bucket = state[type] || {}
  const key = normalizeKey(targetKey)
  const target = (bucket.targets || {})[key] || {}
  const now = Date.now()

  if (target.submittedAt) return false
  if (target.lastPromptAt && now - target.lastPromptAt < cooldownMs) return false
  if (bucket.lastPromptAt && now - bucket.lastPromptAt < 10 * 60 * 1000) return false
  return true
}

export const markFeedbackPrompt = (type, targetKey, status = 'shown') => {
  const state = readPromptState()
  const bucket = ensureBucket(state, type)
  const key = normalizeKey(targetKey)
  const target = bucket.targets[key] || {}
  const now = Date.now()

  target.lastPromptAt = now
  if (status === 'dismissed') target.dismissedAt = now
  if (status === 'submitted') target.submittedAt = now

  bucket.targets[key] = target
  bucket.lastPromptAt = now
  writePromptState(state)
}

export const markFeedbackSubmitted = (type, targetKey) => {
  markFeedbackPrompt(type, targetKey, 'submitted')
}

export const buildFeedbackUrl = (params = {}) => {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return `/pages/feedback/index${query ? `?${query}` : ''}`
}

export const openFeedbackPage = (params = {}) => {
  uni.navigateTo({ url: buildFeedbackUrl(params) })
}

export const promptForFeedback = ({
  type,
  targetKey,
  title,
  content,
  params,
  cooldownMs,
  useCustomModal = false
}) => {
  if (!canPromptFeedback(type, targetKey, cooldownMs)) return Promise.resolve(false)
  markFeedbackPrompt(type, targetKey, 'shown')
  
  if (useCustomModal) {
    return Promise.resolve({
      shouldShow: true,
      type,
      targetKey,
      title,
      content,
      params
    })
  }
  
  return new Promise((resolve) => {
    uni.showModal({
      title,
      content,
      confirmText: '去评价',
      cancelText: '稍后',
      success: (res) => {
        if (res.confirm) {
          openFeedbackPage(params)
          resolve(true)
        } else {
          markFeedbackPrompt(type, targetKey, 'dismissed')
          resolve(false)
        }
      },
      fail: () => {
        resolve(false)
      }
    })
  })
}
