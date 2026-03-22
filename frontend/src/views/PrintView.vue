<template>
  <div class="page-view" id="view-print">
    <div class="page-content">
      <div class="page-header">
        <h2>标签打印</h2>
      </div>
      <div class="card">
        <div class="card-header">生成标签</div>
        <div class="form-group">
          <label>选择产品型号</label>
          <select v-model="selectedModel">
            <option value="">请选择产品</option>
            <option
              v-for="product in products"
              :key="product.id || product.model_number || product.name"
              :value="product.model_number || product.name || String(product.id || '')"
            >
              {{ product.model_number || '-' }} - {{ product.name || '-' }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>打印数量</label>
          <input type="number" v-model.number="quantity" min="1">
        </div>
        <button class="btn btn-primary" @click="printLabel" :disabled="loading">打印标签</button>
        <p class="muted" style="margin-top:10px;font-size:13px;">{{ printerHint }}</p>
        <p v-if="printStatus" class="muted" style="margin-top:6px;font-size:13px;">{{ printStatus }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import productsApi from '../api/products';
import printApi from '../api/print';

const loading = ref(false);
const products = ref([]);
const selectedModel = ref('');
const quantity = ref(1);
const printerHint = ref('正在检测打印机...');
const printStatus = ref('');

async function loadProducts() {
  try {
    const data = await productsApi.getProducts();
    if (data?.success === false) throw new Error(data?.message || '加载产品失败');
    products.value = Array.isArray(data?.data) ? data.data : [];
  } catch (e) {
    console.error('加载产品失败:', e);
    products.value = [];
  }
}

async function loadPrinterStatus() {
  try {
    const data = await printApi.getPrinters();
    if (!data?.success) {
      printerHint.value = '未检测到打印机，请检查连接。';
      return;
    }
    const label = data?.classified?.label_printer;
    if (label?.is_connected && label?.name) {
      printerHint.value = `标签打印机已连接：${label.name}`;
    } else {
      printerHint.value = '未检测到标签打印机，可先生成标签再到专业面板打印。';
    }
  } catch (e) {
    printerHint.value = '打印机状态检查失败，请稍后重试。';
  }
}

async function printLabel() {
  if (!selectedModel.value) {
    printStatus.value = '请选择产品后再打印。';
    return;
  }
  if (!quantity.value || quantity.value < 1) {
    printStatus.value = '请输入正确的打印数量。';
    return;
  }
  loading.value = true;
  printStatus.value = '正在提交打印任务...';
  try {
    const data = await printApi.printSingleLabel({
      model_number: selectedModel.value,
      quantity: quantity.value
    });
    if (!data?.success) {
      throw new Error(data?.message || '打印失败');
    }
    printStatus.value = data?.message || '已提交打印任务。';
  } catch (e) {
    console.error('打印失败:', e);
    printStatus.value = `打印失败: ${e?.message || '未知错误'}`;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadProducts();
  loadPrinterStatus();
});
</script>
