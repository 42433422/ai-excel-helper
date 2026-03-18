import { defineAsyncComponent } from 'vue'

const loadingComponent = {
  template: '<div class="async-loading"></div>'
}

const errorComponent = {
  template: '<div class="async-error">加载失败</div>'
}

export const ProModeComponents = {
  ProModeOverlay: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ProModeOverlay.vue'),
    loadingComponent,
    errorComponent,
    delay: 200,
    timeout: 10000
  }),
  JarvisCore: defineAsyncComponent({
    loader: () => import('./components/pro-mode/JarvisCore.vue'),
    loadingComponent,
    errorComponent,
    delay: 200
  }),
  WireRings: defineAsyncComponent({
    loader: () => import('./components/pro-mode/WireRings.vue'),
    loadingComponent,
    errorComponent
  }),
  EnergyParticles: defineAsyncComponent({
    loader: () => import('./components/pro-mode/EnergyParticles.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisVoiceButton: defineAsyncComponent({
    loader: () => import('./components/pro-mode/JarvisVoiceButton.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisChatPanel: defineAsyncComponent({
    loader: () => import('./components/pro-mode/JarvisChatPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisStatus: defineAsyncComponent({
    loader: () => import('./components/pro-mode/JarvisStatus.vue'),
    loadingComponent,
    errorComponent
  }),
  ProProductOrbitLayer: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ProProductOrbitLayer.vue'),
    loadingComponent,
    errorComponent
  }),
  ProProductInfoBadge: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ProProductInfoBadge.vue'),
    loadingComponent,
    errorComponent
  }),
  ProCoreResetHotspot: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ProCoreResetHotspot.vue'),
    loadingComponent,
    errorComponent
  }),
  CodeRings: defineAsyncComponent({
    loader: () => import('./components/pro-mode/CodeRings.vue'),
    loadingComponent,
    errorComponent
  }),
  IconRingContainer: defineAsyncComponent({
    loader: () => import('./components/pro-mode/IconRingContainer.vue'),
    loadingComponent,
    errorComponent
  }),
  ToolRuntimePanel: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ToolRuntimePanel.vue'),
    loadingComponent,
    errorComponent
  }),
  WorkModeMonitor: defineAsyncComponent({
    loader: () => import('./components/pro-mode/WorkModeMonitor.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisMonitorFloatWrap: defineAsyncComponent({
    loader: () => import('./components/pro-mode/JarvisMonitorFloatWrap.vue'),
    loadingComponent,
    errorComponent
  }),
  ProOrderFloatPanel: defineAsyncComponent({
    loader: () => import('./components/pro-mode/ProOrderFloatPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  ProFeatureWidget: defineAsyncComponent({
    loader: () => import('./components/pro-feature-widget/ProFeatureWidget.vue'),
    loadingComponent,
    errorComponent,
    delay: 300
  }),
  WeChatLoginPanel: defineAsyncComponent({
    loader: () => import('./components/pro-feature-widget/WeChatLoginPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  UserListPanel: defineAsyncComponent({
    loader: () => import('./components/pro-feature-widget/UserListPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  ProductQueryPanel: defineAsyncComponent({
    loader: () => import('./components/pro-feature-widget/ProductQueryPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  DodecaMediaPanel: defineAsyncComponent({
    loader: () => import('./components/pro-mode/DodecaMediaPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  DigitalRainCanvas: defineAsyncComponent({
    loader: () => import('./components/pro-mode/DigitalRainCanvas.vue'),
    loadingComponent,
    errorComponent
  }),
  FallingTextContainer: defineAsyncComponent({
    loader: () => import('./components/pro-mode/FallingTextContainer.vue'),
    loadingComponent,
    errorComponent
  }),
  StarkGrid: defineAsyncComponent({
    loader: () => import('./components/pro-mode/StarkGrid.vue'),
    loadingComponent,
    errorComponent
  })
}

export function registerProModeComponents(app) {
  Object.entries(ProModeComponents).forEach(([name, component]) => {
    app.component(name, component)
  })
}

export function getComponent(name) {
  return ProModeComponents[name] || null
}

export function preloadComponent(name) {
  const component = ProModeComponents[name]
  if (component && component.loader) {
    component.loader()
  }
}

export function preloadAllComponents() {
  Object.values(ProModeComponents).forEach(component => {
    if (component.loader) {
      component.loader()
    }
  })
}

export const componentPreloadMap = {
  'ProModeOverlay': ['JarvisCore', 'WireRings', 'EnergyParticles'],
  'ProFeatureWidget': ['WeChatLoginPanel', 'UserListPanel', 'ProductQueryPanel'],
  'DigitalRainCanvas': ['FallingTextContainer'],
  'StarkGrid': []
}

export function preloadRelatedComponents(componentName) {
  const related = componentPreloadMap[componentName] || []
  related.forEach(name => preloadComponent(name))
}
