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
  }
};

export default wechatApi;
