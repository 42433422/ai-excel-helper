import api from './index';

export const wechatApi = {
  getContacts(params = {}) {
    return api.get('/api/wechat/contacts', params);
  },

  refreshContactCache() {
    return api.post('/api/wechat/contacts/refresh-cache');
  },

  refreshMessagesCache() {
    return api.post('/api/wechat/messages/refresh-cache');
  },

  searchContacts(query) {
    return api.get('/api/wechat/contacts/search', { q: query });
  },

  starContact(contactId) {
    return api.post('/api/wechat/contacts/star', { contact_id: contactId });
  },

  unstarContact(contactId) {
    return api.post('/api/wechat/contacts/unstar', { contact_id: contactId });
  },

  unstarAllContacts() {
    return api.post('/api/wechat/contacts/unstar-all');
  },

  getStarredContacts(params = {}) {
    return api.get('/api/wechat/contacts/starred', params);
  },

  getMessages(params = {}) {
    return api.get('/api/wechat/messages', params);
  },

  clearMessages() {
    return api.post('/api/wechat/messages/clear');
  }
};

export default wechatApi;
