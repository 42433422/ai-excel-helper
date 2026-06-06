<template>
  <div class="page-view" id="view-workflow-employee-space">
    <div class="page-content">
      <header class="ews-page-head">
        <div class="ews-page-head-text">
          <p class="ews-page-crumb">
            <router-link :to="{ name: 'other-tools' }" class="ews-page-crumb-link">员工工作流管理</router-link>
            <span class="ews-page-crumb-sep" aria-hidden="true">/</span>
            <span class="ews-page-crumb-here">员工空间</span>
          </p>
          <h2 class="ews-page-title">员工空间</h2>
          <p class="ews-page-sub">像素入口与工位实况；数据与副窗工作流开关、智能对话任务快照同步。</p>
        </div>
        <router-link
          :to="{ name: 'other-tools' }"
          class="btn btn-secondary btn-sm ews-page-back"
        >
          <span aria-hidden="true">←</span>
          <span>返回员工工作流管理</span>
        </router-link>
      </header>

      <EmployeeWorkspaceScene />
    </div>
  </div>
</template>

<script setup lang="ts">
import EmployeeWorkspaceScene from '@/components/workflow/EmployeeWorkspaceScene.vue'
</script>

<style scoped>
.ews-page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.ews-page-head-text {
  min-width: 0;
}

.ews-page-crumb {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 4px;
  font-size: 12px;
  color: #6b7280;
  letter-spacing: 0.02em;
}

.ews-page-crumb-link {
  color: #2563eb;
  text-decoration: none;
}

.ews-page-crumb-link:hover {
  text-decoration: underline;
}

.ews-page-crumb-sep {
  color: #cbd5e1;
}

.ews-page-crumb-here {
  color: #374151;
  font-weight: 500;
}

.ews-page-title {
  margin: 0 0 6px;
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.01em;
}

.ews-page-sub {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  color: #6b7280;
  max-width: 52rem;
}

.ews-page-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
}
</style>
