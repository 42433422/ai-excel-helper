<template>
  <teleport to="body">
    <div v-if="showOverlay" class="fhd-read-gate-root" role="dialog" aria-modal="true" aria-labelledby="fhd-read-gate-title">
      <div class="fhd-read-gate-backdrop" />
      <div class="fhd-read-gate-panel">
        <h2 id="fhd-read-gate-title" class="fhd-read-gate-title">一级访问验证</h2>
        <p class="fhd-read-gate-desc">
          访问产品列表需要一级口令（与服务器环境变量 <code>FHD_DB_READ_TOKEN</code> 一致）。验证通过前无法加载表格数据。
        </p>
        <label class="fhd-read-gate-label" for="fhd-read-gate-input">一级密码（只读）</label>
        <input
          id="fhd-read-gate-input"
          v-model="password"
          type="password"
          class="fhd-read-gate-input"
          autocomplete="off"
          @keydown.enter.prevent="onUnlock"
        />
        <p v-if="errorText" class="fhd-read-gate-error">{{ errorText }}</p>
        <div class="fhd-read-gate-actions">
          <button type="button" class="fhd-read-gate-btn" :disabled="busy" @click="onUnlock">
            {{ busy ? "验证中…" : "解锁" }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import {
  getProductsReadLockState,
  probeProductsReadAccess,
  saveStoredReadToken,
} from "./dbTokenHeaders";

const props = defineProps<{ apiBase?: string }>();

const emit = defineEmits<{
  unlocked: [];
}>();

const booting = ref(true);
const blocked = ref(false);
const password = ref("");
const errorText = ref("");
const busy = ref(false);

const showOverlay = computed(() => !booting.value && blocked.value);

async function evaluate() {
  errorText.value = "";
  const state = await getProductsReadLockState(props.apiBase || "");
  booting.value = false;
  if (state === "open") {
    blocked.value = false;
    emit("unlocked");
    return;
  }
  blocked.value = true;
  if (state === "locked_bad_token") {
    errorText.value = "本地保存的一级口令无效，请重新输入。";
  }
}

async function onUnlock() {
  errorText.value = "";
  const p = password.value.trim();
  if (!p) {
    errorText.value = "请输入一级密码。";
    return;
  }
  busy.value = true;
  try {
    saveStoredReadToken(p);
    const ok = await probeProductsReadAccess(props.apiBase || "");
    if (!ok) {
      errorText.value = "口令错误或无法访问产品接口，请重试。";
      return;
    }
    blocked.value = false;
    password.value = "";
    emit("unlocked");
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  void evaluate();
});

watch(
  () => props.apiBase,
  () => {
    booting.value = true;
    void evaluate();
  },
);
</script>

<style scoped>
.fhd-read-gate-root {
  position: fixed;
  inset: 0;
  z-index: 2147483645;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  box-sizing: border-box;
}
.fhd-read-gate-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
}
.fhd-read-gate-panel {
  position: relative;
  max-width: 420px;
  width: 100%;
  padding: 24px;
  border-radius: 12px;
  background: #fff;
  color: #0f172a;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
}
.fhd-read-gate-title {
  margin: 0 0 12px;
  font-size: 1.25rem;
}
.fhd-read-gate-desc {
  margin: 0 0 16px;
  font-size: 0.9rem;
  line-height: 1.5;
  color: #475569;
}
.fhd-read-gate-label {
  display: block;
  font-size: 0.85rem;
  margin-bottom: 6px;
  font-weight: 600;
}
.fhd-read-gate-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 1rem;
}
.fhd-read-gate-error {
  margin: 10px 0 0;
  font-size: 0.85rem;
  color: #b91c1c;
}
.fhd-read-gate-actions {
  margin-top: 18px;
}
.fhd-read-gate-btn {
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
}
.fhd-read-gate-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}
</style>
