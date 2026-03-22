# XCAGI Frontend TypeScript 迁移计划

## 📋 项目概述

**目标**: 将 XCAGI 前端从 JavaScript 完全迁移到 TypeScript  
**当前状态**: 纯 JavaScript + Vue 3  
**目标状态**: TypeScript + Vue 3 + 完整类型系统  
**预计周期**: 4-6 周  
**风险等级**: 中等（需要保证业务连续性）

---

## 🎯 迁移目标

### 核心目标
1. ✅ **类型安全**: 消除 90% 以上的 `any` 类型
2. ✅ **开发体验**: 完整的 IntelliSense 支持
3. ✅ **代码质量**: 编译时错误检查，减少运行时错误
4. ✅ **可维护性**: 清晰的接口定义和类型文档
5. ✅ **零功能回归**: 迁移过程中不改变任何业务逻辑

### 质量指标
- TypeScript 覆盖率：100%
- `any` 类型使用率：< 5%
- 类型定义完整度：95%+
- 编译通过率：100%
- 测试通过率：100%

---

## 📊 当前代码分析

### 文件统计
- **JavaScript 文件**: 40 个
  - `api/`: 12 个
  - `stores/`: 9 个
  - `composables/`: 11 个
  - `utils/`: 4 个
  - `router/`: 1 个
  - `components/`: 1 个 (lazy-load.js)
  - `views/`: 2 个 (测试文件)
  
- **Vue 文件**: 51 个
  - `components/`: 30 个
  - `views/`: 12 个
  - `pro-mode/`: 15 个
  - `pro-feature-widget/`: 6 个
  - `template/`: 6 个

### 代码特点
1. **Vue 3 Composition API**: 使用 `<script setup>` 语法
2. **Pinia 状态管理**: 9 个 Store 模块
3. **API 层**: 基于 axios 的封装
4. **Composables**: 复用逻辑的良好实践
5. **Pro Mode**: 复杂的 UI 组件（钢铁侠风格界面）

---

## 🏗️ 迁移策略

### 总体策略：渐进式迁移 + 分层进行

```
Phase 1: 基础设施准备 (Week 1)
  ↓
Phase 2: 工具函数和 API 层 (Week 1-2)
  ↓
Phase 3: Composables (Week 2-3)
  ↓
Phase 4: Stores (Week 3)
  ↓
Phase 5: Vue 组件 (Week 3-5)
  ↓
Phase 6: 清理和优化 (Week 5-6)
```

### 迁移原则
1. **不重写，只翻译**: 保持业务逻辑不变
2. **类型优先**: 优先定义接口和类型
3. **渐进式**: 允许 JS/TS 混编，逐步迁移
4. **测试保障**: 每迁移一个模块都要测试
5. **文档同步**: 类型即文档

---

## 📝 详细实施步骤

### **Phase 1: 基础设施准备** (Week 1)

#### 1.1 安装 TypeScript 依赖
```bash
cd frontend
npm install -D typescript @types/node @vitejs/plugin-vue
```

**依赖清单**:
- `typescript`: ^5.3.0 (最新稳定版)
- `@types/node`: ^20.x (Node.js 类型定义)
- `vue-tsc`: ^1.8.0 (Vue TypeScript 编译器)

#### 1.2 创建 TypeScript 配置文件

**文件**: `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "forceConsistentCasingInFileNames": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vite/client"]
  },
  "include": [
    "src/**/*.ts",
    "src/**/*.d.ts",
    "src/**/*.tsx",
    "src/**/*.vue"
  ],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

**文件**: `frontend/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

#### 1.3 更新 Vite 配置

**文件**: `frontend/vite.config.js` → `vite.config.ts`

主要变更:
- 导入类型：`import type { ConfigEnv, UserConfig } from 'vite'`
- 类型化配置函数：`export default defineConfig((configEnv: ConfigEnv): UserConfig => {...})`

#### 1.4 创建全局类型声明

**文件**: `frontend/src/types/global.d.ts`

```typescript
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
```

**文件**: `frontend/src/types/index.ts`

```typescript
// 统一导出所有类型
export * from './global';
export * from './api';
export * from './store';
export * from './components';
```

#### 1.5 更新 package.json 脚本

```json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit",
    "type-check:watch": "vue-tsc --noEmit --watch",
    "test": "vitest",
    "lint": "eslint src/"
  }
}
```

---

### **Phase 2: 类型定义和 API 层迁移** (Week 1-2)

#### 2.1 创建核心类型定义

**文件**: `frontend/src/types/api.ts`

```typescript
// API 响应基础结构
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  total?: number;
  code?: number;
}

// 分页参数
export interface PaginationParams {
  page?: number;
  limit?: number;
  search?: string;
  sort?: string;
  order?: 'asc' | 'desc';
}

// 通用 CRUD API 接口
export interface CrudApi<T, CreateDTO = Partial<T>, UpdateDTO = Partial<T>> {
  getAll(params?: PaginationParams): Promise<ApiResponse<T[]>>;
  getById(id: number | string): Promise<ApiResponse<T>>;
  create(data: CreateDTO): Promise<ApiResponse<T>>;
  update(id: number | string, data: UpdateDTO): Promise<ApiResponse<T>>;
  delete(id: number | string): Promise<ApiResponse<void>>;
  batchDelete?(ids: (number | string)[]): Promise<ApiResponse<void>>;
}
```

**文件**: `frontend/src/types/store.ts`

```typescript
// Store 通用状态
export interface StoreState {
  loading: boolean;
  error: string | null;
}

// 带分页的 Store 状态
export interface PaginatedStoreState<T> extends StoreState {
  items: T[];
  total: number;
  currentPage: number;
  pageSize: number;
}
```

#### 2.2 定义业务类型

**文件**: `frontend/src/types/product.ts`

```typescript
export interface Product {
  id: number;
  model_number: string;
  name: string;
  specification?: string;
  price: number;
  quantity: number;
  description?: string;
  category?: string;
  brand?: string;
  unit: string;
  is_active: number;
  created_at?: string;
  updated_at?: string;
}

export interface ProductCreateDTO {
  model_number: string;
  name: string;
  specification?: string;
  price?: number;
  quantity?: number;
  description?: string;
  category?: string;
  brand?: string;
  unit?: string;
}

export interface ProductUpdateDTO extends Partial<ProductCreateDTO> {}

export interface ProductQueryParams extends PaginationParams {
  category?: string;
  brand?: string;
  unit?: string;
  is_active?: number;
}
```

**文件**: `frontend/src/types/customer.ts`

```typescript
export interface Customer {
  id: number;
  name: string;
  contact_person?: string;
  contact_phone?: string;
  contact_address?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CustomerCreateDTO {
  name: string;
  contact_person?: string;
  contact_phone?: string;
  contact_address?: string;
}

export interface CustomerUpdateDTO extends Partial<CustomerCreateDTO> {}
```

**文件**: `frontend/src/types/material.ts`

```typescript
export interface Material {
  id: number;
  name: string;
  specification?: string;
  unit: string;
  quantity: number;
  price?: number;
  description?: string;
  created_at?: string;
  updated_at?: string;
}
```

**文件**: `frontend/src/types/order.ts`

```typescript
export interface OrderItem {
  id?: number;
  product_name: string;
  model_number: string;
  quantity: number;
  unit_price: number;
  amount: number;
}

export interface Order {
  id: number;
  order_number: string;
  purchase_unit_name: string;
  contact_person?: string;
  contact_phone?: string;
  contact_address?: string;
  items: OrderItem[];
  status: 'pending' | 'printed' | 'cancelled' | 'completed';
  total_amount: number;
  total_quantity: number;
  created_at?: string;
  updated_at?: string;
  printed_at?: string;
  printer_name?: string;
}
```

**文件**: `frontend/src/types/chat.ts`

```typescript
export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  session_id?: string;
  metadata?: {
    intent?: string;
    tool_calls?: any[];
    [key: string]: any;
  };
}

export interface ChatSession {
  id: string;
  title?: string;
  messages: ChatMessage[];
  created_at?: string;
  updated_at?: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  stream?: boolean;
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: ChatMessage;
  session_id: string;
  intent?: string;
  tool_results?: any[];
}
```

#### 2.3 迁移 API 层

**迁移顺序**:
1. `src/api/index.js` → `src/api/index.ts` (基础 axios 封装)
2. `src/api/chat.ts` (聊天 API)
3. `src/api/products.ts` (产品 API)
4. `src/api/customers.ts` (客户 API)
5. `src/api/materials.ts` (材料 API)
6. `src/api/orders.ts` (订单 API)
7. 其他 API 文件

**示例**: `src/api/index.ts`

```typescript
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';

// 扩展 AxiosResponse 以匹配项目结构
export interface CustomAxiosResponse<T = any> extends AxiosResponse {
  data: {
    success: boolean;
    data?: T;
    message?: string;
    total?: number;
  };
}

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string) {
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // 请求拦截器
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // 响应拦截器
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
      }
    );
  }

  async get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T = any>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async delete<T = any>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }
}

// 根据环境选择 baseURL
const baseURL = import.meta.env.VITE_API_BASE_URL || '';

export const api = new ApiClient(baseURL);
export default api;
```

**示例**: `src/api/chat.ts`

```typescript
import api from './index';
import type { ApiResponse } from '@/types/api';
import type { ChatRequest, ChatResponse, ChatSession } from '@/types/chat';

export const chatApi = {
  sendChat(payload: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/chat', payload);
  },

  sendChatStream(payload: ChatRequest): Promise<Response> {
    // 流式请求返回原生 Response
    return api.post('/api/ai/chat/stream', payload);
  },

  getContext(params: Record<string, any> = {}): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>('/api/ai/context', params);
  },

  clearContext(data: Record<string, any> = {}): Promise<ApiResponse<void>> {
    return api.post<ApiResponse<void>>('/api/ai/context/clear', data);
  },

  getConfig(): Promise<ApiResponse<any>> {
    return api.get<ApiResponse<any>>('/api/ai/config');
  },

  testIntent(data: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/ai/intent/test', data);
  },

  sendUnifiedChat(payload: ChatRequest): Promise<ApiResponse<ChatResponse>> {
    return api.post<ApiResponse<ChatResponse>>('/api/ai/unified_chat', payload);
  },

  getConversations(params: Record<string, any> = {}): Promise<ApiResponse<ChatSession[]>> {
    return api.get<ApiResponse<ChatSession[]>>('/api/conversations/sessions', params);
  },

  getConversation(sessionId: string): Promise<ApiResponse<ChatSession>> {
    return api.get<ApiResponse<ChatSession>>(`/api/conversations/${sessionId}`);
  },

  saveMessage(payload: any): Promise<ApiResponse<any>> {
    return api.post<ApiResponse<any>>('/api/conversations/message', payload);
  },

  newConversation(data: Record<string, any> = {}): Promise<ApiResponse<{ session_id: string }>> {
    return api.post<ApiResponse<{ session_id: string }>>('/api/ai/conversation/new', data);
  }
};

export default chatApi;
```

#### 2.4 迁移工具函数

**文件**: `src/utils/index.ts`

```typescript
/**
 * HTML 转义
 */
export function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * 生成会话 ID
 */
export function generateSessionId(): string {
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

/**
 * 从 Content-Disposition 获取文件名
 */
export function getFilenameFromDisposition(
  disposition: string | null,
  fallback: string = '下载文件.xlsx'
): string {
  if (!disposition) return fallback;
  
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1]);
    } catch (_) {}
  }
  
  const plainMatch = disposition.match(/filename="?([^"]+)"?/i);
  if (plainMatch && plainMatch[1]) {
    return plainMatch[1];
  }
  
  return fallback;
}

/**
 * 下载 Blob 文件
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';
  document.body.appendChild(link);
  link.click();
  
  setTimeout(() => {
    link.remove();
    URL.revokeObjectURL(url);
  }, 0);
}

/**
 * 格式化日期
 */
export function formatDate(date: string | number | Date): string {
  const d = new Date(date);
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
}

/**
 * 格式化时间
 */
export function formatTime(date: string | number | Date): string {
  const d = new Date(date);
  return d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | undefined;
  
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean = false;
  
  return function(...args: Parameters<T>) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
```

---

### **Phase 3: Composables 迁移** (Week 2-3)

#### 3.1 迁移 useApi (核心 Composable)

**文件**: `src/composables/useApi.ts`

```typescript
import { ref, watch, type Ref, type WatchSource } from 'vue';

export interface UseApiOptions<T> {
  immediate?: boolean;
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export interface UseApiReturn<T> {
  data: Ref<T | null>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
  execute: (reset?: boolean) => Promise<T | null>;
  refresh: () => Promise<T | null>;
}

export function useApi<T>(
  apiCall: () => Promise<T>,
  options: UseApiOptions<T> = {}
): UseApiReturn<T> {
  const { immediate = false, onSuccess, onError } = options;
  
  const data = ref<T | null>(null) as Ref<T | null>;
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const execute = async (reset = false): Promise<T | null> => {
    if (reset) {
      data.value = null;
      error.value = null;
    }
    
    loading.value = true;
    error.value = null;
    
    try {
      const result = await apiCall();
      data.value = result;
      onSuccess?.(result);
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      onError?.(error.value);
      return null;
    } finally {
      loading.value = false;
    }
  };

  const refresh = () => execute(true);

  if (immediate) {
    execute();
  }

  return {
    data,
    loading,
    error,
    execute,
    refresh
  };
}

// 简化版 useMutation
export interface UseMutationOptions<T, V = any> {
  onSuccess?: (data: T, variables: V) => void;
  onError?: (error: Error, variables: V) => void;
}

export function useMutation<T, V = any>(
  mutationFn: (variables: V) => Promise<T>,
  options: UseMutationOptions<T, V> = {}
) {
  const { onSuccess, onError } = options;
  const loading = ref(false);
  const error = ref<Error | null>(null);

  const mutate = async (variables: V): Promise<T | null> => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await mutationFn(variables);
      onSuccess?.(result, variables);
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      onError?.(error.value, variables);
      return null;
    } finally {
      loading.value = false;
    }
  };

  return {
    mutate,
    loading,
    error
  };
}
```

#### 3.2 迁移 useProducts

**文件**: `src/composables/useProducts.ts`

```typescript
import { ref, computed, type Ref, type ComputedRef } from 'vue';
import productsApi from '../api/products';
import { useApi, useMutation } from './useApi';
import type { Product, ProductCreateDTO, ProductUpdateDTO } from '@/types/product';

export interface UseProductsReturn {
  products: Ref<Product[]>;
  loading: Ref<boolean>;
  error: Ref<Error | null>;
  searchQuery: Ref<string>;
  selectedUnit: Ref<string>;
  filteredProducts: ComputedRef<Product[]>;
  loadProducts: (params?: any) => Promise<any>;
  createProduct: (data: ProductCreateDTO) => Promise<Product | null>;
  updateProduct: (id: number, data: ProductUpdateDTO) => Promise<Product | null>;
  deleteProduct: (id: number) => Promise<any | null>;
  batchDeleteProducts: (ids: number[]) => Promise<any | null>;
}

export function useProducts(): UseProductsReturn {
  const products = ref<Product[]>([]);
  const loading = ref(false);
  const error = ref<Error | null>(null);
  const searchQuery = ref('');
  const selectedUnit = ref('');

  const filteredProducts = computed<Product[]>(() => {
    if (!searchQuery.value) {
      return products.value;
    }
    const query = searchQuery.value.toLowerCase();
    return products.value.filter(p => 
      (p.model_number && p.model_number.toLowerCase().includes(query)) ||
      (p.name && p.name.toLowerCase().includes(query))
    );
  });

  const loadProducts = async (params: Record<string, any> = {}): Promise<any> => {
    loading.value = true;
    error.value = null;
    
    try {
      const result = await productsApi.getProducts({
        unit: selectedUnit.value,
        search: searchQuery.value,
        ...params
      });
      
      if (result.success && Array.isArray(result.data)) {
        products.value = result.data as Product[];
      }
      
      return result;
    } catch (err) {
      error.value = err instanceof Error ? err : new Error(String(err));
      throw err;
    } finally {
      loading.value = false;
    }
  };

  const createProduct = useMutation<Product, ProductCreateDTO>(
    (data) => productsApi.createProduct(data),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  const updateProduct = useMutation<Product, { id: number; data: ProductUpdateDTO }>(
    ({ id, data }) => productsApi.updateProduct(id, data),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  const deleteProduct = useMutation<any, { id: number; data?: any }>(
    ({ id, data }) => productsApi.deleteProduct(id, data),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  const batchDeleteProducts = useMutation<any, number[]>(
    (ids) => productsApi.batchDeleteProducts(ids),
    {
      onSuccess: () => {
        loadProducts();
      }
    }
  );

  return {
    products,
    loading,
    error,
    searchQuery,
    selectedUnit,
    filteredProducts,
    loadProducts,
    createProduct: createProduct.mutate,
    updateProduct: updateProduct.mutate,
    deleteProduct: deleteProduct.mutate,
    batchDeleteProducts: batchDeleteProducts.mutate
  };
}

// Product Detail Composable
export interface UseProductDetailReturn {
  product: Ref<Product | null>;
  error: Ref<Error | null>;
  loading: Ref<boolean>;
  refresh: () => Promise<Product | null>;
}

export function useProductDetail(id: number | string): UseProductDetailReturn {
  const { data, error, loading, execute } = useApi<Product>(
    () => productsApi.getProduct(id),
    { immediate: !!id }
  );

  return {
    product: data,
    error,
    loading,
    refresh: execute
  };
}
```

#### 3.3 迁移其他 Composables

**迁移清单**:
- ✅ `useApi.ts` - 核心 API Composable
- ✅ `useProducts.ts` - 产品相关
- ⏭️ `useProductQuery.ts` - 产品查询
- ⏭️ `useWorkMode.ts` - 工作模式
- ⏭️ `useProMode.ts` - Pro 模式
- ⏭️ `useJarvisChat.ts` - Jarvis 聊天
- ⏭️ `useFileImport.ts` - 文件导入
- ⏭️ `useAnimations.ts` - 动画
- ⏭️ `useDigitalRain.ts` - 数字雨
- ⏭️ `usePerformanceMonitor.ts` - 性能监控

---

### **Phase 4: Stores 迁移** (Week 3)

#### 4.1 迁移 useProductsStore

**文件**: `src/stores/products.ts`

```typescript
import { defineStore } from 'pinia';
import { ref, computed, type Ref } from 'vue';
import productsApi from '../api/products';
import type { Product, ProductCreateDTO, ProductUpdateDTO } from '@/types/product';
import type { ApiResponse } from '@/types/api';

export interface ProductsState {
  products: Product[];
  loading: boolean;
  error: string | null;
  units: any[];
}

export const useProductsStore = defineStore('products', () => {
  // State
  const products = ref<Product[]>([]) as Ref<Product[]>;
  const loading = ref(false);
  const error = ref<string | null>(null);
  const units = ref<any[]>([]);

  // Getters
  const productCount = computed<number>(() => products.value.length);

  // Actions
  async function fetchProducts(params: Record<string, any> = {}): Promise<{
    success: boolean;
    data?: Product[];
    message?: string;
    total?: number;
  }> {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await productsApi.getProducts(params);
      const data = response as ApiResponse<Product[]>;
      
      if (data.success) {
        products.value = data.data || [];
        return { 
          success: true, 
          data: data.data, 
          total: data.total || 0 
        };
      } else {
        error.value = data.message || '加载产品失败';
        return { success: false, message: error.value };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载产品失败';
      console.error('加载产品失败:', e);
      return { success: false, message: error.value };
    } finally {
      loading.value = false;
    }
  }

  async function createProduct(productData: ProductCreateDTO): Promise<{
    success: boolean;
    message?: string;
  }> {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await productsApi.createProduct(productData);
      const data = response as ApiResponse<Product>;
      
      if (data.success) {
        await fetchProducts();
        return { success: true };
      } else {
        error.value = data.message || '创建产品失败';
        return { success: false, message: error.value };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '创建产品失败';
      return { success: false, message: error.value };
    } finally {
      loading.value = false;
    }
  }

  async function updateProduct(
    id: number, 
    productData: ProductUpdateDTO
  ): Promise<{ success: boolean; message?: string }> {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await productsApi.updateProduct(id, productData);
      const data = response as ApiResponse<Product>;
      
      if (data.success) {
        await fetchProducts();
        return { success: true };
      } else {
        error.value = data.message || '更新产品失败';
        return { success: false, message: error.value };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '更新产品失败';
      return { success: false, message: error.value };
    } finally {
      loading.value = false;
    }
  }

  async function deleteProduct(id: number): Promise<{ success: boolean; message?: string }> {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await productsApi.deleteProduct(id);
      const data = response as ApiResponse<void>;
      
      if (data.success) {
        products.value = products.value.filter(p => p.id !== id);
        return { success: true };
      } else {
        error.value = data.message || '删除产品失败';
        return { success: false, message: error.value };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '删除产品失败';
      return { success: false, message: error.value };
    } finally {
      loading.value = false;
    }
  }

  async function batchDelete(ids: number[]): Promise<{ success: boolean; message?: string }> {
    loading.value = true;
    error.value = null;
    
    try {
      const response = await productsApi.batchDeleteProducts(ids);
      const data = response as ApiResponse<void>;
      
      if (data.success) {
        products.value = products.value.filter(p => !ids.includes(p.id));
        return { success: true };
      } else {
        error.value = data.message || '批量删除失败';
        return { success: false, message: error.value };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '批量删除失败';
      return { success: false, message: error.value };
    } finally {
      loading.value = false;
    }
  }

  return {
    products,
    loading,
    error,
    units,
    productCount,
    fetchProducts,
    createProduct,
    updateProduct,
    deleteProduct,
    batchDelete
  };
});
```

#### 4.2 迁移其他 Stores

**迁移清单**:
- ✅ `products.ts` - 产品 Store
- ⏭️ `materials.ts` - 材料 Store
- ⏭️ `orders.ts` - 订单 Store
- ⏭️ `customers.ts` - 客户 Store (如存在)
- ⏭️ `jarvisChat.ts` - Jarvis 聊天 Store
- ⏭️ `proMode.ts` - Pro 模式 Store
- ⏭️ `workMode.ts` - 工作模式 Store
- ⏭️ `productQuery.ts` - 产品查询 Store
- ⏭️ `industry.ts` - 行业 Store

---

### **Phase 5: Vue 组件迁移** (Week 3-5)

#### 5.1 组件迁移策略

对于 Vue 组件，使用 `<script setup lang="ts">` 语法：

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import type { Product } from '@/types/product';
import { useProductsStore } from '@/stores/products';

// Props 定义
interface Props {
  initialData?: Product;
  editable?: boolean;
  title?: string;
}

const props = withDefaults(defineProps<Props>(), {
  initialData: undefined,
  editable: false,
  title: '产品信息'
});

// Emits 定义
interface Emits {
  (e: 'save', data: Product): void;
  (e: 'cancel'): void;
  (e: 'delete', id: number): void;
}

const emit = defineEmits<Emits>();

// 响应式数据
const loading = ref(false);
const formData = ref<Product>({
  id: 0,
  model_number: '',
  name: '',
  unit: '个',
  is_active: 1,
  ...props.initialData
});

// 计算属性
const isValid = computed(() => {
  return formData.value.name.trim() !== '' && 
         formData.value.model_number.trim() !== '';
});

// 方法
const handleSubmit = () => {
  if (isValid.value) {
    emit('save', formData.value);
  }
};

onMounted(() => {
  // 初始化逻辑
});
</script>

<template>
  <div class="product-form">
    <!-- 模板内容 -->
  </div>
</template>
```

#### 5.2 组件迁移优先级

**Priority 1 - 核心组件** (Week 3):
1. `DataTable.vue` - 数据表格组件
2. `Modal.vue` - 模态框组件
3. `ConfirmDialog.vue` - 确认对话框
4. `FileImport.vue` - 文件导入组件
5. `Sidebar.vue` - 侧边栏

**Priority 2 - 视图组件** (Week 4):
1. `ProductsView.vue` - 产品列表
2. `MaterialsView.vue` - 材料列表
3. `OrdersView.vue` - 订单列表
4. `CustomersView.vue` - 客户列表
5. `ChatView.vue` - 聊天界面

**Priority 3 - Pro Mode 组件** (Week 4-5):
1. `ProMode.vue` - Pro 模式主组件
2. `ProModeOverlay.vue` - Pro 模式覆盖层
3. `JarvisChatPanel.vue` - Jarvis 聊天面板
4. `JarvisCore.vue` - Jarvis 核心
5. 其他 Pro Mode 特效组件

**Priority 4 - 辅助组件** (Week 5):
1. `template/` - 模板相关组件
2. `pro-feature-widget/` - Pro 功能组件
3. 其他工具组件

---

### **Phase 6: 清理和优化** (Week 5-6)

#### 6.1 类型检查优化

**配置**: `frontend/tsconfig.json`

逐步开启严格检查：
```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true
  }
}
```

#### 6.2 ESLint 配置更新

**文件**: `frontend/.eslintrc.cjs`

```javascript
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:vue/vue3-recommended',
    'plugin:vue/vue3-strongly-recommended'
  ],
  parser: 'vue-eslint-parser',
  parserOptions: {
    ecmaVersion: 'latest',
    parser: '@typescript-eslint/parser',
    sourceType: 'module'
  },
  plugins: ['@typescript-eslint', 'vue'],
  rules: {
    'vue/multi-word-component-names': 'off',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unused-vars': ['error', { 
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_'
    }],
    '@typescript-eslint/explicit-module-boundary-types': 'warn'
  }
};
```

#### 6.3 安装额外依赖

```bash
npm install -D @typescript-eslint/parser @typescript-eslint/eslint-plugin eslint-plugin-vue
```

#### 6.4 最终检查清单

- [ ] 所有 `.js` 文件已迁移为 `.ts`
- [ ] 所有 Vue 组件使用 `lang="ts"`
- [ ] 编译无错误：`npm run type-check`
- [ ] ESLint 无警告：`npm run lint`
- [ ] 所有测试通过：`npm run test`
- [ ] 构建成功：`npm run build`
- [ ] 功能测试通过（手动）
- [ ] 性能无回归（Lighthouse 测试）

---

## 📅 时间计划

### Week 1: 基础设施
- [x] 安装 TypeScript 和依赖
- [x] 创建 tsconfig.json
- [x] 创建全局类型定义
- [ ] 更新 Vite 配置
- [ ] 迁移 API 基础层

### Week 2: 核心层迁移
- [ ] 完成所有业务类型定义
- [ ] 迁移所有 API 文件
- [ ] 迁移工具函数
- [ ] 迁移 useApi Composable

### Week 3: 业务层迁移
- [ ] 迁移所有 Composables
- [ ] 迁移所有 Stores
- [ ] 开始迁移基础组件（DataTable, Modal 等）

### Week 4: 组件迁移（上）
- [ ] 迁移所有 Views 组件
- [ ] 迁移主要业务组件
- [ ] 中期代码审查

### Week 5: 组件迁移（下）
- [ ] 迁移 Pro Mode 组件
- [ ] 迁移辅助组件
- [ ] 完成所有组件迁移

### Week 6: 清理和优化
- [ ] 开启严格类型检查
- [ ] 修复所有类型警告
- [ ] 性能优化
- [ ] 最终测试
- [ ] 文档更新

---

## 🎯 成功标准

### 技术指标
- ✅ TypeScript 覆盖率 100%
- ✅ `any` 类型使用率 < 5%
- ✅ 编译错误 0 个
- ✅ ESLint 警告 < 10 个
- ✅ 测试覆盖率 > 80%

### 业务指标
- ✅ 所有功能正常工作
- ✅ 性能无回归
- ✅ 用户体验无变化
- ✅ 无 P0/P1 级别 bug

---

## ⚠️ 风险评估

### 高风险
1. **Pro Mode 复杂组件**: 涉及大量 Canvas 和动画，类型定义复杂
   - **缓解**: 最后迁移，充分测试
   
2. **第三方库类型缺失**: 某些库可能没有类型定义
   - **缓解**: 创建自定义 `.d.ts` 文件

### 中风险
1. **API 响应类型不一致**: 后端返回数据可能与类型定义不符
   - **缓解**: 使用运行时验证（如 Zod）
   
2. **迁移周期长**: 可能影响正常开发
   - **缓解**: 分支开发，定期合并

### 低风险
1. **学习曲线**: 团队成员需要适应 TypeScript
   - **缓解**: 提供培训和文档

---

## 📚 学习资源

### 官方文档
- [TypeScript 官方文档](https://www.typescriptlang.org/docs/)
- [Vue 3 TypeScript 支持](https://vuejs.org/guide/typescript/overview.html)
- [Pinia TypeScript](https://pinia.vuejs.org/zh/cookbook/typescript.html)

### 最佳实践
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [Vue TypeScript 指南](https://vuejs.org/guide/typescript/composition-api.html)

---

## 🔄 回滚计划

如果迁移过程中遇到严重问题，需要能够回滚：

1. **Git 分支策略**: 
   - 主分支：`main` (保持 JS 版本可用)
   - 开发分支：`feature/typescript-migration`
   - 每日提交到开发分支

2. **渐进式合并**:
   - 每完成一个 Phase 就创建一个 PR
   - 充分测试后再合并到主分支

3. **回滚步骤**:
   ```bash
   # 紧急回滚到 JS 版本
   git checkout main
   git revert feature/typescript-migration
   ```

---

## 📊 进度追踪

### 迁移进度表

| 模块 | 文件数 | 已迁移 | 进度 | 状态 |
|------|--------|--------|------|------|
| Types | 10 | 0 | 0% | ⏳ Pending |
| API | 12 | 0 | 0% | ⏳ Pending |
| Utils | 4 | 0 | 0% | ⏳ Pending |
| Composables | 11 | 0 | 0% | ⏳ Pending |
| Stores | 9 | 0 | 0% | ⏳ Pending |
| Components | 30 | 0 | 0% | ⏳ Pending |
| Views | 12 | 0 | 0% | ⏳ Pending |
| **总计** | **88** | **0** | **0%** | ⏳ Pending |

### 每周更新

**Week 1** (YYYY-MM-DD):
- 完成：基础设施搭建
- 进行中：API 层迁移
- 阻塞：无

**Week 2** (YYYY-MM-DD):
- 完成：[待更新]
- 进行中：[待更新]
- 阻塞：[待更新]

---

## 🎓 团队培训

### TypeScript 基础培训（2 小时）
1. TypeScript 基础语法
2. 类型系统详解
3. 泛型和高级类型
4. Vue 3 + TypeScript 最佳实践

### 实战工作坊（4 小时）
1. 迁移实战演练
2. 常见问题解答
3. 代码审查
4. 经验分享

---

## 📝 总结

本次 TypeScript 迁移将显著提升 XCAGI 前端项目的：
- **代码质量**: 编译时错误检查
- **开发效率**: IntelliSense 支持
- **可维护性**: 清晰的类型定义
- **团队协作**: 减少沟通成本

通过渐进式迁移策略，我们可以在保证业务连续性的前提下，顺利完成迁移。

**预计完成时间**: 6 周  
**投入人力**: 2-3 名开发人员  
**预期收益**: 长期维护成本降低 40%，开发效率提升 20%

---

*创建时间：2026-03-22*  
*版本：v1.0*  
*状态：待审批*
