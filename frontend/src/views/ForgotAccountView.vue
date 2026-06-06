<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { ApiError } from '@/api';
import { authApi } from '@/api/auth';

const route = useRoute();
const email = ref('');
const loading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const usernames = ref<string[]>([]);

const loginBackRoute = computed(() => ({
  name: 'login' as const,
  query: route.query,
}));

async function submitLookup() {
  const em = email.value.trim().toLowerCase();
  if (!em || !em.includes('@')) {
    errorMessage.value = '请填写有效邮箱';
    return;
  }
  loading.value = true;
  errorMessage.value = '';
  successMessage.value = '';
  usernames.value = [];
  try {
    const res = await authApi.forgotAccount(em);
    const raw = res as unknown as Record<string, unknown>;
    const data = (raw.data as Record<string, unknown> | undefined) || {};
    const list = Array.isArray(data.usernames) ? (data.usernames as string[]) : [];
    usernames.value = list;
    successMessage.value =
      (typeof raw.message === 'string' && raw.message) ||
      (list.length ? `找到账号：${list.join('、')}` : '未找到关联账号');
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      const d = error.data as Record<string, unknown> | undefined;
      const errObj = d?.error as Record<string, unknown> | undefined;
      errorMessage.value =
        (typeof d?.message === 'string' && d.message) ||
        (typeof errObj?.message === 'string' && (errObj.message as string)) ||
        error.message;
    } else {
      errorMessage.value = '查询失败，请确认后端已连接数据库';
    }
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <main class="login-view" aria-label="忘记账号">
    <section class="login-panel" aria-labelledby="forgot-account-title">
      <router-link class="login-register-corner" :to="loginBackRoute"> 登录 </router-link>

      <h1 id="forgot-account-title" class="login-heading">忘记账号</h1>
      <p class="page-hint">根据邮箱在本机服务器数据库（PostgreSQL）中查询已注册的用户名。</p>

      <form class="login-form" @submit.prevent="submitLookup">
        <div class="login-field-line">
          <input
            v-model="email"
            type="email"
            name="email"
            autocomplete="email"
            placeholder="注册时填写的邮箱"
            :disabled="loading"
            autofocus
          />
        </div>

        <p v-if="errorMessage" class="login-error" role="alert">{{ errorMessage }}</p>
        <p v-if="successMessage" class="login-success" role="status">{{ successMessage }}</p>
        <ul v-if="usernames.length" class="username-list">
          <li v-for="name in usernames" :key="name">{{ name }}</li>
        </ul>

        <button class="login-submit" type="submit" :disabled="loading || !email.trim()">
          <span>{{ loading ? '查询中...' : '查询账号' }}</span>
          <i class="fa fa-long-arrow-right" aria-hidden="true"></i>
        </button>
      </form>

      <p class="page-footer-link">
        <router-link :to="{ name: 'login-forgot-password', query: route.query }">忘记密码</router-link>
        ·
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
}

.login-panel {
  position: relative;
  width: min(460px, 100%);
  padding: 48px 40px 32px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
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
  color: #0052d9;
  text-decoration: none;
  background: linear-gradient(225deg, #e8f3ff 0%, #e8f3ff 48%, transparent 48%);
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

.page-hint {
  margin: 0 0 24px;
  font-size: 12px;
  line-height: 1.6;
  color: #888;
  text-align: center;
}

.login-field-line {
  border-bottom: 1px solid #dcdfe6;
}

.login-field-line input {
  width: 100%;
  height: 48px;
  border: 0;
  outline: none;
  font-size: 14px;
}

.login-error {
  margin: 12px 0 0;
  padding: 8px 10px;
  font-size: 13px;
  color: #e34d59;
  background: #fff1f0;
  border: 1px solid #ffd4d1;
}

.login-success {
  margin: 12px 0 0;
  padding: 8px 10px;
  font-size: 13px;
  color: #067945;
  background: #f0fff4;
  border: 1px solid #b7ebc6;
}

.username-list {
  margin: 12px 0 0;
  padding: 12px 16px;
  list-style: none;
  background: #f5f8ff;
  border: 1px solid #d4e3fc;
  font-size: 15px;
  font-weight: 600;
  color: #0052d9;
  text-align: center;
}

.username-list li + li {
  margin-top: 6px;
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
  font-size: 16px;
  cursor: pointer;
}

.login-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.page-footer-link {
  margin-top: 20px;
  text-align: center;
  font-size: 13px;
}

.page-footer-link a {
  color: #0052d9;
  text-decoration: none;
}
</style>
