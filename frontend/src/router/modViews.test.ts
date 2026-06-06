import { describe, expect, it } from 'vitest';
import { physicalViewExists } from './modViews';

describe('modViews', () => {
  it('finds lan gate physical view in mod package', () => {
    expect(physicalViewExists('xcagi-lan-license-bridge', 'LanGateView.vue')).toBe(true);
  });

  it('finds customer service physical views', () => {
    expect(physicalViewExists('xcagi-customer-service-bridge', 'EnterpriseCustomerServiceView.vue')).toBe(
      true,
    );
  });

  it('finds approval bridge physical views', () => {
    expect(physicalViewExists('xcagi-approval-bridge', 'ApprovalHubView.vue')).toBe(true);
    expect(physicalViewExists('xcagi-approval-bridge', 'ApprovalWorkspaceView.vue')).toBe(true);
  });

  it('finds planner bridge physical views', () => {
    expect(physicalViewExists('xcagi-planner-bridge', 'ChatView.vue')).toBe(true);
    expect(physicalViewExists('xcagi-planner-bridge', 'AIEcosystemView.vue')).toBe(true);
    expect(physicalViewExists('xcagi-planner-bridge', 'BrainView.vue')).toBe(true);
  });

  it('finds erp and model-payment physical views', () => {
    expect(physicalViewExists('xcagi-erp-domain-bridge', 'ProductsView.vue')).toBe(true);
    expect(physicalViewExists('xcagi-model-payment-bridge', 'ModelPaymentView.vue')).toBe(true);
  });
});
