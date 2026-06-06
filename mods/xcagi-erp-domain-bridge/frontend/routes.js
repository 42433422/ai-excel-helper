/**
 * 里程碑 K+ / O+：ERP 业务页 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-erp-domain-bridge'
const PREFIX = `/mod/${MOD_ID}`

function route(pathSuffix, name, viewFile, title) {
  return {
    path: `${PREFIX}${pathSuffix}`,
    name,
    component: modView(MOD_ID, viewFile),
    meta: { title, mod: MOD_ID },
  }
}

const modRoutes = [
  route('/products', 'mod-erp-products', 'ProductsView.vue', '人员管理'),
  route('/customers', 'mod-erp-customers', 'CustomersView.vue', '部门管理'),
  route('/orders', 'mod-erp-orders', 'OrdersView.vue', '考勤单管理'),
  route('/orders/create', 'mod-erp-orders-create', 'CreateOrderView.vue', '新建考勤单'),
  route('/shipment-records', 'mod-erp-shipment-records', 'ShipmentRecordsView.vue', '考勤记录'),
  route('/wechat-contacts', 'mod-erp-wechat-contacts', 'WechatContactsView.vue', '企业微信联系人'),
  route('/materials', 'mod-erp-materials', 'MaterialsView.vue', '排班资源'),
  { path: `${PREFIX}/materials-list`, redirect: `${PREFIX}/materials` },
  route('/traditional-mode', 'mod-erp-traditional-mode', 'TraditionalModeView.vue', '表格模式'),
  { path: `${PREFIX}/business-docking`, redirect: `${PREFIX}/template-preview` },
  route('/data-sources', 'mod-erp-data-sources', 'DataSourcesView.vue', '数据来源'),
  route('/print', 'mod-erp-print', 'PrintView.vue', '考勤表打印'),
  route('/printer-list', 'mod-erp-printer-list', 'PrinterListView.vue', '打印机列表'),
  route('/template-preview', 'mod-erp-template-preview', 'TemplatePreviewView.vue', '模板库'),
  route('/label-editor', 'mod-erp-label-editor', 'LabelEditorView.vue', '标签编辑器'),
  route('/purchase', 'mod-erp-purchase', 'PurchaseView.vue', '耗材申领'),
  route('/inventory', 'mod-erp-inventory', 'InventoryView.vue', '库存管理'),
  route('/batch-analyze', 'mod-erp-batch-analyze', 'BatchAnalyzeView.vue', '批量分析'),
]

const modMenu = [
  { id: 'mod-erp-products', label: '人员管理', icon: 'fa-cubes', path: `${PREFIX}/products` },
  { id: 'mod-erp-customers', label: '部门管理', icon: 'fa-users', path: `${PREFIX}/customers` },
  { id: 'mod-erp-orders', label: '考勤单管理', icon: 'fa-file-text-o', path: `${PREFIX}/orders` },
  { id: 'mod-erp-shipment-records', label: '考勤记录', icon: 'fa-industry', path: `${PREFIX}/shipment-records` },
  { id: 'mod-erp-materials', label: '排班资源', icon: 'fa-archive', path: `${PREFIX}/materials` },
  { id: 'mod-erp-traditional-mode', label: '表格模式', icon: 'fa-table', path: `${PREFIX}/traditional-mode` },
  { id: 'mod-erp-data-sources', label: '数据来源', icon: 'fa-database', path: `${PREFIX}/data-sources` },
  { id: 'mod-erp-printer-list', label: '打印机列表', icon: 'fa-print', path: `${PREFIX}/printer-list` },
  { id: 'mod-erp-template-preview', label: '模板库', icon: 'fa-file-o', path: `${PREFIX}/template-preview` },
]

export { modRoutes, modMenu }
