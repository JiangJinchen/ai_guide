<template>
  <view class="login-container">
    <view class="login-header">
      <view class="logo-circle">
        <text class="logo-text">灵</text>
      </view>
      <text class="login-title">灵山胜境</text>
      <text class="login-subtitle">AI智慧导览</text>
    </view>

    <view class="login-form">
      <view class="form-item">
        <text class="form-icon">📱</text>
        <input 
          class="form-input" 
          v-model="phone" 
          placeholder="请输入手机号" 
          type="number"
          maxlength="11"
        />
      </view>

      <view class="form-item">
        <text class="form-icon">🔒</text>
        <input 
          class="form-input" 
          v-model="password" 
          placeholder="请输入密码" 
          type="password"
        />
      </view>

      <view class="form-actions">
        <text class="forgot-password">忘记密码？</text>
      </view>

      <button 
        class="login-btn" 
        :class="{ disabled: !canSubmit }"
        :disabled="!canSubmit"
        @click="handleLogin"
      >
        登录
      </button>

      <view class="register-link">
        <text>还没有账号？</text>
        <text class="link-text" @click="goToRegister">立即注册</text>
      </view>
    </view>
  </view>
</template>

<script>
import { post } from '@/utils/request'

export default {
  data() {
    return {
      phone: '',
      password: ''
    }
  },
  computed: {
    canSubmit() {
      return this.phone.length === 11 && this.password.length >= 6
    }
  },
  methods: {
    async handleLogin() {
      if (!this.canSubmit) return

      try {
        uni.showLoading({ title: '登录中...' })
        const res = await post('/visitor/auth/login', {
          phone: this.phone,
          password: this.password
        })

        if (res && res.access_token) {
          uni.setStorageSync('access_token', res.access_token)
          uni.setStorageSync('refresh_token', res.refresh_token)
          uni.setStorageSync('user_info', JSON.stringify(res.user))
          if (res.user && res.user.id !== undefined && res.user.id !== null) {
            uni.setStorageSync('userId', String(res.user.id))
          }
          
          uni.hideLoading()
          uni.showToast({ title: '登录成功', icon: 'success' })
          
          setTimeout(() => {
            uni.switchTab({ url: '/pages/home/index' })
          }, 1000)
        } else {
          uni.hideLoading()
          uni.showToast({ title: '登录失败', icon: 'none' })
        }
      } catch (error) {
        uni.hideLoading()
        uni.showToast({ 
          title: error.message || '登录失败', 
          icon: 'none' 
        })
      }
    },
    goToRegister() {
      uni.navigateTo({ url: '/pages/register/index' })
    }
  }
}
</script>

<style>
.login-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #743327 0%, #9b4a34 40%, #d8ad64 100%);
  padding: 60rpx 40rpx;
  box-sizing: border-box;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 0 60rpx;
}

.logo-circle {
  width: 120rpx;
  height: 120rpx;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  border: 3rpx solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20rpx;
}

.logo-text {
  font-size: 56rpx;
  font-weight: bold;
  color: #fff;
}

.login-title {
  font-size: 40rpx;
  font-weight: bold;
  color: #fff;
  margin-bottom: 8rpx;
}

.login-subtitle {
  font-size: 24rpx;
  color: rgba(255, 255, 255, 0.7);
}

.login-form {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20rpx;
  padding: 40rpx;
  box-shadow: 0 20rpx 50rpx rgba(0, 0, 0, 0.2);
}

.form-item {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 12rpx;
  padding: 0 20rpx;
  margin-bottom: 24rpx;
}

.form-icon {
  font-size: 32rpx;
  margin-right: 20rpx;
}

.form-input {
  flex: 1;
  height: 88rpx;
  font-size: 28rpx;
  color: #333;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 30rpx;
}

.forgot-password {
  font-size: 24rpx;
  color: #999;
}

.login-btn {
  width: 100%;
  height: 88rpx;
  background: linear-gradient(135deg, #743327, #d8ad64);
  border-radius: 44rpx;
  color: #fff;
  font-size: 32rpx;
  font-weight: bold;
  border: none;
  margin-bottom: 30rpx;
}

.login-btn.disabled {
  opacity: 0.5;
}

.register-link {
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 26rpx;
  color: #666;
}

.link-text {
  color: #743327;
  margin-left: 8rpx;
}
</style>