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
