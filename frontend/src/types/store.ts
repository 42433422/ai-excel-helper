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
