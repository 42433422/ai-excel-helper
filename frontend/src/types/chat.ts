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
  user_id?: string;
  source?: string;
  mode?: string;
  file_context?: Record<string, any>;
  context?: Record<string, any> | KittenRequestContext;
}

export interface ChatResponse {
  message: ChatMessage;
  session_id: string;
  intent?: string;
  tool_results?: any[];
}

export interface KittenDatasetContext {
  file_name?: string;
  name?: string;
  rows?: number;
  columns?: number;
  fields?: string[];
  field_names?: string[];
  preview_text?: string;
}

export interface KittenRequestContext {
  kitten_analyzer?: boolean;
  has_dataset?: boolean;
  kitten_dataset?: KittenDatasetContext | null;
  [key: string]: any;
}
