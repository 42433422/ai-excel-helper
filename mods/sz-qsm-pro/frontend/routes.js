const qsmProModRoutes = [
  {
    path: '/qsm-pro',
    name: 'qsm-pro-dashboard',
    component: () => import('./views/QSMProDashboard.vue'),
    meta: { 
      title: '奇士美 PRO 仪表盘',
      mod: 'sz-qsm-pro',
      proFeature: true
    }
  },
  {
    path: '/qsm-pro/advanced',
    name: 'qsm-pro-advanced',
    component: () => import('./views/QSMProAdvanced.vue'),
    meta: { 
      title: '高级功能',
      mod: 'sz-qsm-pro',
      proFeature: true
    }
  }
];

const qsmProModMenu = [
  {
    id: 'qsm-pro-dashboard',
    label: '奇士美 PRO 仪表盘',
    icon: 'fa-dashboard',
    path: '/qsm-pro'
  },
  {
    id: 'qsm-pro-advanced',
    label: '高级功能',
    icon: 'fa-cogs',
    path: '/qsm-pro/advanced'
  }
];

export { qsmProModRoutes, qsmProModMenu };
// 4243342
