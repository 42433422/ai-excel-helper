<template>
  <div class="page-view" id="view-wechat-contacts">
    <div class="page-content">
      <div class="page-header">
        <h2>微信联系人</h2>
      </div>
      <div class="card">
        <div class="card-header">搜索并星标</div>
        <p class="muted" style="margin:0 0 10px 0;font-size:13px;">先刷新联系人缓存与聊天记录缓存（从解密库导入一次），之后搜索与查看聊天记录只读本地缓存。</p>
        <div class="form-group" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;">
          <button type="button" class="btn btn-primary" @click="refreshContactCache" :disabled="loading">刷新联系人缓存</button>
          <button type="button" class="btn btn-primary" @click="refreshMessagesCache" :disabled="loading">刷新聊天记录缓存</button>
          <input
            type="text"
            v-model.trim="searchKeyword"
            placeholder="输入昵称/备注/微信号搜索"
            style="max-width:320px;"
            @keydown.enter.prevent="searchContacts"
          >
          <button type="button" class="btn btn-primary" @click="searchContacts" :disabled="loading">搜索</button>
        </div>
        <div style="margin-top:10px;min-height:0;max-height:240px;overflow-y:auto;">
          <div v-if="searchResults.length === 0" class="empty-state">暂无搜索结果</div>
          <div v-for="item in searchResults" :key="item.username" class="wechat-contact-form-item" style="margin-bottom:8px;">
            <div class="wechat-contact-row">
              <span class="wechat-contact-label">昵称</span>
              <span class="wechat-contact-value">{{ item.display_name || '-' }}</span>
            </div>
            <div class="wechat-contact-row">
              <span class="wechat-contact-label">微信号</span>
              <span class="wechat-contact-value">{{ item.username || '-' }}</span>
            </div>
            <div class="wechat-contact-row">
              <span class="wechat-contact-label">状态</span>
              <span class="wechat-contact-value">{{ item.already_starred ? '已星标' : '未星标' }}</span>
            </div>
            <div class="wechat-contact-row" style="margin-top:6px;">
              <button v-if="!item.already_starred" class="btn btn-primary btn-sm" @click="addToStar(item)">⭐ 添加星标</button>
              <span v-else style="color:#888;">已是星标联系人</span>
            </div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">星标联系人列表</div>
        <div class="form-group" style="display:flex;flex-wrap:wrap;align-items:center;gap:12px;">
          <label style="margin:0;white-space:nowrap;">类型：</label>
          <select v-model="contactType" style="width:120px;" @change="loadContacts">
            <option value="all">全部</option>
            <option value="contact">联系人</option>
            <option value="group">群聊</option>
          </select>
          <input type="text" v-model.trim="localFilter" placeholder="🔍 在星标列表中筛选" style="max-width:320px;">
          <button type="button" class="btn btn-secondary" title="清除所有星标，列表将为空" @click="unstarAll">一键解除全部星标</button>
        </div>
        <div>
          <div v-if="loading" class="empty-state">加载中...</div>
          <div v-else-if="filteredContacts.length === 0" class="empty-state">暂无星标联系人</div>
          <div v-else class="wechat-contact-list-form">
            <div v-for="contact in filteredContacts" :key="contact.id" class="wechat-contact-form-item">
              <div class="wechat-contact-fields">
                <div class="wechat-contact-row"><span class="wechat-contact-label">类型</span><span class="wechat-contact-value">{{ contact.contact_type === 'group' ? '群聊' : '联系人' }}</span></div>
                <div class="wechat-contact-row"><span class="wechat-contact-label">昵称</span><span class="wechat-contact-value">{{ contact.contact_name || '-' }}</span></div>
                <div class="wechat-contact-row"><span class="wechat-contact-label">备注</span><span class="wechat-contact-value">{{ contact.remark || '-' }}</span></div>
                <div class="wechat-contact-row"><span class="wechat-contact-label">微信号</span><span class="wechat-contact-value">{{ contact.wechat_id || '-' }}</span></div>
              </div>
              <div class="wechat-contact-actions">
                <button class="btn btn-secondary" @click="showContext(contact)">查看聊天记录</button>
                <button class="btn btn-primary" @click="refreshContactMessages(contact.id)">刷新聊天记录</button>
                <button class="btn btn-secondary" @click="startEdit(contact)">编辑</button>
                <button class="btn btn-danger" @click="deleteContact(contact.id)">删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="modal" :class="{ active: showChatModal }">
        <div class="modal-content" style="max-width: 780px; width: calc(100vw - 32px); display:flex; flex-direction:column; max-height:80vh;">
          <div class="modal-header">{{ chatTitle }}</div>
          <div style="flex:1;overflow-y:auto;min-height:200px;max-height:50vh;padding:12px;background:#f8f9fa;border-radius:8px;font-size:13px;">
            <div v-if="chatMessages.length === 0" class="empty-state">暂无聊天记录</div>
            <div
              v-for="(msg, idx) in chatMessages"
              :key="idx"
              class="wechat-chat-msg"
              style="margin-bottom:10px;padding:8px 10px;border-radius:8px;"
            >
              <div style="font-size:11px;color:#666;margin-bottom:4px;">{{ msg.role === 'self' ? '我' : '对方' }}</div>
              <div style="word-break:break-word;white-space:pre-wrap;">{{ msg.text || '' }}</div>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showChatModal = false">关闭</button>
          </div>
        </div>
      </div>

      <div class="modal" :class="{ active: showEditModal }">
        <div class="modal-content" style="max-width: 520px;">
          <div class="modal-header">编辑联系人</div>
          <div class="form-group">
            <label>联系人名称</label>
            <input type="text" v-model.trim="editForm.contact_name" placeholder="联系人名称">
          </div>
          <div class="form-group">
            <label>备注</label>
            <input type="text" v-model.trim="editForm.remark" placeholder="备注">
          </div>
          <div class="form-group">
            <label>微信号</label>
            <input type="text" v-model.trim="editForm.wechat_id" placeholder="wechat_id">
          </div>
          <div class="form-group">
            <label>类型</label>
            <select v-model="editForm.contact_type">
              <option value="contact">联系人</option>
              <option value="group">群聊</option>
            </select>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click="showEditModal = false">取消</button>
            <button class="btn btn-primary" @click="saveEdit" :disabled="loading">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import wechatApi from '../api/wechat';

const loading = ref(false);
const contacts = ref([]);
const contactType = ref('all');
const localFilter = ref('');
const searchKeyword = ref('');
const searchResults = ref([]);

const showChatModal = ref(false);
const chatTitle = ref('聊天记录');
const chatMessages = ref([]);

const showEditModal = ref(false);
const editId = ref(null);
const editForm = ref({
  contact_name: '',
  remark: '',
  wechat_id: '',
  contact_type: 'contact'
});

const filteredContacts = computed(() => {
  const q = localFilter.value.toLowerCase();
  if (!q) return contacts.value;
  return contacts.value.filter((c) => {
    return [
      c.contact_name || '',
      c.remark || '',
      c.wechat_id || ''
    ].join(' ').toLowerCase().includes(q);
  });
});

async function loadContacts() {
  loading.value = true;
  try {
    await wechatApi.ensureContactCache();
    const data = await wechatApi.getStarredContacts({ type: contactType.value });
    if (!data?.success) throw new Error(data?.message || '加载失败');
    contacts.value = Array.isArray(data.data) ? data.data : [];
  } catch (e) {
    console.error('加载微信联系人失败:', e);
    contacts.value = [];
  } finally {
    loading.value = false;
  }
}

async function refreshContactCache() {
  try {
    const data = await wechatApi.refreshContactCache();
    if (!data?.success) throw new Error(data?.message || '刷新失败');
    await loadContacts();
  } catch (e) {
    alert(`刷新失败: ${e?.message || '未知错误'}`);
  }
}

async function refreshMessagesCache() {
  try {
    const data = await wechatApi.refreshMessagesCache();
    if (!data?.success) throw new Error(data?.message || '刷新失败');
    alert(data.message || '聊天记录缓存已刷新');
  } catch (e) {
    alert(`刷新失败: ${e?.message || '未知错误'}`);
  }
}

async function searchContacts() {
  if (!searchKeyword.value) {
    searchResults.value = [];
    return;
  }
  try {
    const data = await wechatApi.searchContacts(searchKeyword.value);
    if (!data?.success) throw new Error(data?.message || '搜索失败');
    searchResults.value = Array.isArray(data.results) ? data.results : [];
  } catch (e) {
    searchResults.value = [];
    alert(`搜索失败: ${e?.message || '未知错误'}`);
  }
}

async function addToStar(item) {
  try {
    const data = await wechatApi.addContact({
      contact_name: item.display_name || item.nick_name || item.username,
      remark: item.remark || '',
      wechat_id: item.username || '',
      contact_type: 'contact',
      is_starred: true
    });
    if (!data?.success) throw new Error(data?.message || '添加失败');
    item.already_starred = true;
    await loadContacts();
  } catch (e) {
    alert(`添加星标失败: ${e?.message || '未知错误'}`);
  }
}

async function unstarAll() {
  if (!confirm('确定要解除全部星标吗？')) return;
  try {
    const data = await wechatApi.unstarAllContacts();
    if (!data?.success) throw new Error(data?.message || '操作失败');
    await loadContacts();
  } catch (e) {
    alert(`操作失败: ${e?.message || '未知错误'}`);
  }
}

async function showContext(contact) {
  try {
    const data = await wechatApi.getStarredContactContext(contact.id);
    if (!data?.success) throw new Error(data?.message || '加载失败');
    chatMessages.value = Array.isArray(data.messages) ? data.messages : [];
    chatTitle.value = `与 ${contact.contact_name || '联系人'} 的聊天记录`;
    showChatModal.value = true;
  } catch (e) {
    alert(`加载失败: ${e?.message || '未知错误'}`);
  }
}

async function refreshContactMessages(contactId) {
  try {
    const data = await wechatApi.refreshContactMessages(contactId);
    if (!data?.success) throw new Error(data?.message || '刷新失败');
    alert(data.message || '刷新成功');
  } catch (e) {
    alert(`刷新失败: ${e?.message || '未知错误'}`);
  }
}

function startEdit(contact) {
  editId.value = contact.id;
  editForm.value = {
    contact_name: contact.contact_name || '',
    remark: contact.remark || '',
    wechat_id: contact.wechat_id || '',
    contact_type: contact.contact_type || 'contact'
  };
  showEditModal.value = true;
}

async function saveEdit() {
  if (!editId.value) return;
  try {
    const data = await wechatApi.updateStarredContact(editId.value, editForm.value);
    if (!data?.success) throw new Error(data?.message || '保存失败');
    showEditModal.value = false;
    await loadContacts();
  } catch (e) {
    alert(`保存失败: ${e?.message || '未知错误'}`);
  }
}

async function deleteContact(contactId) {
  if (!confirm('确定要删除该联系人吗？')) return;
  try {
    const data = await wechatApi.deleteStarredContact(contactId);
    if (!data?.success) throw new Error(data?.message || '删除失败');
    await loadContacts();
  } catch (e) {
    alert(`删除失败: ${e?.message || '未知错误'}`);
  }
}

onMounted(() => {
  loadContacts();
});
</script>
