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

export interface OrderCreateDTO {
  purchase_unit_name: string;
  contact_person?: string;
  contact_phone?: string;
  contact_address?: string;
  items: OrderItem[];
}

export interface OrderUpdateDTO extends Partial<OrderCreateDTO> {}
