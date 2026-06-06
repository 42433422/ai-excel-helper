import type { RouteLocationRaw, Router } from 'vue-router'
import { ERP_DOMAIN_BRIDGE_MOD_ID, readErpDomainModFacadeEnabled } from '@/constants/erpDomainMod'

const MOD_PREFIX = `/mod/${ERP_DOMAIN_BRIDGE_MOD_ID}`

/** 宿主业务 path → Mod 子路径（K+ 扩展考勤/物料/打印等页） */
const HOST_PATH_TO_MOD: Record<string, string> = {
  '/products': '/products',
  '/customers': '/customers',
  '/orders': '/orders',
  '/orders/create': '/orders/create',
  '/shipment-records': '/shipment-records',
  '/wechat-contacts': '/data-sources',
  '/materials': '/materials',
  '/materials-list': '/materials',
  '/traditional-mode': '/traditional-mode',
  '/business-docking': '/template-preview',
  '/data-sources': '/data-sources',
  '/print': '/print',
  '/printer-list': '/printer-list',
  '/template-preview': '/template-preview',
  '/label-editor': '/label-editor',
  '/purchase': '/purchase',
  '/inventory': '/inventory',
  '/batch-analyze': '/batch-analyze',
}

const HOST_ROUTE_NAME_TO_MOD: Record<string, string> = {
  products: '/products',
  customers: '/customers',
  orders: '/orders',
  'orders-create': '/orders/create',
  'shipment-records': '/shipment-records',
  'wechat-contacts': '/data-sources',
  materials: '/materials',
  'materials-list': '/materials',
  'traditional-mode': '/traditional-mode',
  'business-docking': '/template-preview',
  'data-sources': '/data-sources',
  print: '/print',
  'printer-list': '/printer-list',
  'template-preview': '/template-preview',
  'label-editor': '/label-editor',
  purchase: '/purchase',
  inventory: '/inventory',
  'batch-analyze': '/batch-analyze',
}

export function useErpModPages(): boolean {
  return readErpDomainModFacadeEnabled()
}

export function resolveErpPagePath(hostPath: string): string {
  const raw = hostPath.startsWith('/') ? hostPath : `/${hostPath}`
  const pathOnly = raw.split('?')[0]?.split('#')[0] || raw
  if (!useErpModPages()) return raw
  if (pathOnly === '/wechat-contacts') {
    const suffix = raw.slice(pathOnly.length)
    const query = suffix || '?source=wechat_local_db'
    return `${MOD_PREFIX}/data-sources${query.startsWith('?') ? query : `?source=wechat_local_db${query}`}`
  }
  const seg = HOST_PATH_TO_MOD[pathOnly]
  if (!seg) return raw
  return `${MOD_PREFIX}${seg}${raw.slice(pathOnly.length)}`
}

/** 壳模式访问宿主业务路由名时，重定向到 Mod 页（无映射则返回 null） */
export function resolveErpPageRedirectForRouteName(routeName: string): string | null {
  if (!useErpModPages()) return null
  const seg = HOST_ROUTE_NAME_TO_MOD[routeName]
  if (!seg) return null
  const base = `${MOD_PREFIX}${seg}`
  if (routeName === 'wechat-contacts') {
    return `${base}?source=wechat_local_db`
  }
  return base
}

/** Mod 物理视图内导航：门面开启时解析为 ``/mod/...`` 路径 */
export function pushErpPage(router: Router, to: string | RouteLocationRaw): void {
  if (typeof to === 'string') {
    void router.push(resolveErpPagePath(to))
    return
  }
  if (typeof to === 'object' && to !== null && 'path' in to && typeof to.path === 'string') {
    void router.push({ path: resolveErpPagePath(to.path) })
    return
  }
  if (typeof to === 'object' && to !== null && 'name' in to && typeof to.name === 'string') {
    const modPath = resolveErpPageRedirectForRouteName(to.name)
    if (modPath) {
      const next: RouteLocationRaw = { path: modPath }
      if ('query' in to && to.query) next.query = to.query
      if ('hash' in to && to.hash) next.hash = to.hash
      void router.push(next)
      return
    }
  }
  void router.push(to)
}
