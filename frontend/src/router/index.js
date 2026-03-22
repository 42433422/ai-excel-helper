import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: { title: 'AI 助手' }
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('../views/ProductsView.vue'),
    meta: { title: '产品管理' }
  },
  {
    path: '/materials',
    name: 'materials',
    component: () => import('../views/MaterialsView.vue'),
    meta: { title: '物料管理' }
  },
  {
    path: '/orders',
    name: 'orders',
    component: () => import('../views/OrdersView.vue'),
    meta: { title: '订单管理' }
  },
  {
    path: '/orders/create',
    name: 'orders-create',
    component: () => import('../views/CreateOrderView.vue'),
    meta: { title: '新建订单' }
  },
  {
    path: '/shipment-records',
    name: 'shipment-records',
    component: () => import('../views/ShipmentRecordsView.vue'),
    meta: { title: '出货记录' }
  },
  {
    path: '/customers',
    name: 'customers',
    component: () => import('../views/CustomersView.vue'),
    meta: { title: '客户管理' }
  },
  {
    path: '/wechat-contacts',
    name: 'wechat-contacts',
    component: () => import('../views/WechatContactsView.vue'),
    meta: { title: '微信联系人' }
  },
  {
    path: '/print',
    name: 'print',
    component: () => import('../views/PrintView.vue'),
    meta: { title: '标签打印' }
  },
  {
    path: '/printer-list',
    name: 'printer-list',
    component: () => import('../views/PrinterListView.vue'),
    meta: { title: '打印机列表' }
  },
  {
    path: '/template-preview',
    name: 'template-preview',
    component: () => import('../views/TemplatePreviewView.vue'),
    meta: { title: '模板预览' }
  },
  {
    path: '/label-editor',
    name: 'label-editor',
    component: () => import('../views/LabelEditorView.vue'),
    meta: { title: '标签编辑器' }
  },
  {
    path: '/console',
    name: 'console',
    component: () => import('../views/TemplatePreviewView.vue'),
    meta: { title: '模板预览' },
    beforeEnter: (to, from, next) => {
      // 根据 view 参数重定向到不同的视图
      const view = to.query.view
      if (view === 'excel' || view === 'template-preview') {
        next()
      } else if (view) {
        // 其他 view 参数可以扩展
        next()
      } else {
        // 默认重定向到 template-preview
        next()
      }
    }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../views/SettingsView.vue'),
    meta: { title: '设置' }
  },
  {
    path: '/tools',
    name: 'tools',
    component: () => import('../views/ToolsView.vue'),
    meta: { title: '工具' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - XCAGI`
  }
  next()
})

export default router
