<template>
  <div class="wechat-login-panel">
    <div class="panel-content">
      <div class="qr-container">
        <div class="poly-dodeca">
          <div class="dodeca-face" v-for="i in 12" :key="i"></div>
        </div>
        <div class="scan-line"></div>
        <div v-if="!qrUrl" class="qr-placeholder">
          <div class="loading-spinner"></div>
          <div class="loading-text">加载中...</div>
        </div>
        <img v-else :src="qrUrl" alt="WeChat QR Code" class="qr-image" />
      </div>
      
      <div class="login-info">
        <div class="info-title">微信扫码登录</div>
        <div class="info-desc">请使用微信扫描二维码登录</div>
        <div class="status-indicator" :class="status">
          <span class="status-dot"></span>
          <span class="status-text">{{ statusText }}</span>
        </div>
      </div>
      
      <div v-if="status === 'success'" class="login-success">
        <div class="success-icon"><i class="fa fa-check-circle-o" aria-hidden="true"></i></div>
        <div class="success-text">登录成功</div>
        <div class="user-info">
          <div class="user-avatar">{{ userInfo?.name?.charAt(0) || '?' }}</div>
          <div class="user-name">{{ userInfo?.name }}</div>
        </div>
      </div>
      
      <div class="panel-actions">
        <button class="action-btn refresh" @click="handleRefresh">
          刷新二维码
        </button>
        <button v-if="status === 'success'" class="action-btn logout" @click="handleLogout">
          退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  qrUrl: {
    type: String,
    default: ''
  },
  status: {
    type: String,
    default: 'pending'
  },
  userInfo: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['refresh', 'logout', 'close'])

const statusText = computed(() => {
  switch (props.status) {
    case 'pending':
      return '等待扫码'
    case 'scanning':
      return '扫描中...'
    case 'confirming':
      return '等待确认...'
    case 'success':
      return '登录成功'
    case 'error':
      return '登录失败'
    default:
      return '未知状态'
  }
})

function handleRefresh() {
  emit('refresh')
}

function handleLogout() {
  emit('logout')
}
</script>

<style scoped>
.wechat-login-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
}

.panel-content {
  width: 100%;
  max-width: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.qr-container {
  position: relative;
  width: 200px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.poly-dodeca {
  position: absolute;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  animation: rotate3d 10s linear infinite;
}

.dodeca-face {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 2px solid rgba(0, 255, 255, 0.3);
  background: rgba(0, 255, 255, 0.05);
  transform-style: preserve-3d;
}

.dodeca-face:nth-child(1) { transform: rotateY(0deg) rotateX(0deg); }
.dodeca-face:nth-child(2) { transform: rotateY(30deg) rotateX(0deg); }
.dodeca-face:nth-child(3) { transform: rotateY(60deg) rotateX(0deg); }
.dodeca-face:nth-child(4) { transform: rotateY(90deg) rotateX(0deg); }
.dodeca-face:nth-child(5) { transform: rotateY(120deg) rotateX(0deg); }
.dodeca-face:nth-child(6) { transform: rotateY(150deg) rotateX(0deg); }
.dodeca-face:nth-child(7) { transform: rotateY(180deg) rotateX(0deg); }
.dodeca-face:nth-child(8) { transform: rotateY(210deg) rotateX(0deg); }
.dodeca-face:nth-child(9) { transform: rotateY(240deg) rotateX(0deg); }
.dodeca-face:nth-child(10) { transform: rotateY(270deg) rotateX(0deg); }
.dodeca-face:nth-child(11) { transform: rotateY(300deg) rotateX(0deg); }
.dodeca-face:nth-child(12) { transform: rotateY(330deg) rotateX(0deg); }

@keyframes rotate3d {
  from { transform: rotateZ(0deg); }
  to { transform: rotateZ(360deg); }
}

.scan-line {
  position: absolute;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.8), transparent);
  animation: scanLine 2s linear infinite;
}

@keyframes scanLine {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

.qr-placeholder {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 255, 255, 0.2);
  border-top-color: rgba(0, 255, 255, 0.8);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.7);
}

.qr-image {
  position: relative;
  z-index: 10;
  width: 180px;
  height: 180px;
  border-radius: 8px;
  background: white;
  padding: 10px;
}

.login-info {
  text-align: center;
}

.info-title {
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
  margin-bottom: 8px;
}

.info-desc {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.7);
  margin-bottom: 12px;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 20px;
  background: rgba(0, 255, 255, 0.1);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.8);
}

.status-indicator.scanning .status-dot,
.status-indicator.confirming .status-dot {
  animation: blink 1s infinite;
}

.status-indicator.success .status-dot {
  background: rgba(0, 255, 0, 0.8);
}

.status-indicator.error .status-dot {
  background: rgba(255, 0, 0, 0.8);
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.status-text {
  font-size: 13px;
  color: rgba(0, 255, 255, 0.8);
}

.login-success {
  text-align: center;
  padding: 20px;
}

.success-icon {
  font-size: 48px;
  color: rgba(0, 255, 0, 0.8);
  margin-bottom: 12px;
}

.success-text {
  font-size: 18px;
  font-weight: bold;
  color: rgba(0, 255, 0, 0.9);
  margin-bottom: 16px;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.user-avatar {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.2);
  border: 2px solid rgba(0, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.user-name {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.8);
}

.panel-actions {
  display: flex;
  gap: 12px;
  margin-top: 10px;
}

.action-btn {
  padding: 10px 20px;
  border: 1px solid rgba(0, 255, 255, 0.4);
  border-radius: 6px;
  background: rgba(0, 255, 255, 0.1);
  color: rgba(0, 255, 255, 0.9);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.action-btn:hover {
  background: rgba(0, 255, 255, 0.2);
  transform: scale(1.05);
}

.action-btn.logout {
  border-color: rgba(255, 0, 0, 0.4);
  background: rgba(255, 0, 0, 0.1);
  color: rgba(255, 0, 0, 0.9);
}

.action-btn.logout:hover {
  background: rgba(255, 0, 0, 0.2);
}
</style>
