import api from './index';

export const wechatApi = {
  getTasks(params = {}) {
    return api.get('/api/wechat/tasks', params);
  },

  confirmTask(id) {
    return api.post(`/api/wechat/task/${id}/confirm`);
  },

  ignoreTask(id) {
    return api.post(`/api/wechat/task/${id}/ignore`);
  },

  getContacts(params = {}) {
    return api.get('/api/wechat/contacts', params);
  },

  addContact(data) {
    return api.post('/api/wechat/contacts', data);
  },

  getContact(id) {
    return api.get(`/api/wechat/contacts/${id}`);
  },

  updateContact(id, data) {
    return api.put(`/api/wechat/contacts/${id}`, data);
  },

  deleteContact(id) {
    return api.delete(`/api/wechat/contacts/${id}`);
  },

  scanMessages() {
    return api.post('/api/wechat/scan');
  },

  getContactContext(id) {
    return api.get(`/api/wechat/contacts/${id}/context`);
  },

  // Legacy-compatible contacts endpoints used by current console pages.
  getStarredContacts(params = {}) {
    return api.get('/api/wechat_contacts', params);
  },

  ensureContactCache() {
    return api.get('/api/wechat_contacts/ensure_contact_cache');
  },

  searchContacts(query) {
    return api.get('/api/wechat_contacts/search', { q: query || '' });
  },

  addStarredContact(data) {
    return api.post('/api/wechat_contacts', data);
  },

  updateStarredContact(id, data) {
    return api.put(`/api/wechat_contacts/${id}`, data);
  },

  deleteStarredContact(id) {
    return api.delete(`/api/wechat_contacts/${id}`);
  },

  unstarAllContacts() {
    return api.post('/api/wechat_contacts/unstar_all', {});
  },

  getStarredContactContext(id) {
    return api.get(`/api/wechat_contacts/${id}/context`);
  },

  refreshContactMessages(id) {
    return api.post(`/api/wechat_contacts/${id}/refresh_messages`, {});
  },

  refreshMessagesCache() {
    return api.post('/api/wechat_contacts/refresh_messages_cache', {});
  },

  refreshContactCache() {
    return api.post('/api/wechat_contacts/refresh_contact_cache', {});
  },

  openChat(contactName) {
    return api.post('/api/wechat_contacts/open_chat', { contact_name: contactName });
  },

  sendMessage(contactName, message) {
    return api.post('/api/wechat_contacts/send_message', {
      contact_name: contactName,
      message
    });
  }
};

export default wechatApi;
