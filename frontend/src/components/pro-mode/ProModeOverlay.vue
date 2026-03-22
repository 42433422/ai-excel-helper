<template>
  <div 
    class="pro-mode-overlay"
    :class="{ 
      'active': isActive,
      'entering': isEntering,
      'exiting': isExiting,
      'work-mode': isWorkMode,
      'monitor-mode': isMonitorMode
    }"
  >
    <div class="corner-flash top-left" :class="{ 'entering': isEntering, 'exiting': isExiting }"></div>
    <div class="corner-flash top-right" :class="{ 'entering': isEntering, 'exiting': isExiting }"></div>
    <div class="corner-flash bottom-left" :class="{ 'entering': isEntering, 'exiting': isExiting }"></div>
    <div class="corner-flash bottom-right" :class="{ 'entering': isEntering, 'exiting': isExiting }"></div>
    
    <div class="center-expansion-box" :class="{ 'entering': isEntering, 'exiting': isExiting }"></div>
    
    <div class="halo-pulse-ring" :class="{ 'entering': isEntering }"></div>
    <div class="halo-pulse-ring" :class="{ 'entering': isEntering }" style="animation-delay: 0.1s"></div>
    <div class="halo-pulse-ring" :class="{ 'entering': isEntering }" style="animation-delay: 0.2s"></div>
    
    <FallingTextContainer 
      :is-entering="isEntering" 
      :is-exiting="isExiting" 
      :is-work-mode="isWorkMode"
    />
    <StarkGrid />
    
    <div class="jarvis-container">
      <JarvisCore 
        :is-speaking="isCoreSpeaking"
        :is-work-mode="isWorkMode"
        :is-monitor-mode="isMonitorMode"
        @click="handleCoreClick"
      />
      <WireRings :is-work-mode="isWorkMode" :is-breathing="isBreathing" />
      <EnergyParticles 
        :is-exploding="isEntering"
        :is-imploding="isExiting"
        :is-work-mode="isWorkMode"
      />
    </div>
    
    <JarvisVoiceButton 
      :is-recording="isRecording"
      :is-work-mode="isWorkMode"
      @click="handleVoiceButtonClick"
      @long-press="handleVoiceButtonLongPress"
    />
    
    <JarvisChatPanel 
      :messages="messages"
      :is-work-mode="isWorkMode"
      @message-send="handleMessageSend"
      @task-confirm="handleTaskConfirm"
      @task-ignore="handleTaskIgnore"
    />
    
    <JarvisStatus 
      :status-text="statusText"
      :is-recording="isRecording"
      :is-core-speaking="isCoreSpeaking"
      :is-work-mode="isWorkMode"
    />
    
    <button class="pro-exit-button" @click="handleExit">
      退出专业模式
    </button>
    
    <ProProductOrbitLayer 
      v-if="currentStage !== 'idle'"
      :stage="currentStage"
      :companies="companies"
      :products="products"
      :selected-company="selectedCompany"
      :selected-product="selectedProduct"
      :is-work-mode="isWorkMode"
      @company-select="handleCompanySelect"
      @product-select="handleProductSelect"
      @reset="handleReset"
    />
    
    <CodeRings 
      v-if="currentStage === 'idle'"
      :tools="tools"
      :is-work-mode="isWorkMode"
      :frozen-ring="frozenRing"
      @tool-select="handleToolSelect"
    />
    
    <IconRingContainer 
      v-if="currentStage === 'idle'"
      :is-work-mode="isWorkMode"
      @import-click="handleImportClick"
      @export-click="handleExportClick"
    />
    
    <ToolRuntimePanel 
      v-if="runningTool"
      :tool="runningTool"
      :progress="toolProgress"
      :status="toolStatus"
      :is-work-mode="isWorkMode"
    />
    
    <WorkModeMonitor 
      v-if="isWorkMode"
      :contacts="workModeContacts"
      :is-task-acquisition="isTaskAcquisition"
      :current-order="currentOrder"
      :is-work-mode="isWorkMode"
      @contact-click="handleContactClick"
      @message-send="handleWorkModeMessageSend"
      @download-order="handleOrderDownload"
      @reset-task="handleResetTaskAcquisition"
    />
    
    <MonitorModePanel 
      v-if="isMonitorMode"
      :is-monitor-mode="isMonitorMode"
      @close="handleMonitorModeClose"
      @view-history="handleViewHistory"
    />
    
    <ProFeatureWidget 
      v-if="showFeatureWidget"
      :active-panel="activeFeaturePanel"
      :is-work-mode="isWorkMode"
      @panel-close="handleFeatureWidgetClose"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useProMode } from '@/composables/useProMode'
import { useJarvisChat } from '@/composables/useJarvisChat'
import FallingTextContainer from './FallingTextContainer.vue'
import StarkGrid from './StarkGrid.vue'
import JarvisCore from './JarvisCore.vue'
import WireRings from './WireRings.vue'
import EnergyParticles from './EnergyParticles.vue'
import JarvisVoiceButton from './JarvisVoiceButton.vue'
import JarvisChatPanel from './JarvisChatPanel.vue'
import JarvisStatus from './JarvisStatus.vue'
import ProProductOrbitLayer from './ProProductOrbitLayer.vue'
import CodeRings from './CodeRings.vue'
import IconRingContainer from './IconRingContainer.vue'
import ToolRuntimePanel from './ToolRuntimePanel.vue'
import WorkModeMonitor from './WorkModeMonitor.vue'
import MonitorModePanel from './MonitorModePanel.vue'
import ProFeatureWidget from '../pro-feature-widget/ProFeatureWidget.vue'

const {
  isActive,
  isTransitioning,
  isWorkMode,
  isMonitorMode,
  currentStage,
  selectedCompany,
  selectedProduct,
  coreScale,
  orbitLayerScale,
  exitProMode,
  exitMonitorMode,
  enterMonitorMode,
  resetTransientState
} = useProMode()

const {
  messages,
  isRecording,
  isCoreSpeaking,
  statusText,
  sendMessage,
  addMessage,
  clearMessages
} = useJarvisChat()

const isEntering = computed(() => isTransitioning.value && isActive.value)
const isExiting = computed(() => isTransitioning.value && !isActive.value)
const isBreathing = computed(() => isCoreSpeaking.value || isActive.value)

const companies = ref([])
const products = ref([])
const tools = ref([])
const workModeContacts = ref([])
const frozenRing = ref(null)
const runningTool = ref(null)
const toolProgress = ref(0)
const toolStatus = ref('idle')
const showFeatureWidget = ref(false)
const activeFeaturePanel = ref('none')
const isTaskAcquisition = ref(false)
const currentOrder = ref(null)

function handleCoreClick() {
  resetTransientState()
}

function handleVoiceButtonClick() {
  console.log('Voice button clicked')
}

function handleVoiceButtonLongPress() {
  console.log('Voice button long pressed')
}

function handleMessageSend(message) {
  sendMessage(message)
}

function handleTaskConfirm(task) {
  console.log('Task confirmed:', task)
}

function handleTaskIgnore(task) {
  console.log('Task ignored:', task)
}

function handleExit() {
  exitProMode()
  clearMessages()
}

function handleCompanySelect(company) {
  console.log('Company selected:', company)
}

function handleProductSelect(product) {
  console.log('Product selected:', product)
}

function handleReset() {
  resetTransientState()
}

function handleToolSelect(tool) {
  console.log('Tool selected:', tool)
}

function handleImportClick() {
  console.log('Import clicked')
}

function handleExportClick() {
  console.log('Export clicked')
}

function handleContactClick(contact) {
  console.log('Contact clicked:', contact)
}

function handleWorkModeMessageSend(contactId, message) {
  console.log('Send message:', contactId, message)
}

function handleOrderDownload(orderId) {
  console.log('Download order:', orderId)
}

function handleResetTaskAcquisition() {
  isTaskAcquisition.value = false
  currentOrder.value = null
}

function handleFeatureWidgetClose() {
  showFeatureWidget.value = false
  activeFeaturePanel.value = 'none'
}

function handleMonitorModeClose() {
  exitMonitorMode()
}

function handleViewHistory() {
  console.log('View history')
}
</script>

<style scoped>
@import '@/styles/pro-mode.css';
@import '@/styles/animations.css';
@import '@/styles/gpu-optimizations.css';
</style>
