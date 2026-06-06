import { CLIENT_PRIMARY_ERP_MOD_ID } from '@/constants/genericModPack';
import type { ModInfo } from '@/stores/mods';

/** 与 mods/taiyangniao-pro/manifest.json frontend.menu 保持一致 */
export const SUNBIRD_CLIENT_MOD_FALLBACK_MENU: NonNullable<ModInfo['menu']> = [
  {
    id: 'taiyangniao-pro-home',
    label: '考勤表转换',
    icon: 'fa-file-excel-o',
    path: '/taiyangniao-pro',
  },
];

export const SUNBIRD_CLIENT_MOD_FALLBACK_OVERRIDES: NonNullable<ModInfo['menu_overrides']> = [
  { key: 'products', label: '人员管理' },
  { key: 'customers', label: '部门管理' },
];

/** API 尚未返回太阳鸟包时，侧栏/设置页仍可展示考勤转换入口 */
export function buildSunbirdClientModStub(): ModInfo {
  return {
    id: CLIENT_PRIMARY_ERP_MOD_ID,
    name: '太阳鸟pro',
    version: '1.0.0',
    author: '太阳鸟',
    description: '太阳鸟专业版',
    primary: true,
    frontend: { pro_entry_path: '/taiyangniao-pro' },
    menu: SUNBIRD_CLIENT_MOD_FALLBACK_MENU.map((row) => ({ ...row })),
    menu_overrides: SUNBIRD_CLIENT_MOD_FALLBACK_OVERRIDES.map((row) => ({ ...row })),
    industry: {
      id: '考勤',
      name: '考勤/人事行业',
    },
  };
}
