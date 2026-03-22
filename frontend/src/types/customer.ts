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
