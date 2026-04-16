<template>
  <div class="shell">
    <header class="top">
      <div class="brand">
        <span class="logo">◆</span>
        <router-link to="/" class="brand-link">XCAGI Mod 仓库</router-link>
      </div>
      <nav class="nav">
        <router-link to="/">库</router-link>
        <router-link to="/settings">路径与同步</router-link>
      </nav>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
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
  align-items: center;
  gap: 0.5rem;
  font-weight: 700;
  font-size: 1.1rem;
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
