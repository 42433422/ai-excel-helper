<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from './components/MainLayout.vue'
import ProMode from './components/ProMode.vue'

const route = useRoute()
const router = useRouter()
const isProMode = ref(false)

let switchViewEvent = null

const hasLegacyProModeRuntime = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
  return typeof legacyToggle === 'function'
}

const readProModeStateFromDom = () => {
  const overlay = document.getElementById('proModeOverlay')
  const bodyActive = document.body.classList.contains('pro-mode-active')
  const overlayActive = !!overlay?.classList.contains('active')
  const overlayVisible = !!overlay && overlay.style.display !== 'none'
  const toggle = document.getElementById('proModeToggle')
  const toggleActive = !!toggle?.classList.contains('active')
  return bodyActive || (overlayActive && overlayVisible) || toggleActive
}

const syncProModeStateSoon = () => {
  requestAnimationFrame(() => {
    isProMode.value = readProModeStateFromDom()
  })
  setTimeout(() => {
    isProMode.value = readProModeStateFromDom()
  }, 350)
  setTimeout(() => {
    isProMode.value = readProModeStateFromDom()
  }, 1650)
}

const handleToggleProMode = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
  if (typeof legacyToggle === 'function') {
    legacyToggle()
    syncProModeStateSoon()
    return
  }
  isProMode.value = !isProMode.value
}

let proModeObserver = null
let onToggleProModeEvent = null

onMounted(() => {
  const syncProModeFromDom = () => {
    isProMode.value = readProModeStateFromDom()
  }

  window.setProModeEnabled = (enabled) => {
    const shouldEnable = !!enabled
    const active = readProModeStateFromDom()
    if (shouldEnable === active) {
      isProMode.value = active
      return
    }
    if (hasLegacyProModeRuntime()) {
      const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
      legacyToggle()
      syncProModeStateSoon()
    } else {
      isProMode.value = shouldEnable
    }
  }

  onToggleProModeEvent = () => {
    handleToggleProMode()
  }

  window.addEventListener('xcagi:toggle-pro-mode', onToggleProModeEvent)

  proModeObserver = new MutationObserver(() => {
    syncProModeFromDom()
  })
  proModeObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
  const overlay = document.getElementById('proModeOverlay')
  if (overlay) {
    proModeObserver.observe(overlay, { attributes: true, attributeFilter: ['class', 'style'] })
  }
  syncProModeFromDom()

  const bindOnce = (id, eventName, handler) => {
    const el = document.getElementById(id)
    if (!el) return
    if (el.getAttribute('data-xcagi-bound') === '1') return
    el.setAttribute('data-xcagi-bound', '1')
    el.addEventListener(eventName, handler)
  }

  bindOnce('fileUploadEntry', 'click', () => {
    try {
      if (typeof window.openImportWindow === 'function') {
        console.log('[xcagi] click fileUploadEntry -> openImportWindow()')
        window.openImportWindow()
      } else {
        console.warn('[xcagi] openImportWindow not found on window')
      }
    } catch (err) {
      console.warn('[xcagi] fileUploadEntry click failed:', err)
    }
  })

  bindOnce('chooseFileBtn', 'click', () => {
    const fileInput = document.getElementById('fileInput')
    if (fileInput) fileInput.click()
  })

  switchViewEvent = (event) => {
    const view = event.detail?.view
    if (view) {
      console.log('[App] xcagi:switch-view received, navigating to:', view)
      router.push({ name: view })
    }
  }
  window.addEventListener('xcagi:switch-view', switchViewEvent)
})

onBeforeUnmount(() => {
  if (proModeObserver) {
    proModeObserver.disconnect()
    proModeObserver = null
  }
  if (onToggleProModeEvent) {
    window.removeEventListener('xcagi:toggle-pro-mode', onToggleProModeEvent)
    onToggleProModeEvent = null
  }
  if (switchViewEvent) {
    window.removeEventListener('xcagi:switch-view', switchViewEvent)
    switchViewEvent = null
  }
  if (window.setProModeEnabled) {
    delete window.setProModeEnabled
  }
})
</script>

<template>
  <div class="transition-overlay" id="transitionOverlay"></div>

  <div class="preview-float-window" id="previewFloatWindow">
    <div class="preview-header">
      <h4>📺 媒体预览</h4>
      <button class="preview-close" id="previewCloseBtn" data-close-action="closePreviewWindow">&times;</button>
    </div>
    <div class="preview-content">
      <div class="preview-media" id="previewMedia">
        <div class="preview-placeholder">暂无预览内容</div>
      </div>
    </div>
  </div>

  <div class="progress-panel" id="progressPanel">
    <div class="progress-panel-header">
      <div class="progress-title">任务进度</div>
      <button class="progress-close" id="progressCloseBtn" data-close-action="hideProgress">&times;</button>
    </div>
    <div class="progress-info">
      <span class="progress-status">处理中...</span>
      <span class="progress-percent" id="progressPercent">0%</span>
    </div>
    <div class="progress-bar-wrapper">
      <div class="progress-bar-fill" id="progressBarFill" style="width: 0%;"></div>
    </div>
    <div class="progress-task" id="progressTask">正在初始化任务...</div>
  </div>

  <div class="file-upload-entry" id="fileUploadEntry">
    <span class="entry-icon">📁</span>
    <span class="entry-text">上传文件</span>
  </div>

  <div class="import-float-window" id="importFloatWindow">
    <div class="import-header">
      <h4>📁 导入文件</h4>
      <button class="import-close" id="importCloseBtn" data-close-action="closeImportWindow">&times;</button>
    </div>
    <div class="import-content">
      <div class="drop-zone" id="dropZone">
        <div class="drop-zone-icon">📂</div>
        <div class="drop-zone-text">拖拽文件到此处或点击选择</div>
        <div class="drop-zone-hint">支持 Excel、CSV、图片等文件</div>
      </div>
      <input type="file" class="file-input" id="fileInput" multiple accept="*/*">
      <div class="import-actions">
        <button class="btn btn-primary" id="chooseFileBtn">选择文件</button>
        <button class="btn btn-success" id="openCameraBtn">📷 拍照识别</button>
        <button class="btn btn-secondary" id="cancelImportBtn" data-close-action="closeImportWindow">取消</button>
      </div>
      <div class="camera-panel" id="cameraPanel" style="display: none;">
        <video id="cameraVideo" autoplay playsinline></video>
        <canvas id="cameraCanvas" style="display: none;"></canvas>
        <div class="camera-buttons">
          <button class="btn btn-primary" id="capturePhotoBtn">拍照</button>
          <button class="btn btn-secondary" id="closeCameraBtn" data-close-action="closeCamera">关闭</button>
        </div>
      </div>
      <div class="import-progress" id="importProgress">
        <div class="progress-bar-container">
          <div class="progress-bar" id="progressBar"></div>
        </div>
        <div class="progress-text">
          <span id="progressText">读取中...</span>
          <span id="progressPercent">0%</span>
        </div>
      </div>
      <div class="import-status" id="importStatus"></div>
    </div>
  </div>

  <div class="import-float-window" id="labelsExportWindow">
    <div class="import-header">
      <h4>🏷️ 商标导出</h4>
      <button class="import-close" id="labelsExportCloseBtn" type="button" title="关闭">&times;</button>
    </div>
    <div class="import-content">
      <div id="labelsExportList" class="labels-export-list">
        <p class="labels-export-hint">加载中...</p>
      </div>
      <div class="import-actions" style="margin-top: 12px;">
        <button class="btn btn-secondary" id="labelsExportCloseBtn2" type="button">关闭</button>
      </div>
    </div>
  </div>

  <div class="import-float-window" id="printPanelWindow">
    <div class="import-header">
      <h4>🖨️ 标签打印</h4>
      <button class="import-close" id="printPanelCloseBtn" type="button" title="关闭">&times;</button>
    </div>
    <div class="import-content">
      <div id="printPanelStatus" class="labels-export-hint">正在连接打印机...</div>
      <div id="printPanelProgress" class="print-panel-progress" style="display:none; margin:10px 0;"></div>
      <div id="printPanelResults" class="print-panel-results" style="margin:10px 0; max-height:240px; overflow-y:auto;"></div>
      <div class="import-actions" style="margin-top: 12px;">
        <button class="btn btn-primary" id="printPanelStartBtn" type="button">开始打印</button>
        <button class="btn btn-secondary" id="printPanelCloseBtn2" type="button">关闭</button>
      </div>
    </div>
  </div>

  <div id="labelFloatPreviews" class="label-float-previews hidden" aria-hidden="true"></div>

  <div id="labelPreviewModal" class="label-preview-modal hidden" aria-hidden="true">
    <div class="label-preview-modal-backdrop"></div>
    <div class="label-preview-modal-content">
      <img id="labelPreviewModalImg" src="" alt="标签预览" />
      <div class="label-preview-modal-actions">
        <a id="labelPreviewModalDownload" href="" download="" class="btn btn-primary">下载标签</a>
        <button type="button" class="btn btn-secondary label-preview-modal-close">关闭</button>
      </div>
    </div>
  </div>

  <ProMode v-model="isProMode" />

  <MainLayout
    :is-pro-mode="isProMode"
    @toggle-pro-mode="handleToggleProMode"
  >
    <router-view />
  </MainLayout>
</template>

<style>
</style>
