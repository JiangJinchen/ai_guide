import { createSSRApp } from 'vue'
import App from './App.vue'

export function createApp() {
  // `window` is only available on H5. Touching it during App startup
  // breaks instance creation and leads to a white screen.
  if (typeof window !== 'undefined') {
    ;(window as any).__uniConfig = (window as any).__uniConfig || {}
    ;(window as any).__uniConfig.aMapKey = '4356d3328eff90d2f825b5a0f5d686ca'
  }
  
  const app = createSSRApp(App)
  return {
    app
  }
}
