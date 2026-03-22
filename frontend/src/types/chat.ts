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
