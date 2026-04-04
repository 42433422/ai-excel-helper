<template>
  <div class="page-view" id="view-other-tools">
    <div class="page-content">
      <div class="page-header">
        <h2>员工工作流管理</h2>
      </div>

      <div class="card" style="margin-bottom: 12px;">
        <h3 style="margin: 0 0 8px;">流程与员工</h3>

        <p v-if="ctx.clientModsUiOff" style="margin: 0; color: #6b7280;">
          当前为<strong>原版模式</strong>（前端不加载扩展）：在此查看与管理副窗中的<strong>固定六类</strong>工作流；开关样式与侧栏「专业版」一致。扩展相关蓝图与说明由各扩展包自行提供。
        </p>
        <p v-else-if="ctx.modsDisabledByServer" style="margin: 0; color: #6b7280;">
          后端已关闭扩展（XCAGI_DISABLE_MODS）：仅<strong>固定六类</strong>工作流；副窗与「流程全景」不展示扩展向内容。
        </p>
        <p v-else-if="!ctx.isModsListLoaded" style="margin: 0; color: #6b7280;">
          正在与后端同步扩展列表；当前说明以<strong>固定六类</strong>为主。若环境中存在带工作流员工的扩展，同步完成后本页描述会与副窗一致更新。
        </p>
        <p v-else-if="modWorkflowEmployeesActive" style="margin: 0; color: #6b7280;">
          在此查看与管理副窗中的<strong>固定六类</strong>与当前 manifest 已声明的<strong>扩展工作流员工</strong>；开关样式与侧栏「专业版」一致。各扩展的蓝图、API 与专有步骤以扩展包文档为准。
        </p>
        <p v-else style="margin: 0; color: #6b7280;">
          当前副窗仅<strong>固定六类</strong>（未加载带工作流员工的扩展，或扩展未声明 workflow_employees）。扩展蓝图与对接说明由各扩展包维护。
        </p>

        <p v-if="modWorkflowEmployeesActive" style="margin: 12px 0 0; color: #6b7280;">
          「流程全景」以图解说明固定六类与已出现的扩展工作流执行逻辑；扩展专有细节仍以各扩展为准。
        </p>
        <p v-else style="margin: 12px 0 0; color: #6b7280;">
          「流程全景」以图解说明<strong>固定六类</strong>执行逻辑与任务面板对应关系；扩展相关内容仅在扩展实际启用工作流员工后才会在总览中体现。
        </p>

        <div style="margin-top: 12px;">
          <router-link
            :to="{ name: 'workflow-visualization' }"
            class="btn btn-primary"
            :title="workflowPanoramaTitle"
          >流程全景</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWorkflowModsRuntimeContext } from '@/composables/useWorkflowModsRuntimeContext'

const { ctx, modWorkflowEmployeesActive } = useWorkflowModsRuntimeContext()

const workflowPanoramaTitle = computed(() =>
  modWorkflowEmployeesActive.value
    ? '查看固定六类与扩展工作流的执行逻辑与过程'
    : '查看固定六类工作流的执行逻辑与过程'
)
</script>
