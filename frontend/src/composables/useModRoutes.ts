import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useModsStore } from '@/stores/mods';

export function useModRoutes() {
  const modsStore = useModsStore();
  const { modsForUi } = storeToRefs(modsStore);

  const modMenuItems = computed(() => {
    return modsStore.getModMenu().map((item) => ({
      key: `mod-${item.id}`,
      name: item.label,
      iconClass: item.icon || 'fa-plug',
      modId: item.modId,
      path: item.path,
    }));
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
