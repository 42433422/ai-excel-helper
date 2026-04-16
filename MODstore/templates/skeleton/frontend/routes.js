// __MOD_NAME__ — 须导出名为 modRoutes 的路由数组（供 XCAGI registerModRoutes 识别）

const modRoutes = [
  {
    path: '/__MOD_ID__',
    name: '__MOD_ID__-home',
    component: () => import('./views/HomeView.vue'),
    meta: { title: '__MOD_NAME__', mod: '__MOD_ID__' }
  }
];

const modMenu = [
  {
    id: '__MOD_ID__-home',
    label: '__MOD_NAME__',
    icon: 'fa-cube',
    path: '/__MOD_ID__'
  }
];

export { modRoutes, modMenu };
