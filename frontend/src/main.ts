import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { registerModRoutes } from './router/registerModRoutes';
import { apiFetch } from './utils/apiBase';
import { CLIENT_MODS_UI_OFF_KEY } from '@/stores/mods';
import { applySidebarThemeFromStorage } from './utils/sidebarTheme';

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

window.__VUE_APP_ACTIVE__ = true;
window.__VUE_CHAT_OWNS_INPUT__ = true;

async function bootstrap() {
  applySidebarThemeFromStorage();

  // 须在 mount 之前读完 localStorage 并完成 Mod 路由注册，否则首屏与侧栏可能在路由尚未 addRoute 时渲染，表现为「Mod 模式打不开/点进 Mod 页 404」。
  let vanillaNoModUi = false;
  try {
    vanillaNoModUi = localStorage.getItem(CLIENT_MODS_UI_OFF_KEY) === '1';
  } catch {
    vanillaNoModUi = false;
  }

  if (!vanillaNoModUi) {
    const ctrl = new AbortController();
    const t = window.setTimeout(() => ctrl.abort(), 10000);
    try {
      const res = await apiFetch('/api/mods/routes', { signal: ctrl.signal });
      if (res.ok) {
        const data = await res.json();
        if (data.success && Array.isArray(data.data)) {
          await registerModRoutes(router, data.data);
        }
      }
    } catch (e) {
      console.warn('[mods] Prefetch mod routes failed (offline, timeout or API missing):', e);
    } finally {
      window.clearTimeout(t);
    }
  }

  const app = createApp(App);
  const pinia = createPinia();

  app.use(pinia);
  app.use(router);

  app.mount('#app');
}

void bootstrap();
