<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ApiError } from '@/api';
import { authApi } from '@/api/auth';
import { applyMarketTokensAfterFhdLogin } from '@/api/marketAccount';
import {
  loginAccountInputPlaceholder,
  loginPageTitle,
  loginPasswordInputPlaceholder,
} from '@/constants/loginBranding';
import { isSunbirdAccountUsername } from '@/constants/accountModBinding';
import { fetchProductSku } from '@/utils/productSku';
import { useAccountProfileStore } from '@/stores/accountProfile';
import type { AccountKind } from '@/api/auth';

const route = useRoute();
const router = useRouter();
const accountProfileStore = useAccountProfileStore();

const username = ref('');
const accountKind = ref<AccountKind>('enterprise');
const password = ref('');
const showPassword = ref(false);
const loading = ref(false);
const errorMessage = ref('');
const altLoginHint = ref('');

function peelNestedLoginRedirect(raw: string): string {
  let v = raw.trim();
  for (let i = 0; i < 5 && v.startsWith('/login'); i++) {
    const q = v.indexOf('?');
    if (q < 0) return '/';
    const nested = new URLSearchParams(v.slice(q + 1)).get('redirect');
    v = nested ? decodeURIComponent(nested.trim()) : '/';
  }
  const pathOnly = v.split('?')[0].split('#')[0];
  return pathOnly;
}

const redirectPath = computed(() => {
  const raw = route.query.redirect;
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (!value || typeof value !== 'string') return '/';
  let v = value.trim();
  try {
    v = decodeURIComponent(v);
  } catch {
    /* keep */
  }
  v = peelNestedLoginRedirect(v);
  if (!v.startsWith('/') || v.startsWith('//') || v.startsWith('/login')) return '/';
  return v;
});

const canSubmit = computed(() => username.value.trim().length > 0 && password.value.length > 0 && !loading.value);

const productSku = ref<string>('generic');
const isEnterpriseEdition = computed(() => productSku.value === 'enterprise');

const loginHeading = computed(() =>
  accountKind.value === 'admin' ? '管理员登录' : '企业账号登录',
);
const accountPlaceholder = computed(() => loginAccountInputPlaceholder(productSku.value));
const passwordPlaceholder = computed(() => loginPasswordInputPlaceholder());
const registerRoute = computed(() => ({
  name: 'login-register' as const,
  query: route.query,
}));
const forgotAccountRoute = computed(() => ({
  name: 'login-forgot-account' as const,
  query: route.query,
}));
const forgotPasswordRoute = computed(() => ({
  name: 'login-forgot-password' as const,
  query: route.query,
}));
const loginHelpRoute = computed(() => ({
  name: 'login-help' as const,
  query: route.query,
}));

onMounted(async () => {
  productSku.value = await fetchProductSku();
  document.title = loginPageTitle(productSku.value);
});

function formatLoginFailurePayload(payload: Record<string, unknown> | null | undefined): string {
  const r = payload && typeof payload === 'object' ? payload : {};
  const errObj = r.error && typeof r.error === 'object' ? (r.error as Record<string, unknown>) : null;
  const message =
    (typeof r.message === 'string' && r.message.trim()) ||
    (errObj && typeof errObj.message === 'string' && errObj.message.trim()) ||
    '';
  const errorId = typeof r.error_id === 'string' && r.error_id.trim() ? r.error_id.trim() : '';

  if (message) {
    let out = message;
    if (errorId && !out.includes(errorId)) {
      out = `${out}（错误编号 ${errorId}）`;
    }
    return out;
  }
  if (errorId) {
    return `登录失败（错误编号 ${errorId}），请联系管理员排查后端日志。`;
  }
  return '登录失败，请检查账号或密码';
}

function showAltLoginMessage(label: string) {
  accountKind.value = 'enterprise';
  altLoginHint.value = `${label} 暂未在本版本开放，请使用账号登录或联系管理员。`;
}

function selectEnterpriseLogin() {
  accountKind.value = 'enterprise';
  altLoginHint.value = '';
  errorMessage.value = '';
}

function selectAdminLogin() {
  accountKind.value = 'admin';
  altLoginHint.value = '';
  errorMessage.value = '';
}

async function submitLogin() {
  if (!canSubmit.value) {
    errorMessage.value = '请输入账号和密码';
    return;
  }
  loading.value = true;
  errorMessage.value = '';
  try {
    const result = await authApi.login(
      username.value.trim(),
      password.value,
      accountKind.value,
    );
    const raw = result as unknown as Record<string, unknown>;
    const ok = raw?.success === true || (raw?.data as Record<string, unknown> | undefined)?.success === true;
    if (!ok) {
      const nested = (raw?.data as Record<string, unknown> | undefined) || {};
      errorMessage.value = formatLoginFailurePayload({
        ...nested,
        message: raw.message ?? nested.message,
        error_id: raw.error_id ?? nested.error_id,
        error: raw.error ?? nested.error,
      });
      return;
    }
    await applyMarketTokensAfterFhdLogin(raw);

    accountProfileStore.applyFromLoginPayload(raw as Record<string, unknown>);

    const loginUser =
      raw?.data && typeof raw.data === 'object' && !Array.isArray(raw.data)
        ? (raw.data as Record<string, unknown>)
        : raw;
    const accountUsername = String(
      loginUser?.username || username.value || '',
    ).trim();
    const sunbirdAccount = isSunbirdAccountUsername(accountUsername);
    if (isEnterpriseEdition.value || sunbirdAccount) {
      try {
        const { readEntitledModIdsFromAuthPayload, useModsStore } = await import(
          '@/stores/mods',
        );
        const entitled = readEntitledModIdsFromAuthPayload(raw);
        await useModsStore().initialize(true, {
          entitledModIds: entitled,
          forceFromEntitlements: sunbirdAccount || entitled.length > 0,
          accountUsername,
        });
      } catch (modErr) {
        console.warn('[Login] mods refresh after auth:', modErr);
      }
    }

    await router.replace(redirectPath.value);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      const d = error.data && typeof error.data === 'object' ? (error.data as Record<string, unknown>) : {};
      errorMessage.value = formatLoginFailurePayload({
        ...d,
        message:
          (typeof d.message === 'string' && d.message) ||
          (typeof (d.error as { message?: string } | undefined)?.message === 'string' &&
            (d.error as { message: string }).message) ||
          error.message,
        error_id: d.error_id,
        error: d.error,
      });
    } else {
      const err = error as { response?: { data?: { message?: string; error?: { message?: string } } } };
      const data = err.response?.data;
      errorMessage.value = data?.error?.message || data?.message || '登录失败，请稍后再试';
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-view" aria-label="登录">
    <section class="login-panel" aria-labelledby="login-heading">
      <router-link class="login-register-corner" :to="registerRoute"> 注册 </router-link>

      <h1 id="login-heading" class="login-heading">{{ loginHeading }}</h1>
      <p class="login-kind-hint muted">
        <template v-if="accountKind === 'admin'">需使用修茈市场平台管理员账号</template>
        <template v-else>企业版账号登录后展示企业品牌名</template>
      </p>

      <form class="login-form" @submit.prevent="submitLogin">
        <div class="login-field-line">
          <input
            v-model="username"
            type="text"
            name="username"
            autocomplete="username"
            :placeholder="accountPlaceholder"
            :disabled="loading"
            autofocus
          />
        </div>

        <div class="login-field-line login-field-line--password">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            name="password"
            autocomplete="current-password"
            :placeholder="passwordPlaceholder"
            :disabled="loading"
          />
          <button
            type="button"
            class="login-password-toggle"
            :disabled="loading"
            :aria-label="showPassword ? '隐藏密码' : '显示密码'"
            @click="showPassword = !showPassword"
          >
            <i class="fa" :class="showPassword ? 'fa-eye-slash' : 'fa-eye'" aria-hidden="true"></i>
          </button>
        </div>

        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>

        <button class="login-submit" type="submit" :disabled="!canSubmit">
          <span>{{ loading ? '正在登录...' : '登录' }}</span>
          <i class="fa fa-long-arrow-right" aria-hidden="true"></i>
        </button>
      </form>

      <div class="login-alt">
        <div class="login-alt-divider">
          <span>其他登录方式</span>
        </div>
        <ul class="login-alt-list">
          <li>
            <button
              type="button"
              class="login-alt-item"
              :class="{ 'is-active': accountKind === 'enterprise' }"
              :aria-pressed="accountKind === 'enterprise'"
              :disabled="loading"
              @click="selectEnterpriseLogin"
            >
              <span class="login-alt-icon login-alt-icon--sub" aria-hidden="true">
                <i class="fa fa-user"></i>
              </span>
              <span>企业登录</span>
            </button>
          </li>
          <li>
            <button type="button" class="login-alt-item" @click="showAltLoginMessage('通行密钥')">
              <span class="login-alt-icon login-alt-icon--key" aria-hidden="true">
                <i class="fa fa-key"></i>
              </span>
              <span>通行密钥</span>
            </button>
          </li>
          <li>
            <button
              type="button"
              class="login-alt-item"
              :class="{ 'is-active': accountKind === 'admin' }"
              :aria-pressed="accountKind === 'admin'"
              :disabled="loading"
              @click="selectAdminLogin"
            >
              <span class="login-alt-icon login-alt-icon--admin" aria-hidden="true">
                <i class="fa fa-shield"></i>
              </span>
              <span>管理员</span>
            </button>
          </li>
        </ul>
        <p v-if="altLoginHint" class="login-alt-hint" role="status">{{ altLoginHint }}</p>
      </div>

      <footer class="login-footer">
        <router-link :to="forgotAccountRoute">忘记账号</router-link>
        <span class="login-footer-sep" aria-hidden="true">|</span>
        <router-link :to="forgotPasswordRoute">忘记密码</router-link>
        <span class="login-footer-sep" aria-hidden="true">|</span>
        <router-link :to="loginHelpRoute">登录异常帮助文档</router-link>
      </footer>
    </section>
  </main>
</template>

<style scoped>
.login-view {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 40px 16px;
  background: #f3f4f7;
  color: #000;
}

.login-panel {
  position: relative;
  width: min(460px, 100%);
  padding: 48px 40px 32px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.login-register-corner {
  position: absolute;
  top: 0;
  right: 0;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  padding: 10px 12px 0 0;
  font-size: 13px;
  font-weight: 500;
  color: #0052d9;
  text-decoration: none;
  background: linear-gradient(225deg, #e8f3ff 0%, #e8f3ff 48%, transparent 48%);
  z-index: 2;
}

.login-register-corner:hover {
  color: #003cab;
}

.login-kind-hint {
  margin: -8px 0 20px;
  font-size: 12px;
  text-align: center;
  line-height: 1.45;
}

.login-heading {
  margin: 0 0 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e6e9ef;
  font-size: 16px;
  font-weight: 500;
  color: #0052d9;
  text-align: center;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-bottom: 8px;
}

.login-field-line {
  position: relative;
  border-bottom: 1px solid #dcdfe6;
  transition: border-color 160ms ease;
}

.login-field-line:focus-within {
  border-color: #0052d9;
}

.login-field-line input {
  width: 100%;
  height: 48px;
  border: 0;
  background: transparent;
  color: #000;
  font: inherit;
  font-size: 14px;
  outline: none;
  padding: 0 2px;
}

.login-field-line input::placeholder {
  color: #bbb;
}

.login-field-line input:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.login-field-line--password input {
  padding-right: 40px;
}

.login-password-toggle {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border: 0;
  background: transparent;
  color: #bbb;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.login-password-toggle:hover:not(:disabled) {
  color: #666;
}

.login-error {
  margin: 12px 0 0;
  padding: 8px 10px;
  font-size: 13px;
  color: #e34d59;
  background: #fff1f0;
  border: 1px solid #ffd4d1;
}

.login-submit {
  margin-top: 28px;
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  border: 0;
  border-radius: 0;
  background: #0052d9;
  color: #fff;
  font: inherit;
  font-size: 16px;
  cursor: pointer;
  transition: background 160ms ease;
}

.login-submit:hover:not(:disabled) {
  background: #003cab;
}

.login-submit:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.login-submit .fa {
  font-size: 18px;
}

.login-alt {
  margin-top: 32px;
}

.login-alt-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  color: #bbb;
  font-size: 12px;
}

.login-alt-divider::before,
.login-alt-divider::after {
  content: '';
  flex: 1;
  height: 0;
  border-top: 1px dashed #e0e0e0;
}

.login-alt-list {
  display: flex;
  justify-content: center;
  gap: 48px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.login-alt-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0;
  font: inherit;
  font-size: 12px;
  color: #666;
  cursor: pointer;
  transition: color 160ms ease;
}

.login-alt-item:hover {
  color: #0052d9;
}

.login-alt-item.is-active {
  color: #0052d9;
  font-weight: 600;
}

.login-alt-item.is-active .login-alt-icon--sub,
.login-alt-item.is-active .login-alt-icon--admin {
  box-shadow: 0 0 0 2px #93c5fd;
}

.login-alt-icon {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  font-size: 16px;
  color: #fff;
}

.login-alt-icon--sub {
  background: #6b7a99;
}

.login-alt-icon--key {
  background: #8b5cf6;
}

.login-alt-icon--admin {
  background: #0b72d9;
}

.login-alt-hint {
  margin: 14px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: #888;
  text-align: center;
}

.login-footer {
  margin-top: 28px;
  padding-top: 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 6px 8px;
  font-size: 12px;
}

.login-footer a {
  color: #0052d9;
  text-decoration: none;
}

.login-footer a:hover {
  text-decoration: underline;
}

.login-footer-sep {
  color: #dcdfe6;
}

@media (max-width: 520px) {
  .login-panel {
    padding: 44px 22px 24px;
  }

  .login-alt-list {
    gap: 24px;
  }

  .login-alt-item span:last-child {
    font-size: 11px;
  }
}
</style>
