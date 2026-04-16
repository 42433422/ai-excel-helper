import api from './index';

export const chatApi = {
  sendUnifiedChat(payload) {
    return api.post('/api/ai/chat-unified', payload);
  },

  sendChat(payload) {
    return api.post('/api/ai/chat', payload);
  },

  getConversations(params = {}) {
    return api.get('/api/conversations/sessions', params);
  },

  getConversation(sessionId) {
    return api.get(`/api/conversations/${sessionId}`);
  },

  saveMessage(data) {
    return api.post('/api/conversations/message', data);
  },

  getPreferences(userId = 'default') {
    return api.get('/api/preferences', { user_id: userId });
  },

  savePreferences(data) {
    return api.post('/api/preferences', {
      user_id: 'default',
      ...data
    });
  }
};

export default chatApi;
