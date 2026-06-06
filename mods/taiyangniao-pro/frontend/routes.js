// 太阳鸟pro — 须导出名为 modRoutes 的路由数组（供 XCAGI registerModRoutes 识别）

const modRoutes = [
  {
    path: '/taiyangniao-pro',
    name: 'taiyangniao-pro-home',
    component: () => import('./views/HomeView.vue'),
    meta: { title: '太阳鸟pro', mod: 'taiyangniao-pro' }
  },
  {
    path: '/taiyangniao-pro/settings',
    name: 'taiyangniao-pro-settings',
    component: () => import('./views/AttendanceSettingsView.vue'),
    meta: { title: '考勤设置', mod: 'taiyangniao-pro' }
  }
];

const modMenu = [
  {
    id: 'taiyangniao-pro-home',
    label: '考勤表转换',
    icon: 'fa-file-excel-o',
    path: '/taiyangniao-pro'
  }
];

export { modRoutes, modMenu };
