/**
 * 将 GET /api/mods/loading-status 的 data 转为简短可展示文案（启动页 / 侧栏提示）。
 */
export function summarizeModLoadingData(d: Record<string, unknown> | null | undefined): string | null {
  if (!d || typeof d !== 'object') return null;
  if (d.mods_disabled === true) {
    return 'Mod 扩展已在环境中关闭（XCAGI_DISABLE_MODS）。去掉该变量后重启后端即可加载 mods 目录。';
  }
  const parts: string[] = [];
  if (d.load_mismatch === true) {
    parts.push('磁盘上发现 manifest 但后端未载入任何 Mod。');
  }
  const loadErrs = d.load_errors as Array<{ mod_id?: string; stage?: string; message?: string }> | undefined;
  if (Array.isArray(loadErrs) && loadErrs.length > 0) {
    const e = loadErrs[0];
    parts.push(`${e.mod_id || 'mod'} [${e.stage || '?'}]: ${e.message || ''}`);
  }
  const manErrs = d.manifest_errors as Array<{ entry?: string; message?: string }> | undefined;
  if (Array.isArray(manErrs) && manErrs.length > 0) {
    const e = manErrs[0];
    parts.push(`清单 ${e.entry || '?'}: ${e.message || ''}`);
  }
  const bpErrs = d.blueprint_errors as Array<{ mod_id?: string; message?: string }> | undefined;
  if (Array.isArray(bpErrs) && bpErrs.length > 0) {
    const e = bpErrs[0];
    parts.push(`蓝图 ${e.mod_id || '?'}: ${e.message || ''}`);
  }
  if (d.partial_failure === true && parts.length === 0) {
    parts.push('部分 Mod 未成功加载，请查看后端日志。');
  }
  return parts.length ? parts.join(' ') : null;
}
