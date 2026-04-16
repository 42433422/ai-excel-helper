<template>
  <div class="shell">
    <div v-if="apiBanner" class="api-banner api-banner-err">
      <span>{{ apiBanner }}</span>
      <button type="button" class="banner-dismiss" @click="apiBanner = ''">{{ t('intro.common.close') }}</button>
    </div>
    <header class="top">
      <div class="brand">
        <span class="logo">◆</span>
        <div class="brand-text">
          <router-link to="/" class="brand-link">MODstore</router-link>
          <p class="tagline">{{ t('intro.appTagline') }}</p>
        </div>
      </div>
      <div class="top-right">
        <div class="lang" role="group" aria-label="Language">
          <button type="button" class="lang-btn" :class="{ active: locale === 'zh-CN' }" @click="setLocale('zh-CN')">
            {{ t('intro.common.langZh') }}
          </button>
          <button type="button" class="lang-btn" :class="{ active: locale === 'en-US' }" @click="setLocale('en-US')">
            {{ t('intro.common.langEn') }}
          </button>
        </div>
        <nav class="nav">
          <router-link to="/" :title="t('intro.navTitle.library')">{{ t('intro.navShort.library') }}</router-link>
          <router-link to="/author" :title="t('intro.navTitle.author')">{{ t('intro.navShort.author') }}</router-link>
          <router-link to="/debug" :title="t('intro.navTitle.debug')">{{ t('intro.navShort.debug') }}</router-link>
          <router-link to="/settings" :title="t('intro.navTitle.settings')">{{ t('intro.navShort.settings') }}</router-link>
        </nav>
      </div>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from './api'
import { persistLocale } from './i18n'

const { t, locale } = useI18n()

const apiOk = ref(true)
const apiBanner = ref('')

function setLocale(code) {
  locale.value = code
  persistLocale(code)
}

onMounted(async () => {
  try {
    const h = await api.health()
    apiOk.value = !!(h && (h.ok === true || h.success === true))
    if (apiOk.value) {
      apiBanner.value = ''
    } else {
      apiBanner.value = t('intro.app.apiHealthWarn')
    }
  } catch {
    apiOk.value = false
    apiBanner.value = t('intro.app.apiConnFail')
  }
})
</script>

<style scoped>
.api-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.5rem 1rem;
  font-size: 0.88rem;
  border-bottom: 1px solid var(--border);
}
.api-banner-err {
  background: #450a0a;
  color: #fecaca;
}
.banner-dismiss {
  flex-shrink: 0;
  padding: 0.2rem 0.55rem;
  font-size: 0.78rem;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  background: transparent;
  color: inherit;
  cursor: pointer;
}
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.5rem;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, var(--bg-card) 0%, var(--bg) 100%);
}
.brand {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
}
.brand-text {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.tagline {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 400;
  color: var(--muted);
  max-width: 28rem;
  line-height: 1.35;
}
.logo {
  color: var(--accent);
  font-size: 1rem;
}
.brand-link {
  color: var(--text);
  text-decoration: none;
}
.brand-link:hover {
  color: var(--accent);
  text-decoration: none;
}
.top-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem 1.25rem;
}
.lang {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}
.lang-btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.72rem;
  border: none;
  background: var(--bg-elevated);
  color: var(--muted);
  cursor: pointer;
  font-family: var(--font-sans, inherit);
}
.lang-btn + .lang-btn {
  border-left: 1px solid var(--border);
}
.lang-btn.active {
  background: var(--bg-card);
  color: var(--accent);
  font-weight: 600;
}
.lang-btn:hover:not(.active) {
  color: var(--text);
}
.nav {
  display: flex;
  gap: 1.25rem;
}
.nav a {
  color: var(--muted);
  font-size: 0.9rem;
}
.nav a.router-link-active {
  color: var(--accent);
}
.main {
  flex: 1;
  padding: 1.5rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
