import { GalileoReport, REPORT_CONST } from '../claw-plugin-report/index.js';
import { getExternalGuid, getExternalUid, getExternalAppVersion } from './state.js';

const reporter = GalileoReport.getInstance();

/** 安全上报：包裹 try-catch，不影响业务逻辑 */
export function safeReport(action: string, params: Record<string, unknown> = {}): void {
  try {
    reporter.reportFunc(REPORT_CONST.PLUGIN, {
      page_id: reporter.getPluginName() || 'content-plugin',
      action,
      // 补充公共字段：GUID、user_id、tdbank_imp_date、app_name、app_version
      guid: getExternalGuid() ?? '',
      user_id: getExternalUid() ?? '',
      tdbank_imp_date: Date.now(),
      app_name: 'PC_Qclaw',
      app_version: getExternalAppVersion() ?? '',
      ...params,
    });
  } catch (_) {
    // 上报失败不影响业务
  }
}

export { reporter };
