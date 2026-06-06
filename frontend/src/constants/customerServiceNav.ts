/** 外部（企业）/ 内部（管理员）客服侧栏与路由 */

export const ENTERPRISE_CUSTOMER_SERVICE_KEY = 'enterprise-customer-service'
export const INTERNAL_CUSTOMER_SERVICE_KEY = 'internal-customer-service'

export type CustomerServiceSide = 'enterprise' | 'admin'

export function customerServiceSideForNavKey(key: string): CustomerServiceSide | null {
  if (key === ENTERPRISE_CUSTOMER_SERVICE_KEY) return 'enterprise'
  if (key === INTERNAL_CUSTOMER_SERVICE_KEY) return 'admin'
  return null
}

export function isCustomerServiceNavVisible(
  key: string,
  isAdminAccount: boolean,
): boolean {
  const side = customerServiceSideForNavKey(key)
  if (!side) return true
  return side === 'admin' ? isAdminAccount : !isAdminAccount
}
