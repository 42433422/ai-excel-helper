<template>
  <div class="page-view settings-page" id="view-settings">
    <div class="page-content settings-page__scroll">
      <div class="settings-layout">
        <aside class="settings-profile" aria-label="账号">
          <button
            type="button"
            class="settings-profile__avatar"
            :class="{ 'is-guest': !isLoggedIn, 'is-loading': accountLoading || avatarUploading }"
            :disabled="!isLoggedIn || accountLoading || avatarUploading"
            :title="isLoggedIn ? '点击更换头像' : '登录后可设置头像'"
            @click="onAvatarClick"
          >
            <img
              v-if="profileAvatarUrl"
              :src="profileAvatarUrl"
              alt=""
              class="settings-profile__avatar-img"
            >
            <span v-else-if="avatarInitial" class="settings-profile__avatar-letter">{{ avatarInitial }}</span>
            <i v-else class="fa fa-user" aria-hidden="true"></i>
            <span v-if="isLoggedIn" class="settings-profile__avatar-hint">更换</span>
          </button>
          <input
            ref="avatarInputRef"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            class="settings-profile__avatar-input"
            tabindex="-1"
            aria-hidden="true"
            @change="onAvatarFileChange"
          >
          <p class="settings-profile__name settings-profile__brand">{{ profileBrandTitle }}</p>
          <p class="settings-profile__sub">{{ profileSubline }}</p>
          <div class="settings-profile__actions">
            <button
              v-if="isLoggedIn"
              type="button"
              class="settings-profile__btn settings-profile__btn--ghost"
              :disabled="logoutLoading"
              @click="onLogout"
            >
              {{ logoutLoading ? '退出中…' : '退出登录' }}
            </button>
            <router-link
              v-else
              class="settings-profile__btn settings-profile__btn--primary"
              :to="loginRoute"
            >
              登录
            </router-link>
          </div>
        </aside>

        <div class="settings-layout__main">
        <header class="settings-page__hero">
          <h1 class="settings-page__title">系统设置</h1>
        </header>

        <div class="settings-list">
        <details
          v-if="isLoggedIn"
          id="settings-profile-home"
          class="settings-card"
          data-tutorial-id="settings-profile-home"
          open
        >
          <summary class="settings-row">
            <span class="settings-row__icon settings-row__icon--indigo" aria-hidden="true">
              <i class="fa fa-id-card"></i>
            </span>
            <span class="settings-row__label">个人主页</span>
            <span class="settings-row__meta">{{ profileHomeSummary }}</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>
          <div class="settings-card__body settings-card__body--list">
            <div class="settings-profile-form">
              <div class="settings-profile-form__editable">
                <label class="settings-profile-form__field">
                  <span class="settings-profile-form__label">展示名称</span>
                  <input
                    v-model="profileDisplayNameDraft"
                    class="settings-profile-form__input"
                    type="text"
                    maxlength="64"
                    placeholder="在侧栏与协作中显示的名称"
                    autocomplete="name"
                  >
                </label>
                <label class="settings-profile-form__field">
                  <span class="settings-profile-form__label">邮箱</span>
                  <input
                    v-model="profileEmailDraft"
                    class="settings-profile-form__input"
                    type="email"
                    maxlength="128"
                    placeholder="可选，用于找回账号"
                    autocomplete="email"
                  >
                </label>
              </div>
              <div class="settings-profile-form__readonly" aria-readonly="true">
                <span class="settings-profile-form__label">登录名</span>
                <span class="settings-profile-form__readonly-value">{{
                  localUser?.username || '—'
                }}</span>
                <p class="settings-profile-form__hint muted">
                  由修茈市场/本机账号绑定，此处不可修改。
                </p>
              </div>
              <div class="settings-profile-form__actions">
                <button
                  type="button"
                  class="settings-profile-form__submit"
                  :disabled="!profileFormDirty || profileSaving"
                  @click="saveProfile"
                >
                  {{ profileSaving ? '保存中…' : '保存资料' }}
                </button>
              </div>
            </div>
          </div>
        </details>

        <details
          id="settings-model-payment"
          class="settings-card"
          data-tutorial-id="settings-model-payment"
          open
        >
          <summary class="settings-row">
            <span class="settings-row__icon settings-row__icon--blue" aria-hidden="true">
              <i class="fa fa-credit-card"></i>
            </span>
            <span class="settings-row__label">模型服务</span>
            <span class="settings-row__meta">钱包 · 套餐</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>
          <div class="settings-card__body settings-card__body--flush">
            <ModModelPaymentView embedded />
          </div>
        </details>

        <details
          class="settings-card"
          data-tutorial-id="settings-intent"
          open
        >
          <summary class="settings-row">
            <span class="settings-row__icon settings-row__icon--purple" aria-hidden="true">
              <i class="fa fa-magic"></i>
            </span>
            <span class="settings-row__label">AI 意图能力</span>
            <span v-if="currentIntentIndustryLabel" class="settings-row__pill" @click.stop>
              {{ currentIntentIndustryLabel }}
              <template v-if="currentIndustryUnit"> · {{ currentIndustryUnit }}</template>
            </span>
            <span v-else class="settings-row__meta">只读展示</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>

          <div class="settings-card__body">
        <div v-if="!currentIndustryConfig" class="intent-showcase-state muted">当前行业未加载，请刷新或检查后端行业配置</div>
        <div v-else class="intent-showcase-grid">
          <article
            v-for="entry in intentPackageEntries"
            :key="entry.key"
            class="intent-showcase-tile"
            :class="{ 'is-enabled': entry.enabled, 'is-disabled': !entry.enabled }"
          >
            <div class="intent-tile-top">
              <span class="intent-tile-icon" aria-hidden="true">
                <i class="fa" :class="entry.iconClass"></i>
              </span>
              <div class="intent-tile-title-wrap">
                <h3 class="intent-tile-title">{{ entry.name }}</h3>
                <span
                  class="intent-tile-status"
                  :class="entry.enabled ? 'intent-tile-status--on' : 'intent-tile-status--off'"
                >
                  {{ entry.enabled ? '已接入' : '未接入' }}
                </span>
              </div>
            </div>
            <p class="intent-tile-desc">{{ entry.description }}</p>
            <div class="intent-tile-keywords">
              <span
                v-for="kw in entry.keywords"
                :key="`${entry.key}-${kw}`"
                class="intent-chip"
              >{{ kw }}</span>
              <span v-if="!entry.keywords.length" class="intent-chip intent-chip--empty">暂无示例词</span>
            </div>
          </article>
        </div>
          </div>
        </details>

        <details
          class="settings-card"
          data-tutorial-id="settings-basic"
          open
        >
          <summary class="settings-row">
            <span class="settings-row__icon settings-row__icon--green" aria-hidden="true">
              <i class="fa fa-sliders"></i>
            </span>
            <span class="settings-row__label">基本设置</span>
            <span class="settings-row__meta">{{ basicSettingsSummary }}</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>

          <div class="settings-card__body settings-card__body--list">
        <div class="settings-item-list">
          <div class="settings-item">
            <span class="settings-item__icon settings-row__icon--cyan" aria-hidden="true">
              <i class="fa fa-columns"></i>
            </span>
            <label class="settings-item__label" for="settings-sidebar-theme">侧栏样式</label>
            <select
              id="settings-sidebar-theme"
              v-model="sidebarThemePreset"
              class="settings-item__control settings-item__control--select"
              @change="onSidebarThemeChange"
            >
              <option v-for="theme in SIDEBAR_THEME_OPTIONS" :key="theme.value" :value="theme.value">
                {{ theme.label }}
              </option>
            </select>
          </div>

          <div v-if="showCompanyBrandEditor" class="settings-item">
            <span class="settings-item__icon settings-row__icon--amber" aria-hidden="true">
              <i class="fa fa-building"></i>
            </span>
            <label class="settings-item__label" for="settings-company-brand">企业品牌名</label>
            <div class="settings-item__control-group">
              <input
                id="settings-company-brand"
                v-model="companyBrandDraft"
                class="settings-item__control settings-item__control--text"
                type="text"
                maxlength="64"
                placeholder="对外展示的企业名称"
              >
              <button
                type="button"
                class="settings-item__save-btn"
                :disabled="companyBrandSaving || !companyBrandDirty"
                @click="saveCompanyBrand"
              >
                {{ companyBrandSaving ? '保存中…' : '保存' }}
              </button>
            </div>
          </div>

          <div class="settings-item">
            <span class="settings-item__icon settings-row__icon--indigo" aria-hidden="true">
              <i class="fa fa-user-circle"></i>
            </span>
            <label class="settings-item__label" for="settings-assistant-name">助手名称</label>
            <input
              id="settings-assistant-name"
              v-model="assistantName"
              class="settings-item__control settings-item__control--text"
              type="text"
              maxlength="24"
              placeholder="修茈"
            >
          </div>

          <div class="settings-item settings-item--readonly">
            <span class="settings-item__icon settings-row__icon--slate" aria-hidden="true">
              <i class="fa fa-desktop"></i>
            </span>
            <span class="settings-item__label">系统名称</span>
            <span class="settings-item__value">{{ systemDisplayName }}</span>
          </div>

          <div v-if="desktopDatabaseVisible" class="settings-item settings-item--readonly">
            <span class="settings-item__icon settings-row__icon--slate" aria-hidden="true">
              <i class="fa fa-database"></i>
            </span>
            <span class="settings-item__label">数据存储</span>
            <span class="settings-item__value">{{ databaseStorageLabel }}</span>
          </div>

          <div v-if="desktopDatabaseVisible" class="settings-item settings-item--readonly">
            <span class="settings-item__icon settings-row__icon--slate" aria-hidden="true">
              <i class="fa fa-folder-open-o"></i>
            </span>
            <span class="settings-item__label">数据库路径</span>
            <span class="settings-item__value settings-item__value--mono" :title="currentDbPath">{{ currentDbPath }}</span>
          </div>

          <div class="settings-item">
            <span class="settings-item__icon settings-row__icon--violet" aria-hidden="true">
              <i class="fa fa-cloud"></i>
            </span>
            <label class="settings-item__label" for="settings-ai-mode">AI 模式</label>
            <select
              id="settings-ai-mode"
              v-model="aiMode"
              class="settings-item__control settings-item__control--select"
            >
              <option value="online">在线（DeepSeek）</option>
              <option value="offline">离线（本地）</option>
            </select>
          </div>
        </div>

        <details v-if="!clientModsUiOff" class="settings-card settings-card--nested">
          <summary class="settings-row settings-row--nested">
            <span class="settings-row__icon settings-row__icon--orange" aria-hidden="true">
              <i class="fa fa-puzzle-piece"></i>
            </span>
            <span class="settings-row__label">扩展与 Mod</span>
            <span class="settings-row__meta">{{ modSettingsFoldMeta }}</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>
          <div class="settings-card__body settings-card__body--nested">
            <p v-if="modRoutesStatusText" class="muted mod-routes-status text-warning">
              {{ modRoutesStatusText }}
            </p>
            <button
              v-if="showModRoutesRetry"
              type="button"
              class="btn btn-secondary btn-sm"
              :disabled="modRoutesRetrying"
              @click="retryModRoutesLoad"
            >
              {{ modRoutesRetrying ? '重试中…' : '重试加载 Mod 与路由' }}
            </button>

            <section v-if="hostBridgeMods.length" class="mod-fold-section">
              <div class="mod-fold-section-head">
                <span class="mod-ui-off-label">宿主基础能力包</span>
                <span class="mod-host-pack-stat">
                  {{ hostBridgeInstalledCount }}/{{ hostBridgeExpectedCount }} 已就绪
                </span>
              </div>
              <div class="mod-host-pack-bar">
                <button type="button" class="btn btn-secondary btn-sm" @click="hostPackExpanded = !hostPackExpanded">
                  {{ hostPackExpanded ? '收起' : '清单' }}
                </button>
                <button type="button" class="btn btn-link btn-sm" @click="goHostPackOnboarding">一键装齐</button>
              </div>
              <ul v-if="hostPackExpanded" class="mod-host-pack-list">
                <li v-for="mod in hostBridgeMods" :key="mod.id" class="mod-host-pack-row">
                  <span class="mod-host-pack-name">{{ mod.name || mod.id }}</span>
                  <button
                    type="button"
                    class="btn btn-danger btn-sm mod-single-uninstall"
                    :disabled="uninstallingModId === mod.id || isProtectedClientModId(mod.id)"
                    @click="onUninstallMod(mod.id)"
                  >
                    {{ uninstallingModId === mod.id ? '卸载中…' : '卸载' }}
                  </button>
                </li>
              </ul>
            </section>

            <section v-if="workflowEmployeeMods.length" class="mod-fold-section mod-fold-section--inline">
              <span class="mod-ui-off-label">工作流员工</span>
              <span class="muted">共 {{ workflowEmployeeMods.length }} 个 ·</span>
              <button type="button" class="btn btn-link btn-sm" @click="goModStore">扩展市场</button>
            </section>

            <section class="mod-fold-section">
              <div class="mod-fold-section-head">
                <span class="mod-ui-off-label">行业扩展包</span>
                <button type="button" class="btn btn-link btn-sm" @click="goModStore">扩展市场</button>
              </div>
              <div v-if="selectableExtensionMods.length" class="mod-single-list">
                <div
                  v-for="mod in selectableExtensionMods"
                  :key="mod.id"
                  class="mod-single-item"
                  :class="{ active: activeModId === mod.id }"
                >
                  <label class="mod-single-main">
                    <input
                      type="radio"
                      name="active-mod-id"
                      :value="mod.id"
                      :checked="activeModId === mod.id"
                      @change="onActiveModChange(mod.id)"
                    >
                    <span class="mod-single-text">{{ mod.name || mod.id }}</span>
                  </label>
                  <button
                    type="button"
                    class="btn btn-danger btn-sm mod-single-uninstall"
                    :disabled="uninstallingModId === mod.id || isProtectedClientModId(mod.id)"
                    @click="onUninstallMod(mod.id)"
                  >
                    {{ uninstallingModId === mod.id ? '卸载中…' : '卸载' }}
                  </button>
                </div>
              </div>
              <p v-else class="muted mod-single-empty">
                <template v-if="loadError">加载失败，请重试 Mod 与路由。</template>
                <template v-else>暂无行业扩展包。</template>
              </p>
            </section>
          </div>
        </details>

        <div class="settings-card__footer">
          <button class="settings-primary-btn" type="button" @click="saveSettings" :disabled="loading">
            {{ loading ? '保存中…' : '保存设置' }}
          </button>
        </div>
          </div>
        </details>

        <details class="settings-card">
          <summary class="settings-row">
            <span class="settings-row__icon settings-row__icon--amber" aria-hidden="true">
              <i class="fa fa-flask"></i>
            </span>
            <span class="settings-row__label">蒸馏模型版本</span>
            <span class="settings-row__meta">训练产物</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>
          <div class="settings-card__body settings-card__body--compact">
            <p v-if="loadingVersions" class="muted">加载中...</p>
            <p v-else-if="versionsError" class="muted">{{ versionsError }}</p>
            <p v-else-if="versions.length === 0" class="muted">暂无训练产物</p>
            <div v-else class="settings-table-wrap">
              <table class="data-table settings-table">
                <thead>
                  <tr><th>文件</th><th>说明</th><th>修改时间</th><th>大小</th></tr>
                </thead>
                <tbody>
                  <tr v-for="v in versions" :key="v.name">
                    <td>{{ v.name }}</td>
                    <td>{{ v.label }}</td>
                    <td>{{ v.modified || '-' }}</td>
                    <td>{{ v.size_kb != null ? `${v.size_kb} KB` : '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="muted settings-meta-line">已积累蒸馏样本数：{{ sampleCount }}</p>
            <p v-if="sampleCountWarning" class="muted settings-meta-line">{{ sampleCountWarning }}</p>
          </div>
        </details>

        <details class="settings-card settings-card--about">
          <summary
            class="settings-row about-debug-entry"
            @click="handleAboutHeaderClick"
          >
            <span class="settings-row__icon settings-row__icon--slate" aria-hidden="true">
              <i class="fa fa-info-circle"></i>
            </span>
            <span class="settings-row__label">关于</span>
            <span class="settings-row__meta">8.0.0</span>
            <span class="settings-row__arrow" aria-hidden="true"></span>
          </summary>
          <div class="settings-card__body settings-card__body--compact">
            <p class="settings-about-line">{{ systemDisplayName }}</p>
            <p class="muted settings-about-hint">连点「关于」5 次可进入调试页面（仅本地流程模拟）</p>
          </div>
        </details>
        </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onActivated, onBeforeUnmount, ref, computed, watch, nextTick } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authApi, type User } from '../api/auth';
import { LS_MARKET_USER_JSON } from '../api/marketAccount';
import ModModelPaymentView from '@mod-views/xcagi-model-payment-bridge/ModelPaymentView.vue';
import { storeToRefs } from 'pinia';
import api, { ApiError } from '../api';
import { buildFullApiUrl } from '@/api/core';
import { systemApi, type Industry as ApiIndustry } from '../api/system';
import { intentPackagesApi, type IntentPackage as ApiIntentPackage } from '../api/intentPackages';
import { useIndustryStore } from '../stores/industry';
import {
  SIDEBAR_THEME_OPTIONS,
  readStoredSidebarTheme,
  persistSidebarTheme,
  applySidebarTheme,
} from '@/utils/sidebarTheme';
import { useModsStore } from '@/stores/mods';
import { useAccountProfileStore } from '@/stores/accountProfile';
import { appAlert, appConfirm } from '@/utils/appDialog';
import { DEFAULT_INDUSTRY_ID } from '@/constants/industryDefaults';
import { getIndustryPreset } from '@/constants/industryPresets';
import { isProtectedClientModId } from '@/constants/protectedMods';
import {
  isSunbirdAccountUsername,
  SUNBIRD_CLIENT_MOD_ID,
  augmentEntitledModIdsForAccount,
} from '@/constants/accountModBinding';
import {
  expectedHostBridgeModIds,
  isHostBridgeModId,
  isSelectableExtensionModId,
  isWorkflowEmployeeModId,
} from '@/constants/genericModPack';

const industryStore = useIndustryStore();
const accountProfileStore = useAccountProfileStore();
const router = useRouter();
const route = useRoute();

type ManifestIndustry = {
  id?: string | number
  name?: string
  units?: { primary?: string }
  intent_keywords?: IntentKeywordMap
  [key: string]: unknown
}

type IntentKeywordMap = {
  create_order?: string | string[]
  quantity_unit?: string | string[]
  print_label?: string | string[]
  [key: string]: unknown
}

type IntentPackageKey = 'base' | 'industry' | 'product' | 'quantity' | 'customer'

type IntentPackageState = {
  name: string
  iconClass: string
  description: string
  enabled: boolean
  keywords: string[]
}

type DistillationVersion = {
  name: string
  label?: string
  modified?: string
  size_kb?: number
}

type ApiMessageResult = {
  success?: boolean
  message?: string
  error?: string
}

function errorMessage(error: unknown, fallback = '未知错误'): string {
  return error instanceof Error ? error.message : String(error || fallback)
}

const localUser = ref<User | null>(null);
const sessionValid = ref(false);
const accountLoading = ref(true);
const logoutLoading = ref(false);
const companyBrandDraft = ref('');
const companyBrandSaving = ref(false);
const avatarInputRef = ref<HTMLInputElement | null>(null);
const avatarUploading = ref(false);
const avatarCacheBust = ref(0);
const profileDisplayNameDraft = ref('');
const profileEmailDraft = ref('');
const profileSaving = ref(false);

function unwrapUserFromMe(res: unknown): User | null {
  if (!res || typeof res !== 'object') return null;
  const o = res as Record<string, unknown>;
  const data = o.data as Record<string, unknown> | undefined;
  const u = (data?.user ?? o.user) as User | undefined;
  if (!u || typeof u !== 'object') return null;
  const username = String(u.username || '').trim();
  return username ? u : null;
}

function readMarketUserFromStorage(): User | null {
  try {
    const raw = window.localStorage.getItem(LS_MARKET_USER_JSON);
    if (!raw) return null;
    const u = JSON.parse(raw) as Record<string, unknown>;
    const username = String(u.username || '').trim();
    if (!username) return null;
    return {
      id: Number(u.id) || 0,
      username,
      display_name: String(u.display_name || username).trim() || username,
      email: String(u.email || '').trim(),
      role: 'user',
      is_active: true,
    };
  } catch {
    return null;
  }
}

function userFromSessionValidatePayload(res: unknown): User | null {
  if (!res || typeof res !== 'object') return null;
  const o = res as Record<string, unknown>;
  const ok = o.success === true || o.valid === true;
  if (!ok) return null;
  const data = o.data as Record<string, unknown> | undefined;
  const username = String(data?.username || '').trim();
  if (!username) return readMarketUserFromStorage();
  const uid = data?.user_id;
  return {
    id: uid != null ? Number(uid) : 0,
    username,
    display_name: username,
    email: '',
    role: 'user',
    is_active: true,
  };
}

function applyAccountMetaFromAuthPayload(res: unknown) {
  if (!res || typeof res !== 'object') return;
  const o = res as Record<string, unknown>;
  const base =
    o.data && typeof o.data === 'object' && !Array.isArray(o.data)
      ? (o.data as Record<string, unknown>)
      : {};
  accountProfileStore.applyFromMeData({
    ...base,
    account_kind: o.account_kind ?? base.account_kind,
    company_brand: o.company_brand ?? base.company_brand,
    market_is_admin: o.market_is_admin ?? base.market_is_admin,
    market_is_enterprise: o.market_is_enterprise ?? base.market_is_enterprise,
    impersonating_market_user_id:
      o.impersonating_market_user_id ?? base.impersonating_market_user_id,
    impersonating_username: o.impersonating_username ?? base.impersonating_username,
  });
}

async function hydrateUserFromSessionValidate(): Promise<boolean> {
  try {
    const res = await authApi.validateSession();
    const user = userFromSessionValidatePayload(res);
    if (!user) {
      sessionValid.value = false;
      return false;
    }
    sessionValid.value = true;
    localUser.value = user;
    applyAccountMetaFromAuthPayload(res);
    companyBrandDraft.value = accountProfileStore.companyBrand || '';
    return true;
  } catch {
    sessionValid.value = false;
    return false;
  }
}

const isLoggedIn = computed(() => Boolean(localUser.value) || sessionValid.value);

function syncProfileDraftsFromUser(u: User | null) {
  if (!u) {
    profileDisplayNameDraft.value = '';
    profileEmailDraft.value = '';
    return;
  }
  profileDisplayNameDraft.value = String(u.display_name || u.username || '').trim();
  profileEmailDraft.value = String(u.email || '').trim();
}

async function loadLocalUser() {
  accountLoading.value = true;
  sessionValid.value = false;
  try {
    const res = await authApi.getCurrentUser();
    localUser.value = unwrapUserFromMe(res);
    if (res?.success && res.data && typeof res.data === 'object') {
      applyAccountMetaFromAuthPayload(res);
      companyBrandDraft.value = accountProfileStore.companyBrand || '';
    }
    if (localUser.value) {
      sessionValid.value = true;
      syncProfileDraftsFromUser(localUser.value);
    } else {
      await hydrateUserFromSessionValidate();
      syncProfileDraftsFromUser(localUser.value);
    }
  } catch {
    localUser.value = null;
    await hydrateUserFromSessionValidate();
    syncProfileDraftsFromUser(localUser.value);
  } finally {
    accountLoading.value = false;
  }
}

const profileBrandTitle = computed(() => {
  const brand = String(accountProfileStore.displayBrand || '').trim();
  if (brand) return brand;
  const u = localUser.value;
  if (!u) return '未登录';
  const name = String(u.display_name || u.username || '').trim();
  return name || '用户';
});

const profileSubline = computed(() => {
  const u = localUser.value;
  if (!u) return '登录后同步修茈市场';
  const username = String(u.username || '').trim();
  if (isSunbirdAccountUsername(username)) {
    const mod = activeModMeta.value;
    const modLabel = String(mod?.name || mod?.id || '太阳鸟pro').trim();
    const listed = (mods.value || []).some(
      (m) => String(m.id || '').trim() === SUNBIRD_CLIENT_MOD_ID,
    );
    if (!listed) {
      return '太阳鸟企业账号 · 正在同步太阳鸟pro Mod，请稍候或刷新页面';
    }
    if (String(activeModId.value || '').trim() === SUNBIRD_CLIENT_MOD_ID) {
      return `已绑定 ${modLabel} · 侧栏「考勤表转换」`;
    }
    return '太阳鸟企业账号 · 正在启用太阳鸟pro…';
  }
  const brand = String(accountProfileStore.displayBrand || '').trim();
  if (brand) {
    const display = String(u.display_name || '').trim();
    if (display && display !== brand) return `${username} · ${display}`;
    return username || '修茈市场账号';
  }
  const display = String(u.display_name || '').trim();
  if (display && username && display !== username) return username;
  if (u.id != null) return `ID ${u.id}`;
  return username;
});

const showCompanyBrandEditor = computed(() => accountProfileStore.accountKind === 'enterprise');

const companyBrandDirty = computed(() => {
  const draft = companyBrandDraft.value.trim();
  const current = String(accountProfileStore.companyBrand || '').trim();
  return draft !== current;
});

async function saveCompanyBrand() {
  companyBrandSaving.value = true;
  try {
    const brand = companyBrandDraft.value.trim();
    const res = await authApi.updateCompanyBrand(brand);
    const raw = res as Record<string, unknown>;
    if (raw?.success === false) {
      throw new Error(String(raw.message || '保存失败'));
    }
    accountProfileStore.companyBrand = brand;
    await accountProfileStore.refreshFromServer();
    companyBrandDraft.value = accountProfileStore.companyBrand || brand;
    await appAlert('企业品牌名已保存');
  } catch (e) {
    await appAlert(`保存失败：${e instanceof Error ? e.message : String(e)}`);
  } finally {
    companyBrandSaving.value = false;
  }
}

const avatarInitial = computed(() => {
  if (!localUser.value) return '';
  const name = profileBrandTitle.value;
  const ch = name.charAt(0);
  return ch ? ch.toUpperCase() : '';
});

const profileAvatarUrl = computed(() => {
  const u = localUser.value;
  const local = String(u?.avatar_url || '').trim();
  if (local) {
    const base = local.startsWith('http') ? local : buildFullApiUrl(local);
    const sep = base.includes('?') ? '&' : '?';
    return `${base}${sep}v=${avatarCacheBust.value}`;
  }
  try {
    const raw = window.localStorage.getItem(LS_MARKET_USER_JSON);
    if (!raw) return '';
    const market = JSON.parse(raw) as Record<string, unknown>;
    const url = String(market.avatar_url || market.avatar || '').trim();
    return url.startsWith('http') ? url : '';
  } catch {
    return '';
  }
});

const profileHomeSummary = computed(() => {
  const name = profileDisplayNameDraft.value.trim() || localUser.value?.username || '';
  return name ? `${name} · 头像与资料` : '头像与资料';
});

const profileFormDirty = computed(() => {
  const u = localUser.value;
  if (!u) return false;
  const dn = profileDisplayNameDraft.value.trim();
  const em = profileEmailDraft.value.trim();
  const curDn = String(u.display_name || u.username || '').trim();
  const curEm = String(u.email || '').trim();
  return dn !== curDn || em !== curEm;
});

function onAvatarClick() {
  if (!isLoggedIn.value || avatarUploading.value) return;
  avatarInputRef.value?.click();
}

async function onAvatarFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || !isLoggedIn.value) return;
  if (file.size > 4 * 1024 * 1024) {
    await appAlert('头像图片不能超过 4MB');
    return;
  }
  avatarUploading.value = true;
  try {
    const res = await authApi.uploadAvatar(file);
    const url = String(res?.data?.avatar_url || '/api/auth/avatar').trim();
    if (localUser.value) {
      localUser.value = { ...localUser.value, avatar_url: url || '/api/auth/avatar' };
    }
    avatarCacheBust.value = Date.now();
    await appAlert('头像已更新');
  } catch (e) {
    await appAlert(`头像上传失败：${e instanceof Error ? e.message : String(e)}`);
  } finally {
    avatarUploading.value = false;
  }
}

async function saveProfile() {
  if (!localUser.value || !profileFormDirty.value) return;
  profileSaving.value = true;
  try {
    const res = await authApi.updateProfile({
      display_name: profileDisplayNameDraft.value.trim(),
      email: profileEmailDraft.value.trim(),
    });
    const updated = res?.data?.user;
    if (updated && localUser.value) {
      localUser.value = { ...localUser.value, ...updated };
      syncProfileDraftsFromUser(localUser.value);
    }
    await appAlert('个人资料已保存');
  } catch (e) {
    await appAlert(`保存失败：${e instanceof Error ? e.message : String(e)}`);
  } finally {
    profileSaving.value = false;
  }
}

const loginRoute = computed(() => ({
  name: 'login' as const,
  query: { redirect: route.fullPath },
}));

async function onLogout() {
  if (!(await appConfirm('确定退出本机账号？', { danger: true }))) return;
  logoutLoading.value = true;
  try {
    await authApi.logout();
    accountProfileStore.clear();
    localUser.value = null;
    sessionValid.value = false;
    await appAlert('已退出登录');
    window.location.reload();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    await appAlert(`退出失败：${msg}`);
  } finally {
    logoutLoading.value = false;
  }
}

const modsStore = useModsStore();
const { clientModsUiOff, loadError, isLoaded, mods, modRoutes, activeModId } = storeToRefs(modsStore);

const uninstallingModId = ref('');
const hostPackExpanded = ref(false);

const hostBridgeMods = computed(() => {
  const expected = new Set(expectedHostBridgeModIds());
  return mods.value
    .filter((m) => isHostBridgeModId(String(m.id || '')))
    .sort((a, b) => {
      const aid = String(a.id || '');
      const bid = String(b.id || '');
      const tier = (id: string) => (expected.has(id) ? 0 : 1);
      const t = tier(aid) - tier(bid);
      if (t !== 0) return t;
      return String(a.name || aid).localeCompare(String(b.name || bid), 'zh-CN');
    });
});

const hostBridgeInstalledCount = computed(() => {
  const ids = new Set(mods.value.map((m) => String(m.id || '').trim()));
  return expectedHostBridgeModIds().filter((id) => ids.has(id)).length;
});

const hostBridgeExpectedCount = computed(() => expectedHostBridgeModIds().length);

const selectableExtensionMods = computed(() =>
  mods.value.filter((m) => isSelectableExtensionModId(String(m.id || ''))),
);

const workflowEmployeeMods = computed(() =>
  mods.value.filter((m) => isWorkflowEmployeeModId(String(m.id || ''))),
);

function goHostPackOnboarding() {
  router.push({ path: '/onboarding', query: { step: 'host-pack' } });
}

function goModStore() {
  router.push({ name: 'mod-store' });
}

const activeModMeta = computed(() => {
  const mid = String(activeModId.value || '').trim();
  if (!mid) return null;
  return mods.value.find((m) => String(m.id || '').trim() === mid) || null;
});

/** 取 active mod 的 manifest.industry，不存在返回 null。供主单位/意图关键词读取 */
const activeModIndustry = computed<ManifestIndustry | null>(() => {
  const meta = activeModMeta.value;
  const ind = meta && typeof meta === 'object' ? (meta as { industry?: unknown }).industry : null;
  return ind && typeof ind === 'object' ? (ind as ManifestIndustry) : null;
});

const modRoutesRetrying = ref(false);

const modRoutesStatusText = computed(() => {
  if (clientModsUiOff.value) return '';
  if (loadError.value) return loadError.value;
  if (
    isLoaded.value &&
    mods.value.length > 0 &&
    modRoutes.value.length === 0
  ) {
    return 'Mod 路由未加载，请重试或刷新。';
  }
  return '';
});

const showModRoutesRetry = computed(() => Boolean(modRoutesStatusText.value));

const modSettingsFoldMeta = computed(() => {
  const host = hostBridgeMods.value.length
    ? `核心 ${hostBridgeInstalledCount.value}/${hostBridgeExpectedCount.value}`
    : '';
  const ext = `${selectableExtensionMods.value.length} 个行业包`;
  const wf = workflowEmployeeMods.value.length
    ? `${workflowEmployeeMods.value.length} 个工作流`
    : '';
  return [host, ext, wf].filter(Boolean).join(' · ') || '管理扩展';
});

const basicSettingsSummary = computed(() => {
  const mode = aiMode.value === 'offline' ? '离线' : '在线';
  return `${normalizedAssistantName.value} · ${mode}`;
});

async function retryModRoutesLoad() {
  modRoutesRetrying.value = true;
  try {
    await modsStore.refresh();
    if (loadError.value) {
      await appAlert(loadError.value);
    } else if (mods.value.length > 0 && modRoutes.value.length === 0) {
      await appAlert('仍未获取到路由表，请确认后端已完全启动或查看控制台 / 后端日志。');
    } else {
      await appAlert('Mod 与路由已重新加载。');
    }
  } finally {
    modRoutesRetrying.value = false;
  }
}

async function onActiveModChange(modId: string) {
  const next = String(modId || '').trim();
  if (!next || activeModId.value === next) return;
  const nextMod = mods.value.find((m) => String(m.id || '').trim() === next);
  const nextIndustryId = String(nextMod?.industry?.id || '').trim();

  // 先把前端 activeModId 切到目标 mod；这样侧栏副标题、主单位、意图包等
  // 由 useIndustryUiText / activeModIndustry 派生的 UI 立刻反映新选择，
  // 不依赖后端 industry 切换是否被接受。
  modsStore.setActiveModId(next);

  if (nextIndustryId && nextIndustryId !== String(industryStore.currentIndustryId || '').trim()) {
    const success = await industryStore.switchIndustry(nextIndustryId);
    if (!success) {
      // 后端拒绝（旧版后端、或 Mod backend init 失败）：不再硬性回滚 active mod，
      // 仅给一条提示并让前端 UI 沿用 manifest.industry 兜底（已由 industry.ts
      // loadCurrentIndustry 失败分支与 useIndustryUiText effectiveIndustryId 处理）。
      console.warn(
        '[settings] 切换行业到',
        nextIndustryId,
        '失败：',
        industryStore.error || '未知',
        '；前端将沿用 mod manifest.industry 渲染',
      );
    }
  }
  // 切换 Mod 会改变侧栏菜单、工作流员工与 X-XCAGI-Active-Mod-Id 请求头，
  // 同时同步当前行业，避免侧栏副标题和业务字段仍停留在旧行业。
  window.location.reload();
}

async function onUninstallMod(modId: string) {
  const mid = String(modId || '').trim();
  if (!mid) return;
  if (isProtectedClientModId(mid)) {
    await appAlert('该扩展包为受保护的交付 Mod，不能从本机卸载。');
    return;
  }
  const meta = mods.value.find((m) => String(m.id || '').trim() === mid) || null;
  const label = (meta && String(meta.name || '').trim()) || mid;
  let question = `确定从本机卸载「${label}」（${mid}）吗？\n将删除磁盘上的包目录并解除加载，不可撤销。`;
  if (meta && meta.primary) {
    question += '\n\n该包在 manifest 中标记为主扩展（primary），请确认宿主与其它 Mod 不再依赖此 id。';
  }
  if (activeModId.value === mid) {
    question += '\n\n这是当前启用的扩展包，卸载后页面将刷新。';
  }
  if (!(await appConfirm(question, { danger: true }))) return;
  uninstallingModId.value = mid;
  try {
    const data = await api.delete<ApiMessageResult>(`/api/mods/${encodeURIComponent(mid)}`);
    if (!data || !data.success) {
      await appAlert(`卸载失败：${(data && (data.message || data.error)) || '未知错误'}`);
      return;
    }
    await appAlert(typeof data.message === 'string' ? data.message : `已卸载 ${mid}`);
    window.location.reload();
  } catch (err) {
    const msg =
      err instanceof ApiError
        ? err.message
        : err instanceof Error
          ? err.message
          : String(err);
    await appAlert(`卸载请求失败：${msg}`);
  } finally {
    uninstallingModId.value = '';
  }
}

const loading = ref(false);
const loadingVersions = ref(false);
const aiMode = ref('online');
const assistantName = ref('修茈');
const versions = ref<DistillationVersion[]>([]);
const sampleCount = ref(0);
const versionsError = ref('');
const sampleCountWarning = ref('');
const aboutClickCount = ref(0);
const currentDbPath = ref('');
const databaseStorageLabel = ref('');
const desktopDatabaseVisible = ref(false);

async function loadDesktopDatabaseStatus() {
  try {
    const res = await api.get('/api/desktop/status');
    const data = res?.data ?? res;
    if (!data || data.desktopMode === false) {
      desktopDatabaseVisible.value = false;
      databaseStorageLabel.value = '';
      currentDbPath.value = '';
      return;
    }
    desktopDatabaseVisible.value = true;
    const mode = String(data.storageMode || '');
    databaseStorageLabel.value =
      mode === 'local_sqlite'
        ? '本地数据库（SQLite）'
        : mode === 'remote_postgresql'
          ? '远程 PostgreSQL'
          : '本地数据库';
    if (data.database) {
      currentDbPath.value = String(data.database);
    }
  } catch {
    desktopDatabaseVisible.value = false;
    databaseStorageLabel.value = '';
    currentDbPath.value = '';
  }
}
const ABOUT_CLICK_TARGET = 5;
let aboutClickTimer: number | null = null;
const ASSISTANT_NAME_KEY = 'assistantName';
const DEFAULT_ASSISTANT_NAME = '修茈';
const industries = ref<ApiIndustry[]>([]);
const currentIndustry = ref(DEFAULT_INDUSTRY_ID);
const currentIndustryUnit = ref('天');
const sidebarThemePreset = ref('office-default');

const systemDisplayName = computed(() => {
  const id = String(currentIndustry.value || DEFAULT_INDUSTRY_ID).trim() || DEFAULT_INDUSTRY_ID;
  const name = getIndustryPreset(id).name;
  return `${name}管理系统`;
});

const selectedSidebarAccent = computed(() => {
  const selected = SIDEBAR_THEME_OPTIONS.find((item) => item.value === sidebarThemePreset.value);
  return selected?.accent || '#0f6cbd';
});

const intentPackages = ref<Record<IntentPackageKey, IntentPackageState>>({
  base: {
    name: '基础意图',
    iconClass: 'fa-file-text-o',
    description: '考勤与单据通用意图：创建、查询、修改、导出、审批',
    enabled: true,
    keywords: ['考勤', '查询', '导出', '请假', '加班', '修改', '创建', '统计']
  },
  industry: {
    name: '行业特定',
    iconClass: 'fa-industry',
    description: '当前组织的考勤制度用语与业务词汇',
    enabled: true,
    keywords: []
  },
  product: {
    name: '员工识别',
    iconClass: 'fa-cubes',
    description: '工号、姓名、部门等员工信息的识别与解析',
    enabled: true,
    keywords: ['工号', '姓名', '部门', '岗位', '职级']
  },
  quantity: {
    name: '工时解析',
    iconClass: 'fa-sort-numeric-asc',
    description: '出勤天数、工时小时数及中文数字的智能解析',
    enabled: true,
    keywords: ['天', '小时', '半天', '次', '二十三', '一十']
  },
  customer: {
    name: '组织识别',
    iconClass: 'fa-users',
    description: '部门名称、上下级关系与办公地点等信息的识别',
    enabled: true,
    keywords: ['部门', '科室', '班组', '分公司', '联系人']
  }
});

const currentIndustryConfig = computed(() => {
  return industryStore.industries.find(i => i.id === currentIndustry.value);
});

const INTENT_PACKAGE_ORDER: IntentPackageKey[] = ['base', 'industry', 'product', 'quantity', 'customer'];

const intentPackageEntries = computed(() => {
  const pkgs = intentPackages.value;
  return INTENT_PACKAGE_ORDER.filter((key) => pkgs[key]).map((key) => ({
    key,
    ...pkgs[key],
    keywords: Array.isArray(pkgs[key].keywords)
      ? pkgs[key].keywords.filter((kw) => String(kw || '').trim()).slice(0, 12)
      : [],
  }));
});

const currentIntentIndustryLabel = computed(() => {
  const cfg = currentIndustryConfig.value;
  if (cfg?.name) return String(cfg.name);
  const preset = getIndustryPreset(String(currentIndustry.value || DEFAULT_INDUSTRY_ID));
  return preset?.name || String(currentIndustry.value || '').trim() || '';
});

const normalizedAssistantName = computed(() => {
  const normalized = assistantName.value?.trim();
  return normalized || DEFAULT_ASSISTANT_NAME;
});

async function loadIndustries() {
  try {
    const response = await systemApi.getIndustries();
    if (response.success) {
      const payload = response.data as ApiIndustry[] | { industries?: ApiIndustry[]; current?: string | number } | undefined;
      industries.value = Array.isArray(payload) ? payload : payload?.industries || [];
      const cur =
        (!Array.isArray(payload) ? payload?.current : undefined) ??
        industryStore.currentIndustry?.id ??
        DEFAULT_INDUSTRY_ID;
      currentIndustry.value = String(cur).trim() || DEFAULT_INDUSTRY_ID;
    }
  } catch (e) {
    console.error('加载行业列表失败:', e);
  }
}

async function loadCurrentIndustryDetail() {
  try {
    const response = await systemApi.getCurrentIndustry();
    if (response.success) {
      // 主单位优先采用 active mod 的 manifest.industry.units.primary —— 让"切 mod"
      // 在后端尚未对齐前也能立刻把主单位切对。
      const fromMod = activeModIndustry.value?.units?.primary;
      currentIndustryUnit.value =
        (typeof fromMod === 'string' && fromMod.trim()) ||
        response.data?.units?.primary ||
        '天';
      updateIndustryKeywords();
    }
  } catch (e) {
    console.error('加载行业详情失败:', e);
    // server 失败时也用 mod manifest 兜底，避免主单位卡在默认「天」之前的状态
    const fromMod = activeModIndustry.value?.units?.primary;
    if (typeof fromMod === 'string' && fromMod.trim()) {
      currentIndustryUnit.value = fromMod.trim();
    }
    updateIndustryKeywords();
  }
}

function updateIndustryKeywords() {
  // 优先读 active mod 的 manifest.intent_keywords，让"行业特定"芯片立即跟随 mod 切换；
  // 没有 mod 或 mod 未声明 intent_keywords 时回到 industryStore.currentConfig。
  const modKw = activeModIndustry.value?.intent_keywords;
  const config = industryStore.currentConfig;
  const kw = (modKw && typeof modKw === 'object' ? modKw : (config && config.intent_keywords)) as IntentKeywordMap | undefined;
  if (!kw || typeof kw !== 'object') return;
  const keywords: string[] = [];
  if (kw.create_order) {
    keywords.push(...(Array.isArray(kw.create_order) ? kw.create_order : [kw.create_order]));
  }
  if (kw.quantity_unit) {
    keywords.push(...(Array.isArray(kw.quantity_unit) ? kw.quantity_unit : [kw.quantity_unit]));
  }
  if (kw.print_label) {
    keywords.push(...(Array.isArray(kw.print_label) ? kw.print_label : [kw.print_label]));
  }
  intentPackages.value.industry.keywords = [...new Set(keywords.map((kw) => String(kw || '').trim()).filter(Boolean))].slice(0, 12);
}

async function loadIntentPackages() {
  try {
    const response = await intentPackagesApi.getPackages();
    const payload = response.data as ApiIntentPackage[] | { packages?: Record<string, Partial<IntentPackageState>> } | undefined;
    const packages = !Array.isArray(payload) ? payload?.packages : undefined;
    if (response.success && packages) {
      for (const key of Object.keys(packages) as IntentPackageKey[]) {
        const target = intentPackages.value[key];
        const source = packages[key];
        if (target && source) {
          if (typeof source.enabled === 'boolean') target.enabled = source.enabled;
          if (Array.isArray(source.keywords)) target.keywords = source.keywords;
        }
      }
    }
  } catch (e) {
    console.error('加载意图包失败:', e);
  }
}

async function loadPreferences() {
  try {
    const data = await api.get('/api/preferences', { user_id: 'default' });
    if (!data?.success || !data?.preferences) return;
    const prefs = data.preferences;

    // 与 aiMode 无关的偏好先行读取，避免被 early return 跳过
    const preferredAssistantName = prefs.assistantName;
    if (typeof preferredAssistantName === 'string') {
      assistantName.value = preferredAssistantName;
    } else {
      assistantName.value = window.localStorage.getItem(ASSISTANT_NAME_KEY) || DEFAULT_ASSISTANT_NAME;
    }
    window.localStorage.setItem(ASSISTANT_NAME_KEY, normalizedAssistantName.value);

    const preferredMode = prefs.aiMode;
    if (preferredMode === 'online' || preferredMode === 'offline') {
      aiMode.value = preferredMode;
      return;
    }
    const legacyModel = (prefs.aiModel || '').toLowerCase();
    aiMode.value = legacyModel === 'local' ? 'offline' : 'online';
    if (legacyModel) {
      // 兼容历史键：读取后自动迁移为新键，避免后续逻辑分叉。
      await api.post('/api/preferences', {
        user_id: 'default',
        key: 'aiMode',
        value: aiMode.value,
      });
    }
  } catch (e) {
    console.error('加载设置失败:', e);
    assistantName.value = window.localStorage.getItem(ASSISTANT_NAME_KEY) || DEFAULT_ASSISTANT_NAME;
  }
}

async function saveSettings() {
  loading.value = true;
  try {
    const saveResults = await Promise.all([
      api.post<ApiMessageResult>('/api/preferences', {
        user_id: 'default',
        key: 'aiMode',
        value: aiMode.value
      }),
      api.post<ApiMessageResult>('/api/preferences', {
        user_id: 'default',
        key: ASSISTANT_NAME_KEY,
        value: normalizedAssistantName.value
      })
    ]);
    const failed = saveResults.find(item => !item?.success);
    if (failed) throw new Error(failed?.message || '保存失败');
    assistantName.value = normalizedAssistantName.value;
    window.localStorage.setItem(ASSISTANT_NAME_KEY, normalizedAssistantName.value);
    window.dispatchEvent(new CustomEvent('assistant-name-updated', {
      detail: {
        name: normalizedAssistantName.value
      }
    }));
    await appAlert('设置已保存');
  } catch (e: unknown) {
    console.error('保存设置失败:', e);
    await appAlert(`保存失败: ${errorMessage(e)}`);
  } finally {
    loading.value = false;
  }
}

function onSidebarThemeChange() {
  persistSidebarTheme(sidebarThemePreset.value);
}

async function loadDistillationVersions() {
  loadingVersions.value = true;
  versionsError.value = '';
  sampleCountWarning.value = '';
  try {
    const data = await api.get<{
      success?: boolean
      message?: string
      versions?: DistillationVersion[]
      distillation_samples?: number
      sample_count_error?: string
    }>('/api/distillation/versions');
    if (!data?.success) throw new Error(data?.message || '加载失败');
    versions.value = Array.isArray(data.versions) ? data.versions : [];
    sampleCount.value = Number(data.distillation_samples || 0);
    if (data?.sample_count_error) {
      sampleCountWarning.value = `样本数读取异常：${data.sample_count_error}`;
    }
  } catch (e: unknown) {
    console.error('加载蒸馏版本失败:', e);
    versions.value = [];
    sampleCount.value = 0;
    versionsError.value = `蒸馏信息加载失败：${errorMessage(e, '网络或服务异常')}`;
  } finally {
    loadingVersions.value = false;
  }
}

function resetAboutClickCount() {
  aboutClickCount.value = 0;
  if (aboutClickTimer) {
    window.clearTimeout(aboutClickTimer);
    aboutClickTimer = null;
  }
}

function handleAboutHeaderClick() {
  aboutClickCount.value += 1;

  if (aboutClickTimer) {
    window.clearTimeout(aboutClickTimer);
  }
  aboutClickTimer = window.setTimeout(() => {
    resetAboutClickCount();
  }, 1800);

  if (aboutClickCount.value >= ABOUT_CLICK_TARGET) {
    resetAboutClickCount();
    router.push({ name: 'chat-debug' });
  }
}

function scrollToSettingsSection() {
  const section = String(route.query.section || '').trim();
  if (!section) return;
  nextTick(() => {
    const el =
      document.getElementById(`settings-${section}`) ||
      document.querySelector(`[data-tutorial-id="settings-${section}"]`);
    if (el instanceof HTMLDetailsElement) {
      el.open = true;
    } else if (el) {
      const parentDetails = el.closest('details.settings-card');
      if (parentDetails instanceof HTMLDetailsElement) parentDetails.open = true;
    }
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

watch(() => route.query.section, scrollToSettingsSection);

onMounted(async () => {
  scrollToSettingsSection();
  await loadLocalUser();
  void loadDesktopDatabaseStatus();
  const uname = String(localUser.value?.username || '').trim();
  const sunbird = isSunbirdAccountUsername(uname);
  if (!modsStore.isLoaded) {
    await modsStore.initialize(true, {
      entitledModIds: augmentEntitledModIdsForAccount(uname, []),
      forceFromEntitlements: sunbird,
      accountUsername: uname,
    });
  } else if (sunbird) {
    await modsStore.applyEntitledActiveMod(augmentEntitledModIdsForAccount(uname, []), {
      force: true,
      accountUsername: uname,
    });
  }
  sidebarThemePreset.value = readStoredSidebarTheme();
  applySidebarTheme(sidebarThemePreset.value);
  await industryStore.initialize();
  await loadIndustries();
  const piniaIndustryId = industryStore.currentIndustry?.id;
  if (piniaIndustryId !== undefined && piniaIndustryId !== null && String(piniaIndustryId).trim() !== '') {
    currentIndustry.value = String(piniaIndustryId).trim();
  }
  await loadCurrentIndustryDetail();
  await loadIntentPackages();
  loadPreferences();
  loadDistillationVersions();
});

onActivated(() => {
  void loadLocalUser();
});

watch(
  activeModIndustry,
  () => {
    updateIndustryKeywords();
  },
  { deep: true },
);

onBeforeUnmount(() => {
  resetAboutClickCount();
});
</script>

<style scoped>
/* 豆包式分组列表：浅灰底 + 白卡片 + 左图标右箭头 */
.settings-page {
  --settings-bg: #f3f4f6;
  --settings-card-bg: #ffffff;
  --settings-card-border: rgba(0, 0, 0, 0.06);
  --settings-divider: rgba(0, 0, 0, 0.06);
  --settings-accent: #2d6df6;
  --settings-accent-soft: #eff6ff;
  --settings-radius: 14px;
  --settings-main-max: 640px;
  --settings-profile-width: 168px;
  --settings-row-pad-x: 16px;
  --settings-icon-size: 36px;
}

.settings-page__scroll {
  padding: 0;
  background: var(--settings-bg);
}

.settings-layout {
  display: grid;
  grid-template-columns: var(--settings-profile-width) minmax(0, var(--settings-main-max));
  gap: 32px;
  align-items: start;
  max-width: calc(var(--settings-profile-width) + var(--settings-main-max) + 32px);
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.settings-layout__main {
  min-width: 0;
}

.settings-profile {
  position: sticky;
  top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 8px 4px;
}

.settings-profile__avatar-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.settings-profile__avatar {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 88px;
  height: 88px;
  padding: 0;
  border: none;
  cursor: pointer;
  font: inherit;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(145deg, #60a5fa, #2563eb);
  color: #fff;
  font-size: 32px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.22);
  margin-bottom: 14px;
}

.settings-profile__avatar.is-guest {
  background: linear-gradient(145deg, #e5e7eb, #9ca3af);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  font-size: 28px;
}

.settings-profile__avatar.is-loading {
  opacity: 0.65;
}

.settings-profile__avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.settings-profile__avatar-letter {
  line-height: 1;
}

.settings-profile__avatar:disabled {
  cursor: default;
}

.settings-profile__avatar:not(:disabled):hover .settings-profile__avatar-hint,
.settings-profile__avatar:not(:disabled):focus-visible .settings-profile__avatar-hint {
  opacity: 1;
}

.settings-profile__avatar-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  background: rgba(15, 23, 42, 0.48);
  opacity: 0;
  transition: opacity 0.15s ease;
  pointer-events: none;
}

.settings-profile-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
  max-width: 520px;
  padding: 16px var(--settings-row-pad-x, 16px) 18px;
  box-sizing: border-box;
}

.settings-profile-form__editable {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

@media (min-width: 520px) {
  .settings-profile-form__editable {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px 16px;
  }
}

.settings-profile-form__field {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  margin: 0;
}

.settings-profile-form__label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  line-height: 1.35;
}

.settings-profile-form__input {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 40px;
  padding: 9px 12px;
  font-size: 14px;
  line-height: 1.4;
  color: #111827;
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #fff;
  appearance: none;
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease,
    background-color 0.15s ease;
}

.settings-profile-form__input::placeholder {
  color: #9ca3af;
}

.settings-profile-form__input:hover {
  border-color: #d1d5db;
}

.settings-profile-form__input:focus {
  outline: none;
  border-color: #93c5fd;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(45, 109, 246, 0.15);
}

.settings-profile-form__readonly {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
  background: #f9fafb;
}

.settings-profile-form__readonly-value {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.02em;
}

.settings-profile-form__hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #9ca3af;
}

.settings-profile-form__actions {
  display: flex;
  justify-content: flex-start;
  padding-top: 2px;
}

.settings-profile-form__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 128px;
  min-height: 40px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: var(--settings-accent, #2d6df6);
  box-shadow: 0 4px 12px rgba(45, 109, 246, 0.22);
  cursor: pointer;
  transition:
    filter 0.15s ease,
    box-shadow 0.15s ease,
    opacity 0.15s ease;
}

.settings-profile-form__submit:hover:not(:disabled) {
  filter: brightness(1.05);
}

.settings-profile-form__submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.settings-profile__name {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
  line-height: 1.35;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-profile__brand {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.settings-profile__sub {
  margin: 6px 0 0;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.4;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-profile__actions {
  margin-top: 16px;
  width: 100%;
}

.settings-profile__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.settings-profile__btn--primary {
  border: none;
  background: var(--settings-accent);
  color: #fff;
  box-shadow: 0 4px 12px rgba(45, 109, 246, 0.25);
}

.settings-profile__btn--primary:hover {
  filter: brightness(1.05);
}

.settings-profile__btn--ghost {
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #374151;
}

.settings-profile__btn--ghost:hover:not(:disabled) {
  background: #f9fafb;
  border-color: #d1d5db;
}

.settings-profile__btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.settings-page__hero {
  margin-bottom: 16px;
  padding: 0 4px;
}

.settings-page__title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1a1a1a;
  line-height: 1.3;
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-card {
  margin: 0;
  border: 1px solid var(--settings-card-border);
  border-radius: var(--settings-radius);
  background: var(--settings-card-bg);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.settings-card--nested {
  margin: 0;
  border: none;
  border-radius: 0;
  box-shadow: none;
  border-top: 1px solid var(--settings-divider);
}

.settings-card--about {
  border-style: dashed;
  background: #fafafa;
}

.settings-row {
  display: grid;
  grid-template-columns: var(--settings-icon-size) 1fr auto auto;
  align-items: center;
  gap: 12px;
  min-height: 56px;
  padding: 10px var(--settings-row-pad-x);
  cursor: pointer;
  list-style: none;
  user-select: none;
  transition: background-color 0.12s ease;
}

.settings-row--nested {
  grid-template-columns: var(--settings-icon-size) 1fr auto auto;
}

.settings-row:hover {
  background: #f9fafb;
}

.settings-row::-webkit-details-marker {
  display: none;
}

.settings-row__icon {
  width: var(--settings-icon-size);
  height: var(--settings-icon-size);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #fff;
  font-size: 16px;
  flex-shrink: 0;
}

.settings-row__icon--blue { background: linear-gradient(145deg, #3b82f6, #2563eb); }
.settings-row__icon--purple { background: linear-gradient(145deg, #a78bfa, #7c3aed); }
.settings-row__icon--green { background: linear-gradient(145deg, #4ade80, #16a34a); }
.settings-row__icon--amber { background: linear-gradient(145deg, #fbbf24, #d97706); }
.settings-row__icon--orange { background: linear-gradient(145deg, #fb923c, #ea580c); }
.settings-row__icon--cyan { background: linear-gradient(145deg, #22d3ee, #0891b2); }
.settings-row__icon--indigo { background: linear-gradient(145deg, #818cf8, #4f46e5); }
.settings-row__icon--violet { background: linear-gradient(145deg, #c084fc, #9333ea); }
.settings-row__icon--slate { background: linear-gradient(145deg, #94a3b8, #64748b); }

.settings-row__label {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  min-width: 0;
}

.settings-row__meta {
  font-size: 13px;
  color: #9ca3af;
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-row__pill {
  font-size: 12px;
  font-weight: 500;
  color: #4b5563;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f3f4f6;
  max-width: 46%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.settings-row__arrow {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #d1d5db;
  font-size: 18px;
  line-height: 1;
  transition: transform 0.15s ease, color 0.15s ease;
}

.settings-row__arrow::before {
  content: '›';
  font-weight: 300;
}

.settings-card[open] > .settings-row .settings-row__arrow {
  transform: rotate(90deg);
  color: #9ca3af;
}

.settings-card__body {
  padding: 0 var(--settings-row-pad-x) 16px;
  border-top: 1px solid var(--settings-divider);
}

.settings-card__body--flush {
  padding: 0 12px 12px;
}

.settings-card__body--list {
  padding: 0;
  border-top: 1px solid var(--settings-divider);
}

.settings-card__body--compact {
  padding-top: 12px;
}

.settings-card__body--nested {
  padding: 12px var(--settings-row-pad-x) 14px;
  border-top: 1px solid var(--settings-divider);
  background: #fafafa;
}

.settings-card__footer {
  padding: 12px var(--settings-row-pad-x) 16px;
  border-top: 1px solid var(--settings-divider);
}

.settings-card:not([open]) > .settings-card__body,
.settings-card:not([open]) > .settings-card__footer {
  display: none;
}

.settings-item-list {
  display: flex;
  flex-direction: column;
}

.settings-item {
  display: grid;
  grid-template-columns: var(--settings-icon-size) 1fr minmax(100px, 42%);
  align-items: center;
  gap: 12px;
  min-height: 52px;
  padding: 8px var(--settings-row-pad-x);
  border-bottom: 1px solid var(--settings-divider);
}

.settings-item:last-child {
  border-bottom: none;
}

.settings-item__icon {
  width: var(--settings-icon-size);
  height: var(--settings-icon-size);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
}

.settings-item__label {
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
  margin: 0;
}

.settings-item__control {
  --settings-control-chevron: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%236b7280' d='M2 1.5 6 6.5 10 1.5'/%3E%3C/svg%3E");
  justify-self: end;
  width: 100%;
  max-width: 200px;
  min-height: 36px;
  padding: 0 36px 0 12px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  color: #111827;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background-color: #f9fafb;
  background-image: var(--settings-control-chevron);
  background-repeat: no-repeat;
  background-position: right 12px center;
  background-size: 12px 8px;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    box-shadow 0.15s ease;
}

select.settings-item__control,
.settings-item__control--select {
  text-align-last: left;
}

.settings-item__control:hover {
  border-color: #d1d5db;
  background-color: #fff;
}

.settings-item__control-group {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.settings-item__control-group .settings-item__control--text {
  flex: 1;
  min-width: 0;
}

.settings-item__save-btn {
  flex-shrink: 0;
  border: 1px solid #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.settings-item__save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.settings-item__control--text {
  background-color: #f9fafb;
  background-image: none;
  text-align: left;
  padding-right: 12px;
  font-weight: 400;
  cursor: text;
}

.settings-item__control--text:hover {
  background-color: #fff;
}

.settings-item__control:focus,
.settings-item__control:focus-visible {
  outline: none;
  border-color: #93c5fd;
  background-color: #fff;
  background-image: var(--settings-control-chevron);
  box-shadow: 0 0 0 3px rgba(45, 109, 246, 0.14);
}

.settings-item__control--text:focus,
.settings-item__control--text:focus-visible {
  background-image: none;
}

.settings-item__control option {
  font-size: 14px;
  font-weight: 500;
  color: #111827;
  background: #fff;
}

.settings-item__value {
  justify-self: end;
  font-size: 13px;
  color: #9ca3af;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}

.settings-item__value--mono {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 11px;
}

.settings-primary-btn {
  width: 100%;
  min-height: 44px;
  border: none;
  border-radius: 12px;
  background: var(--settings-accent);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(45, 109, 246, 0.28);
  transition: opacity 0.15s ease, transform 0.1s ease;
}

.settings-primary-btn:hover:not(:disabled) {
  filter: brightness(1.05);
}

.settings-primary-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.settings-table-wrap {
  overflow-x: auto;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}

.settings-table {
  margin: 0;
  font-size: 13px;
}

.settings-meta-line {
  margin: 10px 0 0;
  font-size: 12px;
}

.settings-about-line {
  margin: 0 0 6px;
  font-size: 14px;
  color: #374151;
}

.settings-about-hint {
  margin: 10px 0 0;
  font-size: 12px;
  line-height: 1.45;
}

/* 嵌入：模型服务 Mod */
#settings-model-payment :deep(.mp-root--embedded) {
  margin: 0;
}

#settings-model-payment :deep(.mp-page-content--embedded) {
  padding: 0;
}

#settings-model-payment :deep(.mp-embedded-toolbar) {
  align-items: center;
  gap: 16px;
  margin: 0 0 12px;
  padding: 10px 4px 14px;
  border-bottom: 1px solid #f1f5f9;
}

#settings-model-payment :deep(.mp-embedded-intro) {
  font-size: 13px;
}

#settings-model-payment :deep(.mp-hero-actions--embedded) {
  flex-wrap: nowrap;
}

#settings-model-payment :deep(.mp-hero-btn) {
  border-radius: 10px;
  font-size: 13px;
  padding: 8px 16px;
}

#settings-model-payment :deep(.mp-hero-btn--primary) {
  background: var(--settings-accent);
  border-color: var(--settings-accent);
  box-shadow: 0 4px 12px rgba(45, 109, 246, 0.28);
}

#settings-model-payment :deep(.mp-fold) {
  margin: 0;
  padding: 0;
  border: none;
  border-radius: 0;
  background: transparent;
  border-bottom: 1px solid var(--settings-divider);
}

#settings-model-payment :deep(.mp-fold:last-child) {
  border-bottom: none;
}

#settings-model-payment :deep(.mp-fold-title) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 48px;
  margin: 0;
  padding: 12px 4px;
  font-size: 15px;
  font-weight: 500;
  color: #1a1a1a;
}

#settings-model-payment :deep(.mp-fold-title)::after {
  content: '›';
  color: #d1d5db;
  font-size: 18px;
  font-weight: 300;
  transition: transform 0.15s ease;
}

#settings-model-payment :deep(.mp-fold[open] .mp-fold-title)::after {
  transform: rotate(90deg);
}

#settings-model-payment :deep(.mp-fold-title::-webkit-details-marker) {
  display: none;
}

#settings-model-payment :deep(.mp-panel.mp-balance) {
  border-radius: 12px;
  border-color: #e2e8f0;
  box-shadow: none;
  margin-bottom: 0;
}

#settings-model-payment :deep(.card-header.mp-panel-title) {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
  background: transparent;
  font-size: 14px;
}

#settings-model-payment :deep(.mp-market-quota) {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f1f5f9;
}

#settings-model-payment :deep(.mp-market-quota > div) {
  padding: 10px 12px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e8eef5;
  text-align: center;
}

#settings-model-payment :deep(.mp-market-quota span) {
  display: block;
  font-size: 11px;
  color: #64748b;
  margin-bottom: 4px;
}

#settings-model-payment :deep(.mp-market-quota strong) {
  font-size: 13px;
  color: #0f172a;
}

#settings-model-payment :deep(.mp-balance-amount) {
  align-self: flex-start;
}

#settings-model-payment :deep(.card) {
  margin-bottom: 0;
  box-shadow: none;
}

/* —— AI 意图 —— */

.intent-showcase-state {
  padding: 20px 0;
  text-align: center;
  font-size: 13px;
}

.intent-showcase-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.intent-showcase-tile {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(203, 213, 225, 0.85);
  background: #fff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.intent-showcase-tile.is-enabled {
  border-color: rgba(59, 130, 246, 0.35);
  background: linear-gradient(180deg, #fff 0%, #f8fbff 100%);
}

.intent-showcase-tile.is-disabled {
  opacity: 0.72;
  background: #f8fafc;
}

.intent-tile-top {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.intent-tile-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(219, 234, 254, 0.65);
  color: #2563eb;
  font-size: 16px;
}

.intent-showcase-tile.is-disabled .intent-tile-icon {
  background: #e2e8f0;
  color: #64748b;
}

.intent-tile-title-wrap {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
}

.intent-tile-title {
  margin: 0;
  font-size: 14px;
  font-weight: 650;
  color: #0f172a;
  line-height: 1.3;
}

.intent-tile-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
  line-height: 1.4;
}

.intent-tile-status--on {
  color: #166534;
  background: #dcfce7;
}

.intent-tile-status--off {
  color: #64748b;
  background: #f1f5f9;
}

.intent-tile-desc {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.intent-tile-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.intent-chip {
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 6px;
  background: rgba(219, 234, 254, 0.75);
  color: #1d4ed8;
  border: 1px solid rgba(147, 197, 253, 0.35);
}

.intent-showcase-tile.is-disabled .intent-chip:not(.intent-chip--empty) {
  background: #f1f5f9;
  color: #64748b;
  border-color: #e2e8f0;
}

.intent-chip--empty {
  background: transparent;
  border-style: dashed;
  color: #94a3b8;
}

.about-debug-entry {
  cursor: pointer;
  user-select: none;
}

.theme-color-chip {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  margin: 0 6px -3px 4px;
  border: 1px solid rgba(15, 23, 42, 0.2);
}

.mod-fold-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--app-border-subtle);
}

.mod-fold-section:first-child {
  margin-top: 10px;
  padding-top: 10px;
  border-top: none;
}

.mod-fold-section--inline {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 8px;
}

.mod-fold-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.settings-sidebar-theme-hint {
  line-height: 1.55;
  word-break: break-word;
}

.mod-ui-off-label {
  display: block;
  font-weight: 600;
  margin-bottom: 0;
}

.mod-ui-off-desc {
  margin: 8px 0 0;
  max-width: 52rem;
}

.mod-ui-off-desc code {
  font-size: 0.85em;
  padding: 1px 4px;
  border-radius: 4px;
  background: rgba(15, 23, 42, 0.06);
}

.mod-host-pack-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  margin-top: 8px;
}

.mod-host-pack-stat {
  font-size: 13px;
  color: var(--app-text-secondary);
}

.mod-host-pack-list {
  list-style: none;
  margin: 10px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 160px;
  overflow-y: auto;
}

.mod-host-pack-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid var(--app-border-subtle);
}

.mod-host-pack-name {
  font-size: 12px;
  color: var(--app-text-strong);
  min-width: 0;
}

.mod-single-empty {
  margin: 8px 0 0;
  font-size: 13px;
}

.mod-single-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 180px;
  overflow-y: auto;
  padding-right: 4px;
}

.mod-single-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--app-border-subtle);
  border-radius: 10px;
  background: var(--card-bg);
  padding: 8px 10px 8px 12px;
  transition: border-color 0.16s ease, background-color 0.16s ease, box-shadow 0.16s ease;
}

.mod-single-item:hover {
  border-color: #bfdbfe;
  background: #f8fbff;
}

.mod-single-item.active {
  border-color: var(--app-interactive);
  background: var(--app-interactive-bg);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.mod-single-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.mod-single-main input[type='radio'] {
  margin: 0;
  flex-shrink: 0;
  width: 15px;
  height: 15px;
  accent-color: #2563eb;
}

.mod-single-uninstall {
  flex-shrink: 0;
  min-width: 56px;
}

.mod-single-text {
  font-size: 13px;
  color: var(--app-text-strong);
  line-height: 1.35;
}

.text-warning {
  color: #f59e0b !important;
}

@media (max-width: 1024px) {
  .intent-showcase-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  #settings-model-payment :deep(.mp-market-quota) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .settings-layout {
    grid-template-columns: 1fr;
    gap: 20px;
    padding: 16px 12px 40px;
    max-width: none;
  }

  .settings-profile {
    position: static;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: flex-start;
    gap: 12px 16px;
    text-align: left;
    padding: 12px 14px;
    border-radius: var(--settings-radius);
    background: var(--settings-card-bg);
    border: 1px solid var(--settings-card-border);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  }

  .settings-profile__avatar {
    width: 56px;
    height: 56px;
    font-size: 22px;
    margin: 0;
    flex-shrink: 0;
  }

  .settings-profile__name,
  .settings-profile__sub {
    flex: 1;
    min-width: 120px;
    text-align: left;
  }

  .settings-profile__actions {
    margin: 0;
    width: auto;
    flex: 0 0 auto;
  }

  .settings-profile__btn {
    width: auto;
    min-width: 88px;
  }

  .settings-row__meta,
  .settings-row__pill {
    max-width: 34%;
  }

  .settings-item {
    grid-template-columns: var(--settings-icon-size) 1fr;
    grid-template-rows: auto auto;
    gap: 6px 12px;
  }

  .settings-item__control,
  .settings-item__value {
    grid-column: 2;
    justify-self: stretch;
    max-width: none;
    text-align: left;
  }

  .intent-showcase-grid {
    grid-template-columns: 1fr;
  }

  #settings-model-payment :deep(.mp-embedded-toolbar) {
    flex-direction: column;
  }

  #settings-model-payment :deep(.mp-hero-actions) {
    width: 100%;
  }

  #settings-model-payment :deep(.mp-hero-btn) {
    flex: 1;
    justify-content: center;
  }
}
</style>
