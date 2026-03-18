# Excel 数据导入和管理 API 文档

## 概述

本文档说明如何使用 XCAGI 项目新增的 Excel 数据导入和管理 API。所有 API 均已实现，可直接被 Vue 前端调用。

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **数据格式**: JSON
- **编码**: UTF-8

---

## 一、数据导入 API

### 1.1 导入产品数据

**接口**: `POST /api/excel/data/import/products`

**请求体**:
```json
{
  "data": [
    {
      "product_code": "P001",
      "product_name": "产品名称",
      "specification": "规格型号",
      "unit_price": 100.50,
      "unit": "个",
      "remark": "备注"
    }
  ],
  "options": {
    "skip_duplicates": true,
    "validate_before_import": true,
    "clean_data": true
  },
  "file_name": "products_import.xlsx"
}
```

**响应**:
```json
{
  "success": true,
  "log_id": 1,
  "imported": 10,
  "skipped": 2,
  "failed": 0,
  "details": {
    "skipped_items": ["P001", "P002"],
    "failed_items": []
  }
}
```

**字段说明**:
- `data`: 要导入的产品数据数组
- `options.skip_duplicates`: 是否跳过重复项（默认 true）
- `options.validate_before_import`: 导入前是否验证（默认 true）
- `options.clean_data`: 是否清洗数据（默认 true）
- `imported`: 成功导入数量
- `skipped`: 跳过数量（重复）
- `failed`: 失败数量

---

### 1.2 导入客户数据

**接口**: `POST /api/excel/data/import/customers`

**请求体**:
```json
{
  "data": [
    {
      "customer_name": "客户名称",
      "contact_person": "联系人",
      "contact_phone": "13800138000",
      "address": "地址"
    }
  ],
  "options": {
    "skip_duplicates": true,
    "validate_before_import": true,
    "clean_data": true
  }
}
```

**响应**: 同产品导入

---

## 二、提取日志 API

### 2.1 获取日志列表

**接口**: `GET /api/excel/logs`

**查询参数**:
- `data_type`: 数据类型过滤 (products/customers/orders)
- `status`: 状态过滤 (pending/completed/failed/partial)
- `limit`: 限制数量 (默认 50)
- `offset`: 偏移量 (默认 0)

**示例**: `GET /api/excel/logs?data_type=products&status=completed&limit=20`

**响应**:
```json
{
  "success": true,
  "logs": [
    {
      "id": 1,
      "file_name": "products_import.xlsx",
      "data_type": "products",
      "total_rows": 100,
      "valid_rows": 98,
      "imported_rows": 95,
      "skipped_rows": 3,
      "failed_rows": 0,
      "status": "completed",
      "created_at": "2026-03-17 10:30:00"
    }
  ],
  "total": 1
}
```

---

### 2.2 获取日志详情

**接口**: `GET /api/excel/logs/{log_id}`

**响应**:
```json
{
  "success": true,
  "log": {
    "id": 1,
    "file_name": "products_import.xlsx",
    "file_path": "/path/to/file.xlsx",
    "data_type": "products",
    "total_rows": 100,
    "valid_rows": 98,
    "imported_rows": 95,
    "skipped_rows": 3,
    "failed_rows": 0,
    "status": "completed",
    "field_mapping": {
      "产品编码": "product_code",
      "产品名称": "product_name"
    },
    "created_at": "2026-03-17 10:30:00"
  }
}
```

---

### 2.3 获取数据预览

**接口**: `GET /api/excel/preview/{log_id}`

**响应**:
```json
{
  "success": true,
  "log": {...},
  "message": "预览数据需要从提取源获取"
}
```

**说明**: 目前返回日志信息，实际数据需要结合具体业务场景实现缓存机制。

---

## 三、模板管理 API

### 3.1 获取模板详情

**接口**: `GET /api/excel/templates/{template_id}`

**响应**:
```json
{
  "success": true,
  "template": {
    "id": 1,
    "template_key": "TPL_20260317103000_ABC123",
    "template_name": "发货单模板",
    "template_type": "发货单",
    "analyzed_data": {...},
    "editable_config": {...},
    "zone_config": {...},
    "merged_cells_config": {...},
    "style_config": {...},
    "business_rules": {...},
    "created_at": "2026-03-17 10:30:00",
    "updated_at": "2026-03-17 10:30:00"
  }
}
```

---

### 3.2 创建模板

**接口**: `POST /api/excel/templates`

**请求体**:
```json
{
  "template_name": "发货单模板",
  "template_type": "发货单",
  "original_file_path": "/path/to/template.xlsx",
  "analyzed_data": {...},
  "editable_config": {...},
  "zone_config": {...},
  "merged_cells_config": {...},
  "style_config": {...},
  "business_rules": {...}
}
```

**响应**:
```json
{
  "success": true,
  "template_id": 1,
  "template_key": "TPL_20260317103000_ABC123",
  "message": "模板创建成功"
}
```

---

### 3.3 更新模板

**接口**: `PUT /api/excel/templates/{template_id}`

**请求体** (只包含需要更新的字段):
```json
{
  "template_name": "新模板名称",
  "editable_config": {...},
  "business_rules": {...}
}
```

**响应**:
```json
{
  "success": true,
  "message": "模板更新成功"
}
```

---

### 3.4 删除模板

**接口**: `DELETE /api/excel/templates/{template_id}`

**说明**: 软删除，将 `is_active` 设置为 0

**响应**:
```json
{
  "success": true,
  "message": "模板删除成功"
}
```

---

## 四、Vue 前端调用示例

### 4.1 Axios 配置

```javascript
// src/api/axios.js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:5000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export default apiClient
```

### 4.2 导入服务

```javascript
// src/api/excel-import.js
import apiClient from './axios'

export const excelImportApi = {
  // 导入产品
  importProducts(data, options = {}) {
    return apiClient.post('/excel/data/import/products', {
      data,
      options: {
        skip_duplicates: true,
        validate_before_import: true,
        clean_data: true,
        ...options
      }
    })
  },

  // 导入客户
  importCustomers(data, options = {}) {
    return apiClient.post('/excel/data/import/customers', {
      data,
      options: {
        skip_duplicates: true,
        validate_before_import: true,
        clean_data: true,
        ...options
      }
    })
  },

  // 获取日志列表
  getLogs(params = {}) {
    return apiClient.get('/excel/logs', { params })
  },

  // 获取日志详情
  getLogDetail(logId) {
    return apiClient.get(`/excel/logs/${logId}`)
  },

  // 获取预览
  getPreview(logId) {
    return apiClient.get(`/excel/preview/${logId}`)
  }
}
```

### 4.3 模板管理服务

```javascript
// src/api/excel-templates.js
import apiClient from './axios'

export const excelTemplatesApi = {
  // 获取模板详情
  getTemplate(templateId) {
    return apiClient.get(`/excel/templates/${templateId}`)
  },

  // 创建模板
  createTemplate(templateData) {
    return apiClient.post('/excel/templates', templateData)
  },

  // 更新模板
  updateTemplate(templateId, templateData) {
    return apiClient.put(`/excel/templates/${templateId}`, templateData)
  },

  // 删除模板
  deleteTemplate(templateId) {
    return apiClient.delete(`/excel/templates/${templateId}`)
  }
}
```

### 4.4 Vue 组件使用示例

```vue
<template>
  <div class="product-import">
    <el-button @click="handleImport" type="primary">导入产品</el-button>
    
    <el-table :data="importLogs">
      <el-table-column prop="file_name" label="文件名" />
      <el-table-column prop="data_type" label="类型" />
      <el-table-column prop="imported_rows" label="导入数量" />
      <el-table-column prop="status" label="状态" />
      <el-table-column prop="created_at" label="时间" />
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { excelImportApi } from '@/api/excel-import'

const importLogs = ref([])

const handleImport = async () => {
  try {
    const data = [...] // 从 Excel 提取的数据
    const result = await excelImportApi.importProducts(data)
    
    if (result.data.success) {
      ElMessage.success(`导入成功：${result.data.imported}条`)
      loadLogs()
    }
  } catch (error) {
    ElMessage.error('导入失败')
  }
}

const loadLogs = async () => {
  const result = await excelImportApi.getLogs({ data_type: 'products' })
  importLogs.value = result.data.logs
}

onMounted(() => {
  loadLogs()
})
</script>
```

---

## 五、错误处理

### 5.1 错误响应格式

```json
{
  "success": false,
  "message": "错误信息"
}
```

### 5.2 常见错误码

- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

### 5.3 Vue 错误处理示例

```javascript
try {
  const result = await excelImportApi.importProducts(data)
} catch (error) {
  if (error.response) {
    // 服务器返回错误
    const { status, data } = error.response
    switch (status) {
      case 400:
        ElMessage.error('请求参数错误')
        break
      case 404:
        ElMessage.error('资源不存在')
        break
      case 500:
        ElMessage.error('服务器错误')
        break
      default:
        ElMessage.error(data.message || '操作失败')
    }
  } else {
    // 网络错误
    ElMessage.error('网络连接失败')
  }
}
```

---

## 六、数据库表结构

### 6.1 extract_logs 表

```sql
CREATE TABLE extract_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT,
    data_type TEXT NOT NULL,
    total_rows INTEGER DEFAULT 0,
    valid_rows INTEGER DEFAULT 0,
    imported_rows INTEGER DEFAULT 0,
    skipped_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    field_mapping TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### 6.2 templates 表

```sql
CREATE TABLE templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key TEXT UNIQUE NOT NULL,
    template_name TEXT NOT NULL,
    template_type TEXT DEFAULT '通用',
    original_file_path TEXT,
    analyzed_data TEXT,
    editable_config TEXT,
    zone_config TEXT,
    merged_cells_config TEXT,
    style_config TEXT,
    business_rules TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

---

## 七、测试建议

### 7.1 单元测试

```javascript
// tests/excel-import.test.js
import { excelImportApi } from '@/api/excel-import'

describe('Excel Import API', () => {
  test('should import products successfully', async () => {
    const mockData = [
      { product_code: 'P001', product_name: '测试产品' }
    ]
    
    const result = await excelImportApi.importProducts(mockData)
    
    expect(result.data.success).toBe(true)
    expect(result.data.imported).toBeGreaterThan(0)
  })
})
```

### 7.2 集成测试

使用 Postman 或类似工具测试所有 API 端点。

---

## 更新日志

- **2026-03-17**: 初始版本，包含数据导入、日志管理、模板管理功能
