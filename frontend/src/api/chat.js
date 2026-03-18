import api from './index';

export const chatApi = {
  sendChat(payload) {
    return api.post('/api/ai/chat', payload);
  },

  sendChatStream(payload) {
    return api.post('/api/ai/chat/stream', payload);
  },

  getContext(params = {}) {
    return api.get('/api/ai/context', params);
  },

  clearContext(data = {}) {
    return api.post('/api/ai/context/clear', data);
  },

  getConfig() {
    return api.get('/api/ai/config');
  },

  testIntent(data) {
    return api.post('/api/ai/intent/test', data);
  },

  sendUnifiedChat(payload) {
    return api.post('/api/ai/unified_chat', payload);
  },

  getConversations(params = {}) {
    return api.get('/api/conversations/sessions', params);
  },

  getConversation(sessionId) {
    return api.get(`/api/conversations/${sessionId}`);
  },

  saveMessage(payload) {
    return api.post('/api/ai/message/save', payload);
  },

  newConversation(data = {}) {
    return api.post('/api/ai/conversation/new', data);
  }
};

export default chatApi;
