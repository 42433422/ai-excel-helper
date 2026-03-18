<template>
  <div class="icon-ring-container" :class="{ 'work-mode': isWorkMode }">
    <button 
      class="icon-ring-btn excel-import"
      @click="handleImportClick"
      title="导入Excel"
    >
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M14 2H6a2 2 0 0 0-2 2v2a2 2 0 0 2 2zm-2 0a2 2 0 0-2 2v4a2 2 0 0 2 2zm2 0a2 2 0 0 2 2v2a2 2 0 0 2 2zm2-2 0a2 2 0 0 2 2v4a2 2 0 0 2 2zm-2 0a2 2 0 0-2 2v2a2 2 0 0 2 2zm-2 0a2 2 0 0 2 2v2a2 2 0 0 2 2z" fill="currentColor"/>
      </svg>
    </button>
    
    <button 
      class="icon-ring-btn excel-export"
      @click="handleExportClick"
      title="导出Excel"
    >
      <svg viewBox="0 0 24 24" fill="none">
        <path d="M14 2H6a2 2 0 0 0-2 2v2a2 2 0 0 2 2zm-2 0a2 2 0 0-2 2v4a2 2 0 0 2 2zm2 0a2 2 0 0 2 2v2a2 2 0 0 2 2zm2 0a2 2 0 0 2 2v2a2 2 0 0 2 2zm2 0a2 2 0 0 2 2v2a2 2 0 0 2 2zm-2 0a2 2 0 0 2 2v2a2 2 0 0 2 2z" fill="currentColor"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
const props = defineProps({
  isWorkMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['importClick', 'exportClick'])

function handleImportClick() {
  emit('importClick')
}

function handleExportClick() {
  emit('exportClick')
}
</script>

<style scoped>
.icon-ring-container {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  gap: 20px;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.icon-ring-btn {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: rgba(0, 255, 255, 0.1);
  border: 2px solid rgba(0, 255, 255, 0.3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
  backdrop-filter: blur(5px);
}

.icon-ring-btn:hover {
  background: rgba(0, 255, 255, 0.2);
  transform: scale(1.1);
  box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
}

.icon-ring-btn svg {
  width: 30px;
  height: 30px;
  fill: rgba(0, 255, 255, 0.8);
  transition: fill 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.work-mode .icon-ring-btn {
  background: rgba(255, 0, 0, 0.1);
  border-color: rgba(255, 0, 0, 0.3);
  box-shadow: 0 0 15px rgba(255, 0, 0, 0.2);
}

.work-mode .icon-ring-btn:hover {
  background: rgba(255, 0, 0, 0.2);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
}

.work-mode .icon-ring-btn svg {
  fill: rgba(255, 0, 0, 0.8);
}

@keyframes iconRingBtnBreath {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 15px rgba(0, 255, 255, 0.2);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 20px rgba(0, 255, 255, 0.3);
  }
}

.work-mode @keyframes iconRingBtnBreath {
  0%, 100% {
    box-shadow: 0 0 15px rgba(255, 0, 0, 0.2);
  }
  50% {
    box-shadow: 0 0 20px rgba(255, 0, 0, 0.3);
  }
}
</style>
