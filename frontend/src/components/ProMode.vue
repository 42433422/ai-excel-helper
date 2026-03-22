<template>
  <div class="pro-mode-overlay" :class="overlayClasses" id="proModeOverlay">
    <div class="center-expand-box layer-2"></div>
    <div class="center-expand-box layer-3"></div>
    <div class="center-expand-box layer-4"></div>
    <div class="center-expand-box layer-5"></div>
    
    <div class="glow-pulse-ring r1"></div>
    <div class="glow-pulse-ring r2"></div>
    <div class="glow-pulse-ring r3"></div>
    
    <div class="energy-particles" id="energyParticles"></div>
    
    <div class="corner-flash tl"></div>
    <div class="corner-flash tr"></div>
    <div class="corner-flash bl"></div>
    <div class="corner-flash br"></div>

    <div class="falling-text-container" id="fallingTextContainer"></div>
    
    <div class="stark-grid"></div>
    
    <div class="light-source light-key"></div>
    <div class="light-source light-fill"></div>
    <div class="light-source light-back"></div>

    <div class="corner-decoration corner-tl"></div>
    <div class="corner-decoration corner-tr"></div>
    <div class="corner-decoration corner-bl"></div>
    <div class="corner-decoration corner-br"></div>

    <div class="data-stream">
      <div class="stream-line" style="left: 20%; animation-duration: 3s; animation-delay: 0s;"></div>
      <div class="stream-line" style="left: 40%; animation-duration: 4s; animation-delay: 1s;"></div>
      <div class="stream-line" style="left: 60%; animation-duration: 3.5s; animation-delay: 0.5s;"></div>
      <div class="stream-line" style="left: 80%; animation-duration: 4.5s; animation-delay: 1.5s;"></div>
    </div>

    <div class="scan-line"></div>

    <div class="pro-title">STARK INDUSTRIES</div>

    <div class="pro-buttons" style="position: absolute; top: 20px; right: 20px; display: flex; flex-direction: column; gap: 12px; align-items: center;">
      <button class="pro-exit-btn" @click="exitProMode" style="display: block; min-width: 220px;">EXIT PRO MODE</button>
      <button class="pro-exit-btn" @click="stepBack" style="display: block; min-width: 220px;" title="返回上一步">撤回</button>
    </div>

    <div class="jarvis-container">
      <div class="bloom-effect"></div>
      <div class="glow-orb"></div>
      <div class="core-polyhedron-container">
        <div class="core-poly-scale">
          <div class="core-polyhedron core-icosa">
            <div class="core-poly-face f1"></div>
            <div class="core-poly-face f2"></div>
            <div class="core-poly-face f3"></div>
            <div class="core-poly-face f4"></div>
            <div class="core-poly-face f5"></div>
            <div class="core-poly-face f6"></div>
            <div class="core-poly-face f7"></div>
            <div class="core-poly-face f8"></div>
          </div>
        </div>
      </div>

      <div class="wire-ring ring-1"></div>
      <div class="wire-ring ring-2 ring-dashed"></div>
      <div class="wire-ring ring-3 ring-tilt-1"></div>
      <div class="wire-ring ring-4 ring-tilt-2"></div>
      <div class="wire-ring ring-5"></div>
      <div class="wire-ring ring-6 ring-dashed"></div>
      <div class="wire-ring ring-7"></div>
      <div class="wire-ring ring-8 ring-dashed"></div>
      <div class="wire-ring ring-9 ring-tilt-1"></div>
                  <div class="wire-ring ring-10 ring-tilt-2"></div>

      <div class="code-ring-container" id="codeRingContainer"></div>
      <div class="icon-ring-container" id="iconRingContainer"></div>

      <div class="polyhedron poly-icosa">
        <div class="poly-face f1"></div>
        <div class="poly-face f2"></div>
        <div class="poly-face f3"></div>
        <div class="poly-face f4"></div>
        <div class="poly-face f5"></div>
      </div>

      <div class="polyhedron poly-octa">
        <div class="poly-face f1"></div>
        <div class="poly-face f2"></div>
        <div class="poly-face f3"></div>
        <div class="poly-face f4"></div>
        <div class="poly-face f5"></div>
        <div class="poly-face f6"></div>
      </div>

      <div class="polyhedron poly-tetra">
        <div class="poly-face f1"></div>
        <div class="poly-face f2"></div>
        <div class="poly-face f3"></div>
        <div class="poly-face f4"></div>
      </div>

      <div class="polyhedron poly-dodeca">
        <div class="poly-face f1"></div>
        <div class="poly-face f2"></div>
        <div class="poly-face f3"></div>
        <div class="poly-face f4"></div>
        <div class="poly-face f5"></div>
      </div>

      <div class="polyhedron poly-tetra2">
        <div class="poly-face f1"></div>
        <div class="poly-face f2"></div>
        <div class="poly-face f3"></div>
        <div class="poly-face f4"></div>
      </div>

      <div class="hologram-ring hr-1"></div>
      <div class="hologram-ring hr-2"></div>
      <div class="hologram-ring hr-3"></div>

      <div class="arc-reactor"></div>

      <div class="particle-layer">
        <div class="data-particle" style="--start-angle: 0deg; --orbit-radius: 80px; animation-duration: 8s;">1</div>
        <div class="data-particle" style="--start-angle: 45deg; --orbit-radius: 100px; animation-duration: 10s; animation-delay: 1s;">0</div>
        <div class="data-particle" style="--start-angle: 90deg; --orbit-radius: 120px; animation-duration: 12s; animation-delay: 2s;">1</div>
        <div class="data-particle" style="--start-angle: 135deg; --orbit-radius: 140px; animation-duration: 9s; animation-delay: 0.5s;">1</div>
        <div class="data-particle" style="--start-angle: 180deg; --orbit-radius: 160px; animation-duration: 11s; animation-delay: 1.5s;">0</div>
        <div class="data-particle" style="--start-angle: 225deg; --orbit-radius: 180px; animation-duration: 13s; animation-delay: 2.5s;">1</div>
        <div class="data-particle" style="--start-angle: 270deg; --orbit-radius: 200px; animation-duration: 8s; animation-delay: 0.8s;">0</div>
        <div class="data-particle" style="--start-angle: 315deg; --orbit-radius: 220px; animation-duration: 10s; animation-delay: 1.8s;">1</div>
        <div class="data-particle" style="--start-angle: 30deg; --orbit-radius: 90px; animation-duration: 7s; animation-delay: 3s;">0</div>
        <div class="data-particle" style="--start-angle: 60deg; --orbit-radius: 110px; animation-duration: 9s; animation-delay: 0.3s;">1</div>
        <div class="data-particle" style="--start-angle: 120deg; --orbit-radius: 130px; animation-duration: 11s; animation-delay: 1.2s;">1</div>
        <div class="data-particle" style="--start-angle: 150deg; --orbit-radius: 150px; animation-duration: 8s; animation-delay: 2.2s;">0</div>
        <div class="data-particle" style="--start-angle: 210deg; --orbit-radius: 170px; animation-duration: 10s; animation-delay: 0.7s;">1</div>
        <div class="data-particle" style="--start-angle: 240deg; --orbit-radius: 190px; animation-duration: 12s; animation-delay: 1.7s;">0</div>
        <div class="data-particle" style="--start-angle: 300deg; --orbit-radius: 210px; animation-duration: 9s; animation-delay: 2.7s;">1</div>
        <div class="data-particle" style="--start-angle: 330deg; --orbit-radius: 230px; animation-duration: 11s; animation-delay: 0.2s;">0</div>
      </div>
    </div>

    <div class="jarvis-monitor-float-wrap" id="jarvisMonitorFloatWrap" style="display: none;" aria-hidden="true"></div>

    <div class="tool-runtime-panel" id="toolRuntimePanel">
      <div class="tool-runtime-title">TOOL EXECUTION</div>
      <div class="tool-runtime-chip" id="runtimeToolChip">待命</div>
      <div class="tool-runtime-task" id="runtimeTaskText">等待工具调用...</div>
      <div class="tool-runtime-progress-track">
        <div class="tool-runtime-progress-fill" id="runtimeProgressBar"></div>
      </div>
      <div class="tool-runtime-meta">
        <span id="runtimeProgressPercent">0%</span>
        <span id="runtimeProgressStatus">IDLE</span>
      </div>
    </div>
    <div class="tool-extract-layer" id="toolExtractLayer"></div>

    <div class="pro-status">
      <div class="status-dot-anim"></div>
      <span>修茈 SYSTEM ONLINE</span>
      <span style="opacity: 0.5; margin-left: 20px;" id="jarvisStatusText">READY</span>
    </div>

    <div class="jarvis-chat-panel">
      <div class="jarvis-chat-header">修茈 ASSISTANT</div>
      <div class="jarvis-chat-messages" id="jarvisChatMessages"></div>
      <div class="jarvis-monitor-list-wrap" id="jarvisMonitorListWrap" style="display: none;">
        <div class="jarvis-monitor-list-header">监控列表</div>
        <div class="jarvis-monitor-list" id="jarvisMonitorList"></div>
      </div>
    </div>

    <div class="wechat-messages-panel" id="wechatMessagesPanel" style="display: none;">
      <button class="close-messages" id="closeWechatMessagesBtn" data-close-action="closeWechatMessages">&times;</button>
      <div class="messages-title">
        <span>💬 微信消息</span>
        <div class="messages-actions">
          <button class="msg-action-btn" id="logoutWechatBtn" title="退出登录">🚪</button>
          <button class="msg-action-btn" id="clearWechatMessagesBtn" title="清空消息">🗑️</button>
        </div>
      </div>
      <div class="messages-container" id="wechatMessagesList">
        <div class="loading-messages">加载中...</div>
      </div>
    </div>

    <div class="jarvis-voice-btn" id="jarvisVoiceBtn">
      <div class="voice-btn-inner" id="voiceBtnContent">
        <svg class="mic-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
        </svg>
        <span class="btn-text">按住说话 / 点击输入</span>
        <span class="voice-loading-text" id="voiceLoadingText" aria-live="polite"></span>
      </div>
      <input type="text" class="voice-input" id="voiceInput" placeholder="输入指令..." style="display: none;">
      <div class="voice-wave"></div>
    </div>

    <div class="pro-order-float-panel" id="proOrderFloatPanel" aria-hidden="true">
      <div class="pro-order-float-title">订单信息</div>
      <div class="pro-order-float-text" id="proOrderFloatText"></div>
      <div class="pro-order-float-download" id="proOrderFloatDownload" data-hidden="true">
        <a href="#" id="proOrderFloatDownloadLink" class="pro-order-download-btn">📄 下载发货单</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onBeforeUnmount, onMounted, watch } from 'vue'
import { useProMode } from '@/composables/useProMode'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:modelValue']);

const { stepBack: stepBackPro } = useProMode()

const isActive = ref(props.modelValue);
const isExiting = ref(false);
const isLegacyRuntime = ref(false)
let legacyObserver = null
let workModeObserver = null
let enterTimer = null
let exitTimer = null

const overlayClasses = computed(() => ({
  active: !isLegacyRuntime.value && isActive.value,
  exiting: !isLegacyRuntime.value && isExiting.value
}))

const detectLegacyRuntime = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode;
  return typeof legacyToggle === 'function'
}

isLegacyRuntime.value = detectLegacyRuntime()

const syncFromLegacyDom = () => {
  const overlay = document.getElementById('proModeOverlay');
  const active = document.body.classList.contains('pro-mode-active')
    || !!overlay?.classList.contains('active');
  isActive.value = active;
  emit('update:modelValue', active);
}

let legacyDetectionTimer = null

const enableLegacyBridge = () => {
  isLegacyRuntime.value = true

  const overlay = document.getElementById('proModeOverlay')
  legacyObserver = new MutationObserver(() => {
    syncFromLegacyDom()
  })

  legacyObserver.observe(document.body, { attributes: true, attributeFilter: ['class'] })
  if (overlay) {
    legacyObserver.observe(overlay, { attributes: true, attributeFilter: ['class', 'style'] })
  }
  syncFromLegacyDom()
}

watch(() => props.modelValue, (newVal) => {
  if (!isLegacyRuntime.value && newVal && detectLegacyRuntime()) {
    enableLegacyBridge()
    syncFromLegacyDom()
    return
  }

  if (isLegacyRuntime.value) {
    syncFromLegacyDom();
    return;
  }

  isActive.value = newVal;
  if (newVal) {
    document.body.classList.add('pro-mode-active');
    isExiting.value = false;
    if (exitTimer) {
      clearTimeout(exitTimer)
      exitTimer = null
    }
  } else {
    document.body.classList.remove('pro-mode-active');
    if (enterTimer) {
      clearTimeout(enterTimer)
      enterTimer = null
    }
    isExiting.value = true
    if (exitTimer) clearTimeout(exitTimer)
    exitTimer = window.setTimeout(() => {
      isExiting.value = false
    }, 400)
  }
});

const exitProMode = () => {
  const legacyToggle = window.__legacyToggleProMode || window.toggleProMode
  if (typeof legacyToggle === 'function') {
    legacyToggle()
    return
  }
  emit('update:modelValue', false)
}

const stepBack = () => {
  const legacyStepBack = window.stepBackProMode
  if (typeof legacyStepBack === 'function') {
    legacyStepBack()
    return
  }
  const workModeToggle = window.toggleWorkMode
  if (typeof workModeToggle === 'function' && document.getElementById('proModeOverlay')?.classList.contains('work-mode')) {
    workModeToggle()
    return
  }
  emit('update:modelValue', false)
}

onMounted(() => {
  isLegacyRuntime.value = detectLegacyRuntime()

  window.stepBackProMode = stepBackPro

  if (isLegacyRuntime.value) {
    enableLegacyBridge()
    return;
  }

  if (props.modelValue && detectLegacyRuntime()) {
    enableLegacyBridge()
    return
  }

  isActive.value = props.modelValue;
  if (props.modelValue) {
    document.body.classList.add('pro-mode-active');
  }

  legacyDetectionTimer = window.setInterval(() => {
    if (detectLegacyRuntime()) {
      if (legacyDetectionTimer) {
        clearInterval(legacyDetectionTimer)
        legacyDetectionTimer = null
      }
      enableLegacyBridge()
    }
  }, 300)
});

onBeforeUnmount(() => {
  if (legacyObserver) {
    legacyObserver.disconnect();
    legacyObserver = null;
  }
  if (legacyDetectionTimer) {
    clearInterval(legacyDetectionTimer)
    legacyDetectionTimer = null
  }
  if (enterTimer) clearTimeout(enterTimer)
  if (exitTimer) clearTimeout(exitTimer)
  enterTimer = null
  exitTimer = null
  isExiting.value = false

  // Clean up global function
  if (window.stepBackProMode === stepBackPro) {
    delete window.stepBackProMode
  }
});
</script>