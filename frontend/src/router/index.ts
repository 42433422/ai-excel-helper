import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized, type RouteRecordRaw } from 'vue-router';
import { useModsStore } from '@/stores/mods';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'chat',
    component: () => import('../views/ChatView.vue'),
    meta: { title: 'AI 助手' }
  },
  {
    path: '/ai-ecosystem',
    name: 'ai-ecosystem',
    component: () => import('../views/AIEcosystemView.vue'),
    meta: { title: 'AI生态' }
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
    meta: { title: '原材料仓库' }
  },
  {
    path: '/materials-list',
    name: 'materials-list',
    component: () => import('../views/MaterialsView.vue'),
    meta: { title: '原材料列表' }
  },
  {
    path: '/orders',
    name: 'orders',
    component: () => import('../views/OrdersView.vue'),
    meta: { title: '订单管理' }
  },
  {
    path: '/business-docking',
    name: 'business-docking',
    component: () => import('../views/BusinessDockingView.vue'),
    meta: { title: '业务对接' }
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
    beforeEnter: (to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
      const view = to.query.view;
      if (view === 'excel' || view === 'template-preview') {
        next();
      } else if (view) {
        next();
      } else {
        next();
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
    path: '/purchase',
    name: 'purchase',
    component: () => import('../views/PurchaseView.vue'),
    meta: { title: '采购管理' }
  },
  {
    path: '/chat-debug',
    name: 'chat-debug',
    component: () => import('../views/ChatDebugView.vue'),
    meta: { title: '聊天调试' }
  },
  {
    path: '/tools',
    name: 'tools',
    component: () => import('../views/ToolsView.vue'),
    meta: { title: '工具' }
  },
  {
    path: '/other-tools',
    name: 'other-tools',
    component: () => import('../views/OtherToolsView.vue'),
    meta: { title: '员工工作流管理' }
  },
  {
    path: '/workflow-visualization',
    name: 'workflow-visualization',
    component: () => import('../views/WorkflowVisualizationView.vue'),
    meta: { title: '工作流可视化' }
  },
  {
    path: '/batch-analyze',
    name: 'batch-analyze',
    component: () => import('../views/BatchAnalyzeView.vue'),
    meta: { title: '批量分析' }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - XCAGI`;
  }
  try {
    const modsStore = useModsStore();
    if (modsStore.clientModsUiOff && to.matched.some((r) => Boolean(r.meta?.mod))) {
      next({ name: 'chat' });
      return;
    }
  } catch {
    /* Pinia 未就绪时忽略 */
  }
  next();
});

export default router;
