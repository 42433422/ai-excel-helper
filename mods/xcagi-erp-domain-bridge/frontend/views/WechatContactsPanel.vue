<template>
  <div class="wechat-contacts-panel" data-tutorial-id="wechat-contacts-panel">
    <div class="card" data-tutorial-id="wechat-search-star">
      <div class="card-header">搜索并星标</div>
      <p class="muted wechat-contacts-panel-note">
        先刷新联系人缓存与聊天记录缓存（从解密库导入一次），之后搜索与查看聊天记录只读本地缓存。
      </p>
      <div class="form-group wechat-contacts-panel-toolbar">
        <button type="button" class="btn btn-primary" @click="refreshContactCache" :disabled="loading">刷新联系人缓存</button>
        <button type="button" class="btn btn-primary" @click="refreshMessagesCache" :disabled="loading">刷新聊天记录缓存</button>
        <input
          type="text"
          v-model.trim="searchKeyword"
          placeholder="输入昵称/备注/微信号搜索"
          class="wechat-contacts-panel-search"
          @keydown.enter.prevent="searchContacts"
        >
        <button type="button" class="btn btn-primary" @click="searchContacts" :disabled="loading">搜索</button>
      </div>
      <div class="wechat-contacts-panel-search-results">
        <div v-if="searchResults.length === 0" class="empty-state">暂无搜索结果</div>
        <div v-for="item in searchResults" :key="item.username" class="wechat-contact-form-item wechat-contacts-panel-result">
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
          <div class="wechat-contact-row wechat-contacts-panel-star-action">
            <button v-if="!item.already_starred" class="btn btn-primary btn-sm" @click="addToStar(item)">
              <i class="fa fa-star" aria-hidden="true"></i> 添加星标
            </button>
            <span v-else class="muted">已是星标联系人</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card" data-tutorial-id="wechat-starred-list">
      <div class="card-header">星标联系人列表</div>
      <div class="form-group wechat-contacts-panel-toolbar">
        <label class="wechat-contacts-panel-type-label">类型：</label>
        <select v-model="contactType" class="wechat-contacts-panel-type" @change="loadContacts">
          <option value="all">全部</option>
          <option value="contact">联系人</option>
          <option value="group">群聊</option>
        </select>
        <input type="text" v-model.trim="localFilter" placeholder="在星标列表中筛选" class="wechat-contacts-panel-search">
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
      <div class="modal-content wechat-contacts-panel-chat-modal">
        <div class="modal-header">{{ chatTitle }}</div>
        <div class="wechat-contacts-panel-chat-body">
          <div v-if="chatMessages.length === 0" class="empty-state">暂无聊天记录</div>
          <div
            v-for="(msg, idx) in chatMessages"
            :key="idx"
            class="wechat-chat-msg"
          >
            <div class="muted wechat-contacts-panel-chat-role">{{ msg.role === 'self' ? '我' : '对方' }}</div>
            <div class="wechat-contacts-panel-chat-text">{{ msg.text || '' }}</div>
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
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import wechatApi from '@/api/wechat';
import { appAlert, appConfirm } from '@/utils/appDialog';

const loading = ref(false);
const contacts = ref<any[]>([]);
const contactType = ref('all');
const localFilter = ref('');
const searchKeyword = ref('');
const searchResults = ref<any[]>([]);
const AUTO_REFRESH_STARRED_WECHAT_KEY = 'xcagi_auto_refresh_starred_wechat';
const AUTO_REFRESH_INTERVAL_MS = 60 * 1000;
const autoRefreshRunning = ref(false);
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null;

const showChatModal = ref(false);
const chatTitle = ref('聊天记录');
const chatMessages = ref<any[]>([]);

const showEditModal = ref(false);
const editId = ref<number | null>(null);
const editForm = ref({
  contact_name: '',
  remark: '',
  wechat_id: '',
  contact_type: 'contact',
});

const filteredContacts = computed(() => {
  const q = localFilter.value.toLowerCase();
  if (!q) return contacts.value;
  return contacts.value.filter((c) => {
    return [c.contact_name || '', c.remark || '', c.wechat_id || '']
      .join(' ')
      .toLowerCase()
      .includes(q);
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
  } catch (e: any) {
    await appAlert(`刷新失败: ${e?.message || '未知错误'}`);
  }
}

async function refreshMessagesCache() {
  try {
    const data = await wechatApi.refreshMessagesCache();
    if (!data?.success) throw new Error(data?.message || '刷新失败');
    await appAlert(data.message || '聊天记录缓存已刷新');
  } catch (e: any) {
    await appAlert(`刷新失败: ${e?.message || '未知错误'}`);
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
  } catch (e: any) {
    searchResults.value = [];
    await appAlert(`搜索失败: ${e?.message || '未知错误'}`);
  }
}

async function addToStar(item: any) {
  try {
    const data = await wechatApi.addStarredContact({
      contact_name: item.display_name || item.nick_name || item.username,
      remark: item.remark || '',
      wechat_id: item.username || '',
      contact_type: item.contact_type === 'group' ? 'group' : 'contact',
      is_starred: true,
    });
    if (!data?.success) throw new Error(data?.message || '添加失败');
    item.already_starred = true;
    await loadContacts();
  } catch (e: any) {
    await appAlert(`添加星标失败: ${e?.message || '未知错误'}`);
  }
}

async function unstarAll() {
  if (!(await appConfirm('确定要解除全部星标吗？'))) return;
  try {
    const data = await wechatApi.unstarAllContacts();
    if (!data?.success) throw new Error(data?.message || '操作失败');
    await loadContacts();
  } catch (e: any) {
    await appAlert(`操作失败: ${e?.message || '未知错误'}`);
  }
}

async function showContext(contact: any) {
  try {
    const data = await wechatApi.getStarredContactContext(contact.id);
    if (!data?.success) throw new Error(data?.message || '加载失败');
    chatMessages.value = Array.isArray(data.messages) ? data.messages : [];
    chatTitle.value = `与 ${contact.contact_name || '联系人'} 的聊天记录`;
    showChatModal.value = true;
  } catch (e: any) {
    await appAlert(`加载失败: ${e?.message || '未知错误'}`);
  }
}

async function refreshContactMessages(contactId: number) {
  try {
    const data = await wechatApi.refreshContactMessages(contactId);
    if (!data?.success) throw new Error(data?.message || '刷新失败');
    await appAlert(data.message || '刷新成功');
  } catch (e: any) {
    await appAlert(`刷新失败: ${e?.message || '未知错误'}`);
  }
}

function isAutoRefreshEnabled() {
  return localStorage.getItem(AUTO_REFRESH_STARRED_WECHAT_KEY) === '1';
}

async function refreshStarredMessagesSilently() {
  if (autoRefreshRunning.value || !isAutoRefreshEnabled()) return;
  const targets = (contacts.value || []).filter((c) => c && c.id).slice(0, 30);
  if (!targets.length) return;

  autoRefreshRunning.value = true;
  try {
    await Promise.allSettled(targets.map((c) => wechatApi.refreshContactMessages(c.id)));
  } catch {
    // 静默失败
  } finally {
    autoRefreshRunning.value = false;
  }
}

function stopAutoRefreshTimer() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

function startAutoRefreshTimer() {
  stopAutoRefreshTimer();
  if (!isAutoRefreshEnabled()) return;
  autoRefreshTimer = setInterval(() => {
    refreshStarredMessagesSilently();
  }, AUTO_REFRESH_INTERVAL_MS);
}

function onAutoRefreshWechatChanged() {
  startAutoRefreshTimer();
  if (isAutoRefreshEnabled()) {
    refreshStarredMessagesSilently();
  }
}

function startEdit(contact: any) {
  editId.value = contact.id;
  editForm.value = {
    contact_name: contact.contact_name || '',
    remark: contact.remark || '',
    wechat_id: contact.wechat_id || '',
    contact_type: contact.contact_type || 'contact',
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
  } catch (e: any) {
    await appAlert(`保存失败: ${e?.message || '未知错误'}`);
  }
}

async function deleteContact(contactId: number) {
  if (!(await appConfirm('确定要删除该联系人吗？'))) return;
  try {
    const data = await wechatApi.deleteStarredContact(contactId);
    if (!data?.success) throw new Error(data?.message || '删除失败');
    await loadContacts();
  } catch (e: any) {
    await appAlert(`删除失败: ${e?.message || '未知错误'}`);
  }
}

onMounted(() => {
  loadContacts();
  startAutoRefreshTimer();
  window.addEventListener('xcagi:auto-refresh-wechat-changed', onAutoRefreshWechatChanged);
});

onBeforeUnmount(() => {
  stopAutoRefreshTimer();
  window.removeEventListener('xcagi:auto-refresh-wechat-changed', onAutoRefreshWechatChanged);
});
</script>

<style scoped>
.wechat-contacts-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.wechat-contacts-panel-note {
  margin: 0 0 10px;
  font-size: 13px;
}

.wechat-contacts-panel-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.wechat-contacts-panel-search {
  max-width: 320px;
}

.wechat-contacts-panel-type-label {
  margin: 0;
  white-space: nowrap;
}

.wechat-contacts-panel-type {
  width: 120px;
}

.wechat-contacts-panel-search-results {
  margin-top: 10px;
  min-height: 0;
  max-height: 240px;
  overflow-y: auto;
}

.wechat-contacts-panel-result {
  margin-bottom: 8px;
}

.wechat-contacts-panel-star-action {
  margin-top: 6px;
}

.wechat-contacts-panel-chat-modal {
  max-width: 780px;
  width: calc(100vw - 32px);
  display: flex;
  flex-direction: column;
  max-height: 80vh;
}

.wechat-contacts-panel-chat-body {
  flex: 1;
  overflow-y: auto;
  min-height: 200px;
  max-height: 50vh;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 13px;
}

.wechat-contacts-panel-chat-role {
  font-size: 11px;
  margin-bottom: 4px;
}

.wechat-contacts-panel-chat-text {
  word-break: break-word;
  white-space: pre-wrap;
}

.wechat-chat-msg {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
}
</style>
