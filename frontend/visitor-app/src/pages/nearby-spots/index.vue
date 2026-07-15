<template>
  <view class="nearby-page">
    <view class="page-head">
      <view>
        <text class="page-title">附近景点</text>
        <text class="page-subtitle">实时查看周边景点与配套服务</text>
      </view>
    </view>

    <view class="location-card" :class="statusClass">
      <view class="status-dot"></view>
      <view class="location-copy">
        <text class="location-title">{{ statusTitle }}</text>
      </view>
      <view class="location-actions">
        <view class="icon-btn-small" :class="{ spinning: locationStatus === 'loading' }" @click.stop="refreshLocation">
          <text class="icon-text">⟳</text>
        </view>
        <view class="icon-btn-small" @click.stop="openLocationSelector">
          <text class="icon-text">📍</text>
        </view>
      </view>
    </view>

    <view class="map-panel">
      <view class="map-canvas">
        <view class="map-road road-main"></view>
        <view class="map-road road-side"></view>
        <view class="map-road road-ring"></view>
        <view class="map-water"></view>
        <view class="user-marker" :style="userMapStyle">
          <view class="pulse"></view>
          <text>我</text>
        </view>
        <view
          class="map-point"
          :class="['point-' + point.kind, 'point-' + point.type, { active: isMapPointActive(point), cluster: point.kind === 'cluster' }]"
          v-for="point in mapPoints"
          :key="point.key"
          :style="point.style"
          @click="openMapPoint(point)"
        >
          <text>{{ point.label }}</text>
          <view class="point-bubble" v-if="point.showName">
            <text>{{ point.name }}</text>
          </view>
        </view>
      </view>
      <view class="map-active-card" v-if="activeMapPoint">
        <view class="map-active-main">
          <text class="map-active-title">{{ activeMapPoint.name }}</text>
          <text class="map-active-meta">{{ activeMapPoint.distanceText || activeMapPoint.summary }}</text>
        </view>
        <text class="map-active-action" @click="handleActiveMapPointAction">{{ activeMapPoint.actionText }}</text>
      </view>
      <view class="map-caption">
        <text>{{ mapCaption }}</text>
      </view>
    </view>

    <view class="section-block">
      <view class="section-head">
        <text class="section-title">附近服务点</text>
        <text class="section-count">{{ sortedServicePoints.length }}处</text>
      </view>

      <view
        class="service-row"
        :class="{ active: isListItemActive(item, 'service') }"
        v-for="item in sortedServicePoints"
        :key="mapItemKey(item, 'service')"
        :id="mapItemDomId(item, 'service')"
        @click="selectMapItem(item, 'service')"
      >
        <view class="service-icon" :class="'service-' + item.type">
          <text>{{ item.icon }}</text>
        </view>
        <view class="service-main">
          <text class="item-name">{{ item.name }}</text>
          <text class="item-meta">{{ item.distanceText }}</text>
        </view>
        <view class="nav-plane" @click="openNavigation(item)">
          <text>➤</text>
        </view>
      </view>

      <view class="empty-state compact" v-if="sortedServicePoints.length === 0">
        <text>当前范围内无配套服务设施</text>
      </view>
    </view>

    <view class="section-block">
      <view class="section-head">
        <text class="section-title">附近景点</text>
        <text class="section-count">{{ filteredSpots.length }}处</text>
      </view>

      <scroll-view class="filter-scroll" scroll-x>
        <view class="filter-line">
          <text
            class="filter-chip"
            :class="{ active: selectedDistance === item.value }"
            v-for="item in distanceOptions"
            :key="item.value"
            @click="selectedDistance = item.value"
          >
            {{ item.label }}
          </text>
        </view>
      </scroll-view>

      <view
        class="spot-row"
        :class="{ active: isListItemActive(spot, 'spot') }"
        v-for="spot in filteredSpots"
        :key="spot.id"
        :id="mapItemDomId(spot, 'spot')"
        @click="selectMapItem(spot, 'spot')"
      >
        <view class="spot-thumb" :class="'spot-' + spot.type">
          <text>{{ spot.typeLabel.slice(0, 1) }}</text>
        </view>
        <view class="spot-main">
          <view class="spot-title-line">
            <text class="item-name">{{ spot.name }}</text>
            <text class="spot-tag">{{ spot.typeLabel }}</text>
          </view>
          <text class="item-desc">{{ spot.description || '灵山胜境景点' }}</text>
          <text class="item-meta">{{ spot.distanceText }}{{ spot.walkTime ? ` · 步行${spot.walkTime}` : '' }}</text>
        </view>
      </view>

      <view class="empty-state" v-if="filteredSpots.length === 0">
        <view class="empty-illustration">
          <text>景</text>
        </view>
        <text class="empty-title">没有符合条件的景点</text>
        <text class="empty-desc">换个距离范围试试呢</text>
      </view>
    </view>

    <view class="location-mask" v-if="showLocationSelector" @click="showLocationSelector = false">
      <view class="location-panel" @click.stop>
        <view class="location-head">
          <text class="location-title-text">选择当前所在景点</text>
          <text class="location-close" @click="showLocationSelector = false">×</text>
        </view>
        <view class="location-list">
          <view
            class="location-item"
            :class="{ active: isLocationActive(spot) }"
            v-for="spot in allSpots"
            :key="spot.id"
            @click="selectLocation(spot)"
          >
            <view class="location-check">{{ isLocationActive(spot) ? '✓' : '' }}</view>
            <view class="location-info">
              <text class="location-name">{{ spot.spot_name || spot.name }}</text>
            </view>
          </view>
          <view class="empty-state" v-if="allSpots.length === 0">
            <text>暂无可选景点</text>
          </view>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import { get } from '@/utils/request'
import { formatLocationText, getLocationErrorMessage, requestCurrentLocation, saveLocation } from '@/utils/location'

const DEFAULT_LOCATION = {
  latitude: 31.42892,
  longitude: 120.09487,
  name: '灵山胜境游客中心'
}

const SPOT_COORDS = {
  灵山大照壁: { latitude: 31.42892, longitude: 120.09487, type: 'checkin' },
  五明桥: { latitude: 31.42924, longitude: 120.09542, type: 'scenic' },
  佛足坛: { latitude: 31.42966, longitude: 120.09586, type: 'culture' },
  五智门: { latitude: 31.43003, longitude: 120.09628, type: 'culture' },
  菩提大道: { latitude: 31.43048, longitude: 120.09684, type: 'scenic' },
  九龙灌浴: { latitude: 31.43102, longitude: 120.09726, type: 'performance' },
  降魔浮雕: { latitude: 31.43142, longitude: 120.09782, type: 'culture' },
  阿育王柱: { latitude: 31.43184, longitude: 120.09822, type: 'checkin' },
  百子戏弥勒: { latitude: 31.43218, longitude: 120.09876, type: 'checkin' },
  祥符禅寺: { latitude: 31.43272, longitude: 120.0991, type: 'culture' },
  灵山大佛: { latitude: 31.43334, longitude: 120.09958, type: 'scenic' },
  佛教文化博览馆: { latitude: 31.43235, longitude: 120.10028, type: 'culture' },
  无尽意斋: { latitude: 31.43156, longitude: 120.10066, type: 'scenic' },
  灵山梵宫: { latitude: 31.43072, longitude: 120.10116, type: 'culture' },
  五印坛城: { latitude: 31.42998, longitude: 120.10174, type: 'culture' },
  曼飞龙塔: { latitude: 31.4294, longitude: 120.10208, type: 'checkin' },
  拈花广场: { latitude: 31.42876, longitude: 120.10242, type: 'checkin' },
  香月花街: { latitude: 31.42822, longitude: 120.10282, type: 'checkin' },
  拈花堂: { latitude: 31.42774, longitude: 120.10318, type: 'culture' },
  五灯湖: { latitude: 31.42728, longitude: 120.10362, type: 'scenic' },
  梵天花海: { latitude: 31.42688, longitude: 120.10418, type: 'checkin' },
  鹿鸣谷: { latitude: 31.42636, longitude: 120.10462, type: 'scenic' }
}

const fallbackSpots = [
  { id: 1, spot_name: '灵山大佛', description: '太湖之滨的地标佛像，适合祈福与远眺。' },
  { id: 2, spot_name: '灵山梵宫', description: '佛教艺术殿堂，建筑、壁画与演出皆值得停留。' },
  { id: 3, spot_name: '九龙灌浴', description: '经典动态表演场景，适合亲子和初到游客。' },
  { id: 4, spot_name: '五印坛城', description: '藏传佛教文化空间，色彩浓烈，适合拍照打卡。' },
  { id: 5, spot_name: '拈花广场', description: '开阔打卡点，适合短暂停留和拍照。' }
]

const servicePoints = [
  { id: 'parking-east', name: '东入口停车场', type: 'parking', icon: 'P', latitude: 31.42858, longitude: 120.09422 },
  { id: 'parking-south', name: '南区停车场', type: 'parking', icon: 'P', latitude: 31.42696, longitude: 120.0962 },
  { id: 'restroom-gate', name: '售票处卫生间', type: 'toilet', icon: '卫', latitude: 31.420139, longitude: 120.103038 },
  { id: 'restroom-gate', name: '入口卫生间', type: 'toilet', icon: '卫', latitude: 31.4206, longitude: 120.103612 },
  { id: 'restroom-buddha', name: '大佛广场卫生间', type: 'toilet', icon: '卫', latitude: 31.426747, longitude: 120.097625 },
  { id: 'visitor-center', name: '游客服务中心', type: 'center', icon: 'i', latitude: 31.43039, longitude: 120.09658 },
  { id: 'food-street', name: '香月花街餐饮', type: 'food', icon: '食', latitude: 31.42822, longitude: 120.10282 },
  { id: 'food-palace', name: '梵宫简餐点', type: 'food', icon: '食', latitude: 31.43066, longitude: 120.1009 }
]

const spotTypeLabels = {
  scenic: '景点',
  checkin: '打卡点',
  culture: '文化点',
  performance: '演出点'
}

export default {
  data() {
    return {
      locationStatus: 'loading',
      locationMessage: '',
      userLocation: null,
      allSpots: [],
      backendNearbySpots: [],
      selectedDistance: 1000,
      selectedMapPointKey: '',
      showLocationSelector: false,
      distanceOptions: [
        { label: '500m内', value: 500 },
        { label: '1km内', value: 1000 },
        { label: '2km内', value: 2000 },
        { label: '全部', value: 'all' }
      ]
    }
  },
  computed: {
    hasLocation() {
      return Boolean(this.userLocation)
    },
    statusClass() {
      return `status-${this.locationStatus}`
    },
    statusTitle() {
      if (this.locationStatus === 'loading') return '正在获取您的实时位置'
      if (this.locationStatus === 'success') return '定位成功'
      return '定位失败，请检查定位授权，或走到开阔地段后手动刷新'
    },
    mapCaption() {
      if (!this.hasLocation) return '地图已定位到灵山胜境游客中心，获取定位后会自动切换到您的当前位置'
      return `已按当前位置刷新 ${this.sortedServicePoints.length} 个服务点、${this.filteredSpots.length} 个景点`
    },
    userMapStyle() {
      return 'left: 50%; top: 50%;'
    },
    mapRangeMeters() {
      if (this.selectedDistance === 'all') {
        const distances = [...this.sortedServicePoints, ...this.filteredSpots]
          .map(item => Number(item.distance))
          .filter(Number.isFinite)
        const maxDistance = distances.length ? Math.max(...distances) : 900
        return Math.max(900, Math.min(3000, Math.ceil(maxDistance * 1.15)))
      }
      return Math.max(500, Number(this.selectedDistance || 900))
    },
    mapServicePoints() {
      const range = this.mapRangeMeters
      const points = this.sortedServicePoints
        .filter(item => this.selectedDistance === 'all' || item.distance <= range)
        .slice(0, 3)
      const selected = this.sortedServicePoints.find(item => this.mapItemKey(item, 'service') === this.selectedMapPointKey)
      if (selected && !points.some(item => this.mapItemKey(item, 'service') === this.selectedMapPointKey)) {
        points.push(selected)
      }
      return points
    },
    mapSpotPoints() {
      const points = this.filteredSpots.slice(0, 5)
      const selected = this.filteredSpots.find(item => this.mapItemKey(item, 'spot') === this.selectedMapPointKey)
      if (selected && !points.some(item => this.mapItemKey(item, 'spot') === this.selectedMapPointKey)) {
        points.push(selected)
      }
      return points
    },
    mapHiddenCount() {
      return Math.max(0, this.sortedServicePoints.length - this.mapServicePoints.length) +
        Math.max(0, this.filteredSpots.length - this.mapSpotPoints.length)
    },
    mapPoints() {
      const services = this.mapServicePoints.map(item => ({
        ...item,
        kind: 'service',
        label: item.icon,
        key: this.mapItemKey(item, 'service')
      }))
      const spots = this.mapSpotPoints.map(item => ({
        ...item,
        kind: 'spot',
        label: this.spotMapIcon(item),
        key: this.mapItemKey(item, 'spot')
      }))
      return this.clusterMapPoints(this.createMapPoints([...services, ...spots]))
    },
    activeMapPoint() {
      if (!this.selectedMapPointKey) return null
      const flatPoints = this.mapPoints.flatMap(point => point.children || [point])
      const point = flatPoints.find(item => item.key === this.selectedMapPointKey) ||
        this.mapPoints.find(item => item.key === this.selectedMapPointKey)
      if (!point) return null
      if (point.kind === 'cluster') {
        return {
          ...point,
          name: `${point.children.length} 个位置较近`,
          summary: point.children.slice(0, 3).map(item => item.name).join('、'),
          actionText: '查看最近'
        }
      }
      return {
        ...point,
        actionText: point.kind === 'service' ? '导航' : '详情'
      }
    },
    sortedServicePoints() {
      if (!this.hasLocation) return []
      return servicePoints
        .map(item => this.withDistance(item))
        .filter(item => item.distance <= 3000)
        .sort((a, b) => a.distance - b.distance)
    },
    normalizedSpots() {
      const source = this.backendNearbySpots.length
        ? this.backendNearbySpots
        : this.allSpots.length
          ? this.allSpots
          : fallbackSpots
      return source
        .map(spot => this.normalizeSpot(spot))
        .filter(item => item.latitude && item.longitude)
        .map(item => {
          if (Number.isFinite(item.distance)) return item
          return this.hasLocation ? this.withDistance(item) : { ...item, distance: Infinity, distanceText: '待定位' }
        })
        .sort((a, b) => a.distance - b.distance)
    },
    filteredSpots() {
      if (!this.hasLocation) return []
      return this.normalizedSpots.filter(item => {
        return this.selectedDistance === 'all' || item.distance <= this.selectedDistance
      })
    }
  },
  onLoad() {
    this.loadAllSpots()
    this.refreshLocation()
  },
  methods: {
    async loadAllSpots() {
      try {
        const list = await get('/spots')
        this.allSpots = Array.isArray(list) && list.length ? list : fallbackSpots
      } catch (e) {
        this.allSpots = fallbackSpots
      }
    },
    async refreshLocation(options = {}) {
      if (!options.silent) {
        this.locationStatus = 'loading'
        this.locationMessage = ''
      }

      try {
        const location = await requestCurrentLocation({
          allowCache: true,
          allowFallback: !this.hasLocation,
          highAccuracy: true
        })
        this.applyLocation(location)
      } catch (error) {
        if (!this.hasLocation) {
          this.locationStatus = 'failed'
          this.locationMessage = getLocationErrorMessage(error)
        }
      }
    },
    openLocationSelector() {
      this.showLocationSelector = true
    },
    selectLocation(spot) {
      const latitude = Number(spot.latitude)
      const longitude = Number(spot.longitude)
      if (!latitude || !longitude) return
      
      this.userLocation = {
        latitude,
        longitude,
        name: spot.spot_name || spot.name,
        spot_id: spot.id,
        source: 'manual'
      }
      this.locationStatus = 'success'
      this.locationMessage = `当前起点 ${spot.spot_name || spot.name}`
      this.showLocationSelector = false
      saveLocation({ latitude, longitude, accuracy: 0, provider: 'gcj02' })
      this.loadNearbySpots()
    },
    isLocationActive(spot) {
      if (!this.userLocation || !spot) return false
      return Math.abs(this.userLocation.latitude - Number(spot.latitude)) < 0.00001 &&
             Math.abs(this.userLocation.longitude - Number(spot.longitude)) < 0.00001
    },
    formatCoordinate(value) {
      return Number(value).toFixed(5)
    },
    applyLocation(location) {
      const latitude = Number(location.latitude)
      const longitude = Number(location.longitude)
      if (!latitude || !longitude) return

      this.userLocation = { latitude, longitude }
      this.locationStatus = 'success'
      this.locationMessage = formatLocationText(location)
      this.loadNearbySpots()
    },
    async loadNearbySpots() {
      if (!this.hasLocation) return
      try {
        const res = await get('/gps', {
          lat: this.userLocation.latitude,
          lon: this.userLocation.longitude,
          max_results: 30,
          max_distance_km: 3,
          mode: 'walking'
        })
        this.backendNearbySpots = (res.nearby_spots || []).map(item => ({
          id: item.id,
          name: item.name || item.spot_name,
          description: item.description || '',
          latitude: item.location?.latitude,
          longitude: item.location?.longitude,
          distance: Number(item.distance),
          distanceText: item.distance_text || this.formatDistance(Number(item.distance)),
          walkTime: item.walk_time || '',
          provider: item.provider
        }))
      } catch (e) {
        this.backendNearbySpots = []
      }
    },
    normalizeSpot(spot) {
      const name = spot.spot_name || spot.name || '灵山景点'
      const coord = SPOT_COORDS[name] || {}
      const type = spot.type || coord.type || this.inferSpotType(name)
      return {
        id: spot.id,
        name,
        description: spot.description || spot.culture_connotation || '',
        latitude: Number(spot.latitude || coord.latitude),
        longitude: Number(spot.longitude || coord.longitude),
        distance: Number.isFinite(spot.distance) ? spot.distance : undefined,
        distanceText: spot.distanceText,
        walkTime: spot.walkTime,
        provider: spot.provider,
        type,
        typeLabel: spotTypeLabels[type] || '景点'
      }
    },
    inferSpotType(name) {
      if (/广场|花海|塔|柱|照壁/.test(name)) return 'checkin'
      if (/灌浴|演出|吉祥颂/.test(name)) return 'performance'
      if (/寺|宫|坛城|博览|斋/.test(name)) return 'culture'
      return 'scenic'
    },
    withDistance(item) {
      const distance = this.calculateDistance(
        this.userLocation.latitude,
        this.userLocation.longitude,
        item.latitude,
        item.longitude
      )
      return {
        ...item,
        distance,
        distanceText: this.formatDistance(distance)
      }
    },
    calculateDistance(lat1, lon1, lat2, lon2) {
      const toRad = value => (value * Math.PI) / 180
      const radius = 6371000
      const dLat = toRad(lat2 - lat1)
      const dLon = toRad(lon2 - lon1)
      const a =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
        Math.sin(dLon / 2) * Math.sin(dLon / 2)
      return Math.round(radius * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)))
    },
    formatDistance(distance) {
      if (!Number.isFinite(distance)) return '待定位'
      if (distance < 1000) return `${distance}米`
      return `${(distance / 1000).toFixed(1)}公里`
    },
    createMapPoints(points) {
      const center = this.userLocation || DEFAULT_LOCATION
      return points
        .map(point => {
          const position = this.toMapPosition(center, point)
          if (!position) return null
          const isSelected = this.mapItemKey(point, point.kind) === this.selectedMapPointKey
          return {
            ...point,
            ...position,
            key: this.mapItemKey(point, point.kind),
            domId: this.mapItemDomId(point, point.kind),
            showName: isSelected,
            style: `left: ${position.x}%; top: ${position.y}%;`
          }
        })
        .filter(Boolean)
    },
    toMapPosition(center, point) {
      const meterPerLat = 111000
      const meterPerLon = 111000 * Math.cos(center.latitude * Math.PI / 180)
      const dx = (point.longitude - center.longitude) * meterPerLon
      const dy = (point.latitude - center.latitude) * meterPerLat
      const range = this.mapRangeMeters
      const rawX = 50 + (dx / range) * 42
      const rawY = 50 - (dy / range) * 42
      if (rawX < 4 || rawX > 96 || rawY < 4 || rawY > 96) return null
      const x = Math.max(8, Math.min(92, rawX))
      const y = Math.max(8, Math.min(92, rawY))
      return { x: Math.round(x), y: Math.round(y) }
    },
    clusterMapPoints(points) {
      const groups = []
      points.forEach(point => {
        if (point.key === this.selectedMapPointKey) {
          groups.push({ x: point.x, y: point.y, children: [point], locked: true })
          return
        }
        const group = groups.find(item => {
          return !item.locked && Math.abs(item.x - point.x) < 8 && Math.abs(item.y - point.y) < 8
        })
        if (group) {
          group.children.push(point)
          group.x = Math.round(group.children.reduce((sum, item) => sum + item.x, 0) / group.children.length)
          group.y = Math.round(group.children.reduce((sum, item) => sum + item.y, 0) / group.children.length)
        } else {
          groups.push({ x: point.x, y: point.y, children: [point], locked: false })
        }
      })

      return groups.map(group => {
        if (group.children.length === 1) return group.children[0]
        const key = `cluster-${group.children.map(item => item.key).join('-')}`
        return {
          id: key,
          key,
          kind: 'cluster',
          type: 'cluster',
          label: String(group.children.length),
          x: group.x,
          y: group.y,
          children: group.children,
          style: `left: ${group.x}%; top: ${group.y}%;`
        }
      })
    },
    spotMapIcon(item) {
      const icons = {
        scenic: '景',
        checkin: '拍',
        culture: '文',
        performance: '演'
      }
      return icons[item.type] || '景'
    },
    mapItemKey(item, kind) {
      return `${kind}-${item.id || item.name}-${Number(item.latitude).toFixed(6)}-${Number(item.longitude).toFixed(6)}`
    },
    mapItemDomId(item, kind) {
      return this.mapItemKey(item, kind).replace(/[^a-zA-Z0-9_-]/g, '-')
    },
    isMapPointActive(point) {
      if (point.kind === 'cluster') return point.key === this.selectedMapPointKey
      return point.key === this.selectedMapPointKey
    },
    isListItemActive(item, kind) {
      return this.mapItemKey(item, kind) === this.selectedMapPointKey
    },
    selectMapItem(item, kind) {
      this.selectedMapPointKey = this.mapItemKey(item, kind)
    },
    scrollToMapItem(point) {
      if (!point.domId) return
      this.$nextTick(() => {
        uni.pageScrollTo({
          selector: `#${point.domId}`,
          duration: 240
        })
      })
    },
    openMapPoint(point) {
      if (point.kind === 'cluster') {
        this.selectedMapPointKey = point.key
        return
      }
      this.selectedMapPointKey = point.key
      this.scrollToMapItem(point)
    },
    handleActiveMapPointAction() {
      const point = this.activeMapPoint
      if (!point) return
      if (point.kind === 'cluster') {
        const first = point.children?.[0]
        if (first) {
          this.selectedMapPointKey = first.key
          this.scrollToMapItem(first)
        }
        return
      }
      if (point.kind === 'service') {
        this.openNavigation(point)
        return
      }
      this.goToGuide(point.id)
    },
    openNavigation(item) {
      if (!item.latitude || !item.longitude) {
        uni.showToast({ title: '暂无可导航位置', icon: 'none' })
        return
      }
      uni.openLocation({
        latitude: Number(item.latitude),
        longitude: Number(item.longitude),
        name: item.name,
        address: '灵山胜境景区内'
      })
    },
    goToGuide(id) {
      uni.navigateTo({ url: `/pages/spot-detail/index?spot_id=${id}` })
    }
  }
}
</script>

<style lang="scss" scoped>
.nearby-page {
  min-height: 100vh;
  padding: 28rpx 24rpx 48rpx;
  background:
    radial-gradient(circle at 8% 4%, rgba(188, 65, 48, 0.14), transparent 34%),
    linear-gradient(180deg, #f5ead8 0%, #efe1ca 45%, #f7f1e7 100%);
  color: #33251b;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20rpx;
  padding: 22rpx 4rpx 24rpx;
}

.page-title,
.page-subtitle,
.location-title,
.section-title,
.item-name,
.item-meta,
.item-desc,
.empty-title,
.empty-desc {
  display: block;
}

.page-title {
  color: #4b2b1f;
  font-size: 44rpx;
  font-weight: 850;
}

.page-subtitle {
  margin-top: 8rpx;
  color: #8c765e;
  font-size: 24rpx;
}

.refresh-icon {
  width: 72rpx;
  height: 72rpx;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #8b2d22;
  color: #fff7e6;
  font-size: 34rpx;
  font-weight: 800;
}

.refresh-icon.spinning {
  opacity: 0.72;
}

.location-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
  margin-bottom: 22rpx;
  padding: 24rpx;
  border: 1rpx solid rgba(120, 72, 37, 0.12);
  border-radius: 10rpx;
  background: rgba(255, 251, 242, 0.92);
  box-shadow: 0 12rpx 30rpx rgba(70, 41, 22, 0.08);
}

.status-dot {
  width: 18rpx;
  height: 18rpx;
  flex-shrink: 0;
  border-radius: 50%;
  background: #c19148;
}

.status-success .status-dot {
  background: #355447;
}

.status-failed .status-dot {
  background: #8b2d22;
}

.location-copy {
  flex: 1;
  min-width: 0;
}

.location-title {
  color: #4b2b1f;
  font-size: 28rpx;
  font-weight: 850;
}

.manual-btn {
  flex-shrink: 0;
  padding: 12rpx 18rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #843429;
  font-size: 23rpx;
  font-weight: 700;
}

.map-panel,
.section-block {
  margin-bottom: 24rpx;
  border: 1rpx solid rgba(120, 72, 37, 0.12);
  border-radius: 10rpx;
  overflow: hidden;
  background: rgba(255, 251, 242, 0.9);
  box-shadow: 0 12rpx 30rpx rgba(70, 41, 22, 0.08);
}

.map-canvas {
  position: relative;
  width: 100%;
  height: 360rpx;
  overflow: hidden;
  background:
    radial-gradient(circle at 16% 18%, rgba(47, 91, 104, 0.18), transparent 20%),
    radial-gradient(circle at 82% 76%, rgba(193, 145, 72, 0.2), transparent 22%),
    linear-gradient(135deg, #eadbbf, #d5bd8a);
}

.map-road {
  position: absolute;
  background: rgba(121, 74, 38, 0.22);
}

.road-main {
  left: -10%;
  right: -10%;
  top: 51%;
  height: 10rpx;
  transform: rotate(-13deg);
}

.road-side {
  top: -10%;
  bottom: -10%;
  left: 56%;
  width: 9rpx;
  transform: rotate(20deg);
}

.road-ring {
  left: 23%;
  top: 22%;
  width: 340rpx;
  height: 210rpx;
  border: 8rpx solid rgba(121, 74, 38, 0.16);
  border-radius: 50%;
  background: transparent;
  transform: rotate(-18deg);
}

.map-water {
  position: absolute;
  right: -36rpx;
  bottom: -26rpx;
  width: 230rpx;
  height: 120rpx;
  border-radius: 50%;
  background: rgba(47, 91, 104, 0.2);
}

.user-marker,
.map-point {
  position: absolute;
  z-index: 3;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff7e6;
  font-weight: 850;
  box-shadow: 0 8rpx 20rpx rgba(66, 42, 23, 0.18);
}

.user-marker {
  width: 68rpx;
  height: 68rpx;
  background: #8b2d22;
  font-size: 24rpx;
}

.pulse {
  position: absolute;
  inset: -12rpx;
  border: 3rpx solid rgba(139, 45, 34, 0.28);
  border-radius: 50%;
}

.map-point {
  width: 48rpx;
  height: 48rpx;
  font-size: 22rpx;
}

.map-point.active {
  z-index: 5;
  width: 58rpx;
  height: 58rpx;
  border: 4rpx solid #fff7e6;
}

.map-point.cluster {
  background: #3f2c20;
}

.point-bubble {
  position: absolute;
  left: 50%;
  bottom: 64rpx;
  transform: translateX(-50%);
  max-width: 260rpx;
  padding: 10rpx 14rpx;
  border-radius: 10rpx;
  background: rgba(255, 248, 232, 0.96);
  color: #3f2c20;
  font-size: 22rpx;
  line-height: 1.3;
  white-space: nowrap;
  box-shadow: 0 8rpx 20rpx rgba(66, 42, 23, 0.16);
}

.point-service {
  background: #415646;
}

.point-spot {
  background: #2f5b68;
}

.point-parking,
.point-scenic {
  background: #2f5b68;
}

.point-toilet,
.point-checkin {
  background: #8b2d22;
}

.point-center,
.point-culture {
  background: #415646;
}

.point-food,
.point-performance {
  background: #c19148;
}

.map-active-card {
  display: flex;
  align-items: center;
  gap: 18rpx;
  padding: 18rpx 22rpx;
  border-top: 1rpx solid rgba(120, 72, 37, 0.1);
  background: #fff8e8;
}

.map-active-main {
  flex: 1;
  min-width: 0;
}

.map-active-title,
.map-active-meta {
  display: block;
}

.map-active-title {
  color: #3f2c20;
  font-size: 27rpx;
  font-weight: 850;
}

.map-active-meta {
  margin-top: 6rpx;
  color: #8c765e;
  font-size: 22rpx;
  line-height: 1.35;
}

.map-active-action {
  flex-shrink: 0;
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  background: #8b2d22;
  color: #fff7e6;
  font-size: 22rpx;
  font-weight: 800;
}

.map-caption {
  padding: 18rpx 22rpx;
  color: #7c6a57;
  font-size: 23rpx;
  line-height: 1.45;
}

.section-block {
  padding: 24rpx;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20rpx;
}

.section-title {
  color: #4b2b1f;
  font-size: 32rpx;
  font-weight: 850;
}

.section-count {
  padding: 8rpx 16rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #843429;
  font-size: 22rpx;
}

.service-row,
.spot-row {
  display: flex;
  align-items: center;
  padding: 22rpx 0;
  border-bottom: 1rpx solid rgba(120, 72, 37, 0.1);
}

.service-row.active,
.spot-row.active {
  margin: 0 -12rpx;
  padding-left: 12rpx;
  padding-right: 12rpx;
  border-radius: 10rpx;
  background: #fff3d9;
}

.service-row:last-child,
.spot-row:last-child {
  border-bottom: none;
}

.service-icon,
.spot-thumb {
  width: 74rpx;
  height: 74rpx;
  flex-shrink: 0;
  margin-right: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  color: #fff7e6;
  font-size: 26rpx;
  font-weight: 850;
}

.service-parking,
.spot-scenic {
  background: #2f5b68;
}

.service-toilet,
.spot-checkin {
  background: #8b2d22;
}

.service-center,
.spot-culture {
  background: #415646;
}

.service-food,
.spot-performance {
  background: #c19148;
}

.service-main,
.spot-main {
  flex: 1;
  min-width: 0;
}

.item-name {
  color: #3f2c20;
  font-size: 28rpx;
  font-weight: 800;
}

.item-meta {
  margin-top: 8rpx;
  color: #8c765e;
  font-size: 23rpx;
}

.item-desc {
  margin-top: 8rpx;
  color: #80694f;
  font-size: 23rpx;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.nav-plane {
  width: 58rpx;
  height: 58rpx;
  flex-shrink: 0;
  margin-left: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #8b2d22;
  color: #fff7e6;
  font-size: 25rpx;
  transform: rotate(-35deg);
}

.filter-scroll {
  width: 100%;
  margin-bottom: 12rpx;
  white-space: nowrap;
}

.filter-line {
  display: flex;
  flex-wrap: nowrap;
  gap: 12rpx;
  margin-bottom: 14rpx;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 116rpx;
  height: 58rpx;
  margin-right: 12rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: #f2e2c2;
  color: #6c4a2d;
  font-size: 24rpx;
}

.filter-chip.active {
  background: #8b2d22;
  color: #fff7e6;
  font-weight: 800;
}

.spot-title-line {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.spot-tag {
  flex-shrink: 0;
  padding: 6rpx 12rpx;
  border-radius: 999rpx;
  background: #efe0bd;
  color: #843429;
  font-size: 21rpx;
}

.empty-state {
  padding: 70rpx 20rpx;
  text-align: center;
  color: #8c765e;
}

.empty-state.compact {
  padding: 46rpx 20rpx;
  font-size: 25rpx;
}

.empty-illustration {
  width: 108rpx;
  height: 108rpx;
  margin: 0 auto 22rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #efe0bd;
  color: #8b2d22;
  font-size: 42rpx;
  font-weight: 850;
}

.empty-title {
  color: #4b2b1f;
  font-size: 28rpx;
  font-weight: 800;
}

.empty-desc {
  margin-top: 10rpx;
  color: #8c765e;
  font-size: 24rpx;
}

.location-actions {
  display: flex;
  align-items: center;
  gap: 10rpx;
}

.icon-btn-small {
  width: 56rpx;
  height: 56rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: #f3e3c4;
  color: #8c3228;
  font-size: 28rpx;
}

.icon-btn-small.spinning {
  animation: spin 1s linear infinite;
}

.icon-text {
  font-size: 28rpx;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.location-mask {
  position: fixed;
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}

.location-panel {
  width: 100%;
  max-height: 70vh;
  border-radius: 24rpx 24rpx 0 0;
  background: #fff;
  overflow: hidden;
}

.location-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 28rpx 32rpx;
  border-bottom: 1rpx solid rgba(120, 72, 37, 0.1);
}

.location-title-text {
  font-size: 32rpx;
  font-weight: 850;
  color: #4b2b1f;
}

.location-close {
  font-size: 40rpx;
  color: #8c765e;
}

.location-list {
  max-height: 60vh;
  overflow-y: auto;
  padding: 16rpx 0;
}

.location-item {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 24rpx 32rpx;
}

.location-item.active {
  background: rgba(140, 50, 40, 0.05);
}

.location-check {
  width: 40rpx;
  height: 40rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 2rpx solid #d4c5a8;
  color: #8c3228;
  font-size: 24rpx;
  font-weight: 800;
}

.location-item.active .location-check {
  background: #8c3228;
  border-color: #8c3228;
  color: #fff;
}

.location-info {
  flex: 1;
}

.location-name {
  display: block;
  font-size: 28rpx;
  font-weight: 800;
  color: #4b2b1f;
}

.location-coord {
  display: block;
  margin-top: 6rpx;
  font-size: 22rpx;
  color: #8c765e;
}
</style>
