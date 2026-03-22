// 全局变量声明
declare global {
  interface Window {
    __VUE_APP_ACTIVE__: boolean;
    __VUE_CHAT_OWNS_INPUT__: boolean;
    __legacyToggleProMode?: () => void;
    toggleProMode?: () => void;
    setProModeEnabled: (enabled: boolean) => void;
    openImportWindow?: () => void;
  }
}

export {};
