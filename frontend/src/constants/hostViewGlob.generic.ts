type ViewLoader = () => Promise<{ default: unknown }>

/**
 * generic 发行构建：平台壳宿主页 + 常见 Mod 回退视图（不含行业 ERP 全量页，由 Mod 物理视图承担）。
 */
export const hostViewGlob = {
  ...import.meta.glob('../views/LoginView.vue'),
  ...import.meta.glob('../views/LoginHelpView.vue'),
  ...import.meta.glob('../views/RegisterView.vue'),
  ...import.meta.glob('../views/ForgotPasswordView.vue'),
  ...import.meta.glob('../views/ForgotAccountView.vue'),
  ...import.meta.glob('../views/ChatView.vue'),
  ...import.meta.glob('../views/LanGateView.vue'),
  ...import.meta.glob('../views/ModStore.vue'),
  ...import.meta.glob('../views/ModLandingView.vue'),
  ...import.meta.glob('../views/ModDetails.vue'),
  ...import.meta.glob('../views/SettingsView.vue'),
  ...import.meta.glob('../views/DesktopRuntimeView.vue'),
  ...import.meta.glob('../views/ChatDebugView.vue'),
  ...import.meta.glob('../views/ToolsView.vue'),
  ...import.meta.glob('../views/OtherToolsView.vue'),
  ...import.meta.glob('../views/EmployeeWorkspaceView.vue'),
  ...import.meta.glob('../views/YuangongStitchFullView.vue'),
  ...import.meta.glob('../views/AIEcosystemView.vue'),
  ...import.meta.glob('../views/BrainView.vue'),
  ...import.meta.glob('../views/ModelPaymentView.vue'),
  ...import.meta.glob('../views/ApprovalHubView.vue'),
  ...import.meta.glob('../views/ApprovalWorkspaceView.vue'),
  ...import.meta.glob('../views/WorkflowVisualizationView.vue'),
  ...import.meta.glob('../views/InternalCustomerServiceView.vue'),
  ...import.meta.glob('../views/EnterpriseCustomerServiceView.vue'),
} as Record<string, ViewLoader>
