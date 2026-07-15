<script>
export default {
  onLaunch() {
    if (!uni.getStorageSync('userId')) {
      const userId = 'visitor_' + Date.now()
      uni.setStorageSync('userId', userId)
    }
    const launchCount = Number(uni.getStorageSync('appLaunchCount') || 0)
    uni.setStorageSync('appLaunchCount', launchCount + 1)
    
    const userInfo = uni.getStorageSync('user_info')
    if (userInfo) {
      try {
        const parsed = JSON.parse(userInfo)
        uni.setStorageSync('userId', parsed.id)
      } catch (e) {
        uni.removeStorageSync('user_info')
      }
    }
  },
  onShow() {},
  onHide() {}
}
</script>

<style lang="scss">
@import './uni.scss';

page {
  background-color: #f5f5f5;
  font-size: 28rpx;
  color: #333;
}

view, text {
  box-sizing: border-box;
}
</style>
