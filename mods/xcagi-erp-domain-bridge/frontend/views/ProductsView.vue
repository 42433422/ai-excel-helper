<template>
  <div class="page-view" id="view-products">
    <div class="page-content">
      <div class="page-header">
        <h2>{{ pageNavTitle }}</h2>
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <button class="btn btn-secondary" @click="triggerImportExcel" title="上传 Excel 批量导入产品">
            <i class="fa fa-upload" aria-hidden="true"></i> 导入Excel
          </button>
          <input
            ref="importExcelInput"
            type="file"
            accept=".xlsx,.xls"
            style="display:none"
            @change="handleImport"
          >
          <button class="btn btn-primary" @click="exportPriceList" style="margin-right:6px;" title="导出当前单位价目表（Word .docx，使用下方所选 Word 模板）">
            <i class="fa fa-file-text-o" aria-hidden="true"></i> 导出价格表
          </button>
          <button class="btn btn-secondary" @click="exportPriceListExcel" title="导出为 Excel（与旧版一致）">导出Excel</button>
          <button v-if="selectedIds.length > 0" class="btn btn-danger" @click="batchDelete" style="margin-right:10px;">批量删除 ({{ selectedIds.length }})</button>
          <button class="btn btn-primary" @click="showAddModal">+ 添加产品</button>
        </div>
      </div>
      <div class="search-box" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
        <label style="white-space:nowrap;">产品单位：</label>
        <select v-model="selectedUnit" style="min-width:180px;" @change="loadProducts">
          <option value="">请选择产品单位</option>
          <option v-for="u in units" :key="u" :value="u">{{ u }}</option>
        </select>
        <select v-model="selectedWordTemplateSlug" style="min-width:240px;" title="Word 价目表模板（在「模板预览」管理 .docx）">
          <option value="">默认 Word 模板（price_list_default）</option>
          <option v-for="tpl in wordTemplateOptions" :key="tpl.id" :value="tpl.id">{{ tpl.name }}</option>
        </select>
        <input v-model="searchQuery" type="text" placeholder="搜索产品型号或名称..." @input="loadProducts">
        <label class="lbl-inline" title="从考勤统计表「明细」工作表读取：第4行起每6行一块，A部门 B性质 C姓名">
          <input v-model="useAttendanceDetailImport" type="checkbox" />
          考勤统计表·明细导入人员
        </label>
        <label
          v-show="useAttendanceDetailImport"
          class="lbl-inline"
          title="仅删除此前通过本导入方式写入的记录（内部标记），不动其它产品"
        >
          <input v-model="replaceTaggedAttendancePersonnel" type="checkbox" />
          导入前移除上次「明细」导入的人员
        </label>
      </div>
      <div class="card">
        <DataTable
          :columns="columns"
          :data="products"
          :loading="loading"
          :selectable="true"
          :selected-ids="selectedIds"
          :has-more="hasMore"
          :height="'500px'"
          row-key="id"
          empty-text="暂无产品数据"
          @update:selected-ids="selectedIds = $event"
          @load-more="loadMoreProducts"
        >
          <template #cell-model_number="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-name="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-specification="{ value }">
            {{ value || '-' }}
          </template>
          <template #cell-price="{ value }">
            {{ value ? '¥' + value.toFixed(2) : '-' }}
          </template>
          <template #actions="{ row }">
            <button type="button" class="btn btn-sm btn-secondary" @click.stop="editProduct(row)">编辑</button>
            <button type="button" class="btn btn-sm btn-danger" @click.stop="handleDelete(row)">删除</button>
          </template>
        </DataTable>
      </div>
    </div>

    <ConfirmDialog
      v-model="showDeleteConfirm"
      title="确认删除"
      :message="`确定要删除该产品吗？`"
      confirm-text="删除"
      confirm-class="btn-danger"
      @confirm="confirmDelete"
    />

    <ConfirmDialog
      v-model="showBatchDeleteConfirm"
      title="批量删除"
      :message="`确定要删除选中的 ${selectedIds.length} 个产品吗？`"
      confirm-text="批量删除"
      confirm-class="btn-danger"
      @confirm="confirmBatchDelete"
    />

    <div v-if="showModal" class="modal active">
      <div class="modal-content">
        <div class="modal-header">{{ isEdit ? '编辑产品' : '添加产品' }}</div>
        <div class="modal-body">
          <div class="form-group">
            <label>产品型号 *</label>
            <input v-model="formData.model_number" type="text" placeholder="如：A001">
          </div>
          <div class="form-group">
            <label>产品名称 *</label>
            <input v-model="formData.name" type="text" placeholder="产品名称">
          </div>
          <div class="form-group">
            <label>规格</label>
            <input v-model="formData.specification" type="text" placeholder="规格描述">
          </div>
          <div class="form-group">
            <label>价格</label>
            <input v-model.number="formData.price" type="number" step="0.01" placeholder="0.00">
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="showModal = false">取消</button>
          <button class="btn btn-primary" @click="saveProduct">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useProductsStore } from '@/stores/products';
import { storeToRefs } from 'pinia';
import customersApi from '@/api/customers';
import productsApi from '@/api/products';
import templatePreviewApi from '@/api/templatePreview';
import { api } from '@/api/index';
import DataTable from '@/components/DataTable.vue';
import ConfirmDialog from '@/components/ConfirmDialog.vue';
import { appAlert } from '@/utils/appDialog';
import { useCoreNavLabel } from '@/composables/useCoreNavLabel';

const pageNavTitle = useCoreNavLabel('products');

const store = useProductsStore();
const { products, loading } = storeToRefs(store);

const units = ref([]);
const showModal = ref(false);
const isEdit = ref(false);
const selectedIds = ref([]);
const selectAll = ref(false);
const searchQuery = ref('');
const selectedUnit = ref('');
const currentPage = ref(1);
const perPage = ref(1000);
const hasMore = ref(false);
/** Word 价目表模板 slug，传给 /api/products/export.docx?template_id= */
const selectedWordTemplateSlug = ref('');
const wordTemplateOptions = ref([]);
const formData = ref({
  id: null,
  model_number: '',
  name: '',
  specification: '',
  price: 0
});
const showDeleteConfirm = ref(false);
const showBatchDeleteConfirm = ref(false);
const itemToDelete = ref(null);
const importExcelInput = ref(null);
/** 使用 /api/excel/data/extract/upload 的 attendance_detail 解析（与太阳鸟考勤模板「明细」一致） */
const useAttendanceDetailImport = ref(false);
/** 删除 description 为考勤明细标记的旧记录后再导入 */
const replaceTaggedAttendancePersonnel = ref(true);

const columns = [
  { key: 'model_number', label: '型号' },
  { key: 'name', label: '名称' },
  { key: 'specification', label: '规格' },
  { key: 'price', label: '价格' }
];

const currentRequestId = ref(0);

const loadProducts = async (reset = true) => {
  const requestId = ++currentRequestId.value;
  if (reset) {
    currentPage.value = 1;
    hasMore.value = false;
  }
  const params = { page: currentPage.value, per_page: perPage.value };
  if (searchQuery.value) params.keyword = searchQuery.value;
  if (selectedUnit.value) params.unit = selectedUnit.value;
  const result = await store.fetchProducts(params);
  if (requestId !== currentRequestId.value) return;
  if (result && result.data) {
    if (reset) {
      products.value = result.data;
    } else {
      products.value = [...products.value, ...result.data];
    }
    hasMore.value = false;
    currentPage.value++;
  }
};

let isLoadingMore = false;

const loadMoreProducts = async () => {
  if (loading.value || !hasMore.value || isLoadingMore) return;
  isLoadingMore = true;
  try {
    await loadProducts(false);
  } finally {
    isLoadingMore = false;
  }
};

async function loadUnits() {
  try {
    const resp = await customersApi.getCustomers({ page: 1, per_page: 1000 });
    if (!resp?.success) throw new Error(resp?.message || '加载客户/购买单位失败');
    const list = resp?.data || [];
    units.value = Array.isArray(list) ? list.map(c => c.unit_name || c.customer_name).filter(Boolean) : [];
  } catch (e) {
    console.error('加载产品单位失败:', e);
    units.value = [];
  }
}

const showAddModal = () => {
  isEdit.value = false;
  formData.value = {
    id: null,
    model_number: '',
    name: '',
    specification: '',
    price: 0
  };
  showModal.value = true;
};

const editProduct = (product) => {
  isEdit.value = true;
  formData.value = { ...product };
  showModal.value = true;
};

const saveProduct = async () => {
  const result = isEdit.value && formData.value.id
    ? await store.updateProduct(formData.value.id, formData.value)
    : await store.createProduct(formData.value);

  if (result.success) {
    showModal.value = false;
    loadProducts();
  } else {
    await appAlert('保存失败: ' + (result.message || '未知错误'));
  }
};

const handleDelete = (product) => {
  itemToDelete.value = product;
  showDeleteConfirm.value = true;
};

const confirmDelete = async () => {
  if (!itemToDelete.value) return;
  const result = await store.deleteProduct(itemToDelete.value.id);
  if (!result.success) {
    await appAlert('删除失败: ' + (result.message || '未知错误'));
  }
  itemToDelete.value = null;
};

const batchDelete = () => {
  showBatchDeleteConfirm.value = true;
};

const confirmBatchDelete = async () => {
  const result = await store.batchDelete(selectedIds.value);
  if (result.success) {
    selectedIds.value = [];
    selectAll.value = false;
    loadProducts();
  } else {
    await appAlert('批量删除失败: ' + (result.message || '未知错误'));
  }
};

function docxSlugFromListTemplate(tpl) {
  const fn = String(tpl?.filename || '').trim();
  if (fn.toLowerCase().endsWith('.docx')) {
    return fn.replace(/\.docx$/i, '');
  }
  const raw = String(tpl?.id || '').replace(/^fs:/i, '').trim();
  if (raw.toLowerCase().endsWith('.docx')) {
    return raw.replace(/\.docx$/i, '');
  }
  return String(tpl?.slug || '').trim();
}

const exportPriceList = async () => {
  try {
    const params = {};
    if (selectedUnit.value) params.unit = selectedUnit.value;
    if (searchQuery.value) params.keyword = searchQuery.value;
    if (selectedWordTemplateSlug.value) params.template_id = selectedWordTemplateSlug.value;
    const response = await productsApi.exportUnitProductsDocx(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const contentDisposition = response.headers?.get('content-disposition') || '';
    let filename = '产品价格表.docx';
    const utf8NameMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plainNameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (utf8NameMatch?.[1]) {
      try {
        filename = decodeURIComponent(utf8NameMatch[1]);
      } catch (_) {
        filename = utf8NameMatch[1];
      }
    } else if (plainNameMatch?.[1]) {
      filename = plainNameMatch[1];
    }
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('导出失败:', e);
    await appAlert('导出失败: ' + (e.message || '未知错误'));
  }
};

const exportPriceListExcel = async () => {
  try {
    const params = {};
    if (selectedUnit.value) params.unit = selectedUnit.value;
    if (searchQuery.value) params.keyword = searchQuery.value;
    const response = await productsApi.exportUnitProductsXlsx(params);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const contentDisposition = response.headers?.get('content-disposition') || '';
    let filename = '产品价格表.xlsx';
    const utf8NameMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
    const plainNameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (utf8NameMatch?.[1]) {
      try {
        filename = decodeURIComponent(utf8NameMatch[1]);
      } catch (_) {
        filename = utf8NameMatch[1];
      }
    } else if (plainNameMatch?.[1]) {
      filename = plainNameMatch[1];
    }
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    console.error('Excel 导出失败:', e);
    await appAlert('Excel 导出失败: ' + (e.message || '未知错误'));
  }
};

const loadWordTemplateOptions = async () => {
  try {
    const res = await templatePreviewApi.listTemplates();
    if (!res?.success) return;
    const templates = Array.isArray(res.templates) ? res.templates : [];
    const slugSeen = new Set();
    const rows = [];
    for (const tpl of templates) {
      if (!tpl || tpl.virtual || tpl.category !== 'word') continue;
      const fn = String(tpl.filename || '').toLowerCase();
      const nm = String(tpl.name || '').toLowerCase();
      const id = String(tpl.id || '').toLowerCase();
      const isPriceLike =
        fn.includes('price_list') ||
        fn.includes('价目') ||
        fn.includes('价格表') ||
        nm.includes('价目') ||
        nm.includes('价格表') ||
        id.includes('price_list');
      if (!isPriceLike) continue;
      const slug = docxSlugFromListTemplate(tpl);
      if (!slug || slugSeen.has(slug)) continue;
      slugSeen.add(slug);
      rows.push({
        id: slug,
        name: `${tpl.name || slug}（Word）`,
      });
    }
    if (!rows.length) {
      rows.push({ id: 'price_list_default', name: '产品价格表（Word 价目，默认）' });
    }
    wordTemplateOptions.value = rows;
    if (!rows.find((r) => String(r.id) === String(selectedWordTemplateSlug.value))) {
      selectedWordTemplateSlug.value = '';
    }
  } catch (e) {
    console.error('加载 Word 价目模板失败:', e);
  }
};

const triggerImportExcel = () => {
  importExcelInput.value?.click();
};

const handleImport = async (e) => {
  const file = e.target.files?.[0];
  if (!file) return;

  try {
    // 1. 上传并提取Excel数据 (使用 extract/upload 端点)
    const formData = new FormData();
    formData.append('excel_file', file);
    if (useAttendanceDetailImport.value) {
      formData.append('parse_mode', 'attendance_detail');
    }
    const extractRes = await api.post('/api/excel/data/extract/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });

    if (!extractRes.success) {
      await appAlert('文件解析失败: ' + (extractRes.message || '未知错误'));
      return;
    }
    const rows = extractRes.rows || [];
    if (!rows.length) {
      await appAlert(
        useAttendanceDetailImport.value
          ? '未从「明细」表解析到任何人员行。请确认 Excel 含「明细」工作表，且第4行起为每人6行（A部门、B性质、C姓名）。'
          : '未解析到任何数据行，请检查表头或换用「考勤统计表·明细导入人员」。'
      );
      return;
    }

    // 2. 调用产品导入API
    const importRes = await api.post('/api/excel/data/import/products', {
      file_name: file.name,
      data: rows,
      field_mapping: extractRes.headers?.reduce((map, h) => {
        map[h.value] = h.value;
        return map;
      }, {}),
      options: {
        skip_duplicates: true,
        validate_before_import: true,
        clean_data: true,
        replace_attendance_detail_tagged:
          useAttendanceDetailImport.value && replaceTaggedAttendancePersonnel.value,
      }
    });

    if (importRes.success) {
      const imported = importRes.imported || 0;
      const skipped = importRes.skipped || 0;
      let msg = `导入成功！共导入 ${imported} 条产品`;
      if (skipped > 0) {
        msg += `，跳过 ${skipped} 条重复产品`;
      }
      await appAlert(msg);
      await loadProducts();
    } else {
      await appAlert('导入失败: ' + (importRes.message || '未知错误'));
    }
  } catch (err) {
    console.error('导入失败:', err);
    await appAlert('导入失败: ' + (err.message || '未知错误'));
  } finally {
    e.target.value = '';
  }
};

onMounted(() => {
  loadUnits().then(() => loadProducts());
  loadWordTemplateOptions();
});
</script>

<style scoped>
.lbl-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #334155;
  white-space: nowrap;
}
</style>
