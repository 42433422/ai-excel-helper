// Example Mod frontend routes

const exampleModRoutes = [
  {
    path: '/example',
    name: 'example-mod',
    component: () => import('./views/ExampleView.vue'),
    meta: { title: '示例页面', mod: 'example-mod' }
  }
];

const exampleModMenu = [
  {
    id: 'example',
    label: '示例页面',
    icon: 'fa-star',
    path: '/example'
  }
];

export { exampleModRoutes, exampleModMenu };
