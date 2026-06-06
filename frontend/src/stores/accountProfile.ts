import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authApi, type AccountKind } from '@/api/auth';

export const useAccountProfileStore = defineStore('accountProfile', () => {
  const accountKind = ref<AccountKind>('enterprise');
  const companyBrand = ref('');
  const marketIsAdmin = ref(false);
  const marketIsEnterprise = ref(false);
  const impersonatingMarketUserId = ref<number | null>(null);
  const impersonatingUsername = ref('');
  const loaded = ref(false);

  const isAdminAccount = computed(
    () => accountKind.value === 'admin' && marketIsAdmin.value,
  );

  const isImpersonating = computed(() => impersonatingMarketUserId.value != null);

  const displayBrand = computed(() => {
    const brand = companyBrand.value.trim();
    if (brand) return brand;
    return '';
  });

  function applyFromMeData(data: Record<string, unknown> | null | undefined) {
    if (!data || typeof data !== 'object') return;
    const kind = String(data.account_kind || 'enterprise').trim();
    if (kind === 'personal' || kind === 'enterprise' || kind === 'admin') {
      accountKind.value = kind;
    }
    companyBrand.value = String(data.company_brand || '').trim();
    marketIsAdmin.value = Boolean(data.market_is_admin);
    marketIsEnterprise.value = Boolean(data.market_is_enterprise);
    const imp = data.impersonating_market_user_id;
    impersonatingMarketUserId.value =
      imp === null || imp === undefined || imp === '' ? null : Number(imp);
    impersonatingUsername.value = String(data.impersonating_username || '').trim();
    loaded.value = true;
  }

  function applyFromLoginPayload(raw: Record<string, unknown>) {
    const payload =
      raw.data && typeof raw.data === 'object' && !Array.isArray(raw.data)
        ? (raw.data as Record<string, unknown>)
        : raw;
    const kind = String(payload.account_kind || 'enterprise').trim();
    if (kind === 'personal' || kind === 'enterprise' || kind === 'admin') {
      accountKind.value = kind;
    }
    if (payload.company_brand != null) {
      companyBrand.value = String(payload.company_brand).trim();
    }
    marketIsAdmin.value = Boolean(payload.market_is_admin);
    marketIsEnterprise.value = Boolean(payload.market_is_enterprise);
    loaded.value = true;
  }

  async function refreshFromServer() {
    try {
      const res = await authApi.getCurrentUser();
      if (res?.success && res.data) {
        applyFromMeData(res.data as Record<string, unknown>);
      }
    } catch {
      /* ignore */
    }
  }

  function clear() {
    accountKind.value = 'enterprise';
    companyBrand.value = '';
    marketIsAdmin.value = false;
    marketIsEnterprise.value = false;
    impersonatingMarketUserId.value = null;
    impersonatingUsername.value = '';
    loaded.value = false;
  }

  return {
    accountKind,
    companyBrand,
    marketIsAdmin,
    marketIsEnterprise,
    impersonatingMarketUserId,
    impersonatingUsername,
    loaded,
    isAdminAccount,
    isImpersonating,
    displayBrand,
    applyFromMeData,
    applyFromLoginPayload,
    refreshFromServer,
    clear,
  };
});
