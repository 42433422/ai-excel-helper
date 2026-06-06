<template>
  <div class="mod-store">
    <section class="modstore-primary">
      <h1 class="store-title">
        <i class="fa fa-puzzle-piece"></i>
        MOD 扩展
      </h1>
      <p class="lead">
        浏览并安装 Mod。
        <a :href="modstoreWebUrl" target="_blank" rel="noopener noreferrer">打开工作台</a>
      </p>
      <div v-if="onboardingBanner" class="onboarding-banner">
        <p>
          请先安装宿主基础员工包。
          <span v-if="missingModHint" class="mono">缺少：{{ missingModHint }}</span>
        </p>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="bootstrapBusy"
          @click="runBootstrapPack"
        >
          <i class="fa fa-download" :class="{ 'fa-spin': bootstrapBusy }"></i>
          安装宿主基础员工包
        </button>
        <button
          v-if="route.query.onboarding === '1'"
          type="button"
          class="btn btn-ghost"
          @click="finishOnboardingFromStore"
        >
          完成引导，进入对话
        </button>
      </div>
      <div class="modstore-toolbar">
        <a
          :href="modstoreWebUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="btn btn-primary"
        >
          <i class="fa fa-external-link"></i>
          在浏览器打开工作台
        </a>
        <a
          :href="marketBaseUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="btn btn-link"
        >
          <i class="fa fa-store"></i>
          修茈市场首页
        </a>
        <button type="button" class="btn btn-ghost" :disabled="loading" @click="loadMods">
          <i class="fa fa-refresh" :class="{ 'fa-spin': loading }"></i>
          刷新目录
        </button>
      </div>
    </section>

    <div class="catalog-store">
    <!-- 顶部导航与搜索 -->
    <div class="store-header">
      <h2 class="catalog-heading">
        <i class="fa fa-shopping-cart"></i>
        Catalog 与本地安装状态
      </h2>
      
      <div class="search-bar">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索 MOD..."
          class="search-input"
          @keyup.enter="searchMods"
        />
        <button class="search-btn" @click="searchMods">
          <i class="fa fa-search"></i>
          搜索
        </button>
      </div>
      
      <div class="filter-bar">
        <label class="filter-label">
          <input type="checkbox" v-model="filterInstalled" @change="applyFilters" />
          仅显示已安装
        </label>
        
        <select v-model="sortBy" @change="applyFilters" class="sort-select">
          <option value="name">按名称</option>
          <option value="downloads">按下载量</option>
          <option value="rating">按评分</option>
          <option value="created_at">最新上架</option>
        </select>
      </div>
    </div>

    <!-- 标签页：员工包分区 + 浏览 -->
    <div class="tabs">
      <button
        :class="['tab', { active: currentTab === 'host_foundation' }]"
        @click="switchTab('host_foundation')"
      >
        <i class="fa fa-cubes"></i>
        宿主基础员工
      </button>
      <button
        :class="['tab', { active: currentTab === 'workflow_employee' }]"
        @click="switchTab('workflow_employee')"
      >
        <i class="fa fa-users"></i>
        工作流员工
      </button>
      <button
        :class="['tab', { active: currentTab === 'industry_mod' }]"
        @click="switchTab('industry_mod')"
      >
        <i class="fa fa-industry"></i>
        行业扩展
      </button>
      <button
        :class="['tab', { active: currentTab === 'all' }]"
        @click="switchTab('all')"
      >
        全部
      </button>
      <button
        :class="['tab', { active: currentTab === 'installed' }]"
        @click="switchTab('installed')"
      >
        <i class="fa fa-check-circle"></i>
        已安装
      </button>
    </div>

    <!-- MOD 列表 -->
    <div class="mod-grid" v-if="filteredMods.length > 0">
      <div
        v-for="mod in filteredMods"
        :key="mod.id"
        class="mod-card"
        :class="{ installed: mod.is_installed }"
      >
        <div class="mod-card-header">
          <div class="mod-icon">
            <i :class="mod.icon || 'fa fa-puzzle-piece'"></i>
          </div>
          <div class="mod-basic">
            <h3 class="mod-name">{{ mod.name }}</h3>
            <p class="mod-author">by {{ mod.author || 'Unknown' }}</p>
            <div class="mod-badges">
              <span v-if="collectionLabel(mod)" class="source-badge collection-badge">
                {{ collectionLabel(mod) }}
              </span>
              <span :class="['source-badge', mod.source === 'remote' ? 'remote' : 'local']">
                {{ mod.source === 'remote' ? '远端 Catalog' : '本机' }}
              </span>
              <span v-if="mod.is_installed" class="source-badge installed-badge">已安装</span>
            </div>
          </div>
          <div class="mod-version">
            v{{ mod.version }}
          </div>
        </div>

        <p class="mod-description">{{ mod.description || '暂无描述' }}</p>

        <div class="mod-stats">
          <span class="stat" v-if="mod.download_count || mod.total_downloads">
            <i class="fa fa-download"></i>
            {{ mod.download_count || mod.total_downloads || 0 }}
          </span>
          <span class="stat" v-if="mod.avg_rating || mod.rating_count">
            <i class="fa fa-star"></i>
            {{ (mod.avg_rating || 0).toFixed(1) }}
            ({{ mod.rating_count || 0 }})
          </span>
        </div>

        <div class="mod-actions">
          <button
            v-if="!mod.is_installed"
            class="btn btn-primary"
            @click="installMod(mod)"
            :disabled="mod.installationInProgress"
          >
            <i class="fa fa-download"></i>
            {{ mod.installationInProgress ? '安装中...' : '安装' }}
          </button>
          
          <button
            v-else
            class="btn btn-secondary"
            @click="uninstallMod(mod)"
            :disabled="mod.uninstallationInProgress"
          >
            <i class="fa fa-trash"></i>
            {{ mod.uninstallationInProgress ? '卸载中...' : '卸载' }}
          </button>

          <button
            class="btn btn-info"
            @click="viewDetails(mod)"
          >
            <i class="fa fa-info-circle"></i>
            详情
          </button>

          <a
            v-if="mod.source === 'remote'"
            class="btn btn-link"
            :href="marketModUrl(mod)"
            target="_blank"
            rel="noopener noreferrer"
          >
            <i class="fa fa-external-link"></i>
            网页查看
          </a>

          <button
            v-if="hasUpdate(mod)"
            class="btn btn-warning"
            @click="updateMod(mod)"
            :disabled="mod.updateInProgress"
          >
            <i class="fa fa-refresh"></i>
            {{ mod.updateInProgress ? '更新中...' : '更新' }}
          </button>
        </div>

        <div class="mod-tags" v-if="mod.dependencies && Object.keys(mod.dependencies).length > 0">
          <span class="tag">
            <i class="fa fa-plug"></i>
            {{ Object.keys(mod.dependencies).length }} 依赖
          </span>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <i class="fa fa-inbox"></i>
      <p>暂无 MOD</p>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <i class="fa fa-spinner fa-spin"></i>
      <p>加载中...</p>
    </div>

    <!-- MOD 详情对话框 -->
    <Modal
      v-if="selectedMod"
      :title="selectedMod.name"
      @close="selectedMod = null"
    >
      <ModDetails :mod="selectedMod" @install="installMod" @uninstall="uninstallMod" />
    </Modal>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { apiFetch } from '@/utils/apiBase';
import { installHostFoundation } from '@/api/modStore';
import {
  catalogStoreCollection,
  HOST_FOUNDATION_EMPLOYEE_PACK_ID,
  isHostFoundationEmployeePackId,
  readBuildEdition,
  STORE_COLLECTION_HOST_FOUNDATION,
  STORE_COLLECTION_INDUSTRY_MOD,
  STORE_COLLECTION_WORKFLOW_EMPLOYEE,
} from '@/constants/genericModPack';
import { markProductFlowCompleted } from '@/constants/productFlow';
import { fetchDeliverableStatus } from '@/utils/platformShellApi';
import { useModsStore } from '@/stores/mods';
import Modal from '@/components/Modal.vue';
import ModDetails from './ModDetails.vue';
import { appAlert, appConfirm } from '@/utils/appDialog';

export default {
  name: 'ModStore',
  components: {
    Modal,
    ModDetails,
  },
  setup() {
    const route = useRoute();
    const router = useRouter();
    const modstoreWebUrl = String(
      import.meta.env.VITE_MODSTORE_WEB_URL ||
        'https://xiu-ci.com/market/workbench/unified',
    ).replace(/\/$/, '');
    const marketBaseUrl = String(
      import.meta.env.VITE_MARKET_BASE || 'https://xiu-ci.com/market',
    ).replace(/\/$/, '');
    const modsStore = useModsStore();

    function refreshHostMods() {
      void modsStore.refresh().catch((e) => {
        console.warn('[ModStore] modsStore.refresh:', e);
      });
    }

    const allMods = ref([]);
    const filteredMods = ref([]);
    const searchQuery = ref('');
    const filterInstalled = ref(false);
    const sortBy = ref('name');
    const currentTab = ref('all');
    const loading = ref(false);
    const selectedMod = ref(null);
    const deliverableOk = ref(true);
    const missingModIds = ref([]);
    const bootstrapBusy = ref(false);

    const onboardingBanner = computed(
      () => route.query.onboarding === '1' || deliverableOk.value === false,
    );
    const missingModHint = computed(() =>
      missingModIds.value.length ? missingModIds.value.join(', ') : '',
    );

    const refreshDeliverable = async () => {
      try {
        const st = await fetchDeliverableStatus(true);
        deliverableOk.value = st.deliverable !== false;
        missingModIds.value = st.missing_mod_ids || [];
      } catch {
        deliverableOk.value = true;
      }
    };

    const finishOnboardingFromStore = () => {
      markProductFlowCompleted();
      const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
      void router.replace(redirect);
    };

    const runBootstrapPack = async () => {
      bootstrapBusy.value = true;
      try {
        const edition = readBuildEdition();
        const res = await installHostFoundation(edition === 'minimal' ? 'minimal' : 'generic');
        await refreshDeliverable();
        refreshHostMods();
        if (res.success && deliverableOk.value) {
          await appAlert('宿主基础能力员工包已就绪，可开始使用。');
          const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/';
          await router.replace(redirect);
        } else {
          await appAlert(res.message || '宿主 bridge 未齐，请检查本机 mods 种子目录。');
        }
      } catch (e) {
        await appAlert(e instanceof Error ? e.message : '装包失败');
      } finally {
        bootstrapBusy.value = false;
      }
    };

    const collectionLabel = (mod) => {
      const sc = catalogStoreCollection(mod);
      if (sc === STORE_COLLECTION_HOST_FOUNDATION) return '宿主基础员工';
      if (sc === STORE_COLLECTION_WORKFLOW_EMPLOYEE) return '工作流员工';
      if (sc === STORE_COLLECTION_INDUSTRY_MOD) return '行业扩展';
      return '';
    };

    const filterByCollectionTab = (mods) => {
      if (currentTab.value === 'host_foundation') {
        return mods.filter((m) => catalogStoreCollection(m) === STORE_COLLECTION_HOST_FOUNDATION);
      }
      if (currentTab.value === 'workflow_employee') {
        return mods.filter((m) => catalogStoreCollection(m) === STORE_COLLECTION_WORKFLOW_EMPLOYEE);
      }
      if (currentTab.value === 'industry_mod') {
        return mods.filter((m) => catalogStoreCollection(m) === STORE_COLLECTION_INDUSTRY_MOD);
      }
      return mods;
    };

    const loadMods = async () => {
      loading.value = true;
      try {
        const response = await apiFetch('/api/mod-store/catalog');
        const data = await response.json();
        
        if (data.success) {
          allMods.value = data.data.available || [];
          applyFilters();
        }
      } catch (error) {
        console.error('Failed to load mods:', error);
      } finally {
        loading.value = false;
      }
    };

    const searchMods = async () => {
      if (!searchQuery.value.trim()) {
        loadMods();
        return;
      }

      loading.value = true;
      try {
        const params = new URLSearchParams({
          q: searchQuery.value,
          installed: filterInstalled.value,
          limit: 50,
        });

        const response = await apiFetch(`/api/mod-store/search?${params}`);
        const data = await response.json();

        if (data.success) {
          allMods.value = data.data || [];
          applyFilters();
        }
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        loading.value = false;
      }
    };

    const applyFilters = () => {
      let mods = [...allMods.value];

      if (filterInstalled.value) {
        mods = mods.filter(mod => mod.is_installed);
      }

      mods = filterByCollectionTab(mods);

      if (sortBy.value === 'downloads') {
        mods.sort((a, b) => (b.total_downloads || b.download_count || 0) - (a.total_downloads || a.download_count || 0));
      } else if (sortBy.value === 'rating') {
        mods.sort((a, b) => (b.avg_rating || 0) - (a.avg_rating || 0));
      } else if (sortBy.value === 'created_at') {
        mods.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      } else {
        mods.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
      }

      filteredMods.value = mods;
    };

    const switchTab = async (tab) => {
      currentTab.value = tab;
      loading.value = true;

      try {
        if (tab !== 'installed') {
          filterInstalled.value = false;
        }
        if (
          tab === 'host_foundation' ||
          tab === 'workflow_employee' ||
          tab === 'industry_mod'
        ) {
          await loadMods();
        } else if (tab === 'installed') {
          filterInstalled.value = true;
          applyFilters();
        } else {
          await loadMods();
        }
      } catch (error) {
        console.error('Failed to switch tab:', error);
      } finally {
        loading.value = false;
      }
    };

    const installMod = async (mod) => {
      mod.installationInProgress = true;
      try {
        let data;
        if (isHostFoundationEmployeePackId(mod.pkg_id || mod.id)) {
          const edition = readBuildEdition();
          data = await installHostFoundation(edition === 'minimal' ? 'minimal' : 'generic');
        } else {
          const payload = {
            pkg_id: mod.pkg_id || mod.id,
            version: mod.version,
            package_file: mod.package_file,
            activate: true,
            verify_signature: false,
          };
          const response = await apiFetch('/api/mod-store/install', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          data = await response.json();
        }

        if (data.success) {
          mod.is_installed = true;
          await appAlert(`MOD ${mod.name} 安装成功！`);
          await loadMods();
          refreshHostMods();
        } else {
          await appAlert(`安装失败：${data.error || data.detail}`);
        }
      } catch (error) {
        console.error('Installation failed:', error);
        await appAlert('安装失败，请重试');
      } finally {
        mod.installationInProgress = false;
      }
    };

    const uninstallMod = async (mod) => {
      if (!(await appConfirm(`确定要卸载 MOD "${mod.name}" 吗？`, { danger: true }))) {
        return;
      }

      mod.uninstallationInProgress = true;
      try {
        const formData = new FormData();
        formData.append('mod_id', mod.id);
        formData.append('remove_files', 'true');

        const response = await apiFetch('/api/mod-store/uninstall', {
          method: 'POST',
          body: formData,
        });

        const data = await response.json();

        if (data.success) {
          mod.is_installed = false;
          await appAlert(`MOD ${mod.name} 卸载成功！`);
          await loadMods();
          refreshHostMods();
        } else {
          await appAlert(`卸载失败：${data.error || data.detail}`);
        }
      } catch (error) {
        console.error('Uninstallation failed:', error);
        await appAlert('卸载失败，请重试');
      } finally {
        mod.uninstallationInProgress = false;
      }
    };

    const updateMod = async (mod) => {
      mod.updateInProgress = true;
      try {
        const payload = {
          mod_id: mod.id,
          pkg_id: mod.pkg_id || mod.id,
          version: mod.new_version || mod.version,
          package_file: mod.package_file,
          verify_signature: false,
        };

        const response = await apiFetch('/api/mod-store/update', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });

        const data = await response.json();

        if (data.success) {
          mod.version = data.data.version;
          await appAlert(`MOD ${mod.name} 更新成功！`);
          await loadMods();
          refreshHostMods();
        } else {
          await appAlert(`更新失败：${data.error || data.detail}`);
        }
      } catch (error) {
        console.error('Update failed:', error);
        await appAlert('更新失败，请重试');
      } finally {
        mod.updateInProgress = false;
      }
    };

    const hasUpdate = (mod) => {
      return mod.is_installed && mod.new_version && mod.new_version !== mod.version;
    };

    const viewDetails = (mod) => {
      selectedMod.value = mod;
    };

    const marketModUrl = (mod) => {
      const id = encodeURIComponent(mod.pkg_id || mod.id || '');
      return `${marketBaseUrl}/mods/${id}`;
    };

    onMounted(() => {
      currentTab.value = 'host_foundation';
      void loadMods();
      void refreshDeliverable();
    });

    return {
      modstoreWebUrl,
      marketBaseUrl,
      onboardingBanner,
      missingModHint,
      bootstrapBusy,
      runBootstrapPack,
      finishOnboardingFromStore,
      allMods,
      filteredMods,
      searchQuery,
      filterInstalled,
      sortBy,
      currentTab,
      loading,
      selectedMod,
      loadMods,
      searchMods,
      applyFilters,
      switchTab,
      installMod,
      uninstallMod,
      updateMod,
      hasUpdate,
      viewDetails,
      marketModUrl,
      collectionLabel,
      HOST_FOUNDATION_EMPLOYEE_PACK_ID,
    };
  },
};
</script>

<style scoped>
.mod-store {
  padding: 22px;
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  overflow-y: auto;
}

.modstore-primary {
  margin-bottom: 18px;
  padding: 24px;
  border-radius: 26px;
  background:
    radial-gradient(circle at 84% 0%, rgba(34, 211, 238, 0.18), transparent 28%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(239, 246, 255, 0.82));
  border: 1px solid rgba(213, 222, 235, 0.78);
  box-shadow: var(--app-shadow-md, 0 18px 44px rgba(15, 23, 42, 0.12));
}

.lead {
  color: #475569;
  line-height: 1.6;
  margin: 0 0 12px;
  font-size: 14px;
  max-width: 980px;
}

.lead .mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  color: #2c3e50;
}

.lead a {
  color: #2980b9;
  font-weight: 600;
}

.onboarding-banner {
  margin: 12px 0 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
  border: 1px solid #93c5fd;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.onboarding-banner p {
  margin: 0;
  flex: 1 1 280px;
  color: #1e3a5f;
  font-size: 14px;
}

.modstore-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.modstore-toolbar .btn.btn-link {
  text-decoration: none;
}

.catalog-store {
  padding: 18px;
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.68);
  border: 1px solid rgba(213, 222, 235, 0.72);
  box-shadow: var(--app-shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.08));
  backdrop-filter: blur(14px);
}

.catalog-heading {
  font-size: 21px;
  color: #0f172a;
  margin: 0;
  letter-spacing: -0.02em;
}

.store-header {
  margin-bottom: 22px;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(300px, 1.2fr);
  align-items: center;
  gap: 14px;
}

.store-title {
  font-size: 30px;
  color: #0f172a;
  margin-bottom: 14px;
  letter-spacing: -0.04em;
}

.store-title i {
  color: #3498db;
  margin-right: 10px;
}

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 0;
}

.search-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid rgba(190, 203, 221, 0.9);
  border-radius: 14px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.9);
}

.search-input:focus {
  outline: none;
  border-color: #3498db;
}

.search-btn {
  padding: 10px 18px;
  background: linear-gradient(135deg, #0b72d9, #13a8e8);
  color: white;
  border: 1px solid rgba(11, 114, 217, 0.9);
  border-radius: 14px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 800;
  box-shadow: 0 8px 18px rgba(11, 114, 217, 0.16);
}

.search-btn:hover {
  background: #2980b9;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 7px;
  cursor: pointer;
  padding: 8px 11px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(203, 213, 225, 0.72);
  color: #475569;
  font-weight: 650;
}

.sort-select {
  padding: 8px 12px;
  border: 1px solid rgba(190, 203, 221, 0.9);
  border-radius: 999px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.84);
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  border-bottom: 0;
  padding: 6px;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.78);
  width: fit-content;
  border: 1px solid rgba(226, 232, 240, 0.86);
}

.tab {
  padding: 9px 15px;
  background: transparent;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  font-weight: 750;
  transition: all 0.2s;
}

.tab:hover {
  background: #f5f5f5;
}

.tab.active {
  background: #ffffff;
  border: 1px solid rgba(147, 197, 253, 0.62);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  color: #0b72d9;
}

.tab.active {
  color: white;
}

.tab.active {
  color: #0b72d9;
}

.tab i {
  margin-right: 5px;
}

.mod-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  gap: 20px;
}

.mod-card {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(213, 222, 235, 0.82);
  border-radius: 22px;
  padding: 20px;
  transition: all 0.22s ease;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
}

.mod-card::before {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at 84% 12%, rgba(14, 116, 217, 0.12), transparent 28%);
  opacity: 0;
  transition: opacity 0.22s ease;
}

.mod-card:hover {
  border-color: rgba(11, 114, 217, 0.46);
  box-shadow: 0 18px 38px rgba(11, 114, 217, 0.14);
  transform: translateY(-2px);
}

.mod-card:hover::before {
  opacity: 1;
}

.mod-card.installed {
  border-color: rgba(22, 163, 74, 0.42);
  background: linear-gradient(135deg, rgba(240, 253, 244, 0.9), rgba(255, 255, 255, 0.9));
}

.mod-card-header {
  display: flex;
  align-items: flex-start;
  gap: 15px;
  margin-bottom: 15px;
}

.mod-icon {
  width: 50px;
  height: 50px;
  background: linear-gradient(135deg, #0b72d9, #22c1f1);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 24px;
  box-shadow: 0 10px 22px rgba(11, 114, 217, 0.2);
}

.mod-name {
  font-size: 18px;
  color: #0f172a;
  margin: 0 0 5px 0;
  letter-spacing: -0.02em;
}

.mod-author {
  font-size: 13px;
  color: #7f8c8d;
  margin: 0;
}

.mod-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.source-badge {
  font-size: 11px;
  line-height: 1;
  color: #54616c;
  background: #eef2f5;
  border-radius: 999px;
  padding: 4px 7px;
}

.source-badge.collection-badge {
  color: #4338ca;
  background: rgba(99, 102, 241, 0.12);
}

.source-badge.remote {
  color: #1f5c99;
  background: #e8f3ff;
}

.source-badge.local,
.installed-badge {
  color: #1f7a4d;
  background: #e8f8ef;
}

.mod-version {
  position: absolute;
  top: 20px;
  right: 20px;
  font-size: 12px;
  color: #64748b;
  background: rgba(248, 250, 252, 0.92);
  padding: 5px 9px;
  border: 1px solid rgba(226, 232, 240, 0.86);
  border-radius: 999px;
  font-weight: 750;
}

.mod-description {
  font-size: 14px;
  color: #475569;
  margin-bottom: 15px;
  line-height: 1.6;
  min-height: 60px;
}

.mod-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.stat {
  font-size: 13px;
  color: #7f8c8d;
  display: flex;
  align-items: center;
  gap: 5px;
}

.stat i {
  color: #f39c12;
}

.mod-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.mod-actions .btn {
  border-radius: 12px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 5px;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-ghost {
  background: #f8f9fa;
  color: #2c3e50;
  border: 1px solid #dee2e6;
}

.btn-ghost:hover:not(:disabled) {
  background: #e9ecef;
}

.btn-secondary {
  background: #e74c3c;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #c0392b;
}

.btn-info {
  background: #95a5a6;
  color: white;
}

.btn-info:hover:not(:disabled) {
  background: #7f8c8d;
}

.btn-warning {
  background: #f39c12;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #e67e22;
}

.btn-link {
  color: #2c3e50;
  background: #ecf0f1;
  text-decoration: none;
}

.btn-link:hover {
  background: #dfe6e9;
}

.mod-tags {
  margin-top: 15px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  font-size: 12px;
  color: #7f8c8d;
  background: #f5f5f5;
  padding: 4px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #95a5a6;
}

.empty-state i {
  font-size: 48px;
  margin-bottom: 15px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(8px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  z-index: 1000;
}

.loading-overlay i {
  font-size: 48px;
  margin-bottom: 15px;
}

@media (max-width: 900px) {
  .store-header {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}
</style>
