import { createSSRApp } from 'vue'
import App from './App.vue'

export function createApp() {
  ;(window as any).__uniConfig = (window as any).__uniConfig || {}
  ;(window as any).__uniConfig.aMapKey = '4356d3328eff90d2f825b5a0f5d686ca'
  
  const app = createSSRApp(App)
  return {
    app
  }
}
