import { GalileoReport, REPORT_CONST } from '../claw-plugin-report/index.js';

const reporter = GalileoReport.getInstance();

/** 安全上报：包裹 try-catch，不影响业务逻辑 */
export function safeReport(action: string, params: Record<string, unknown> = {}): void {
  try {
    reporter.reportFunc(REPORT_CONST.PLUGIN, {
      page_id: reporter.getPluginName() || 'lossless-claw',
      action,
      ...params,
    });
  } catch (_) {
    // 上报失败不影响业务
  }
}

export { reporter };
