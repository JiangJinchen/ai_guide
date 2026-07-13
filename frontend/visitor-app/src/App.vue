<script>
export default {
  onLaunch() {
    if (!uni.getStorageSync('userId')) {
      const userId = 'visitor_' + Date.now()
      uni.setStorageSync('userId', userId)
    }
    const launchCount = Number(uni.getStorageSync('appLaunchCount') || 0)
    uni.setStorageSync('appLaunchCount', launchCount + 1)
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
