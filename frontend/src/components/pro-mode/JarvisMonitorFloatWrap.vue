<template>
  <div class="jarvis-monitor-float-wrap" :class="{ 'task-acquiring': isTaskAcquiring }">
    <div 
      v-for="(contact, index) in contacts" 
      :key="contact.id"
      class="monitor-float-contact"
      :style="contactStyle(index)"
    >
      <div 
        class="float-avatar"
        :class="{ 'unread': contact.unreadCount > 0 }"
      >
        {{ contact.name?.charAt(0) || '?' }}
      </div>
      <div class="float-name">{{ contact.name }}</div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  contacts: {
    type: Array,
    default: () => []
  },
  isTaskAcquiring: {
    type: Boolean,
    default: false
  },
  radius: {
    type: Number,
    default: 420
  }
})

const emit = defineEmits(['contactClick'])

function contactStyle(index) {
  const total = props.contacts.length
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2
  const x = Math.cos(angle) * props.radius
  const y = Math.sin(angle) * props.radius
  
  return {
    transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
    animationDelay: `${index * 0.1}s`
  }
}

function handleContactClick(contact) {
  emit('contactClick', contact)
}
</script>

<style scoped>
.jarvis-monitor-float-wrap {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 1000px;
  height: 1000px;
  pointer-events: none;
  transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

.jarvis-monitor-float-wrap.task-acquiring {
  transform: translate(-50%, -50%) translateX(-180px);
}

.monitor-float-contact {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: monitorFloatBob 3s ease-in-out infinite;
}

.monitor-float-contact:hover {
  transform: translate(-50%, -50%) scale(1.2) !important;
}

.float-avatar {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: rgba(255, 0, 0, 0.2);
  border: 2px solid rgba(255, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.9);
  box-shadow: 0 0 15px rgba(255, 0, 0, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.float-avatar.unread {
  background: rgba(255, 0, 0, 0.3);
  border-color: rgba(255, 0, 0, 0.6);
  box-shadow: 0 0 20px rgba(255, 0, 0, 0.5);
  animation: pulse 1s ease-in-out infinite;
}

.float-name {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  text-shadow: 0 0 5px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

@keyframes monitorFloatBob {
  0%, 100% {
    transform: translate(-50%, -50%) translateY(0);
  }
  50% {
    transform: translate(-50%, -50%) translateY(-5px);
  }
}

.jarvis-monitor-float-wrap.task-acquiring .monitor-float-contact {
  animation-delay: 0s;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 15px rgba(255, 0, 0, 0.3);
  }
  50% {
    transform: scale(1.1);
    box-shadow: 0 0 25px rgba(255, 0, 0, 0.5);
  }
}
</style>
