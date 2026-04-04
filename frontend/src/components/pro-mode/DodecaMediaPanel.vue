<template>
  <div 
    class="dodeca-media-panel"
    :class="{ 'visible': visible, 'work-mode': isWorkMode }"
  >
    <div class="panel-header">
      <h3 class="panel-title">{{ title }}</h3>
      <div class="panel-counter">{{ currentIndex + 1 }} / {{ items.length }}</div>
      <button class="close-btn" @click="handleClose">×</button>
    </div>
    
    <div class="media-container">
      <div class="dodeca-wrapper">
        <div class="poly-dodeca">
          <div class="dodeca-face" v-for="i in 12" :key="i"></div>
        </div>
        <div class="scan-line"></div>
      </div>
      
      <div class="media-frame">
        <div v-if="isLoading" class="loading-state">
          <div class="loading-spinner"></div>
          <div class="loading-text">加载中...</div>
        </div>
        
        <img 
          v-else-if="currentItem && currentItem.type === 'image'"
          :src="currentItem.url" 
          :alt="currentItem.alt"
          class="media-image"
          @error="handleError"
        />
        
        <video 
          v-else-if="currentItem && currentItem.type === 'video'"
          :src="currentItem.url"
          class="media-video"
          controls
          @error="handleError"
        ></video>
        
        <div v-else class="empty-media">
          <div class="empty-icon">
            <i class="fa" :class="mediaType === 'image' ? 'fa-file-image-o' : 'fa-film'" aria-hidden="true"></i>
          </div>
          <div class="empty-text">暂无{{ mediaType === 'image' ? '图片' : '视频' }}</div>
        </div>
      </div>
    </div>
    
    <div v-if="items.length > 1" class="panel-navigation">
      <button 
        class="nav-btn prev"
        :disabled="currentIndex === 0"
        @click="handlePrev"
      >
        <i class="fa fa-chevron-left" aria-hidden="true"></i>
      </button>
      
      <div class="thumbnail-strip">
        <div 
          v-for="(item, index) in items" 
          :key="index"
          class="thumbnail"
          :class="{ 'active': index === currentIndex }"
          @click="handleThumbnailClick(index)"
        >
          <img v-if="item.thumbnail" :src="item.thumbnail" :alt="item.alt" />
          <div v-else class="thumbnail-placeholder">
            <i class="fa" :class="mediaType === 'image' ? 'fa-file-image-o' : 'fa-film'" aria-hidden="true"></i>
          </div>
        </div>
      </div>
      
      <button 
        class="nav-btn next"
        :disabled="currentIndex === items.length - 1"
        @click="handleNext"
      >
        <i class="fa fa-chevron-right" aria-hidden="true"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  items: {
    type: Array,
    default: () => []
  },
  mediaType: {
    type: String,
    default: 'image'
  },
  title: {
    type: String,
    default: '媒体浏览'
  },
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'change'])

const currentIndex = ref(0)
const isLoading = ref(false)
const hasError = ref(false)

const currentItem = computed(() => props.items[currentIndex.value] || null)

function handleClose() {
  emit('close')
}

function handlePrev() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    handleItemChange()
  }
}

function handleNext() {
  if (currentIndex.value < props.items.length - 1) {
    currentIndex.value++
    handleItemChange()
  }
}

function handleThumbnailClick(index) {
  currentIndex.value = index
  handleItemChange()
}

function handleItemChange() {
  isLoading.value = true
  hasError.value = false
  emit('change', currentIndex.value, currentItem.value)
  
  setTimeout(() => {
    isLoading.value = false
  }, 500)
}

function handleError() {
  hasError.value = true
  isLoading.value = false
}
</script>

<style scoped>
.dodeca-media-panel {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  width: 800px;
  max-height: 90vh;
  background: rgba(10, 14, 39, 0.98);
  border: 1px solid rgba(0, 255, 255, 0.5);
  border-radius: 16px;
  box-shadow: 0 0 40px rgba(0, 255, 255, 0.3);
  backdrop-filter: blur(20px);
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1100;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dodeca-media-panel.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translate(-50%, -50%) scale(1);
}

.work-mode .dodeca-media-panel {
  border-color: rgba(255, 0, 0, 0.5);
  box-shadow: 0 0 40px rgba(255, 0, 0, 0.3);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(0, 255, 255, 0.05);
  border-bottom: 1px solid rgba(0, 255, 255, 0.2);
}

.work-mode .panel-header {
  background: rgba(255, 0, 0, 0.05);
  border-bottom-color: rgba(255, 0, 0, 0.2);
}

.panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: bold;
  color: rgba(0, 255, 255, 0.9);
}

.work-mode .panel-title {
  color: rgba(255, 0, 0, 0.9);
}

.panel-counter {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.7);
}

.work-mode .panel-counter {
  color: rgba(255, 0, 0, 0.7);
}

.close-btn {
  background: transparent;
  border: none;
  color: rgba(0, 255, 255, 0.7);
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.work-mode .close-btn {
  color: rgba(255, 0, 0, 0.7);
}

.media-container {
  position: relative;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  overflow: hidden;
}

.dodeca-wrapper {
  position: absolute;
  width: 300px;
  height: 300px;
  pointer-events: none;
}

.poly-dodeca {
  position: absolute;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  animation: rotate3d 20s linear infinite;
  opacity: 0.3;
}

.dodeca-face {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid rgba(0, 255, 255, 0.3);
  background: rgba(0, 255, 255, 0.05);
  transform-style: preserve-3d;
}

.dodeca-face:nth-child(1) { transform: rotateY(0deg); }
.dodeca-face:nth-child(2) { transform: rotateY(30deg); }
.dodeca-face:nth-child(3) { transform: rotateY(60deg); }
.dodeca-face:nth-child(4) { transform: rotateY(90deg); }
.dodeca-face:nth-child(5) { transform: rotateY(120deg); }
.dodeca-face:nth-child(6) { transform: rotateY(150deg); }
.dodeca-face:nth-child(7) { transform: rotateY(180deg); }
.dodeca-face:nth-child(8) { transform: rotateY(210deg); }
.dodeca-face:nth-child(9) { transform: rotateY(240deg); }
.dodeca-face:nth-child(10) { transform: rotateY(270deg); }
.dodeca-face:nth-child(11) { transform: rotateY(300deg); }
.dodeca-face:nth-child(12) { transform: rotateY(330deg); }

@keyframes rotate3d {
  from { transform: rotateY(0deg); }
  to { transform: rotateY(360deg); }
}

.scan-line {
  position: absolute;
  width: 100%;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.5), transparent);
  animation: dodecaScanLine 3s linear infinite;
}

@keyframes dodecaScanLine {
  0% { top: 0; opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { top: 100%; opacity: 0; }
}

.work-mode .dodeca-face {
  border-color: rgba(255, 0, 0, 0.3);
  background: rgba(255, 0, 0, 0.05);
}

.work-mode .scan-line {
  background: linear-gradient(90deg, transparent, rgba(255, 0, 0, 0.5), transparent);
}

.media-frame {
  position: relative;
  z-index: 10;
  max-width: 90%;
  max-height: 90%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.media-image,
.media-video {
  max-width: 100%;
  max-height: 400px;
  border-radius: 8px;
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.2);
}

.work-mode .media-image,
.work-mode .media-video {
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.2);
}

.loading-state,
.empty-media {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 255, 255, 0.2);
  border-top-color: rgba(0, 255, 255, 0.8);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

.work-mode .loading-spinner {
  border-color: rgba(255, 0, 0, 0.2);
  border-top-color: rgba(255, 0, 0, 0.8);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text,
.empty-text {
  font-size: 14px;
  color: rgba(0, 255, 255, 0.7);
}

.work-mode .loading-text,
.work-mode .empty-text {
  color: rgba(255, 0, 0, 0.7);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.panel-navigation {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 255, 255, 0.2);
}

.work-mode .panel-navigation {
  border-top-color: rgba(255, 0, 0, 0.2);
}

.nav-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid rgba(0, 255, 255, 0.4);
  background: rgba(0, 255, 255, 0.1);
  color: rgba(0, 255, 255, 0.9);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.3s;
}

.nav-btn:hover:not(:disabled) {
  background: rgba(0, 255, 255, 0.2);
  transform: scale(1.1);
}

.nav-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.work-mode .nav-btn {
  border-color: rgba(255, 0, 0, 0.4);
  background: rgba(255, 0, 0, 0.1);
  color: rgba(255, 0, 0, 0.9);
}

.thumbnail-strip {
  flex: 1;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 8px;
}

.thumbnail {
  width: 60px;
  height: 60px;
  flex-shrink: 0;
  border-radius: 6px;
  border: 2px solid rgba(0, 255, 255, 0.3);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
}

.thumbnail:hover {
  border-color: rgba(0, 255, 255, 0.6);
  transform: scale(1.05);
}

.thumbnail.active {
  border-color: rgba(0, 255, 255, 0.9);
  box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
}

.thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.thumbnail-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 255, 255, 0.1);
  font-size: 24px;
}

.work-mode .thumbnail {
  border-color: rgba(255, 0, 0, 0.3);
}

.work-mode .thumbnail.active {
  border-color: rgba(255, 0, 0, 0.9);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.5);
}
</style>
