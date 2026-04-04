export const SIDEBAR_THEME_STORAGE_KEY = 'sidebarThemePreset';

/** 与系统设置「样式选择」一致；写入 body[data-sidebar-theme]，由 office-theme.css 覆盖侧栏 */
export const SIDEBAR_THEME_OPTIONS = [
  { value: 'office-default', label: 'Office（浅色顶栏与底栏）', accent: '#0f6cbd' },
  { value: 'dark-navy', label: '深海军蓝', accent: '#5b8ff9' },
  { value: 'dark-slate', label: '深岩灰', accent: '#38bdf8' },
  { value: 'dark-indigo', label: '深靛紫', accent: '#a78bfa' },
  { value: 'dark-steel', label: '深冷灰', accent: '#0a84ff' },
] as const;

const VALID = new Set<string>(SIDEBAR_THEME_OPTIONS.map((o) => o.value));

export function applySidebarTheme(preset: string | null | undefined) {
  if (typeof document === 'undefined') return;
  const body = document.body;
  if (!preset || preset === 'office-default' || !VALID.has(preset)) {
    body.removeAttribute('data-sidebar-theme');
    return;
  }
  body.setAttribute('data-sidebar-theme', preset);
}

const LEGACY_PAGE_THEME_KEY = 'settingsPageTheme';

export function readStoredSidebarTheme(): string {
  try {
    const v = localStorage.getItem(SIDEBAR_THEME_STORAGE_KEY);
    if (v && VALID.has(v)) return v;
    const legacy = localStorage.getItem(LEGACY_PAGE_THEME_KEY);
    if (legacy && legacy.startsWith('light-')) return 'office-default';
  } catch (_) {
    /* ignore */
  }
  return 'office-default';
}

export function applySidebarThemeFromStorage() {
  applySidebarTheme(readStoredSidebarTheme());
}

export function persistSidebarTheme(preset: string) {
  try {
    localStorage.setItem(SIDEBAR_THEME_STORAGE_KEY, preset);
  } catch (_) {
    /* ignore */
  }
  applySidebarTheme(preset);
}
