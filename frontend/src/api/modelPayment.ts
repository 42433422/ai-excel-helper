import { api } from './core';
import { resolveModelPaymentApiPath } from '@/utils/modelPaymentPaths';

const mp = (path: string) => resolveModelPaymentApiPath(path);

export type ModelPaymentPlan = {
  id: string;
  title: string;
  description: string;
  amount_cents: number;
  currency: string;
  badge: string | null;
};

export type ModelPaymentIntegration = {
  alipay_configured: boolean;
};

export type ModelPaymentEntitlement = {
  plan_id: string;
  purchase_count: number;
  first_paid_at?: string | null;
  last_paid_at?: string | null;
  last_out_trade_no?: string | null;
  last_trade_no?: string | null;
};

export const modelPaymentApi = {
  getPlans: () =>
    api.get<{
      success: boolean;
      data?: { plans: ModelPaymentPlan[]; integration: ModelPaymentIntegration };
      message?: string;
    }>(mp('/api/model-payment/plans')),

  checkout: (plan_id: string) =>
    api.post<{
      success: boolean;
      data?: {
        order_id: string;
        channel: 'alipay';
        status: string;
        amount_cents: number;
        plan_id: string;
        client_payload: unknown;
        /** 网站支付（page.pay / wap.pay）返回的跳转 URL */
        redirect_url?: string | null;
        /** 订单码支付（precreate）返回的二维码内容 */
        qr_code?: string | null;
        setup_hint?: string;
      };
      message?: string;
    }>(mp('/api/model-payment/checkout'), { plan_id }),

  getEntitlements: () =>
    api.get<{
      success: boolean;
      data?: { entitlements: ModelPaymentEntitlement[] };
      message?: string;
    }>(mp('/api/model-payment/entitlements')),
};

export default modelPaymentApi;
