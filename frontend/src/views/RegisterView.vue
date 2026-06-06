<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ApiError } from '@/api';
import { authApi } from '@/api/auth';
import { applyMarketTokensAfterFhdLogin } from '@/api/marketAccount';
import { loginPageTitle } from '@/constants/loginBranding';
import { fetchProductSku } from '@/utils/productSku';

const route = useRoute();
const router = useRouter();

const username = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const showPassword = ref(false);
const loading = ref(false);
const errorMessage = ref('');

const productSku = ref<string>('generic');
const isEnterpriseEdition = computed(() => productSku.value === 'enterprise');
const requiresEmail = computed(() => isEnterpriseEdition.value);

const loginBackRoute = computed(() => ({
  name: 'login' as const,
  query: route.query,
}));

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

const canSubmit = computed(() => {
  if (loading.value) return false;
  if (!username.value.trim() || password.value.length < 6) return false;
  if (password.value !== confirmPassword.value) return false;
  if (requiresEmail.value && !email.value.trim()) return false;
  return true;
});

onMounted(async () => {
  productSku.value = await fetchProductSku();
  document.title = `注册 · ${loginPageTitle(productSku.value).replace(' · 登录', '')}`;
});

function formatRegisterError(error: unknown): string {
  if (error instanceof ApiError) {
    const d = error.data && typeof error.data === 'object' ? (error.data as Record<string, unknown>) : {};
    const errObj = d.error && typeof d.error === 'object' ? (d.error as Record<string, unknown>) : null;
    return (
      (typeof d.message === 'string' && d.message) ||
      (errObj && typeof errObj.message === 'string' && (errObj.message as string)) ||
      error.message ||
      '注册失败'
    );
  }
  const err = error as { message?: string };
  return err.message || '注册失败，请稍后再试';
}

async function submitRegister() {
  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致';
    return;
  }
  if (!canSubmit.value) {
    errorMessage.value = requiresEmail.value
      ? '请填写用户名、邮箱和密码（至少 6 位）'
      : '请填写用户名和密码（至少 6 位）';
    return;
  }

  loading.value = true;
  errorMessage.value = '';
  try {
    const result = await authApi.register({
      username: username.value.trim(),
      password: password.value,
      email: email.value.trim() || undefined,
    });
    const raw = result as unknown as Record<string, unknown>;
    const ok = raw?.success === true;
    if (!ok) {
      const errObj = raw.error && typeof raw.error === 'object' ? (raw.error as Record<string, unknown>) : {};
      errorMessage.value =
        (typeof raw.message === 'string' && raw.message) ||
        (typeof errObj.message === 'string' && (errObj.message as string)) ||
        '注册失败';
      return;
    }

    await applyMarketTokensAfterFhdLogin(raw);

    if (isEnterpriseEdition.value) {
      try {
        const { useModsStore } = await import('@/stores/mods');
        await useModsStore().initialize(true);
      } catch (modErr) {
        console.warn('[Register] enterprise mods refresh:', modErr);
      }
    }

    await router.replace(redirectPath.value);
  } catch (error: unknown) {
    errorMessage.value = formatRegisterError(error);
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-view" aria-label="注册">
    <section class="login-panel" aria-labelledby="register-heading">
      <router-link class="login-register-corner" :to="loginBackRoute"> 登录 </router-link>

      <h1 id="register-heading" class="login-heading">账号注册</h1>
      <p class="register-hint">
        {{
          isEnterpriseEdition
            ? '将在本机数据库创建用户，并同步注册修茈市场账号（需市场服务可达）。'
            : '在本机服务器数据库创建账号，注册成功后自动登录。'
        }}
      </p>

      <form class="login-form" @submit.prevent="submitRegister">
        <div class="login-field-line">
          <input
            v-model="username"
            type="text"
            name="username"
            autocomplete="username"
            placeholder="用户名"
            :disabled="loading"
            autofocus
          />
        </div>

        <div v-if="requiresEmail" class="login-field-line">
          <input
            v-model="email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="邮箱（企业版必填）"
            :disabled="loading"
          />
        </div>
        <div v-else class="login-field-line">
          <input
            v-model="email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="邮箱（选填）"
            :disabled="loading"
          />
        </div>

        <div class="login-field-line login-field-line--password">
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            name="password"
            autocomplete="new-password"
            placeholder="密码（至少 6 位）"
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

        <div class="login-field-line">
          <input
            v-model="confirmPassword"
            :type="showPassword ? 'text' : 'password'"
            name="confirm-password"
            autocomplete="new-password"
            placeholder="确认密码"
            :disabled="loading"
          />
        </div>

        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>

        <button class="login-submit" type="submit" :disabled="!canSubmit">
          <span>{{ loading ? '正在注册...' : '注册并登录' }}</span>
          <i class="fa fa-long-arrow-right" aria-hidden="true"></i>
        </button>
      </form>

      <p class="register-footer-link">
        已有账号？
        <router-link :to="loginBackRoute">返回登录</router-link>
      </p>
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

.login-heading {
  margin: 0 0 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e6e9ef;
  font-size: 16px;
  font-weight: 500;
  color: #0052d9;
  text-align: center;
}

.register-hint {
  margin: 0 0 24px;
  font-size: 12px;
  line-height: 1.6;
  color: #888;
  text-align: center;
}

.login-form {
  display: flex;
  flex-direction: column;
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
  background: #0052d9;
  color: #fff;
  font: inherit;
  font-size: 16px;
  cursor: pointer;
}

.login-submit:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.register-footer-link {
  margin: 20px 0 0;
  text-align: center;
  font-size: 13px;
  color: #888;
}

.register-footer-link a {
  color: #0052d9;
  text-decoration: none;
}

.register-footer-link a:hover {
  text-decoration: underline;
}

@media (max-width: 520px) {
  .login-panel {
    padding: 44px 22px 24px;
  }
}
</style>
