import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import {
  apiFetch,
  DEFAULT_MOD_API_TIMEOUT_MS,
  MOD_PROBE_API_TIMEOUT_MS,
  isApiFetchTimeoutError,
} from '@/utils/apiBase';
import { fetchModRoutesPayloadShared } from '@/utils/modRoutesSharedFetch';
import { fetchModLoadingStatusShared } from '@/utils/modLoadingStatusShared';
import { summarizeModLoadingData } from '@/utils/modLoadingStatus';
import { fetchPlatformShellCapabilities } from '@/utils/platformShellApi';
import { APPROVAL_BRIDGE_MOD_ID, setApprovalModFacadeEnabled } from '@/constants/approvalMod';
import { ERP_DOMAIN_BRIDGE_MOD_ID, setErpDomainModFacadeEnabled } from '@/constants/erpDomainMod';
import { erpDomainModStatusPath } from '@/utils/erpDomainPaths';
import { LAN_BRIDGE_MOD_ID, setLanModFacadeEnabled } from '@/constants/lanMod';
import { MODEL_PAYMENT_BRIDGE_MOD_ID, setModelPaymentModFacadeEnabled } from '@/constants/modelPaymentMod';
import {
  CUSTOMER_SERVICE_BRIDGE_MOD_ID,
  setCustomerServiceModPagesEnabled,
} from '@/constants/customerServiceMod';
import { PLANNER_FACADE_MOD_ID, setPlannerModFacadeEnabled } from '@/constants/plannerMod';
import {
  OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID,
  setOfficeEmployeePackModPagesEnabled,
} from '@/constants/officeEmployeePackMod';
import {
  CORE_WORKFLOW_MOD_ID,
  coreWorkflowModEmployeesPath,
  setCoreWorkflowModPagesEnabled,
} from '@/constants/coreWorkflowMod';
import { applyEditionPackPlatformShell } from '@/constants/platformShellMode';
import {
  CLIENT_PRIMARY_ERP_MOD_ID,
  hasInstalledClientPrimaryErpMod,
  isAuxEmployeePackModId,
  isClientErpSidebarContext,
  isHostMountedModMenuPath,
  isSelectableExtensionModId,
  shouldSuppressClientErpModMenuId,
} from '@/constants/genericModPack';
import {
  augmentEntitledModIdsForAccount,
  isSunbirdAccountUsername,
} from '@/constants/accountModBinding';
import { buildSunbirdClientModStub } from '@/constants/sunbirdClientMod';
import { isProtectedClientModId } from '@/constants/protectedMods';
import { bootstrapHostConfig, clientModPolicies } from '@/stores/hostConfig';
import { XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY } from '@/utils/xcagiStorageKeys';

/** 防止 applyEntitledActiveMod 内 refetch 再次触发 entitlement 回流 */
let entitledRefetchInProgress = false;

type FetchModsOptions = {
  /** 为 true 时只更新 mods 列表，不再调用 applyEntitledActiveMod（打破递归） */
  skipEntitledApply?: boolean;
};

export type ModsInitializeOptions = {
  entitledModIds?: string[];
  /** 登录后按账号权益强制选 Mod（覆盖 localStorage 中的旧扩展） */
  forceFromEntitlements?: boolean;
  /** 本机登录名（用于 SUNBIRD 等演示账号与太阳鸟 Mod 绑定） */
  accountUsername?: string;
};

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

function readActiveModId(): string {
  try {
    return String(localStorage.getItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY) || '').trim();
  } catch {
    return '';
  }
}

const MOD_PROBE_CACHE_MS = 5 * 60 * 1000;
const MOD_PROBE_RATE_LIMIT_CACHE_MS = 90 * 1000;

type ModProbeCacheEntry = { ok: boolean; at: number; ttlMs: number };
const modStatusProbeCache = new Map<string, ModProbeCacheEntry>();
let modFacadeProbesCompleted = false;

function readModProbeCache(cacheKey: string): boolean | null {
  const row = modStatusProbeCache.get(cacheKey);
  if (!row) return null;
  if (Date.now() - row.at > row.ttlMs) {
    modStatusProbeCache.delete(cacheKey);
    return null;
  }
  return row.ok;
}

function writeModProbeCache(cacheKey: string, ok: boolean, ttlMs = MOD_PROBE_CACHE_MS) {
  modStatusProbeCache.set(cacheKey, { ok, at: Date.now(), ttlMs });
}

/** 太阳鸟等客户 ERP：走宿主路由，勿在启动时打 /api/mod/* 探测（与全局限流桶冲突）。 */
function shouldSkipModFacadeProbes(
  installedModIds: string[],
  activeId: string | null | undefined,
): boolean {
  const active = String(activeId || '').trim();
  if (isProtectedClientModId(active)) return true;
  return isClientErpSidebarContext(installedModIds, activeId);
}

async function probeModStatusSuccess(
  cacheKey: string,
  path: string,
  warnLabel: string,
): Promise<boolean> {
  const cached = readModProbeCache(cacheKey);
  if (cached !== null) return cached;

  try {
    const response = await apiFetch(path, {
      timeoutMs: MOD_PROBE_API_TIMEOUT_MS,
    });
    if (response.status === 429) {
      writeModProbeCache(cacheKey, false, MOD_PROBE_RATE_LIMIT_CACHE_MS);
      return false;
    }
    if (!response.ok) {
      console.warn(`[mods] ${warnLabel} probe failed:`, response.status, path);
      writeModProbeCache(cacheKey, false);
      return false;
    }
    const body = await response.json().catch(() => null);
    const ok = Boolean(body && typeof body === 'object' && (body as { success?: boolean }).success);
    writeModProbeCache(cacheKey, ok);
    return ok;
  } catch (error) {
    console.warn(`[mods] ${warnLabel} probe error:`, error);
    writeModProbeCache(cacheKey, false);
    return false;
  }
}

/** 核心工作流 Mod：流程可视化物理页挂载前校验 employees 列表。 */
async function probeCoreWorkflowModAvailable(): Promise<boolean> {
  return probeModStatusSuccess(
    'core-workflow-employees',
    coreWorkflowModEmployeesPath(),
    'Core workflow mod listed but employees',
  );
}

/** ERP 门面：仅在后端 Mod HTTP 路由可用时开启，避免全站请求落入 SPA 404。 */
async function probeErpDomainModFacadeAvailable(): Promise<boolean> {
  return probeModStatusSuccess(
    'erp-domain-status',
    erpDomainModStatusPath(),
    'ERP domain mod listed but status',
  );
}

async function applyModFacadeFlagsFromListing(
  modsList: ModInfo[],
  activeId: string | null | undefined,
  forceProbe = false,
): Promise<void> {
  if (modFacadeProbesCompleted && !forceProbe) return;

  const installedIds = modsList.map((m) => String(m.id || '').trim()).filter(Boolean);
  const active = String(activeId || '').trim();
  const skipProbes = shouldSkipModFacadeProbes(installedIds, active);

  setPlannerModFacadeEnabled(modsList.some((m) => m.id === PLANNER_FACADE_MOD_ID));

  const hasErpDomainModListed = modsList.some((m) => m.id === ERP_DOMAIN_BRIDGE_MOD_ID);
  const hasCoreWorkflowListed = modsList.some((m) => m.id === CORE_WORKFLOW_MOD_ID);

  let erpFacade = false;
  let coreWorkflow = false;
  if (skipProbes) {
    setErpDomainModFacadeEnabled(false);
    setCoreWorkflowModPagesEnabled(false);
  } else {
    const [erpOk, wfOk] = await Promise.all([
      hasErpDomainModListed ? probeErpDomainModFacadeAvailable() : Promise.resolve(false),
      hasCoreWorkflowListed ? probeCoreWorkflowModAvailable() : Promise.resolve(false),
    ]);
    erpFacade = erpOk;
    coreWorkflow = wfOk;
    setErpDomainModFacadeEnabled(erpFacade);
    setCoreWorkflowModPagesEnabled(coreWorkflow);
  }

  setApprovalModFacadeEnabled(modsList.some((m) => m.id === APPROVAL_BRIDGE_MOD_ID));
  setLanModFacadeEnabled(modsList.some((m) => m.id === LAN_BRIDGE_MOD_ID));
  setModelPaymentModFacadeEnabled(modsList.some((m) => m.id === MODEL_PAYMENT_BRIDGE_MOD_ID));
  setCustomerServiceModPagesEnabled(
    modsList.some((m) => m.id === CUSTOMER_SERVICE_BRIDGE_MOD_ID),
  );
  setOfficeEmployeePackModPagesEnabled(
    modsList.some((m) => m.id === OFFICE_EMPLOYEE_PACK_BRIDGE_MOD_ID),
  );

  modFacadeProbesCompleted = true;
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

export interface ModInfo {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;
  /** 后端 list_mods：mod | employee_pack 等 */
  type?: string;
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
  frontend?: {
    pro_entry_path?: string;
    [key: string]: unknown;
  };
  menu_overrides?: Array<{
    key: string;
    label?: string;
    icon?: string;
    hidden?: boolean;
  }>;
  industry?: {
    id?: string;
    name?: string;
    [key: string]: unknown;
  };
  ui_labels?: Record<string, unknown>;
  ui_starter_pack?: Array<Record<string, unknown>>;
  primary_workflow?: {
    title?: string;
    steps?: Array<string | Record<string, unknown>>;
  };
  workflow_employees?: ModWorkflowEmployee[];
  /** 可选：贡献教程路线、步骤或页内高亮 */
  tutorial?: {
    tracks?: Array<{
      id: string;
      title: string;
      summary?: string;
      description?: string;
      requires_mod_menu?: boolean;
      recommended?: boolean;
    }>;
    steps?: Array<Record<string, unknown>>;
    page_highlights?: Record<string, Array<Record<string, unknown>>>;
  };
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

/** 与后端当前行业对齐：从若干 manifest 中选一个扩展包 */
function pickModMatchingIndustry(
  list: ModInfo[],
  industryId: string,
  preferredModId: string,
): ModInfo | null {
  const sid = String(industryId || '').trim();
  if (!sid || !list.length) return null;
  const candidates = list.filter((m) => String(m.industry?.id || '').trim() === sid);
  if (!candidates.length) return null;
  const pref = String(preferredModId || '').trim();
  const prefHit = candidates.find((m) => String(m.id || '').trim() === pref);
  if (prefHit) return prefHit;
  const primary = candidates.find((m) => m.primary === true);
  if (primary) return primary;
  return candidates[0];
}

export function readEntitledModIdsFromAuthPayload(raw: unknown): string[] {
  if (!raw || typeof raw !== 'object') return [];
  const o = raw as Record<string, unknown>;
  const data =
    o.data && typeof o.data === 'object' && !Array.isArray(o.data)
      ? (o.data as Record<string, unknown>)
      : undefined;
  const list = o.entitled_mod_ids ?? data?.entitled_mod_ids;
  return normalizeEntitledModIds(Array.isArray(list) ? (list as string[]) : undefined);
}

function normalizeEntitledModIds(raw: string[] | undefined): string[] {
  if (!Array.isArray(raw)) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const item of raw) {
    const id = String(item || '').trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

function pickModIdFromEntitled(
  entitledModIds: string[],
  modsList: ModInfo[],
  primaryErpModId: string,
): string {
  const entitledSet = new Set(entitledModIds);
  const selectable = modsList.filter((m) => {
    const id = String(m.id || '').trim();
    if (!id || !isSelectableExtensionModId(id)) return false;
    return entitledSet.size === 0 || entitledSet.has(id);
  });
  if (!selectable.length) return '';

  if (primaryErpModId && entitledSet.has(primaryErpModId)) {
    const erpHit = selectable.find((m) => String(m.id || '').trim() === primaryErpModId);
    if (erpHit) return primaryErpModId;
  }

  const primaryHit = selectable.find(
    (m) => m.primary && entitledSet.has(String(m.id || '').trim()),
  );
  if (primaryHit) return String(primaryHit.id || '').trim();

  return String(selectable[0].id || '').trim();
}

export const useModsStore = defineStore('mods', () => {
  const mods = ref<ModInfo[]>([]);
  const modRoutes = ref<ModRoute[]>([]);
  /** 用户在前端启用「原版模式」：完全隔离 Mod（无请求、无路由、无侧栏/工作流痕迹） */
  const clientModsUiOff = ref(readClientModsUiOff());
  /** 当前会话只启用一个扩展包（空字符串表示未选择） */
  const activeModId = ref(readActiveModId());
  /** 仅在为 true 时表示「已成功拉取过 /api/mods/」；失败时为 false，可再次 initialize */
  const isLoaded = ref(false);
  const loadError = ref<string | null>(null);
  let initInFlight: Promise<void> | null = null;
  let pendingInitOptions: ModsInitializeOptions | null = null;
  let lastInitAccountUsername = '';

  function resolveModsAccountUsername(): string {
    const pending = String(pendingInitOptions?.accountUsername || '').trim();
    if (pending) return pending;
    if (lastInitAccountUsername) return lastInitAccountUsername;
    try {
      const raw = localStorage.getItem('xcagi_market_user_json');
      if (!raw) return '';
      const parsed = JSON.parse(raw) as { username?: string };
      return String(parsed?.username || '').trim();
    } catch {
      return '';
    }
  }

  function findClientPrimaryErpMod(): ModInfo | undefined {
    return mods.value.find(
      (m) => String(m.id || '').trim() === CLIENT_PRIMARY_ERP_MOD_ID,
    );
  }

  /** 侧栏、副窗工作流等应使用此列表；仍为完整拉取结果时用 mods */
  const modsForUi = computed<ModInfo[]>(() => {
    if (clientModsUiOff.value) return [];
    const active = String(activeModId.value || '').trim();
    if (!active) return mods.value;
    const hit = mods.value.find((m) => String(m.id || '').trim() === active);
    if (hit) return [hit];
    if (active === CLIENT_PRIMARY_ERP_MOD_ID) {
      return [findClientPrimaryErpMod() || buildSunbirdClientModStub()];
    }
    return mods.value;
  });

  function setActiveModId(modId: string | null | undefined) {
    const next = String(modId || '').trim();
    activeModId.value = next;
    try {
      if (next) localStorage.setItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY, next);
      else localStorage.removeItem(XCAGI_ACTIVE_EXTENSION_MOD_ID_KEY);
    } catch {
      /* private mode */
    }
  }

  function ensureActiveModSelection() {
    if (clientModsUiOff.value) return;
    if (!mods.value.length) {
      setActiveModId('');
      return;
    }
    const current = String(activeModId.value || '').trim();
    const accountUsername = resolveModsAccountUsername();
    if (isSunbirdAccountUsername(accountUsername)) {
      const sunbird = findClientPrimaryErpMod();
      if (sunbird || current === CLIENT_PRIMARY_ERP_MOD_ID) {
        setActiveModId(CLIENT_PRIMARY_ERP_MOD_ID);
        return;
      }
    }
    const primaryErp = String(
      clientModPolicies.value?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID,
    ).trim();
    const primaryListed = mods.value.some((m) => String(m.id || '').trim() === primaryErp);
    if (
      primaryErp &&
      isProtectedClientModId(primaryErp) &&
      (primaryListed || isClientErpSidebarContext(mods.value.map((m) => String(m.id || '')), primaryErp))
    ) {
      if (
        !current ||
        current === ERP_DOMAIN_BRIDGE_MOD_ID ||
        !isSelectableExtensionModId(current)
      ) {
        setActiveModId(primaryErp);
        return;
      }
    }
    if (current && mods.value.some((m) => String(m.id || '').trim() === current)) {
      // 若误选宿主 bridge，优先改到第一个行业扩展包（bridge 不作为「当前扩展」）
      if (!isSelectableExtensionModId(current)) {
        const ext =
          findClientPrimaryErpMod() ||
          mods.value.find((m) => isSelectableExtensionModId(String(m.id || '')));
        if (ext) setActiveModId(String(ext.id || '').trim());
      }
      return;
    }
    const preferred =
      findClientPrimaryErpMod() ||
      mods.value.find((m) => m.primary && isSelectableExtensionModId(String(m.id || ''))) ||
      mods.value.find((m) => isSelectableExtensionModId(String(m.id || '')));
    setActiveModId(preferred ? String(preferred.id || '').trim() : '');
  }

  async function syncIndustryForActiveMod(): Promise<void> {
    if (clientModsUiOff.value) return;
    const mid = String(activeModId.value || '').trim();
    if (!mid) return;
    const mod = mods.value.find((m) => String(m.id || '').trim() === mid);
    const industryId = String(mod?.industry?.id || '').trim();
    if (!industryId) return;
    try {
      const { useIndustryStore } = await import('@/stores/industry');
      const industryStore = useIndustryStore();
      const current = String(industryStore.currentIndustryId || '').trim();
      if (industryId === current) return;
      const ok = await industryStore.switchIndustry(industryId);
      if (!ok) {
        console.warn(
          '[mods] 同步行业失败',
          industryId,
          industryStore.error || '未知',
        );
      }
    } catch (exc) {
      console.warn('[mods] syncIndustryForActiveMod:', exc);
    }
  }

  /**
   * 企业版登录/会话：按 entitled_mod_ids 与宿主 client_primary_erp_mod_id 选定当前扩展。
   */
  async function applyEntitledActiveMod(
    entitledModIds: string[] | undefined,
    options?: { force?: boolean; accountUsername?: string },
  ): Promise<void> {
    if (clientModsUiOff.value || !mods.value.length) return;

    const username = String(
      options?.accountUsername || pendingInitOptions?.accountUsername || '',
    ).trim();
    const entitled = augmentEntitledModIdsForAccount(
      username,
      normalizeEntitledModIds(entitledModIds),
    );
    if (!entitled.length && !isSunbirdAccountUsername(username)) return;

    await bootstrapHostConfig();

    /** SUNBIRD 演示账号：只要本机已装太阳鸟 pro，始终作为当前扩展（考勤表转换等 Mod 页） */
    if (isSunbirdAccountUsername(username)) {
      const listed = mods.value.some(
        (m) => String(m.id || '').trim() === CLIENT_PRIMARY_ERP_MOD_ID,
      );
      const current = String(activeModId.value || '').trim();
      if (listed) {
        if (current !== CLIENT_PRIMARY_ERP_MOD_ID) {
          setActiveModId(CLIENT_PRIMARY_ERP_MOD_ID);
        }
        await syncIndustryForActiveMod();
        return;
      }
      if (Boolean(options?.force) || pendingInitOptions?.forceFromEntitlements) {
        setActiveModId(CLIENT_PRIMARY_ERP_MOD_ID);
        await syncIndustryForActiveMod();
        if (!entitledRefetchInProgress) {
          entitledRefetchInProgress = true;
          try {
            const refetch = await fetchModsOnce({ skipEntitledApply: true });
            if (
              refetch.ok &&
              mods.value.some((m) => String(m.id || '').trim() === CLIENT_PRIMARY_ERP_MOD_ID)
            ) {
              await syncIndustryForActiveMod();
            }
          } finally {
            entitledRefetchInProgress = false;
          }
        }
        return;
      }
    }
    const primaryErp = String(
      clientModPolicies.value?.client_primary_erp_mod_id || CLIENT_PRIMARY_ERP_MOD_ID,
    ).trim();

    const force = Boolean(options?.force);
    const entitledSet = new Set(entitled);
    const current = String(activeModId.value || '').trim();

    let next = '';
    const sunbirdForce =
      force && isSunbirdAccountUsername(username) && entitledSet.has(CLIENT_PRIMARY_ERP_MOD_ID);
    if (sunbirdForce) {
      next = CLIENT_PRIMARY_ERP_MOD_ID;
    } else if (force && entitledSet.has(CLIENT_PRIMARY_ERP_MOD_ID)) {
      const listed = mods.value.some(
        (m) => String(m.id || '').trim() === CLIENT_PRIMARY_ERP_MOD_ID,
      );
      if (listed) next = CLIENT_PRIMARY_ERP_MOD_ID;
    }
    if (!next && (force || !current || !entitledSet.has(current))) {
      next = pickModIdFromEntitled(entitled, mods.value, primaryErp);
    }
    if (!next) return;

    const listedNext = mods.value.some((m) => String(m.id || '').trim() === next);
    if (!listedNext && sunbirdForce) {
      setActiveModId(next);
      await syncIndustryForActiveMod();
      if (!entitledRefetchInProgress) {
        entitledRefetchInProgress = true;
        try {
          const refetch = await fetchModsOnce({ skipEntitledApply: true });
          if (refetch.ok && mods.value.some((m) => String(m.id || '').trim() === next)) {
            await syncIndustryForActiveMod();
          }
        } finally {
          entitledRefetchInProgress = false;
        }
      }
      return;
    }

    if (next !== current) {
      setActiveModId(next);
      await syncIndustryForActiveMod();
    } else if (force) {
      await syncIndustryForActiveMod();
    }
  }

  /**
   * 仅在 activeModId 为空时按 server 当前行业回填一个 active mod：
   * 用户已经在 Settings 单选过的 mod，不应被静默换回（此前实现会在每次刷新都
   * 把 activeModId 拉回到与 server 行业匹配的 mod，导致选了 taiyangniao-pro
   * 后下次刷新被换成 sz-qsm-pro）。
   *
   * 用户主动通过 onActiveModChange 切 mod 时，会先 setActiveModId(next)，
   * 再调用 industryStore.switchIndustry——server 行业在那一刻就跟着走了，
   * 因此这里不需要"刷新对齐"。
   */
  async function syncActiveModWithServerIndustry(): Promise<void> {
    if (clientModsUiOff.value || !mods.value.length) return;
    const current = String(activeModId.value || '').trim();
    if (current) {
      // 已经有用户选定的 active mod，server 行业以它为准，不再反向覆盖
      return;
    }
    try {
      const response = await apiFetch('/api/system/industry', {
        timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS,
      });
      if (!response.ok) return;
      const payload = await response.json();
      const serverId =
        payload?.success && payload?.data?.id != null
          ? String(payload.data.id).trim()
          : '';
      if (!serverId) return;
      const picked = pickModMatchingIndustry(mods.value, serverId, '');
      if (picked) {
        setActiveModId(String(picked.id || '').trim());
      }
    } catch {
      /* 忽略：保持 ensureActiveModSelection 结果 */
    }
  }

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

  async function fetchModsOnce(fetchOpts?: FetchModsOptions): Promise<{
    ok: boolean
    modsDisabled?: boolean
    /** 连接被拒绝/中断等，适合稍长间隔再试（例如刚启动 Vite 或 run.py） */
    transportError?: boolean
  }> {
    try {
      const response = await apiFetch('/api/mods/', { timeoutMs: DEFAULT_MOD_API_TIMEOUT_MS });
      if (!response.ok) {
        loadError.value = `HTTP ${response.status}`;
        return { ok: false };
      }
      const data = await response.json();
      if (!data.success) {
        // 后端 list_mods 异常时返回 message；部分接口用 error —— 都要展示，避免统一成含糊的「列表失败」
        const apiErr =
          typeof data.error === 'string'
            ? data.error
            : typeof data.message === 'string'
              ? data.message
              : '';
        loadError.value = apiErr || '列表失败';
        return { ok: false };
      }
      if (data.mods_disabled === true) {
        mods.value = [];
        setActiveModId('');
        loadError.value = 'Mod 扩展已关闭（XCAGI_DISABLE_MODS）';
        return { ok: true, modsDisabled: true };
      }
      mods.value = Array.isArray(data.data) ? data.data : [];
      ensureActiveModSelection();
      const active = String(activeModId.value || '').trim();
      const postTasks: Promise<unknown>[] = [];
      if (!fetchOpts?.skipEntitledApply) {
        postTasks.push(
          applyEntitledActiveMod(pendingInitOptions?.entitledModIds, {
            force: pendingInitOptions?.forceFromEntitlements ?? false,
            accountUsername: pendingInitOptions?.accountUsername,
          }),
        );
      }
      if (!active || !mods.value.some((m) => String(m.id || '').trim() === active)) {
        postTasks.push(syncActiveModWithServerIndustry());
      }
      if (postTasks.length) {
        await Promise.all(postTasks);
      }
      loadError.value = null;
      void fetchPlatformShellCapabilities(true).catch((e) =>
        console.warn('[mods] platform-shell capabilities:', e),
      );
      await applyModFacadeFlagsFromListing(mods.value, activeModId.value);
      applyEditionPackPlatformShell(mods.value.map((m) => String(m.id || '')));
      if (typeof performance !== 'undefined' && performance.mark) {
        performance.mark('mods_list_ok');
      }
      return { ok: true };
    } catch (error) {
      if (isApiFetchTimeoutError(error)) {
        loadError.value = 'Mod 列表请求超时，请确认后端已启动';
        console.warn('[mods] /api/mods/ 超时:', error);
        return { ok: false, transportError: true };
      }
      console.error('Failed to fetch mods:', error);
      const raw = error instanceof Error ? error.message : '网络错误';
      const looksLikeTransport =
        raw === 'Failed to fetch' ||
        /networkerror|load failed/i.test(raw) ||
        /socket|ecconn|econnrefused|aborted/i.test(raw);
      loadError.value = looksLikeTransport ? '无法连接后端，请检查服务是否启动' : raw;
      return { ok: false, transportError: looksLikeTransport };
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
  async function readLoadingStatusPayload() {
    const d = await fetchModLoadingStatusShared();
    if (!d) return null;
    return d as {
      discovered_mod_ids?: string[];
      mods_loaded?: number;
      load_mismatch?: boolean;
      load_errors?: unknown[];
      manifest_errors?: unknown[];
      blueprint_errors?: unknown[];
      partial_failure?: boolean;
      mods_disabled?: boolean;
    };
  }

  async function confirmServerReportsZeroDiscoveredMods(): Promise<boolean> {
    try {
      const d = await readLoadingStatusPayload();
      if (!d) return false;
      const discovered = Array.isArray(d.discovered_mod_ids) ? d.discovered_mod_ids : [];
      return discovered.length === 0;
    } catch {
      return false;
    }
  }

  async function shouldRetryModsListWhenEmpty(): Promise<boolean> {
    try {
      const d = await readLoadingStatusPayload();
      if (!d) return false;
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
      const d = await readLoadingStatusPayload();
      if (!d) return null;
      return summarizeModLoadingData(d as Record<string, unknown>);
    } catch {
      return null;
    }
  }

  async function fetchModsWithRetry(
    fetchOpts?: FetchModsOptions,
  ): Promise<{ ok: boolean; modsDisabled?: boolean }> {
    let r = await fetchModsOnce(fetchOpts);
    if (r.modsDisabled) return r;
    if (!r.ok) {
      await delay(r.transportError ? 1200 : 400);
      r = await fetchModsOnce(fetchOpts);
    }
    if (r.modsDisabled) return r;
    if (r.ok && mods.value.length === 0) {
      const mismatch = await shouldRetryModsListWhenEmpty();
      if (mismatch) {
        await delay(500);
        r = await fetchModsOnce(fetchOpts);
        if (r.modsDisabled) return r;
        if (r.ok && mods.value.length === 0) {
          await delay(800);
          r = await fetchModsOnce(fetchOpts);
        }
      }
    }
    return r;
  }

  async function fetchModRoutes(): Promise<void> {
    const data = await fetchModRoutesPayloadShared();
    if (data) {
      modRoutes.value = data;
    }
  }

  function setClientModsUiOff(off: boolean) {
    clientModsUiOff.value = off;
    if (off) {
      mods.value = [];
      modRoutes.value = [];
      setActiveModId('');
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

  /** 同一 manifest.menu.id 冲突时，优先保留的 Mod（靠前优先） */
  const DUPLICATE_MENU_MOD_PRIORITY: Record<string, readonly string[]> = {
    'mod-workflow-visualization': [
      'xcagi-workflow-visualization-bridge',
      'xcagi-core-workflow-employees',
    ],
  };

  function modPriorityForMenuEntry(menuId: string, modId: string): number {
    const order = DUPLICATE_MENU_MOD_PRIORITY[menuId];
    if (!order) return 50;
    const idx = order.indexOf(modId);
    return idx >= 0 ? idx : 100;
  }

  /** 侧栏 Mod 菜单来源：已选行业扩展时仅该包 + AI 员工触点；不遍历全部 bridge */
  function modsContributingSidebarMenu(): ModInfo[] {
    const ui = modsForUi.value;
    const full = mods.value;
    const active = String(activeModId.value || '').trim();

    const pickForActive = (pool: ModInfo[]): ModInfo[] =>
      pool.filter((m) => {
        const id = String(m.id || '').trim();
        if (!id) return false;
        if (id === active) return true;
        if (isAuxEmployeePackModId(id)) return true;
        return false;
      });

    if (active && isSelectableExtensionModId(active)) {
      const fromUi = pickForActive(ui);
      if (fromUi.length) return fromUi;
      const fromFull = pickForActive(full);
      if (fromFull.length) return fromFull;
      if (active === CLIENT_PRIMARY_ERP_MOD_ID) {
        const stub = findClientPrimaryErpMod() || buildSunbirdClientModStub();
        return [stub, ...full.filter((m) => isAuxEmployeePackModId(String(m.id || '')))];
      }
      return [];
    }
    const installedIds = mods.value.map((m) => String(m.id || '').trim()).filter(Boolean);
    if (isClientErpSidebarContext(installedIds, activeModId.value)) {
      const extensions = ui.filter((m) => isSelectableExtensionModId(String(m.id || '')));
      if (extensions.length) return extensions;
    }
    return ui;
  }

  function shouldHideModMenuEntry(menuId: string): boolean {
    const installedIds = mods.value.map((m) => String(m.id || '').trim()).filter(Boolean);
    return shouldSuppressClientErpModMenuId(menuId, installedIds, activeModId.value);
  }

  /**
   * 侧栏 Mod 菜单项：来自各 manifest.frontend.menu（与 routes.js 的 modMenu 保持一致）。
   * 多 Mod 时条目合并；10–20 个 Mod 时建议每包 menu 控制在合理数量并由 menu_overrides 隐藏宿主重复项。
   */
  function getModMenu() {
    const menus: Array<{
      id: string;
      label: string;
      icon: string;
      path: string;
      modId: string;
    }> = [];

    const byMenuId = new Map<
      string,
      { item: NonNullable<ModInfo['menu']>[number]; modId: string }
    >();

    for (const mod of modsContributingSidebarMenu()) {
      if (!mod.menu || !Array.isArray(mod.menu)) continue;
      const modId = String(mod.id || '').trim();
      for (const item of mod.menu) {
        const menuId = String(item.id || '').trim();
        if (!menuId || shouldHideModMenuEntry(menuId)) continue;
        const existing = byMenuId.get(menuId);
        if (
          !existing ||
          modPriorityForMenuEntry(menuId, modId) <
            modPriorityForMenuEntry(menuId, existing.modId)
        ) {
          byMenuId.set(menuId, { item, modId });
        }
      }
    }

    for (const { item, modId } of byMenuId.values()) {
      menus.push({
        ...item,
        modId,
      });
    }

    if (import.meta.env.DEV) {
      validateModMenuPaths(menus);
    }

    return menus;
  }

  const warnedModMenuPathKeys = new Set<string>();

  /** DEV：manifest.menu.path 应落在 /mod/{modId}/ 下；员工包可复用宿主 pro_entry_path */
  function validateModMenuPaths(
    menus: Array<{ path?: string; modId?: string; label?: string }>,
  ) {
    for (const item of menus) {
      const path = String(item.path || '').trim();
      const modId = String(item.modId || '').trim();
      if (!path || !modId) continue;
      const expectedPrefix = `/mod/${modId}/`;
      if (path.startsWith(expectedPrefix) || path === `/mod/${modId}`) continue;
      const mod = mods.value.find((m) => String(m.id || '').trim() === modId);
      const proEntry =
        String(mod?.frontend?.pro_entry_path || '').trim() ||
        (modId === 'wechat-contacts-ai-employee'
          ? '/wechat-contacts'
          : modId === 'lan-gate-ai-employee'
            ? '/lan-gate'
            : '');
      if (isHostMountedModMenuPath(path, proEntry)) continue;
      const warnKey = `${modId}\0${path}`;
      if (warnedModMenuPathKeys.has(warnKey)) continue;
      warnedModMenuPathKeys.add(warnKey);
      console.warn(
        `[mods] menu path "${path}" does not match mod id prefix ${expectedPrefix} (${item.label || modId})`,
      );
    }
  }

  async function initialize(force = false, options?: ModsInitializeOptions) {
    pendingInitOptions = options ?? null;
    const uname = String(options?.accountUsername || '').trim();
    if (uname) lastInitAccountUsername = uname;
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
      setActiveModId('');
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
        setActiveModId('');
        loadError.value = null;
        isLoaded.value = true;
        return;
      }
      if (force) {
        isLoaded.value = false;
        modFacadeProbesCompleted = false;
      }
      const r = await fetchModsWithRetry();
      await fetchModRoutes();
      if (r.modsDisabled) {
        setActiveModId('');
        isLoaded.value = true;
        return;
      }
      const ok = r.ok;
      if (ok) {
        ensureActiveModSelection();
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
      try {
        const { registerAllModRoutesFromGlob, registerModRoutes } = await import(
          '@/router/registerModRoutes'
        );
        const router = (await import('@/router')).default;
        await registerAllModRoutesFromGlob(router);
        if (modRoutes.value.length > 0) {
          await registerModRoutes(router, modRoutes.value);
        }
      } catch (e) {
        console.warn('[mods] registerModRoutes after initialize failed:', e);
      }
    })();

    try {
      await initInFlight;
    } finally {
      initInFlight = null;
      pendingInitOptions = null;
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
    activeModId,
    clientModsUiOff,
    setActiveModId,
    setClientModsUiOff,
    isLoaded,
    loadError,
    fetchMods: fetchModsWithRetry,
    fetchModRoutes,
    getModMenu,
    initialize,
    refresh,
    applyLoadingStatusPreview,
    syncActiveModWithServerIndustry,
    applyEntitledActiveMod,
  };
});
