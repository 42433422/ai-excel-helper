<template>
  <div
    v-if="props.visible"
    ref="rootRef"
    class="floating-chat-root"
    :class="{ dragging: isDragging }"
    :style="rootStyle"
  >
    <button
      class="floating-chat-toggle"
      type="button"
      :aria-expanded="isOpen ? 'true' : 'false'"
      aria-controls="floating-chat-panel"
      aria-label="打开智能对话悬浮窗"
      title="智能对话"
      @pointerdown="onDragStart"
      @click="toggleOpen"
    >
      <span class="floating-chat-logo-wrap" aria-hidden="true">
        <img class="floating-chat-logo" src="/brand-xc-logo.jpg" alt="" width="34" height="34" decoding="async" />
      </span>
      <span class="floating-chat-toggle-label">智能对话</span>
    </button>

    <div
      v-if="isOpen"
      id="floating-chat-panel"
      class="floating-chat-panel"
      role="dialog"
      aria-modal="false"
      aria-labelledby="floating-chat-title"
    >
      <div class="floating-chat-header" @pointerdown="onDragStart">
        <div class="floating-chat-title-wrap">
          <img class="floating-chat-title-logo" src="/brand-xc-logo.jpg" alt="" width="28" height="28" decoding="async" />
          <div>
            <div id="floating-chat-title" class="floating-chat-title">智能对话</div>
            <div class="floating-chat-subtitle">悬浮助手</div>
          </div>
        </div>
        <button class="floating-chat-close" type="button" aria-label="关闭智能对话悬浮窗" @click="isOpen = false">
          ×
        </button>
      </div>

      <div ref="messageListRef" class="floating-chat-messages">
        <div
          v-for="(msg, idx) in visibleMessages"
          :key="`${idx}-${msg.time}`"
          class="floating-chat-message"
          :class="msg.role"
        >
          <div class="floating-chat-bubble" v-html="sanitizeChatBubbleHtml(msg.content)"></div>
          <div class="floating-chat-time">{{ msg.time }}</div>
        </div>
        <div v-if="isLoading && !isStreamingReply" class="floating-chat-message ai">
          <div class="floating-chat-bubble">{{ loadingProgressText }}</div>
        </div>
      </div>

      <form class="floating-chat-input-row" @submit.prevent="submitMessage">
        <textarea
          v-model.trim="draft"
          class="floating-chat-input"
          rows="2"
          placeholder="输入消息..."
          :disabled="isLoading"
          @keydown.enter.exact.prevent="submitMessage"
        ></textarea>
        <button class="floating-chat-send" type="submit" :disabled="!draft || isLoading">
          发送
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useChatView } from '@/composables/useChatView'
import { sanitizeChatBubbleHtml } from '@/utils/sanitizeHtml'

const props = defineProps({
  visible: {
    type: Boolean,
    default: true
  }
})

function generateSessionId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2)
}

const storedSessionId = localStorage.getItem('ai_session_id')
const currentSessionId = ref(storedSessionId || generateSessionId())
if (!storedSessionId) {
  localStorage.setItem('ai_session_id', currentSessionId.value)
}

const PRO_INTENT_EXPERIENCE_KEY = 'xcagi_pro_intent_experience'
const proIntentExperienceEnabled = ref(localStorage.getItem(PRO_INTENT_EXPERIENCE_KEY) === '1')

const isOpen = ref(false)
const draft = ref('')
const messageListRef = ref<HTMLElement | null>(null)
const rootRef = ref<HTMLElement | null>(null)
const rootLeft = ref(0)
const rootTop = ref(0)
const isDragging = ref(false)
const hasDraggedSincePointerDown = ref(false)
const suppressNextToggleClick = ref(false)
const dragPointerId = ref<number | null>(null)
const dragStartClientX = ref(0)
const dragStartClientY = ref(0)
const dragStartLeft = ref(0)
const dragStartTop = ref(0)
const DRAG_THRESHOLD_PX = 4
const EDGE_PADDING_PX = 8
const ROOT_MARGIN_PX = 22

const {
  messages,
  isLoading,
  isStreamingReply,
  loadingProgressText,
  sendMessage,
} = useChatView({
  sessionId: currentSessionId,
  proIntentExperienceEnabled,
})

const visibleMessages = computed(() => messages.value.slice(-20))
const rootStyle = computed(() => ({
  left: `${rootLeft.value}px`,
  top: `${rootTop.value}px`
}))

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value))

const clampRootPosition = (left: number, top: number) => {
  const root = rootRef.value
  if (!root) {
    return { left, top }
  }
  const rect = root.getBoundingClientRect()
  const maxLeft = Math.max(EDGE_PADDING_PX, window.innerWidth - rect.width - EDGE_PADDING_PX)
  const maxTop = Math.max(EDGE_PADDING_PX, window.innerHeight - rect.height - EDGE_PADDING_PX)
  return {
    left: clamp(left, EDGE_PADDING_PX, maxLeft),
    top: clamp(top, EDGE_PADDING_PX, maxTop),
  }
}

const placeRootToBottomRight = async () => {
  await nextTick()
  const root = rootRef.value
  if (!root) return
  const rect = root.getBoundingClientRect()
  rootLeft.value = Math.max(EDGE_PADDING_PX, window.innerWidth - rect.width - ROOT_MARGIN_PX)
  rootTop.value = Math.max(EDGE_PADDING_PX, window.innerHeight - rect.height - ROOT_MARGIN_PX)
}

const keepRootInViewport = () => {
  const normalized = clampRootPosition(rootLeft.value, rootTop.value)
  rootLeft.value = normalized.left
  rootTop.value = normalized.top
}

const scrollToBottom = async () => {
  await nextTick()
  const el = messageListRef.value
  if (!el) return
  el.scrollTop = el.scrollHeight
}

const toggleOpen = async () => {
  if (suppressNextToggleClick.value) {
    suppressNextToggleClick.value = false
    return
  }
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    await scrollToBottom()
    keepRootInViewport()
  }
}

const onDragStart = (event: PointerEvent) => {
  if (event.button !== 0) return
  if (!props.visible) return
  const eventTarget = event.target as HTMLElement | null
  if (eventTarget?.closest('.floating-chat-close')) return
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  dragPointerId.value = event.pointerId
  dragStartClientX.value = event.clientX
  dragStartClientY.value = event.clientY
  dragStartLeft.value = rootLeft.value
  dragStartTop.value = rootTop.value
  isDragging.value = false
  hasDraggedSincePointerDown.value = false
  target.setPointerCapture(event.pointerId)
  target.addEventListener('pointermove', onDragMove)
  target.addEventListener('pointerup', onDragEnd)
  target.addEventListener('pointercancel', onDragEnd)
}

const onDragMove = (event: PointerEvent) => {
  if (dragPointerId.value !== event.pointerId) return
  const deltaX = event.clientX - dragStartClientX.value
  const deltaY = event.clientY - dragStartClientY.value
  if (!hasDraggedSincePointerDown.value) {
    const distance = Math.hypot(deltaX, deltaY)
    if (distance < DRAG_THRESHOLD_PX) return
    hasDraggedSincePointerDown.value = true
    isDragging.value = true
  }
  const normalized = clampRootPosition(dragStartLeft.value + deltaX, dragStartTop.value + deltaY)
  rootLeft.value = normalized.left
  rootTop.value = normalized.top
}

const onDragEnd = (event: PointerEvent) => {
  const target = event.currentTarget as HTMLElement | null
  if (target) {
    target.removeEventListener('pointermove', onDragMove)
    target.removeEventListener('pointerup', onDragEnd)
    target.removeEventListener('pointercancel', onDragEnd)
    if (dragPointerId.value !== null && target.hasPointerCapture(dragPointerId.value)) {
      target.releasePointerCapture(dragPointerId.value)
    }
  }
  if (hasDraggedSincePointerDown.value) {
    suppressNextToggleClick.value = true
  }
  dragPointerId.value = null
  isDragging.value = false
  hasDraggedSincePointerDown.value = false
}

const submitMessage = async () => {
  const text = draft.value.trim()
  if (!text || isLoading.value) return
  draft.value = ''
  await sendMessage(text)
  await scrollToBottom()
}

watch(
  () => messages.value.length,
  () => {
    if (isOpen.value) void scrollToBottom()
  }
)

watch(
  () => props.visible,
  (visibleNow) => {
    if (visibleNow) void placeRootToBottomRight()
  }
)

watch(isOpen, () => {
  void nextTick(() => {
    keepRootInViewport()
  })
})

onMounted(() => {
  void placeRootToBottomRight()
  window.addEventListener('resize', keepRootInViewport)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', keepRootInViewport)
})
</script>

<style scoped>
.floating-chat-root {
  position: fixed;
  max-width: calc(100vw - 16px);
  max-height: calc(100vh - 16px);
  z-index: 2600;
}

.floating-chat-root.dragging {
  user-select: none;
}

.floating-chat-toggle {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 54px;
  max-width: calc(100vw - 32px);
  padding: 8px 14px 8px 9px;
  border: 1px solid rgba(74, 144, 217, 0.36);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.94));
  color: #172033;
  box-shadow:
    0 14px 30px rgba(15, 76, 129, 0.18),
    0 4px 12px rgba(37, 99, 235, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transition:
    transform 180ms ease,
    box-shadow 180ms ease,
    border-color 180ms ease,
    background 180ms ease;
  touch-action: none;
}

.floating-chat-root:not(.dragging) .floating-chat-toggle {
  cursor: grab;
}

.floating-chat-root.dragging .floating-chat-toggle {
  cursor: grabbing;
}

.floating-chat-toggle:hover {
  transform: translateY(-2px);
  border-color: rgba(37, 99, 235, 0.58);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(219, 234, 254, 0.96));
  box-shadow:
    0 18px 36px rgba(15, 76, 129, 0.22),
    0 6px 16px rgba(37, 99, 235, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.96);
}

.floating-chat-toggle:focus-visible,
.floating-chat-close:focus-visible,
.floating-chat-send:focus-visible,
.floating-chat-input:focus-visible {
  outline: 3px solid rgba(24, 144, 255, 0.32);
  outline-offset: 2px;
}

.floating-chat-logo-wrap {
  width: 38px;
  height: 38px;
  border-radius: 12px;
  display: inline-grid;
  place-items: center;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(24, 144, 255, 0.42);
  box-shadow: 0 4px 10px rgba(15, 76, 129, 0.12);
  flex: 0 0 auto;
}

.floating-chat-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
  display: block;
}

.floating-chat-toggle-label {
  font-size: 14px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: 0.01em;
  white-space: nowrap;
  color: #1e3a8a;
}

.floating-chat-panel {
  position: absolute;
  right: 0;
  bottom: 68px;
  width: min(380px, calc(100vw - 28px));
  height: min(560px, calc(100vh - 110px));
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(147, 197, 253, 0.55);
  box-shadow:
    0 22px 52px rgba(15, 76, 129, 0.22),
    0 8px 18px rgba(37, 99, 235, 0.12);
}

.floating-chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 12px 10px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.98), rgba(255, 255, 255, 0.96));
  cursor: grab;
  touch-action: none;
}

.floating-chat-root.dragging .floating-chat-header {
  cursor: grabbing;
}

.floating-chat-title-wrap {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.floating-chat-title-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  object-fit: contain;
  border: 1px solid rgba(24, 144, 255, 0.36);
}

.floating-chat-title {
  font-size: 14px;
  line-height: 1.2;
  font-weight: 800;
  color: #172033;
}

.floating-chat-subtitle {
  margin-top: 2px;
  font-size: 11px;
  color: rgba(71, 85, 105, 0.72);
}

.floating-chat-close {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #64748b;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}

.floating-chat-close:hover {
  background: rgba(219, 234, 254, 0.72);
  color: #1e3a8a;
}

.floating-chat-messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px;
  background:
    radial-gradient(circle at 80% 0%, rgba(219, 234, 254, 0.7), transparent 36%),
    linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.floating-chat-message {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}

.floating-chat-message.user {
  align-items: flex-end;
}

.floating-chat-message.ai,
.floating-chat-message.task {
  align-items: flex-start;
}

.floating-chat-bubble {
  max-width: 86%;
  padding: 9px 11px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.55;
  color: #172033;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 4px 12px rgba(15, 76, 129, 0.06);
  overflow-wrap: anywhere;
}

.floating-chat-message.user .floating-chat-bubble {
  color: #ffffff;
  background: linear-gradient(135deg, #2563eb 0%, #1890ff 100%);
  border-color: rgba(37, 99, 235, 0.2);
}

.floating-chat-time {
  margin-top: 3px;
  padding: 0 4px;
  font-size: 10px;
  color: rgba(100, 116, 139, 0.78);
}

.floating-chat-input-row {
  display: flex;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
  background: rgba(255, 255, 255, 0.98);
}

.floating-chat-input {
  flex: 1;
  min-width: 0;
  resize: none;
  border: 1px solid rgba(203, 213, 225, 0.95);
  border-radius: 12px;
  padding: 9px 10px;
  font: inherit;
  font-size: 13px;
  line-height: 1.45;
  color: #172033;
  background: #ffffff;
}

.floating-chat-send {
  align-self: stretch;
  min-width: 58px;
  border: none;
  border-radius: 12px;
  background: #2563eb;
  color: #ffffff;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.floating-chat-send:disabled {
  cursor: not-allowed;
  opacity: 0.58;
}

@media (max-width: 767px) {
  .floating-chat-root {
    max-width: calc(100vw - 12px);
  }

  .floating-chat-toggle {
    min-height: 50px;
    padding: 7px;
  }

  .floating-chat-toggle-label {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .floating-chat-panel {
    bottom: 62px;
    height: min(520px, calc(100vh - 90px));
  }
}
</style>
