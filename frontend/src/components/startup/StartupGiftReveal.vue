<script setup lang="ts">
import { computed, watch } from 'vue'
import { useStartupRevealStore } from '@/stores/startupReveal'

const props = defineProps<{
  primaryModName?: string
  modNames?: string[]
}>()

const emit = defineEmits<{
  unboxed: []
}>()

const reveal = useStartupRevealStore()

const steps = [
  { id: 1, label: '准备环境' },
  { id: 2, label: '发现扩展' },
  { id: 3, label: '生成导航' },
]

const modHint = computed(() => {
  const names = props.modNames || []
  if (names.length > 1) return `已发现 ${names.length} 个扩展包`
  if (props.primaryModName) return props.primaryModName
  return ''
})

function onUnboxAnimationEnd(e: AnimationEvent) {
  if (e.animationName !== 'giftLidOpen') return
  reveal.notifyUnboxed()
  emit('unboxed')
}

watch(
  () => reveal.isUnboxing,
  (open) => {
    if (!open) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) {
      reveal.notifyUnboxed()
      emit('unboxed')
    }
  },
)
</script>

<template>
  <div class="startup-gift" aria-live="polite">
    <ol class="startup-gift-steps">
      <li
        v-for="s in steps"
        :key="s.id"
        class="startup-gift-step"
        :class="{
          active: reveal.activeStep === s.id,
          done: reveal.activeStep > s.id || reveal.phase === 'unboxing' || reveal.phase === 'done',
        }"
      >
        <span class="startup-gift-step-num">{{ s.id }}</span>
        <span class="startup-gift-step-label">{{ s.label }}</span>
      </li>
    </ol>

    <div
      class="gift-box"
      :class="{ 'gift-box--open': reveal.isUnboxing || reveal.phase === 'done' }"
    >
      <div class="gift-box-glow" aria-hidden="true" />
      <div class="gift-lid" @animationend="onUnboxAnimationEnd" />
      <div class="gift-base">
        <span v-if="modHint && !reveal.isUnboxing" class="gift-base-label">{{ modHint }}</span>
        <span v-else-if="reveal.isUnboxing" class="gift-base-label">正在展开导航…</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.startup-gift {
  width: 100%;
  max-width: 320px;
  margin: 1rem auto 0.5rem;
}

.startup-gift-steps {
  list-style: none;
  margin: 0 0 1.25rem;
  padding: 0;
  display: flex;
  justify-content: space-between;
  gap: 0.35rem;
}

.startup-gift-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  opacity: 0.45;
  transition: opacity 0.25s ease;
}

.startup-gift-step.active,
.startup-gift-step.done {
  opacity: 1;
}

.startup-gift-step-num {
  width: 1.5rem;
  height: 1.5rem;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
}

.startup-gift-step.done .startup-gift-step-num {
  background: rgba(74, 222, 128, 0.2);
  border-color: rgba(74, 222, 128, 0.55);
  color: #4ade80;
}

.startup-gift-step.active .startup-gift-step-num {
  border-color: rgba(255, 255, 255, 0.65);
  color: #fff;
}

.startup-gift-step-label {
  font-size: 0.68rem;
  color: rgba(255, 255, 255, 0.55);
  text-align: center;
  line-height: 1.2;
}

.gift-box {
  position: relative;
  width: 140px;
  height: 110px;
  margin: 0 auto;
  perspective: 480px;
}

.gift-box-glow {
  position: absolute;
  inset: -20% -10% -30%;
  background: radial-gradient(ellipse at center, rgba(74, 222, 128, 0.35), transparent 70%);
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
}

.gift-box--open .gift-box-glow {
  opacity: 1;
}

.gift-lid {
  position: absolute;
  top: 0;
  left: 8%;
  width: 84%;
  height: 28px;
  background: linear-gradient(180deg, #c2410c 0%, #9a3412 100%);
  border-radius: 4px 4px 2px 2px;
  transform-origin: top center;
  z-index: 2;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.35);
}

.gift-lid::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -6px;
  width: 18px;
  height: 100%;
  margin-left: -9px;
  background: #ea580c;
  border-radius: 2px;
}

.gift-box--open .gift-lid {
  animation: giftLidOpen 0.75s ease-in-out forwards;
}

.gift-base {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 72px;
  background: linear-gradient(180deg, #b91c1c 0%, #7f1d1d 100%);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  box-shadow: inset 0 2px 0 rgba(255, 255, 255, 0.12);
}

.gift-base::before {
  content: '';
  position: absolute;
  left: 50%;
  top: 0;
  bottom: 0;
  width: 20px;
  margin-left: -10px;
  background: rgba(234, 88, 12, 0.85);
}

.gift-base-label {
  position: relative;
  z-index: 1;
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.9);
  text-align: center;
  line-height: 1.3;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes giftLidOpen {
  0% {
    transform: rotateX(0deg) translateY(0);
  }
  40% {
    transform: rotateX(-110deg) translateY(-8px);
  }
  100% {
    transform: rotateX(-125deg) translateY(-14px);
    opacity: 0.85;
  }
}

@media (prefers-reduced-motion: reduce) {
  .gift-box--open .gift-lid {
    animation: none;
    transform: rotateX(-125deg) translateY(-14px);
    opacity: 0.5;
  }
}
</style>
