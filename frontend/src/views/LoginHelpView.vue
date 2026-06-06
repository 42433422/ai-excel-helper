<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  LOGIN_HELP_PAGE_TITLE,
  LOGIN_HELP_SECTIONS,
  loginHelpDocUrl,
  loginPageTitle,
  marketForgotPasswordUrl,
} from '@/constants/loginBranding';
import { fetchProductSku } from '@/utils/productSku';

const route = useRoute();
const router = useRouter();

const productSku = ref<string>('generic');
const forgotPasswordHref = computed(() => marketForgotPasswordUrl());
const externalHelpHref = computed(() => loginHelpDocUrl().trim());
const loginBackQuery = computed(() => {
  const q = { ...route.query };
  return Object.keys(q).length ? q : undefined;
});

onMounted(async () => {
  productSku.value = await fetchProductSku();
  document.title = `${LOGIN_HELP_PAGE_TITLE} · ${loginPageTitle(productSku.value).replace(' · 登录', '')}`;
});

function goBackToLogin() {
  router.push({ name: 'login', query: loginBackQuery.value });
}
</script>

<template>
  <main class="login-view" aria-label="登录帮助">
    <section class="login-panel login-help-panel" aria-labelledby="login-help-title">
      <button type="button" class="login-help-back" @click="goBackToLogin">
        <i class="fa fa-angle-left" aria-hidden="true"></i>
        返回登录
      </button>

      <h1 id="login-help-title" class="login-help-title">{{ LOGIN_HELP_PAGE_TITLE }}</h1>
      <p class="login-help-intro">常见问题如下；仍无法登录请联系管理员。</p>

      <div class="login-help-sections">
        <article v-for="section in LOGIN_HELP_SECTIONS" :key="section.title" class="login-help-section">
          <h2>{{ section.title }}</h2>
          <ul>
            <li v-for="(item, idx) in section.items" :key="idx">{{ item }}</li>
          </ul>
        </article>
      </div>

      <footer class="login-help-actions">
        <a :href="forgotPasswordHref" target="_blank" rel="noopener noreferrer">修茈市场 · 忘记密码</a>
        <a
          v-if="externalHelpHref"
          :href="externalHelpHref"
          target="_blank"
          rel="noopener noreferrer"
        >
          查看在线文档
        </a>
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
}

.login-help-panel {
  max-height: min(90vh, 720px);
  overflow-y: auto;
}

.login-help-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin: 0 0 20px;
  padding: 0;
  border: 0;
  background: transparent;
  color: #0052d9;
  font: inherit;
  font-size: 14px;
  cursor: pointer;
}

.login-help-back:hover {
  color: #003cab;
  text-decoration: underline;
}

.login-help-title {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 600;
  color: #000;
}

.login-help-intro {
  margin: 0 0 24px;
  font-size: 13px;
  line-height: 1.6;
  color: #888;
}

.login-help-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.login-help-section h2 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.login-help-section ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.65;
  color: #666;
}

.login-help-section li + li {
  margin-top: 4px;
}

.login-help-actions {
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1px solid #e6e9ef;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 16px;
  font-size: 13px;
}

.login-help-actions a {
  color: #0052d9;
  text-decoration: none;
}

.login-help-actions a:hover {
  text-decoration: underline;
}

@media (max-width: 520px) {
  .login-panel {
    padding: 36px 22px 24px;
  }
}
</style>
