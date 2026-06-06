type ViewLoader = () => Promise<{ default: unknown }>

export const hostViewGlob = {
  ...import.meta.glob('../views/LoginView.vue'),
  ...import.meta.glob('../views/ChatView.vue'),
  ...import.meta.glob('../views/LanGateView.vue'),
  ...import.meta.glob('../views/ModStore.vue'),
  ...import.meta.glob('../views/SettingsView.vue'),
  ...import.meta.glob('../views/DesktopRuntimeView.vue'),
  ...import.meta.glob('../views/ChatDebugView.vue'),
  ...import.meta.glob('../views/ToolsView.vue'),
  ...import.meta.glob('../views/OtherToolsView.vue'),
  ...import.meta.glob('../views/EmployeeWorkspaceView.vue'),
  ...import.meta.glob('../views/YuangongStitchFullView.vue'),
  ...import.meta.glob('../views/ModLandingView.vue'),
} as Record<string, ViewLoader>
