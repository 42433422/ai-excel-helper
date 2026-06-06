import { createApp } from 'vue';
import { createPinia } from 'pinia';
import * as ElementPlusIconsVue from '@element-plus/icons-vue';
import './fhd/installFetchDbReadToken';
import { useAppShellStore } from '@/stores/appShell';
import {
  bootstrapEditionDefaults,
  bootstrapEnterpriseShellDefaults,
} from '@/constants/platformShellMode';

bootstrapEditionDefaults();
bootstrapEnterpriseShellDefaults();

import App from './App.vue';
import router from './router';
import { bindTutorialRouter } from '@/stores/tutorial';
import { registerAllModRoutesFromGlob, registerModRoutes } from './router/registerModRoutes';

bindTutorialRouter(router);
import { fetchModRoutesPayloadShared } from './utils/modRoutesSharedFetch';
import { CLIENT_MODS_UI_OFF_KEY } from '@/stores/mods';
import { applySidebarThemeFromStorage } from './utils/sidebarTheme';
import { installClientConsoleBridge } from './utils/clientDebugLog';
import { initServiceWorker, unregisterStaleServiceWorkers } from './utils/serviceWorker';
import { bootstrapHostConfig } from '@/stores/hostConfig';

import './styles/css/base.css';
import './styles/css/components/sidebar.css';
import './styles/css/components/chat.css';
import './styles/css/components/tables.css';
import './styles/css/components/modals.css';
import './styles/css/components/ui-components.css';
import './styles/css/animations/transitions.css';
import './styles/css/animations/ui-effects.css';
import './styles/css/animations/pro-mode.css';
import './styles/css/animations/gpu-optimizations.css';
import './styles/css/office-theme.css';
import 'font-awesome/css/font-awesome.min.css';

// Window globals are kept for backward compatibility; prefer using the Pinia appShell store.

function readVanillaNoModUi(): boolean {
  try {
    return localStorage.getItem(CLIENT_MODS_UI_OFF_KEY) === '1';
  } catch {
    return false;
  }
}

/**
 * 与 mount 并行预取 Mod 路由，避免在 bootstrap 里 await 网络导致整页长时间不挂载（用户感觉「卡死」）。
 * 深链直达 Mod 页时若此请求晚于首跳，仍可由 modsStore.initialize 内 registerModRoutes 补齐。
 */
async function bootstrap() {
  bootstrapEditionDefaults();
  void bootstrapHostConfig();
  applySidebarThemeFromStorage();
  installClientConsoleBridge();

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    const port = window.location.port;
    const isLocalHost =
      import.meta.env.DEV ||
      host === '127.0.0.1' ||
      host === 'localhost' ||
      port === '5000' ||
      port === '5001';

    if (isLocalHost) {
      // 打包页走 127.0.0.1:5000 时 main 不会注册 SW，但必须清掉历史残留，否则会劫持 fetch 并报 206 cache 错
      void unregisterStaleServiceWorkers();
    } else {
      initServiceWorker()
        .then((swStatus) => {
          if (swStatus.registered) {
            console.log(`[Bootstrap] Service Worker ready (offline: ${swStatus.offline})`);
          }
        })
        .catch(() => {});
    }
  }

  const app = createApp(App);
  const pinia = createPinia();

  app.config.errorHandler = (err, _instance, info) => {
    console.error('[Vue]', info || 'unknown hook', err);
  };
  window.addEventListener('unhandledrejection', (event) => {
    console.error('[unhandledrejection]', event.reason);
  });

  app.use(pinia);
  try {
    const shell = useAppShellStore()
    shell.setAppActive(true)
    shell.setChatOwnsInput(true)
    try {
      window.__VUE_APP_ACTIVE__ = !!shell.appActive
      window.__VUE_CHAT_OWNS_INPUT__ = !!shell.chatOwnsInput
    } catch {
      // ignore
    }
  } catch {
    // ignore if store import fails in legacy environments
  }

  app.use(router);

  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component);
  }

  app.mount('#app');

  if (typeof performance !== 'undefined' && performance.mark) {
    performance.mark('bootstrap_mount');
  }

  if (!readVanillaNoModUi()) {
    void (async () => {
      try {
        await registerAllModRoutesFromGlob(router);
      } catch (e) {
        console.warn('[bootstrap] mod routes (glob) after mount failed:', e);
      }
    })();
  }

  void (async () => {
    if (readVanillaNoModUi()) return;
    try {
      const entries = await fetchModRoutesPayloadShared();
      if (entries?.length) {
        await registerModRoutes(router, entries);
      }
    } catch (e) {
      console.warn('[bootstrap] Mod routes (API) register failed:', e);
    }
  })();
}

void bootstrap();
