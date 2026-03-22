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

export interface MaterialCreateDTO {
  name: string;
  specification?: string;
  unit: string;
  quantity?: number;
  price?: number;
  description?: string;
}

export interface MaterialUpdateDTO extends Partial<MaterialCreateDTO> {}
