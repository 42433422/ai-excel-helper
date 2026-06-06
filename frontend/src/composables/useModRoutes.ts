import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useModsStore } from '@/stores/mods';

export function useModRoutes() {
  const modsStore = useModsStore();
  const { modsForUi } = storeToRefs(modsStore);

  const modMenuItems = computed(() => {
    return modsStore.getModMenu().map((item) => {
      const menuId = String(item.id || '').trim();
      // manifest.menu.id 已是 mod-xxx，勿再拼前缀（否则 mod-mod-xxx 导致去重失效）
      const key = menuId.startsWith('mod-') ? menuId : `mod-${menuId}`;
      return {
        key,
        name: item.label,
        iconClass: item.icon || 'fa-plug',
        modId: item.modId,
        path: item.path,
      };
    });
  });

  async function initializeMods() {
    await modsStore.initialize();
  }

  return {
    modMenuItems,
    initializeMods,
    /** 与侧栏一致：前端关闭 Mod 界面时为 [] */
    mods: modsForUi,
    modRoutes: modsStore.modRoutes,
  };
}
