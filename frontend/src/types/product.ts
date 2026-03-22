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

export interface ProductQueryParams {
  page?: number;
  limit?: number;
  search?: string;
  sort?: string;
  order?: 'asc' | 'desc';
  category?: string;
  brand?: string;
  unit?: string;
  is_active?: number;
}
