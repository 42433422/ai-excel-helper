<template>
  <div class="page-view" id="view-other-tools">
    <div class="page-content">
      <div class="page-header">
        <h2>员工工作流管理</h2>
      </div>

      <div class="card" style="margin-bottom: 12px;">
        <h3 style="margin: 0 0 8px;">流程与员工</h3>

        <p v-if="ctx.clientModsUiOff" style="margin: 0; color: #6b7280;">
          当前为<strong>原版模式</strong>（前端不加载扩展）：副窗无工作流员工行。请关闭原版模式并从 MOD 商店「AI 员工 → 工作流员工」安装对应 Mod 后刷新。
        </p>
        <p v-else-if="ctx.modsDisabledByServer" style="margin: 0; color: #6b7280;">
          后端已关闭扩展（XCAGI_DISABLE_MODS）：副窗与「流程全景」不展示工作流员工。
        </p>
        <p v-else-if="!ctx.isModsListLoaded" style="margin: 0; color: #6b7280;">
          正在与后端同步扩展列表。若已从商店安装工作流员工 Mod，同步完成后本页与副窗将自动一致更新。
        </p>
        <p v-else-if="modWorkflowEmployeesActive" style="margin: 0; color: #6b7280;">
          在此查看与管理副窗中<strong>已从商店安装</strong>的工作流员工（manifest 声明 workflow_employees）；开关样式与侧栏「专业版」一致。各 Mod 的蓝图、API 与专有步骤以扩展包文档为准。
        </p>
        <p v-else style="margin: 0; color: #6b7280;">
          当前未加载任何工作流员工 Mod。请从 MOD 商店「AI 员工 → 工作流员工」安装 6 类独立商品（标签打印、出货、收货、微信消息、微信电话、真实电话等）。
        </p>

        <p v-if="modWorkflowEmployeesActive" style="margin: 12px 0 0; color: #6b7280;">
          「流程全景」以图解说明已安装工作流员工的执行逻辑；专有细节仍以各 Mod 为准。
        </p>
        <p v-else style="margin: 12px 0 0; color: #6b7280;">
          安装工作流员工 Mod 并启用副窗开关后，「流程全景」总览卡与过程说明将随 manifest 自动出现。
        </p>

        <div style="margin-top: 12px;">
          <router-link
            :to="workflowVisualizationLocation"
            class="btn btn-primary"
            :title="workflowPanoramaTitle"
          >流程全景</router-link>
        </div>
        <p v-if="!ctx.clientModsUiOff && !ctx.modsDisabledByServer" style="margin: 12px 0 0; color: #6b7280;">
          「微信联系人」侧栏入口与副窗「微信触点管家」工作流员工由可选扩展 Mod<strong> wechat-contacts-ai-employee</strong>（微信触点 AI 员工）提供；源码见公司仓库 <code>mods/wechat-contacts-ai-employee/</code>，可打包上架 MODstore。
        </p>
      </div>

      <div class="card" style="margin-bottom: 12px;">
        <h3 style="margin: 0 0 8px;">员工空间</h3>
        <p style="margin: 0; color: #6b7280;">
          像素风入口与工位实况展示（与副窗「一键托管」工作流员工、智能对话任务快照同步）。不在本页直接展开工位网格；进入独立页查看。
        </p>
        <div style="margin-top: 12px;">
          <router-link
            :to="{ name: 'workflow-employee-space' }"
            class="btn btn-primary"
            :title="employeeSpaceTitle"
          >进入员工空间</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWorkflowModsRuntimeContext } from '@/composables/useWorkflowModsRuntimeContext'
import { resolveWorkflowVisualizationLocation } from '@/utils/workflowNav'

const { ctx, modWorkflowEmployeesActive } = useWorkflowModsRuntimeContext()
const workflowVisualizationLocation = resolveWorkflowVisualizationLocation()

const workflowPanoramaTitle = computed(() =>
  modWorkflowEmployeesActive.value
    ? '查看已安装工作流员工的执行逻辑与过程'
    : '查看工作流执行逻辑与过程（需先安装工作流员工 Mod）'
)

const employeeSpaceTitle = computed(() =>
  modWorkflowEmployeesActive.value
    ? '打开员工空间：像素入口与工作流工位实况'
    : '打开员工空间：像素入口与工位实况'
)
</script>
