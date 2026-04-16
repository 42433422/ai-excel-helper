<template>
  <div class="workflow-demo">
    <h2>真实电话业务员工作流示例</h2>
    
    <div class="workflow-section">
      <h3>员工开关控制</h3>
      <div class="employee-list">
        <WorkflowEmployeeRow
          label="真实电话业务员"
          employee-id="real_phone"
          v-model="isRealPhoneActive"
          @change="handleEmployeeChange"
          @toggle="handleEmployeeToggle"
        />
        
        <WorkflowEmployeeRow
          label="在线客服业务员"
          employee-id="online_service"
          v-model="isOnlineServiceActive"
          @change="handleEmployeeChange"
        />
        
        <WorkflowEmployeeRow
          label="邮件业务员"
          employee-id="email_service"
          v-model="isEmailServiceActive"
          @change="handleEmployeeChange"
        />
      </div>
    </div>
    
    <div class="workflow-section">
      <h3>工作流分支可视化</h3>
      <div class="branch-cards">
        <WfVizBranchCard
          title="真实电话业务员"
          badge-text="固定扩展"
          branch-id="real_phone"
          :is-fixed="true"
          :triggers="realPhoneTriggers"
          @configure="handleBranchConfigure"
          @view-details="handleBranchViewDetails"
        >
          <template #triggers>
            固定行 id=real_phone；副窗启用 → ADB 设备连通检查 → 来电检测/接听 → 语音转写与回复（与状态轮询同步）
          </template>
        </WfVizBranchCard>
        
        <WfVizBranchCard
          title="在线客服扩展"
          badge-text="动态扩展"
          branch-id="online_service"
          :is-fixed="false"
          :triggers="onlineServiceTriggers"
          @configure="handleBranchConfigure"
          @view-details="handleBranchViewDetails"
        />
      </div>
    </div>
    
    <div class="workflow-section">
      <h3>状态日志</h3>
      <div class="status-log">
        <div v-for="(log, index) in logs" :key="index" class="log-entry">
          <span class="log-time">{{ log.time }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue'
import WorkflowEmployeeRow from './WorkflowEmployeeRow.vue'
import WfVizBranchCard from './WfVizBranchCard.vue'
import type { BranchTrigger } from '../types/workflow-employee'

export default defineComponent({
  name: 'WorkflowDemo',
  components: {
    WorkflowEmployeeRow,
    WfVizBranchCard
  },
  setup() {
    const isRealPhoneActive = ref(false)
    const isOnlineServiceActive = ref(false)
    const isEmailServiceActive = ref(false)
    
    const logs = ref<Array<{ time: string; message: string }>>([])
    
    const realPhoneTriggers: BranchTrigger[] = [
      {
        id: 'adb_check',
        name: 'ADB 设备连通检查',
        type: 'fixed',
        status: 'active',
        order: 1
      },
      {
        id: 'call_detection',
        name: '来电检测/接听',
        type: 'fixed',
        status: 'active',
        order: 2
      },
      {
        id: 'voice_transcription',
        name: '语音转写',
        type: 'fixed',
        status: 'active',
        order: 3
      },
      {
        id: 'voice_reply',
        name: '语音回复',
        type: 'fixed',
        status: 'active',
        order: 4
      }
    ]
    
    const onlineServiceTriggers: BranchTrigger[] = [
      {
        id: 'chat_init',
        name: '聊天初始化',
        type: 'dynamic',
        status: 'active',
        order: 1
      },
      {
        id: 'message_handler',
        name: '消息处理',
        type: 'dynamic',
        status: 'pending',
        order: 2
      }
    ]
    
    const addLog = (message: string) => {
      logs.value.unshift({
        time: new Date().toLocaleTimeString('zh-CN'),
        message
      })
    }
    
    const handleEmployeeChange = (isActive: boolean) => {
      addLog(`员工状态变更：${isActive ? '启用' : '禁用'}`)
    }
    
    const handleEmployeeToggle = ({ employeeId, active }: { employeeId: string; active: boolean }) => {
      addLog(`员工切换：${employeeId} -> ${active ? '启用' : '禁用'}`)
    }
    
    const handleBranchConfigure = ({ branchId }: { branchId: string }) => {
      addLog(`配置分支：${branchId}`)
      console.log('Configure branch:', branchId)
    }
    
    const handleBranchViewDetails = ({ branchId }: { branchId: string }) => {
      addLog(`查看详情：${branchId}`)
      console.log('View details:', branchId)
    }
    
    return {
      isRealPhoneActive,
      isOnlineServiceActive,
      isEmailServiceActive,
      realPhoneTriggers,
      onlineServiceTriggers,
      logs,
      handleEmployeeChange,
      handleEmployeeToggle,
      handleBranchConfigure,
      handleBranchViewDetails
    }
  }
})
</script>

<style scoped>
.workflow-demo {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.workflow-demo h2 {
  font-size: 24px;
  font-weight: 600;
  color: #111827;
  margin-bottom: 24px;
}

.workflow-demo h3 {
  font-size: 18px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
}

.workflow-section {
  margin-bottom: 32px;
}

.employee-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 500px;
}

.branch-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.status-log {
  background: #1f2937;
  border-radius: 8px;
  padding: 16px;
  max-height: 300px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.log-entry {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
  color: #e5e7eb;
}

.log-time {
  color: #9ca3af;
  flex-shrink: 0;
}

.log-message {
  color: #10b981;
}
</style>
