import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { apiFetch } from '@/utils/apiBase';
import { summarizeModLoadingData } from '@/utils/modLoadingStatus';

/**
 * 仅前端「原版模式」：不展示 Mod、不请求 /api/mods*、不注册 Mod 路由、不保留 Mod 内存状态。
 * 与后端 XCAGI_DISABLE_MODS 无关；重新打开需刷新页面。
 */
export const CLIENT_MODS_UI_OFF_KEY = 'xcagi_client_mods_ui_off';

function readClientModsUiOff(): boolean {
  try {
    return localStorage.getItem(CLIENT_MODS_UI_OFF_KEY) === '1';
  } catch {
    return false;
  }
}

/** 与各 Mod manifest.json 的 workflow_employees 项一致（由 /api/mods/ 下发） */
export interface ModWorkflowEmployee {
  id: string;
  label: string;
  /** 任务面板摘要；与 panel_summary 二选一，优先 summary */
  summary?: string;
  /** 任务面板摘要（manifest 常用字段名） */
  panel_summary?: string;
  /** 覆盖默认标题「工作流 · {label}」 */
  panel_title?: string;
  /** 若设置，聊天任务面板将定期 GET 该绝对路径，响应 data 合并进工作流状态 */
  status_poll_path?: string;
  /** 若设置，开关打开/关闭时分别 POST {prefix}/start、{prefix}/stop */
  agent_control_prefix?: string;
  /** 与 phone_agent_status_poll 联用：POST/GET 的 API 根（如 /api/mod/xxx/phone-agent） */
  phone_agent_api_base?: string;
  /** 为 true 时轮询 GET {phone_agent_api_base}/status */
  phone_agent_status_poll?: boolean;
  /** 占位员工：仅展示摘要与简单步骤，无状态轮询 */
  workflow_placeholder?: boolean;
}

interface ModInfo {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  /** 与后端 manifest primary 一致，主扩展优先用于顶栏角标等 */
  primary?: boolean;
  /** manifest comms.exports，声明本 Mod 提供的通信通道（文档用，实际以注册为准） */
  comms_exports?: string[];
  menu?: Array<{
    id: string;
    label: string;
    icon: string;
    path: string;
  }>;
  workflow_employees?: ModWorkflowEmployee[];
}

interface ModRoute {
  mod_id: string;
  routes_path: string;
}

function delay(ms: number) {
  return new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });
}

export const useModsStore = defineStore('mods', () => {
  const mods = ref<ModInfo[]>([]);
  const modRoutes = ref<ModRoute[]>([]);
  /** 用户在前端启用「原版模式」：完全隔离 Mod（无请求、无路由、无侧栏/工作流痕迹） */
  const clientModsUiOff = ref(readClientModsUiOff());
  /** 仅在为 true 时表示「已成功拉取过 /api/mods/」；失败时为 false，可再次 initialize */
  const isLoaded = ref(false);
  const loadError = ref<string | null>(null);
  let initInFlight: Promise<void> | null = null;

  /** 侧栏、副窗工作流等应使用此列表；仍为完整拉取结果时用 mods */
  const modsForUi = computed<ModInfo[]>(() => (clientModsUiOff.value ? [] : mods.value));

  /** 启动页 loading-status 先写入，侧栏可立刻显示名称；完整列表仍靠 initialize */
  function applyLoadingStatusPreview(
    rows: Array<{ id: string; name?: string; version?: string }> | null | undefined
  ) {
    if (clientModsUiOff.value) return;
    if (!Array.isArray(rows) || rows.length === 0) return;
    if (mods.value.length > 0) return;
    mods.value = rows.map((r) => ({
      id: String(r.id || '').trim() || 'unknown',
      name: String(r.name || r.id || '').trim() || String(r.id || ''),
      version: String(r.version || ''),
      author: '',
      description: '',
    }));
  }

  async function fetchModsOnce(): Promise<{ ok: boolean; modsDisabled?: boolean }> {
    try {
      const response = await apiFetch('/api/mods/');
      if (!response.ok) {
        loadError.value = `HTTP ${response.status}`;
        return { ok: false };
      }
      const data = await response.json();
      if (!data.success) {
        loadError.value = typeof data.error === 'string' ? data.error : '列表失败';
        return { ok: false };
      }
      if (data.mods_disabled === true) {
        mods.value = [];
        loadError.value =
          'Mod 扩展已关闭：环境变量 XCAGI_DISABLE_MODS 已启用。请从 .env 或系统环境去掉该项后重启后端（run.py）。';
        return { ok: true, modsDisabled: true };
      }
      mods.value = Array.isArray(data.data) ? data.data : [];
      loadError.value = null;
      return { ok: true };
    } catch (error) {
      console.error('Failed to fetch mods:', error);
      loadError.value = error instanceof Error ? error.message : '网络错误';
      return { ok: false };
    }
  }

  /**
   * 重启后端后可能出现：磁盘上有 Mod 但首轮 load 尚未进注册表，/api/mods/ 暂时为空。
   * 与 GET /api/mods/loading-status 的 discovered_mod_ids / load_mismatch 对齐后再拉列表。
   */
  /**
   * 仅当 loading-status 明确「磁盘上未发现任何 manifest」时为 true。
   * 用于避免：/api/mods/ 暂时空列表 + loading-status 失败时误把 isLoaded 置 true，导致之后 initialize 被短路、Mod 永远不拉。
   */
  async function confirmServerReportsZeroDiscoveredMods(): Promise<boolean> {
    try {
      const response = await apiFetch('/api/mods/loading-status');
      if (!response.ok) return false;
      const data = await response.json();
      if (!data.success || !data.data) return false;
      const discovered = Array.isArray(data.data.discovered_mod_ids)
        ? data.data.discovered_mod_ids
        : [];
      return discovered.length === 0;
    } catch {
      return false;
    }
  }

  async function shouldRetryModsListWhenEmpty(): Promise<boolean> {
    try {
      const response = await apiFetch('/api/mods/loading-status');
      if (!response.ok) return false;
      const data = await response.json();
      if (!data.success || !data.data) return false;
      const d = data.data as {
        discovered_mod_ids?: string[];
        mods_loaded?: number;
        load_mismatch?: boolean;
        load_errors?: unknown[];
        manifest_errors?: unknown[];
        blueprint_errors?: unknown[];
        partial_failure?: boolean;
      };
      const discovered = Array.isArray(d.discovered_mod_ids) ? d.discovered_mod_ids : [];
      const loaded = typeof d.mods_loaded === 'number' ? d.mods_loaded : 0;
      if (d.mods_disabled === true) return false;
      if (d.load_mismatch === true) return true;
      if (discovered.length > 0 && loaded === 0) return true;
      return false;
    } catch {
      return false;
    }
  }

  async function fetchModLoadingStatusHint(): Promise<string | null> {
    try {
      const response = await apiFetch('/api/mods/loading-status');
      if (!response.ok) return null;
      const data = await response.json();
      if (!data.success || !data.data) return null;
      return summarizeModLoadingData(data.data as Record<string, unknown>);
    } catch {
      return null;
    }
  }

  async function fetchModsWithRetry(): Promise<{ ok: boolean; modsDisabled?: boolean }> {
    let r = await fetchModsOnce();
    if (r.modsDisabled) return r;
    if (!r.ok) {
      await delay(900);
      r = await fetchModsOnce();
    }
    if (r.modsDisabled) return r;
    if (r.ok && mods.value.length === 0) {
      const mismatch = await shouldRetryModsListWhenEmpty();
      if (mismatch) {
        await delay(1000);
        r = await fetchModsOnce();
        if (r.modsDisabled) return r;
        if (r.ok && mods.value.length === 0) {
          await delay(1500);
          r = await fetchModsOnce();
        }
      }
    }
    return r;
  }

  async function fetchModRoutes(): Promise<void> {
    try {
      const response = await apiFetch('/api/mods/routes');
      if (!response.ok) return;
      const data = await response.json();
      if (data.success && Array.isArray(data.data)) {
        modRoutes.value = data.data;
      }
    } catch (error) {
      console.error('Failed to fetch mod routes:', error);
    }
  }

  function setClientModsUiOff(off: boolean) {
    clientModsUiOff.value = off;
    if (off) {
      mods.value = [];
      modRoutes.value = [];
      loadError.value = null;
      isLoaded.value = true;
    } else {
      // 从原版切回 Mod：必须允许下一轮 initialize 真正拉 /api/mods*（否则 isLoaded 仍为 true 会短路）
      isLoaded.value = false;
      mods.value = [];
      modRoutes.value = [];
      loadError.value = null;
    }
    try {
      if (off) {
        localStorage.setItem(CLIENT_MODS_UI_OFF_KEY, '1');
      } else {
        localStorage.removeItem(CLIENT_MODS_UI_OFF_KEY);
      }
    } catch {
      /* private mode */
    }
  }

  function getModMenu() {
    const menus: Array<{
      id: string;
      label: string;
      icon: string;
      path: string;
      modId: string;
    }> = [];

    for (const mod of modsForUi.value) {
      if (mod.menu && Array.isArray(mod.menu)) {
        for (const item of mod.menu) {
          menus.push({
            ...item,
            modId: mod.id,
          });
        }
      }
    }

    return menus;
  }

  async function initialize(force = false) {
    // 同步原版模式状态到后端
    if (clientModsUiOff.value) {
      try {
        const { syncClientModsStateToBackend } = await import('@/utils/apiBase')
        syncClientModsStateToBackend()
      } catch {
        // ignore
      }
    }

    if (clientModsUiOff.value) {
      mods.value = [];
      modRoutes.value = [];
      loadError.value = null;
      isLoaded.value = true;
      return;
    }

    // 已标记 loaded 但没有任何 Mod 数据时视为未就绪（例如刚从原版切回、或异常中断）
    if (isLoaded.value && !force) {
      if (mods.value.length > 0 || modRoutes.value.length > 0) return;
      isLoaded.value = false;
    }

    if (initInFlight) {
      await initInFlight;
      // 并发调用：等首轮结束后若仍失败（后端晚于前端启动），再拉一次
      if (!isLoaded.value && !force) {
        await initialize(false);
      }
      return;
    }

    initInFlight = (async () => {
      if (clientModsUiOff.value) {
        mods.value = [];
        modRoutes.value = [];
        loadError.value = null;
        isLoaded.value = true;
        return;
      }
      if (force) {
        isLoaded.value = false;
      }
      const r = await fetchModsWithRetry();
      await fetchModRoutes();
      if (r.modsDisabled) {
        isLoaded.value = true;
        return;
      }
      const ok = r.ok;
      if (ok) {
        if (mods.value.length > 0) {
          isLoaded.value = true;
          loadError.value = null;
        } else if (await shouldRetryModsListWhenEmpty()) {
          isLoaded.value = false;
          const hint = await fetchModLoadingStatusHint();
          loadError.value =
            hint ||
            '检测到 Mod 目录有扩展但后端未加载成功，请查看后端日志，或稍后刷新页面';
        } else if (await confirmServerReportsZeroDiscoveredMods()) {
          isLoaded.value = true;
          loadError.value = null;
        } else {
          isLoaded.value = false;
          loadError.value =
            (await fetchModLoadingStatusHint()) ||
            'Mod 列表为空，且未能确认后端磁盘扫描结果 — 请确认后端已启动后刷新';
        }
      }
      if (modRoutes.value.length > 0) {
        try {
          const { registerModRoutes } = await import('@/router/registerModRoutes');
          const router = (await import('@/router')).default;
          await registerModRoutes(router, modRoutes.value);
        } catch (e) {
          console.warn('[mods] registerModRoutes after initialize failed:', e);
        }
      }
    })();

    try {
      await initInFlight;
    } finally {
      initInFlight = null;
    }
  }

  /** 强制重新拉取（后端晚于前端启动时可调用） */
  async function refresh() {
    await initialize(true);
  }

  return {
    mods,
    modsForUi,
    modRoutes,
    clientModsUiOff,
    setClientModsUiOff,
    isLoaded,
    loadError,
    fetchMods: fetchModsWithRetry,
    fetchModRoutes,
    getModMenu,
    initialize,
    refresh,
    applyLoadingStatusPreview,
  };
});
