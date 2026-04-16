# 真实电话业务员工作流组件

## 组件概述

本目录包含"真实电话业务员"功能的完整前端组件实现，提供员工开关控制和工作流分支可视化功能。

## 组件列表

### 1. WorkflowEmployeeRow.vue
员工行开关组件，用于控制业务员的启用/禁用状态。

**功能特性：**
- ✅ 支持 v-model 双向绑定
- ✅ 自定义标签文本
- ✅ 切换动画效果
- ✅ 事件发射（change, toggle）
- ✅ 无障碍支持（ARIA）

**使用示例：**
```vue
<template>
  <WorkflowEmployeeRow
    label="真实电话业务员"
    employee-id="real_phone"
    v-model="isActive"
    @change="handleChange"
    @toggle="handleToggle"
  />
</template>
```

### 2. WfVizBranchCard.vue
工作流分支可视化卡片组件，展示业务流程和触发器。

**功能特性：**
- ✅ 固定/动态分支标识
- ✅ 触发器链展示
- ✅ 配置和详情操作按钮
- ✅ 可自定义插槽内容
- ✅ 响应式设计

**使用示例：**
```vue
<template>
  <WfVizBranchCard
    title="真实电话业务员"
    badge-text="固定扩展"
    branch-id="real_phone"
    :is-fixed="true"
    :triggers="triggers"
    @configure="handleConfigure"
    @view-details="handleViewDetails"
  >
    <template #triggers>
      固定行 id=real_phone；副窗启用 → ADB 设备连通检查 → 来电检测/接听
    </template>
  </WfVizBranchCard>
</template>
```

### 3. WorkflowDemo.vue
完整的演示组件，展示两个组件的组合使用。

## 类型定义

在 `src/types/workflow-employee.ts` 中定义了完整的 TypeScript 类型：

- `WorkflowEmployee` - 员工配置
- `BranchTrigger` - 分支触发器
- `WorkflowBranch` - 工作流分支
- `ToggleEvent` - 切换事件
- `BranchActionEvent` - 分支操作事件

## 样式定制

所有组件都使用 scoped CSS，可以通过以下方式定制：

### 1. CSS 变量覆盖
```css
:root {
  --wf-primary-color: #3b82f6;
  --wf-border-color: #e5e7eb;
  --wf-bg-hover: #f9fafb;
}
```

### 2. 深度选择器
```vue
<style>
.workflow-employee-row {
  /* 覆盖全局样式 */
}
</style>
```

## 工作流程

真实电话业务员的标准工作流程：

1. **启用员工** → 切换开关
2. **ADB 设备检查** → 验证设备连接
3. **来电检测** → 监听来电事件
4. **自动接听** → 根据配置接听
5. **语音转写** → 实时语音识别
6. **语音回复** → AI 生成回复
7. **状态轮询** → 同步设备状态

## 集成指南

### 步骤 1：导入组件
```typescript
// main.ts
import WorkflowEmployeeRow from './components/workflow/WorkflowEmployeeRow.vue'
import WfVizBranchCard from './components/workflow/WfVizBranchCard.vue'

app.component('WorkflowEmployeeRow', WorkflowEmployeeRow)
app.component('WfVizBranchCard', WfVizBranchCard)
```

### 步骤 2：在业务组件中使用
```vue
<template>
  <div class="workflow-panel">
    <WorkflowEmployeeRow
      v-for="employee in employees"
      :key="employee.id"
      :label="employee.name"
      :employee-id="employee.id"
      v-model="employee.isActive"
      @toggle="handleEmployeeToggle"
    />
  </div>
</template>
```

### 步骤 3：处理业务逻辑
```typescript
const handleEmployeeToggle = async ({ employeeId, active }) => {
  if (active) {
    await api.enableEmployee(employeeId)
    await checkAdbDevice(employeeId)
  } else {
    await api.disableEmployee(employeeId)
  }
}
```

## API 集成建议

```typescript
// services/workflow.ts
import axios from 'axios'

export const workflowApi = {
  async enableEmployee(id: string) {
    return axios.post(`/api/workflow/employees/${id}/enable`)
  },
  
  async disableEmployee(id: string) {
    return axios.post(`/api/workflow/employees/${id}/disable`)
  },
  
  async getBranchDetails(id: string) {
    return axios.get(`/api/workflow/branches/${id}`)
  },
  
  async configureBranch(id: string, config: any) {
    return axios.put(`/api/workflow/branches/${id}/config`, config)
  }
}
```

## 测试建议

```typescript
// tests/workflow-components.test.ts
import { mount } from '@vue/test-utils'
import WorkflowEmployeeRow from '../src/components/workflow/WorkflowEmployeeRow.vue'

describe('WorkflowEmployeeRow', () => {
  it('should toggle when clicked', async () => {
    const wrapper = mount(WorkflowEmployeeRow)
    await wrapper.trigger('click')
    expect(wrapper.emitted('toggle')).toHaveLength(1)
  })
  
  it('should update when modelValue changes', async () => {
    const wrapper = mount(WorkflowEmployeeRow, {
      props: { modelValue: true }
    })
    expect(wrapper.vm.isActive).toBe(true)
  })
})
```

## 注意事项

1. **状态管理**：建议使用 Vuex 或 Pinia 管理全局员工状态
2. **错误处理**：添加 API 调用失败的回滚机制
3. **性能优化**：大量员工时使用虚拟滚动
4. **国际化**：使用 i18n 支持多语言
5. **可访问性**：确保键盘导航和屏幕阅读器支持

## 未来扩展

- [ ] 添加拖拽排序功能
- [ ] 支持批量操作
- [ ] 添加员工状态实时监控
- [ ] 集成通知系统
- [ ] 添加配置向导
- [ ] 支持主题切换

## 相关文档

- [Vue 3 组件开发指南](https://vuejs.org/guide/)
- [TypeScript 最佳实践](https://www.typescriptlang.org/docs/)
- [无障碍设计指南](https://www.w3.org/WAI/ARIA/apg/)
