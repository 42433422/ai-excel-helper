# 模板预览功能重构方案 v2

## 一、需求分析

### 1.1 核心功能
1. **智能识别**：上传文件后自动判定类型
   - Excel 文件 → 识别为 Excel 模板（发货单等）
   - 图片文件 → 识别为标签模板
2. **二次编辑**：对识别出的字段进行增删改
   - 固定词条（只读标签）
   - 可变词条（可编辑数据）
3. **直观预览**：Excel 模板和标签模板的卡片展示

### 1.2 用户流程
```
上传文件 → 自动识别类型 → 生成预览 + 字段列表
    ↓
二次编辑字段（增删改、设置固定/可变）
    ↓
保存模板
```

---

## 二、重构方案

### 2.1 智能识别逻辑

| 上传文件 | 识别结果 | 后续处理 |
|----------|----------|----------|
| `.xlsx`, `.xls` | Excel 模板 | 调用 Excel 分析器提取字段 |
| `.png`, `.jpg`, `.jpeg`, `.gif` | 标签模板 | 调用 OCR 或使用默认字段 |

### 2.2 创建模板 Modal 流程（2步）

#### 步骤1：上传 + 自动识别
```
┌─────────────────────────────────────────┐
│  📁 创建新模板                           │
├─────────────────────────────────────────┤
│                                         │
│   模板名称：___________________         │
│   (例如：运动鞋标签、出货单)              │
│                                         │
│   ┌─────────────────────────────┐       │
│   │                             │       │
│   │   点击或拖拽上传文件        │       │
│   │   支持 .xlsx, .xls, 图片    │       │
│   │                             │       │
│   └─────────────────────────────┘       │
│                                         │
│   已识别类型：[ Excel ] / [ 标签 ]       │
│   (自动识别，无需手动选择)               │
│                                         │
├─────────────────────────────────────────┤
│            [取消]  [下一步 →]            │
└─────────────────────────────────────────┘
```

#### 步骤2：编辑字段
```
┌──────────────────────────────────────────────────────────┐
│  ✏️ 编辑模板字段                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ 📋 预览区         │  │ 📝 字段列表                   │ │
│  │                  │  │                              │ │
│  │ [Excel表格预览]   │  │ ┌──────────────────────────┐│ │
│  │ 或               │  │ │ 品名：运动鞋 [固定] [✏️] [🗑️]││ │
│  │ [标签图片预览]    │  │ │ 货号：1635   [可变] [✏️] [🗑️]││ │
│  │                  │  │ │ 颜色：白色   [可变] [✏️] [🗑️]││ │
│  └──────────────────┘  │ │ [+ 添加新字段]            ││ │
│                         │ └──────────────────────────┘│ │
│                         └──────────────────────────────┘ │
│                                                          │
├──────────────────────────────────────────────────────────┤
│            [← 上一步]  [取消]  [保存模板]                  │
└──────────────────────────────────────────────────────────┘
```

### 2.3 字段类型说明

| 类型 | 说明 | 可编辑 | 示例 |
|------|------|--------|------|
| 固定词条 | 标签上的标识文字 | 否 | 品名：、货号：、颜色： |
| 可变词条 | 对应的值 | 是 | 运动鞋、1635、白色 |

### 2.4 模板卡片展示

#### Excel 模板卡片
- 预览区：CSS Grid 模拟 Excel 表格
- 显示表头和部分数据行

#### 标签模板卡片
- 预览区：Canvas 模拟 PIL 生成的标签图片
- 显示边框、字段布局

---

## 三、实现步骤

### 步骤 1：前端 - 上传识别组件
- 创建 `FileUploadStep.vue` 组件
- 支持拖拽上传
- 自动识别文件类型

### 步骤 2：前端 - 字段编辑器组件
- 创建 `FieldEditor.vue` 组件
- 字段列表展示
- 增删改功能
- 固定/可变切换

### 步骤 3：前端 - 预览渲染
- Excel 预览：CSS Grid
- 标签预览：Canvas 渲染

### 步骤 4：后端 - 模板分析接口
- `POST /api/templates/analyze` - 分析上传文件
- Excel：使用 `excel_template_analyzer`
- 图片：使用 `label_template_generator`

### 步骤 5：集成到 TemplatePreviewView.vue
- 合并现有"添加模板"和"从图片生成"
- 更新卡片展示样式

---

## 四、API 设计

### 4.1 分析模板接口
```
POST /api/templates/analyze
Content-Type: multipart/form-data

file: <文件>
template_name: <模板名称，可选>

Response:
{
  "success": true,
  "template_name": "用户自定义的名称",
  "template_type": "excel" | "label",
  "fields": [
    {"label": "品名", "value": "运动鞋", "type": "fixed"},
    {"label": "货号", "value": "1635", "type": "dynamic"}
  ],
  "preview_data": {...}
}
```

---

## 五、文件清单

| 文件 | 操作 |
|------|------|
| `frontend/src/components/template/FileUploadStep.vue` | 新建 |
| `frontend/src/components/template/FieldEditor.vue` | 新建 |
| `frontend/src/components/template/ExcelPreview.vue` | 新建 |
| `frontend/src/components/template/LabelPreview.vue` | 新建 |
| `frontend/src/views/TemplatePreviewView.vue` | 修改 |
| `app/routes/templates.py` | 新增 analyze 接口 |
| `app/services/skills/label_template_generator/label_template_generator.py` | 复用 |
| `app/services/skills/excel_analyzer/excel_template_analyzer.py` | 复用 |

---

## 六、模拟数据示例

### 6.1 标签模板模拟数据
```javascript
{
  template_name: '运动鞋标签',
  template_type: 'label',
  fields: [
    { label: '品名', value: 'XX运动鞋', type: 'fixed' },
    { label: '货号', value: '1635', type: 'dynamic' },
    { label: '颜色', value: '白色', type: 'dynamic' },
    { label: '码段', value: '00001', type: 'dynamic' },
    { label: '等级', value: '合格品', type: 'fixed' },
    { label: '执行标准', value: 'QB/T4331-2013', type: 'fixed' },
    { label: '统一零售价', value: '¥199', type: 'dynamic' }
  ]
}
```

### 6.2 Excel 模板模拟数据
```javascript
{
  template_name: '出货单模板',
  template_type: 'excel',
  fields: [
    { label: '订单号', type: 'dynamic' },
    { label: '客户名称', type: 'dynamic' },
    { label: '发货日期', type: 'dynamic' },
    { label: '品名', type: 'dynamic' },
    { label: '数量', type: 'dynamic' },
    { label: '单价', type: 'dynamic' },
    { label: '金额', type: 'dynamic' }
  ]
}
```
