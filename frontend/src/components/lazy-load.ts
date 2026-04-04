import { defineAsyncComponent, type App, type Component } from 'vue';

const loadingComponent = {
  template: '<div class="async-loading"></div>'
};

const errorComponent = {
  template: '<div class="async-error">加载失败</div>'
};

type AsyncComponentMap = Record<string, Component>;

export const ProModeComponents: AsyncComponentMap = {
  ProModeOverlay: defineAsyncComponent({
    loader: () => import('./pro-mode/ProModeOverlay.vue'),
    loadingComponent,
    errorComponent,
    delay: 200,
    timeout: 10000
  }),
  JarvisCore: defineAsyncComponent({
    loader: () => import('./pro-mode/JarvisCore.vue'),
    loadingComponent,
    errorComponent,
    delay: 200
  }),
  WireRings: defineAsyncComponent({
    loader: () => import('./pro-mode/WireRings.vue'),
    loadingComponent,
    errorComponent
  }),
  EnergyParticles: defineAsyncComponent({
    loader: () => import('./pro-mode/EnergyParticles.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisVoiceButton: defineAsyncComponent({
    loader: () => import('./pro-mode/JarvisVoiceButton.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisChatPanel: defineAsyncComponent({
    loader: () => import('./pro-mode/JarvisChatPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisStatus: defineAsyncComponent({
    loader: () => import('./pro-mode/JarvisStatus.vue'),
    loadingComponent,
    errorComponent
  }),
  ProProductOrbitLayer: defineAsyncComponent({
    loader: () => import('./pro-mode/ProProductOrbitLayer.vue'),
    loadingComponent,
    errorComponent
  }),
  ProProductInfoBadge: defineAsyncComponent({
    loader: () => import('./pro-mode/ProProductInfoBadge.vue'),
    loadingComponent,
    errorComponent
  }),
  ProCoreResetHotspot: defineAsyncComponent({
    loader: () => import('./pro-mode/ProCoreResetHotspot.vue'),
    loadingComponent,
    errorComponent
  }),
  CodeRings: defineAsyncComponent({
    loader: () => import('./pro-mode/CodeRings.vue'),
    loadingComponent,
    errorComponent
  }),
  IconRingContainer: defineAsyncComponent({
    loader: () => import('./pro-mode/IconRingContainer.vue'),
    loadingComponent,
    errorComponent
  }),
  ToolRuntimePanel: defineAsyncComponent({
    loader: () => import('./pro-mode/ToolRuntimePanel.vue'),
    loadingComponent,
    errorComponent
  }),
  WorkModeMonitor: defineAsyncComponent({
    loader: () => import('./pro-mode/WorkModeMonitor.vue'),
    loadingComponent,
    errorComponent
  }),
  JarvisMonitorFloatWrap: defineAsyncComponent({
    loader: () => import('./pro-mode/JarvisMonitorFloatWrap.vue'),
    loadingComponent,
    errorComponent
  }),
  ProOrderFloatPanel: defineAsyncComponent({
    loader: () => import('./pro-mode/ProOrderFloatPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  ProFeatureWidget: defineAsyncComponent({
    loader: () => import('./pro-feature-widget/ProFeatureWidget.vue'),
    loadingComponent,
    errorComponent,
    delay: 300
  }),
  WeChatLoginPanel: defineAsyncComponent({
    loader: () => import('./pro-feature-widget/WeChatLoginPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  UserListPanel: defineAsyncComponent({
    loader: () => import('./pro-feature-widget/UserListPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  ProductQueryPanel: defineAsyncComponent({
    loader: () => import('./pro-feature-widget/ProductQueryPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  DodecaMediaPanel: defineAsyncComponent({
    loader: () => import('./pro-mode/DodecaMediaPanel.vue'),
    loadingComponent,
    errorComponent
  }),
  FallingTextContainer: defineAsyncComponent({
    loader: () => import('./pro-mode/FallingTextContainer.vue'),
    loadingComponent,
    errorComponent
  }),
  StarkGrid: defineAsyncComponent({
    loader: () => import('./pro-mode/StarkGrid.vue'),
    loadingComponent,
    errorComponent
  })
};

export function registerProModeComponents(app: App<Element>) {
  Object.entries(ProModeComponents).forEach(([name, component]) => {
    app.component(name, component);
  });
}

export function getComponent(name: string) {
  return ProModeComponents[name] || null;
}

export function preloadComponent(name: string) {
  const component = ProModeComponents[name] as any;
  if (component && component.loader) {
    component.loader();
  }
}

export function preloadAllComponents() {
  Object.values(ProModeComponents).forEach((component: any) => {
    if (component.loader) {
      component.loader();
    }
  });
}

export const componentPreloadMap: Record<string, string[]> = {
  ProModeOverlay: ['JarvisCore', 'WireRings', 'EnergyParticles'],
  ProFeatureWidget: ['WeChatLoginPanel', 'UserListPanel', 'ProductQueryPanel'],
  StarkGrid: []
};

export function preloadRelatedComponents(componentName: string) {
  const related = componentPreloadMap[componentName] || [];
  related.forEach((name) => preloadComponent(name));
}
