import { ref, computed, onUnmounted } from 'vue';
import { useProModeStore } from '@/stores/proMode';

export function useProMode() {
  const store = useProModeStore();
  const animationId = ref<number | null>(null);

  const toggleProMode = () => {
    store.toggleProMode();
  };

  const enterProMode = () => {
    store.enterProMode();
  };

  const exitProMode = () => {
    store.exitProMode();
  };

  const enterWorkMode = () => {
    store.enterWorkMode();
  };

  const exitWorkMode = () => {
    store.exitWorkMode();
  };

  const enterMonitorMode = () => {
    store.enterMonitorMode();
  };

  const exitMonitorMode = () => {
    store.exitMonitorMode();
  };

  const setStage = (stage: string, payload: Record<string, unknown> = {}) => {
    store.setStage(stage, payload);
  };

  const resetTransientState = () => {
    store.resetTransientState();
  };

  const stepBack = () => {
    store.stepBack();
  };

  const isActive = computed(() => store.isActive);
  const isTransitioning = computed(() => store.isTransitioning);
  const isWorkMode = computed(() => store.isWorkMode);
  const isMonitorMode = computed(() => store.isMonitorMode);
  const currentStage = computed(() => store.currentStage);
  const selectedCompany = computed(() => store.selectedCompany);
  const selectedProduct = computed(() => store.selectedProduct);
  const coreScale = computed(() => store.coreScale);
  const orbitLayerScale = computed(() => store.orbitLayerScale);

  onUnmounted(() => {
    if (animationId.value) {
      cancelAnimationFrame(animationId.value);
    }
  });

  return {
    isActive,
    isTransitioning,
    isWorkMode,
    isMonitorMode,
    currentStage,
    selectedCompany,
    selectedProduct,
    coreScale,
    orbitLayerScale,
    toggleProMode,
    enterProMode,
    exitProMode,
    enterWorkMode,
    exitWorkMode,
    enterMonitorMode,
    exitMonitorMode,
    setStage,
    resetTransientState,
    stepBack
  };
}
