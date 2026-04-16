import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ModDetailView from '../views/ModDetailView.vue'
import SettingsView from '../views/SettingsView.vue'
import DebugView from '../views/DebugView.vue'
import AuthorView from '../views/AuthorView.vue'
import NotFoundView from '../views/NotFoundView.vue'

export default createRouter({
  history: createWebHistory(),
  scrollBehavior() {
    return { top: 0 }
  },
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/mod/:id',
      name: 'mod',
      component: ModDetailView,
      props: (route) => ({ id: route.params.id }),
    },
    { path: '/settings', name: 'settings', component: SettingsView },
    { path: '/author', name: 'author', component: AuthorView },
    { path: '/debug', name: 'debug', component: DebugView },
    { path: '/:pathMatch(.*)*', name: 'notfound', component: NotFoundView },
  ],
})
