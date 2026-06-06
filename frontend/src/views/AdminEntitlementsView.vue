<template>
  <div class="page-view admin-entitlements-view">
    <div class="page-content">
      <header class="admin-entitlements-head">
        <h2>用户 Mod 管理</h2>
        <p class="muted">为市场用户分配客户 Mod 权益，或进入代管模式代为配置。</p>
      </header>

      <div v-if="loadError" class="admin-entitlements-alert" role="alert">{{ loadError }}</div>

      <section class="admin-sync-strip" aria-label="本地安装与同步状态">
        <div>
          <strong>本地宿主状态</strong>
          <span class="muted">
            {{ installedModIds.size }} 个 Mod 已安装
            <template v-if="syncLastText"> · 最后同步 {{ syncLastText }}</template>
          </span>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" :disabled="localStatusLoading" @click="refreshLocalStatus">
          {{ localStatusLoading ? '刷新中…' : '刷新状态' }}
        </button>
      </section>
      <div v-if="localStatusError" class="admin-entitlements-alert admin-entitlements-alert--soft" role="status">
        {{ localStatusError }}
      </div>

      <div class="admin-entitlements-layout">
        <aside class="admin-user-list">
          <div class="admin-user-list__toolbar">
            <input
              v-model="userFilter"
              type="search"
              class="admin-user-search"
              placeholder="搜索用户名 / 邮箱"
            >
          </div>
          <ul v-if="filteredUsers.length" class="admin-user-list__items">
            <li
              v-for="u in filteredUsers"
              :key="u.id"
              class="admin-user-row"
              :class="{ active: selectedUserId === u.id }"
            >
              <button type="button" class="admin-user-row__btn" @click="selectUser(u)">
                <span class="admin-user-row__name">{{ u.username }}</span>
                <span class="admin-user-row__meta muted">
                  <span v-if="u.is_admin">管理员</span>
                  <span v-else-if="u.is_enterprise">企业</span>
                  <span v-else>普通</span>
                  · {{ (u.mod_ids || []).length }} Mod
                </span>
              </button>
            </li>
          </ul>
          <p v-else class="muted admin-user-list__empty">暂无用户</p>
        </aside>

        <section v-if="selectedUser" class="admin-user-detail">
          <header class="admin-user-detail__head">
            <div>
              <h3>{{ selectedUser.username }}</h3>
              <p class="muted">ID {{ selectedUser.id }} · {{ selectedUser.email || '无邮箱' }}</p>
            </div>
            <div class="admin-user-detail__actions">
              <label class="admin-flag">
                <input
                  type="checkbox"
                  :checked="selectedUser.is_enterprise"
                  @change="toggleEnterprise($event)"
                >
                企业用户
              </label>
              <button
                type="button"
                class="btn btn-primary btn-sm"
                :disabled="impersonateLoading"
                @click="startImpersonate"
              >
                {{ impersonateLoading ? '进入中…' : '进入代管' }}
              </button>
            </div>
          </header>

          <div class="admin-mod-panel">
            <h4>已绑定客户 Mod</h4>
            <div v-if="userModIds.length" class="admin-mod-chips">
              <span v-for="mid in userModIds" :key="mid" class="admin-mod-chip">
                {{ modLabel(mid) }}
                <small :class="['admin-mod-install', isModInstalled(mid) ? 'is-installed' : '']">
                  {{ modInstallText(mid) }}
                </small>
                <button type="button" class="admin-mod-chip__remove" @click="unbindMod(mid)">×</button>
              </span>
            </div>
            <p v-else class="muted">尚未绑定客户 Mod</p>

            <h4>可分配 Mod</h4>
            <div class="admin-mod-assign">
              <select v-model="modToBind" class="admin-mod-select">
                <option value="">选择 Mod…</option>
                <option
                  v-for="m in assignableMods"
                  :key="m.id"
                  :value="m.id"
                  :disabled="userModIds.includes(m.id)"
                >
                  {{ m.name || m.id }} · {{ modInstallText(m.id) }}
                </option>
              </select>
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                :disabled="!modToBind || binding"
                @click="bindMod"
              >
                {{ binding ? '绑定中…' : '绑定' }}
              </button>
            </div>
          </div>
        </section>

        <section v-else class="admin-user-detail admin-user-detail--empty muted">
          请选择左侧用户
        </section>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { xcmaxAdminApi } from '@/api/xcmaxAdmin';
import { appAlert } from '@/utils/appDialog';
import { apiFetch } from '@/utils/apiBase';

type AdminUser = {
  id: number;
  username: string;
  email?: string;
  is_admin?: boolean;
  is_enterprise?: boolean;
  mod_ids?: string[];
};

type AssignableMod = { id: string; name?: string };
type LocalModRow = { id?: string; name?: string; version?: string; is_installed?: boolean };

const users = ref<AdminUser[]>([]);
const assignableMods = ref<AssignableMod[]>([]);
const selectedUserId = ref<number | null>(null);
const userModIds = ref<string[]>([]);
const userFilter = ref('');
const loadError = ref('');
const modToBind = ref('');
const binding = ref(false);
const impersonateLoading = ref(false);
const localStatusLoading = ref(false);
const localStatusError = ref('');
const installedMods = ref<LocalModRow[]>([]);
const syncStatus = ref<Record<string, unknown> | null>(null);

const selectedUser = computed(() =>
  users.value.find((u) => u.id === selectedUserId.value) || null,
);

const filteredUsers = computed(() => {
  const q = userFilter.value.trim().toLowerCase();
  if (!q) return users.value;
  return users.value.filter(
    (u) =>
      u.username.toLowerCase().includes(q) ||
      String(u.email || '')
        .toLowerCase()
        .includes(q),
  );
});

const installedModMap = computed(() => {
  const m = new Map<string, LocalModRow>();
  for (const row of installedMods.value) {
    const id = String(row?.id || '').trim();
    if (id) m.set(id, row);
  }
  return m;
});

const installedModIds = computed(() => new Set(installedModMap.value.keys()));

const syncLastText = computed(() => {
  const raw = String(syncStatus.value?.last_sync_at || '').trim();
  if (!raw) return '';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString();
});

function modLabel(modId: string) {
  const hit = assignableMods.value.find((m) => m.id === modId);
  return hit?.name || modId;
}

function isModInstalled(modId: string) {
  return installedModMap.value.has(String(modId || '').trim());
}

function modInstallText(modId: string) {
  const row = installedModMap.value.get(String(modId || '').trim());
  if (!row) return '未安装';
  const version = String(row.version || '').trim();
  return version ? `已安装 v${version}` : '已安装';
}

function normalizeLocalCatalogRows(raw: Record<string, unknown>): LocalModRow[] {
  const data = (raw?.data && typeof raw.data === 'object' ? raw.data : raw) as Record<string, unknown>;
  const installed = Array.isArray(data.installed) ? data.installed : [];
  const available = Array.isArray(data.available) ? data.available : [];
  const byId = new Map<string, LocalModRow>();
  for (const row of [...available, ...installed]) {
    if (!row || typeof row !== 'object') continue;
    const r = row as LocalModRow;
    const id = String(r.id || '').trim();
    if (!id) continue;
    const prev = byId.get(id) || {};
    const installedFlag = Boolean(prev.is_installed || r.is_installed || installed.includes(row));
    byId.set(id, { ...prev, ...r, id, is_installed: installedFlag });
  }
  return Array.from(byId.values()).filter((row) => row.is_installed);
}

async function refreshLocalStatus() {
  localStatusLoading.value = true;
  localStatusError.value = '';
  try {
    const catalogRes = await apiFetch('/api/mod-store/catalog');
    if (!catalogRes.ok) throw new Error(`本地 Mod 目录 HTTP ${catalogRes.status}`);
    installedMods.value = normalizeLocalCatalogRows(await catalogRes.json());
  } catch (e) {
    installedMods.value = [];
    localStatusError.value = `本地安装状态读取失败：${e instanceof Error ? e.message : String(e)}`;
  }
  try {
    const syncRes = await apiFetch('/api/xcmax/sync/status');
    if (!syncRes.ok) throw new Error(`同步状态 HTTP ${syncRes.status}`);
    const body = await syncRes.json();
    const data = body?.data && typeof body.data === 'object' ? body.data : body;
    syncStatus.value = data as Record<string, unknown>;
  } catch (e) {
    syncStatus.value = null;
    const msg = `同步状态读取失败：${e instanceof Error ? e.message : String(e)}`;
    localStatusError.value = localStatusError.value ? `${localStatusError.value}；${msg}` : msg;
  } finally {
    localStatusLoading.value = false;
  }
}

async function loadUsers() {
  const res = await xcmaxAdminApi.listUsers();
  const data = res as { users?: AdminUser[]; data?: { users?: AdminUser[] } };
  users.value = data.users || data.data?.users || [];
}

async function loadAssignable() {
  const res = await xcmaxAdminApi.listAssignableMods();
  const data = res as { mods?: AssignableMod[]; data?: { mods?: AssignableMod[] } };
  assignableMods.value = data.mods || data.data?.mods || [];
}

async function selectUser(u: AdminUser) {
  selectedUserId.value = u.id;
  modToBind.value = '';
  try {
    const res = await xcmaxAdminApi.listUserMods(u.id);
    const data = res as { mod_ids?: string[]; data?: { mod_ids?: string[] } };
    userModIds.value = [...(data.mod_ids || data.data?.mod_ids || u.mod_ids || [])];
  } catch (e) {
    userModIds.value = [...(u.mod_ids || [])];
    await appAlert(`加载用户 Mod 失败：${e instanceof Error ? e.message : String(e)}`);
  }
}

async function bindMod() {
  if (!selectedUserId.value || !modToBind.value) return;
  binding.value = true;
  try {
    await xcmaxAdminApi.bindUserMod(selectedUserId.value, modToBind.value);
    if (!userModIds.value.includes(modToBind.value)) {
      userModIds.value = [...userModIds.value, modToBind.value];
    }
    modToBind.value = '';
    await loadUsers();
    await appAlert('已绑定');
  } catch (e) {
    await appAlert(`绑定失败：${e instanceof Error ? e.message : String(e)}`);
  } finally {
    binding.value = false;
  }
}

async function unbindMod(modId: string) {
  if (!selectedUserId.value) return;
  try {
    await xcmaxAdminApi.unbindUserMod(selectedUserId.value, modId);
    userModIds.value = userModIds.value.filter((id) => id !== modId);
    await loadUsers();
  } catch (e) {
    await appAlert(`解绑失败：${e instanceof Error ? e.message : String(e)}`);
  }
}

async function toggleEnterprise(ev: Event) {
  if (!selectedUser.value) return;
  const checked = (ev.target as HTMLInputElement).checked;
  try {
    await xcmaxAdminApi.setUserEnterprise(selectedUser.value.id, checked);
    selectedUser.value.is_enterprise = checked;
    await loadUsers();
  } catch (e) {
    await appAlert(`更新失败：${e instanceof Error ? e.message : String(e)}`);
  }
}

async function startImpersonate() {
  if (!selectedUser.value) return;
  impersonateLoading.value = true;
  try {
    await xcmaxAdminApi.startImpersonate(selectedUser.value.id, selectedUser.value.username);
    const { useAccountProfileStore } = await import('@/stores/accountProfile');
    await useAccountProfileStore().refreshFromServer();
    await appAlert(`已进入代管：${selectedUser.value.username}`);
    window.location.href = '/';
  } catch (e) {
    await appAlert(`代管失败：${e instanceof Error ? e.message : String(e)}`);
  } finally {
    impersonateLoading.value = false;
  }
}

onMounted(async () => {
  try {
    await Promise.all([loadUsers(), loadAssignable(), refreshLocalStatus()]);
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  }
});
</script>

<style scoped>
.admin-entitlements-view .page-content {
  padding: 20px 24px 40px;
  max-width: 1100px;
  margin: 0 auto;
}

.admin-entitlements-head h2 {
  margin: 0 0 6px;
}

.admin-entitlements-alert {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.admin-entitlements-alert--soft {
  color: #455a64;
  background: #eef3f7;
  border-color: #d6e0e8;
}

.admin-sync-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 12px 0 16px;
  padding: 12px 14px;
  border: 1px solid #dce3eb;
  border-radius: 8px;
  background: #f8fafc;
}

.admin-entitlements-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
  margin-top: 16px;
  min-height: 420px;
}

.admin-user-list {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.admin-user-search {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: none;
  border-bottom: 1px solid #e5e7eb;
  font-size: 13px;
}

.admin-user-list__items {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 520px;
  overflow-y: auto;
}

.admin-user-row__btn {
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.admin-user-row.active .admin-user-row__btn,
.admin-user-row__btn:hover {
  background: #f3f4f6;
}

.admin-user-row__name {
  display: block;
  font-weight: 600;
  font-size: 14px;
}

.admin-user-row__meta {
  font-size: 12px;
}

.admin-user-detail {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fff;
  padding: 16px 18px;
}

.admin-user-detail--empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.admin-user-detail__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.admin-user-detail__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.admin-flag {
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.admin-mod-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 8px 0 16px;
}

.admin-mod-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 12px;
}

.admin-mod-install {
  color: #8a94a6;
  font-size: 11px;
}

.admin-mod-install.is-installed {
  color: #16803c;
}

.admin-mod-chip__remove {
  border: none;
  background: transparent;
  cursor: pointer;
  color: #64748b;
  font-size: 14px;
  line-height: 1;
}

.admin-mod-assign {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 8px;
}

.admin-mod-select {
  flex: 1;
  min-height: 34px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  padding: 0 10px;
}

@media (max-width: 900px) {
  .admin-entitlements-layout {
    grid-template-columns: 1fr;
  }
}
</style>
