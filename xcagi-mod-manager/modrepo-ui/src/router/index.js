import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import ModDetailView from '../views/ModDetailView.vue'
import SettingsView from '../views/SettingsView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    {
      path: '/mod/:id',
      name: 'mod',
      component: ModDetailView,
      props: (route) => ({ id: route.params.id }),
    },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})
