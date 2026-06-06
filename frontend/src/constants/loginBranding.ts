import packageJson from '../../package.json';

/** 主版本号展示，如 8.0.0 → V8 */
export const XCAGI_VERSION_LABEL = `V${String(packageJson.version || '8.0.0').split('.')[0]}`;

export type LoginSku = 'enterprise' | 'personal' | 'generic' | string;

export function normalizeLoginSku(raw: string | null | undefined): LoginSku {
  const s = String(raw || 'generic').trim().toLowerCase();
  if (s === 'enterprise' || s === 'personal') return s;
  return 'generic';
}

export function loginEyebrow(sku: LoginSku): string {
  switch (normalizeLoginSku(sku)) {
    case 'enterprise':
      return `XCAGI 企业版 · ${XCAGI_VERSION_LABEL}`;
    case 'personal':
      return `XCAGI 个人版 · ${XCAGI_VERSION_LABEL}`;
    default:
      return `XCAGI · ${XCAGI_VERSION_LABEL}`;
  }
}

export function loginSubtitle(sku: LoginSku): string {
  switch (normalizeLoginSku(sku)) {
    case 'enterprise':
      return '使用修茈市场账号登录';
    case 'personal':
      return '本地账号登录';
    default:
      return '登录进入工作台';
  }
}

export function loginUsernamePlaceholder(sku: LoginSku): string {
  return normalizeLoginSku(sku) === 'enterprise' ? '市场账号' : '账号';
}

export function loginAccountInputPlaceholder(sku: LoginSku): string {
  switch (normalizeLoginSku(sku)) {
    case 'enterprise':
      return '市场账号或邮箱';
    case 'personal':
      return '本地账号';
    default:
      return '账号';
  }
}

export function loginPasswordInputPlaceholder(): string {
  return '密码';
}

export function marketBaseUrl(): string {
  return String(import.meta.env.VITE_MARKET_BASE || 'https://xiu-ci.com/market').replace(/\/$/, '');
}

export function marketRegisterUrl(): string {
  return `${marketBaseUrl()}/register`;
}

export function marketForgotPasswordUrl(): string {
  return `${marketBaseUrl()}/forgot-password`;
}

export function loginHelpDocUrl(): string {
  return String(import.meta.env.VITE_LOGIN_HELP_URL || '');
}

export type LoginHelpSection = {
  title: string;
  items: string[];
};

export const LOGIN_HELP_PAGE_TITLE = '登录帮助';

export function loginPageTitle(sku: LoginSku): string {
  return `${loginEyebrow(sku)} · 登录`;
}

export const LOGIN_HELP_SECTIONS: LoginHelpSection[] = [
  {
    title: '账号或密码错误',
    items: ['核对账号密码', '记下错误编号联系管理员'],
  },
  {
    title: '无法连接后端',
    items: ['确认本机后端已启动（默认 5000 端口）', '检查数据库是否运行'],
  },
  {
    title: '市场同步',
    items: ['登录后可在设置同步市场 Token', '502 多为市场服务不可达'],
  },
  {
    title: '注册',
    items: ['使用登录页注册入口', '企业版需市场服务可达'],
  },
];
