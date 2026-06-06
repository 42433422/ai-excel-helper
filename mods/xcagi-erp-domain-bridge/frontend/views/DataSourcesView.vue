<template>
  <div class="page-view" id="view-data-sources">
    <div class="page-content">
      <div class="page-header">
        <h2>数据来源</h2>
      </div>

      <div class="card">
        <div class="card-header">私人数据库读取助手</div>
        <p class="muted data-source-note">
          这里管理 AI 员工可读取的数据来源。市场展示为通用员工；启用具体适配器前，需要用户在本页明确选择并授权。
        </p>
        <div class="data-source-status">
          <span>员工状态：{{ statusText }}</span>
          <span>当前来源：{{ selectedSourceLabel }}</span>
        </div>
      </div>

      <div class="card">
        <div class="card-header">选择数据来源</div>
        <div v-if="sources.length === 0" class="empty-state">暂无可用数据来源</div>
        <div v-else>
          <template v-for="(group, idx) in groupedSources" :key="idx">
            <h4 class="data-source-group-title">{{ group.label }}</h4>
            <div class="data-source-grid">
              <button
                v-for="source in group.items"
                :key="source.id"
                type="button"
                class="data-source-card"
                :class="{ active: selectedSourceId === source.id, 'is-planned': source.status !== 'available' }"
                @click="selectSource(source.id)"
              >
                <div class="data-source-card-badge" v-if="source.status !== 'available'">规划中</div>
                <div style="display:flex; align-items:center; gap:10px;">
                  <img class="data-source-card-icon" :src="iconUrl(source.icon || source.id)" alt="" />
                  <div>
                    <div class="data-source-card-title">{{ source.label }}</div>
                    <div class="data-source-card-desc">{{ source.description || '无说明' }}</div>
                    <div class="data-source-card-meta">
                      <span>{{ source.status === 'available' ? '可用' : '规划中' }}</span>
                      <span v-if="source.requires_authorization"> · 需要授权</span>
                    </div>
                  </div>
                </div>
              </button>
            </div>
          </template>
        </div>
        <template v-if="!isWechatSourceSelected">
          <div class="form-group data-source-actions">
            <button class="btn btn-primary" type="button" :disabled="loading || isSelectedSourcePlanned" @click="refreshContacts">
              刷新联系人缓存
            </button>
            <button class="btn btn-secondary" type="button" :disabled="loading || isSelectedSourcePlanned" @click="refreshMessages">
              检查消息缓存
            </button>
          </div>
          <div v-if="isSelectedSourcePlanned" class="muted" style="margin-top:8px">该数据源还在规划中，暂时只有微信适配器可执行操作。</div>
        </template>
        <p v-else class="muted data-source-wechat-hint">
          已选中微信本地库：下方可进行星标联系人、搜索、聊天记录与发送相关操作。
        </p>
        <div class="muted" style="margin-top:8px; font-size:12px">图标为本应用自制单色字形，仅用于功能区分，不代表对应品牌的官方授权。</div>
      </div>

      <WechatContactsPanel v-if="isWechatSourceSelected" />

      <div v-if="!isWechatSourceSelected" class="card">
        <div class="card-header">搜索联系人</div>
        <div class="form-group data-source-search">
          <input
            v-model.trim="keyword"
            type="text"
            placeholder="输入联系人名称、备注或本地账号标识"
            @keydown.enter.prevent="searchContacts"
          />
          <button class="btn btn-primary" type="button" :disabled="loading || !keyword" @click="searchContacts">
            搜索
          </button>
        </div>
        <div v-if="contacts.length === 0" class="empty-state">暂无搜索结果</div>
        <div v-else class="data-source-results">
          <div v-for="contact in contacts" :key="`${contact.id || 'raw'}-${contact.source_user_id}`" class="data-source-result">
            <div>
              <strong>{{ contact.display_name || contact.contact_name || '-' }}</strong>
              <div class="muted">标识：{{ contact.source_user_id || '-' }} · 类型：{{ contact.contact_type === 'group' ? '群聊' : '联系人' }}</div>
            </div>
            <div class="data-source-result-actions">
              <button
                class="btn btn-secondary btn-sm"
                type="button"
                :disabled="!contact.id"
                @click="showContext(contact)"
              >
                查看上下文
              </button>
              <button class="btn btn-primary btn-sm" type="button" @click="prepareSend(contact)">发送消息</button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!isWechatSourceSelected" class="card">
        <div class="card-header">发送消息辅助</div>
        <div class="form-group">
          <label>联系人</label>
          <input v-model.trim="sendForm.contactName" type="text" placeholder="选择搜索结果或手动输入联系人名称" />
        </div>
        <div class="form-group">
          <label>消息内容</label>
          <textarea v-model.trim="sendForm.message" rows="4" placeholder="发送前请确认内容，员工只在你点击发送后执行"></textarea>
        </div>
        <button class="btn btn-primary" type="button" :disabled="loading || !sendForm.contactName || !sendForm.message" @click="sendMessage">
          确认发送
        </button>
      </div>

      <div class="modal" :class="{ active: contextModalOpen }">
        <div class="modal-content data-source-modal">
          <div class="modal-header">{{ contextTitle }}</div>
          <div class="data-source-context">
            <div v-if="contextMessages.length === 0" class="empty-state">暂无上下文</div>
            <div v-for="(msg, idx) in contextMessages" :key="idx" class="data-source-message">
              <div class="muted">{{ msg.role === 'self' ? '我' : '对方' }}</div>
              <div>{{ msg.text || msg.content || '' }}</div>
            </div>
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" type="button" @click="contextModalOpen = false">关闭</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import privateDbAssistantApi, { type PrivateDbContact, type PrivateDbSource } from '@/api/privateDbAssistant';
import { appAlert } from '@/utils/appDialog';
import WechatContactsPanel from './WechatContactsPanel.vue';

const WECHAT_SOURCE_ID = 'wechat_local_db';

const STORAGE_KEY = 'xcagi_private_db_assistant_source';

// Static catalog — augments the backend response. The backend is the authority for
// "available" status and actual operations; this catalog provides the full set of
// planned entries with categories and icons so the UI renders correctly even before
// a backend restart picks up source_catalog.py.
const STATIC_CATALOG: PrivateDbSource[] = [
  { id: 'local_message_db', label: '本地消息数据库', category: 'generic', icon: 'local_message_db', description: '通用 SQLite/SQLCipher 消息库适配器。需要用户提供数据库路径与访问凭据。', status: 'planned', requires_authorization: true },
  { id: 'wechat_local_db', label: '微信本地数据库适配器', category: 'im', icon: 'wechat', description: '读取已授权、已解密的本地联系人与消息缓存；含星标联系人、搜索、聊天记录与桌面发送通道。', status: 'planned', requires_authorization: true },
  { id: 'qq_local_db', label: 'QQ 本地数据库', category: 'im', icon: 'qq', description: 'QQ 本地消息与联系人读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'dingtalk_local_db', label: '钉钉本地数据库', category: 'im', icon: 'dingtalk', description: '钉钉本地消息与联系人读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'wework_local_db', label: '企业微信本地数据库', category: 'im', icon: 'wework', description: '企业微信本地消息与联系人读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'feishu_local_db', label: '飞书本地数据库', category: 'im', icon: 'feishu', description: '飞书本地消息读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'telegram_local_db', label: 'Telegram 本地数据库', category: 'im', icon: 'telegram', description: 'Telegram 本地消息读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'whatsapp_local_db', label: 'WhatsApp 本地数据库', category: 'im', icon: 'whatsapp', description: 'WhatsApp 本地消息读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'skype_local_db', label: 'Skype 本地数据库', category: 'im', icon: 'skype', description: 'Skype 本地消息读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'outlook_local_db', label: 'Outlook 本地邮箱', category: 'mail', icon: 'outlook', description: 'Outlook 本地邮箱读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'foxmail_local_db', label: 'Foxmail 本地邮箱', category: 'mail', icon: 'foxmail', description: 'Foxmail 本地邮箱读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'netease_mailmaster_local_db', label: '网易邮箱大师', category: 'mail', icon: 'netease_mailmaster', description: '网易邮箱大师读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'yongyou_local_db', label: '用友本地数据', category: 'erp', icon: 'yongyou', description: '用友本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'kingdee_local_db', label: '金蝶本地数据', category: 'erp', icon: 'kingdee', description: '金蝶本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'guanjiapo_local_db', label: '管家婆本地数据', category: 'erp', icon: 'guanjiapo', description: '管家婆本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'sap_local_db', label: 'SAP 本地数据', category: 'erp', icon: 'sap', description: 'SAP 本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'suda_local_db', label: '速达本地数据', category: 'erp', icon: 'suda', description: '速达本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'langchao_local_db', label: '浪潮本地数据', category: 'erp', icon: 'langchao', description: '浪潮本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'notion_local_db', label: 'Notion 本地数据', category: 'office', icon: 'notion', description: 'Notion 本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'onenote_local_db', label: 'OneNote 本地数据', category: 'office', icon: 'onenote', description: 'OneNote 本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'evernote_local_db', label: '印象笔记 / Evernote', category: 'office', icon: 'evernote', description: '印象笔记本地数据读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'wps_local_db', label: 'WPS 本地数据', category: 'office', icon: 'wps', description: 'WPS 本地文档读取（规划中）', status: 'planned', requires_authorization: true },
  { id: 'qianniu_local_db', label: '千牛(淘宝) 本地数据', category: 'ecommerce', icon: 'qianniu', description: '千牛本地客服数据（规划中）', status: 'planned', requires_authorization: true },
  { id: 'jingmai_local_db', label: '京麦(京东) 本地数据', category: 'ecommerce', icon: 'jingmai', description: '京麦本地客服数据（规划中）', status: 'planned', requires_authorization: true },
  { id: 'pdd_merchant_local_db', label: '拼多多商家', category: 'ecommerce', icon: 'pdd_merchant', description: '拼多多本地客服数据（规划中）', status: 'planned', requires_authorization: true },
];

const loading = ref(false);
const statusText = ref('未连接');
const sources = ref<PrivateDbSource[]>([]);
const route = useRoute();
const selectedSourceId = ref(localStorage.getItem(STORAGE_KEY) || WECHAT_SOURCE_ID);
const keyword = ref('');
const contacts = ref<PrivateDbContact[]>([]);
const contextModalOpen = ref(false);
const contextTitle = ref('上下文');
const contextMessages = ref<any[]>([]);
const sendForm = reactive({
  contactName: '',
  message: '',
});

const selectedSourceLabel = computed(() => {
  const row = sources.value.find((s) => s.id === selectedSourceId.value);
  return row?.label || selectedSourceId.value || '未选择';
});

const groupedSources = computed(() => {
  const order = ["generic", "im", "mail", "erp", "office", "ecommerce"];
  const labels: Record<string, string> = {
    generic: "通用",
    im: "即时通讯",
    mail: "邮件",
    erp: "ERP · 财务",
    office: "办公 · 协作",
    ecommerce: "电商客服",
  };
  const groups: { label: string; items: any[] }[] = [];
  for (const cat of order) {
    const items = sources.value.filter((s) => (s.category || "generic") === cat);
    if (items.length) groups.push({ label: labels[cat], items });
  }
  return groups;
});

function iconUrl(name: string) {
  return `/data-sources/icons/${name}.svg`;
}

const isSelectedSourcePlanned = computed(() => {
  const row = sources.value.find((s) => s.id === selectedSourceId.value);
  return !row || row.status !== 'available';
});

const isWechatSourceSelected = computed(() => selectedSourceId.value === WECHAT_SOURCE_ID);

function applyRouteSourceHint() {
  const src = String(route.query.source || '').trim();
  if (!src) return;
  selectedSourceId.value = src;
  localStorage.setItem(STORAGE_KEY, src);
}

watch(() => route.query.source, applyRouteSourceHint);

async function loadStatus() {
  try {
    const [status, sourceResp] = await Promise.all([
      privateDbAssistantApi.status(),
      privateDbAssistantApi.listSources(),
    ]);
    statusText.value = status?.success ? '已就绪' : '不可用';
    const backendMap = new Map<string, PrivateDbSource>(
      (Array.isArray(sourceResp.data) ? sourceResp.data : []).map((s: PrivateDbSource) => [s.id, s])
    );
    // Merge: backend is authoritative for status/capabilities; static catalog fills in
    // category, icon, and the full set of planned entries the backend may not yet serve.
    sources.value = STATIC_CATALOG.map((entry) => {
      const live = backendMap.get(entry.id);
      return live ? { ...entry, ...live, icon: entry.icon, category: entry.category } : entry;
    });
  } catch (e: any) {
    statusText.value = '不可用';
    // On error, fall back to static catalog (all planned)
    sources.value = STATIC_CATALOG;
  }
}

async function selectSource(sourceId: string) {
  selectedSourceId.value = sourceId;
  localStorage.setItem(STORAGE_KEY, sourceId);
  // 同时持久化到服务端偏好（fallback to localStorage if server unavailable）
  try {
    const { api } = await import('@/api');
    await api.post('/api/preferences', {
      user_id: 'default',
      key: 'privateDbAssistantSource',
      value: sourceId,
    });
  } catch {
    // 非致命：服务端不可用时仅本地保存
  }
}

async function refreshContacts() {
  loading.value = true;
  try {
    const resp = await privateDbAssistantApi.refreshSource(selectedSourceId.value, 'contacts');
    if (!resp?.success) throw new Error(resp?.message || '刷新失败');
    await appAlert(resp.message || '联系人缓存已刷新');
  } catch (e: any) {
    await appAlert(`刷新失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function refreshMessages() {
  loading.value = true;
  try {
    const resp = await privateDbAssistantApi.refreshSource(selectedSourceId.value, 'messages');
    if (!resp?.success) throw new Error(resp?.message || '检查失败');
    await appAlert(resp.message || '消息缓存已检查');
  } catch (e: any) {
    await appAlert(`检查失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function searchContacts() {
  if (!keyword.value) return;
  loading.value = true;
  try {
    const resp = await privateDbAssistantApi.searchContacts(selectedSourceId.value, keyword.value);
    if (!resp?.success) throw new Error(resp?.message || '搜索失败');
    contacts.value = Array.isArray(resp.data) ? resp.data : [];
  } catch (e: any) {
    contacts.value = [];
    await appAlert(`搜索失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

async function showContext(contact: PrivateDbContact) {
  if (!contact.id) return;
  loading.value = true;
  try {
    const resp = await privateDbAssistantApi.getContext(selectedSourceId.value, contact.id);
    if (!resp?.success) throw new Error(resp?.message || '读取失败');
    contextMessages.value = Array.isArray(resp.data) ? resp.data : [];
    contextTitle.value = `${contact.display_name || contact.contact_name || '联系人'} · 上下文`;
    contextModalOpen.value = true;
  } catch (e: any) {
    await appAlert(`读取上下文失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

function prepareSend(contact: PrivateDbContact) {
  sendForm.contactName = contact.display_name || contact.contact_name || contact.source_user_id || '';
}

async function sendMessage() {
  loading.value = true;
  try {
    const resp = await privateDbAssistantApi.sendMessage(selectedSourceId.value, sendForm.contactName, sendForm.message);
    if (!resp?.success) throw new Error(resp?.message || '发送失败');
    await appAlert(resp.message || '消息已发送');
    sendForm.message = '';
  } catch (e: any) {
    await appAlert(`发送失败: ${e?.message || '未知错误'}`);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  applyRouteSourceHint();
  // 优先从服务端偏好恢复（覆盖 localStorage 初始值）
  try {
    const { api } = await import('@/api');
    const resp = await api.get('/api/preferences', { user_id: 'default' });
    const saved = resp?.preferences?.privateDbAssistantSource;
    if (saved) {
      selectedSourceId.value = saved;
      localStorage.setItem(STORAGE_KEY, saved);
    }
  } catch { /* 静默降级到 localStorage */ }
  loadStatus();
});
</script>

<style scoped>
.data-source-note {
  margin: 0 0 12px;
  font-size: 13px;
}

.data-source-status,
.data-source-card-meta,
.data-source-result,
.data-source-result-actions,
.data-source-actions,
.data-source-search {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.data-source-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
}

.data-source-card {
  text-align: left;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  background: #fff;
  cursor: pointer;
}

.data-source-card.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.data-source-card-title {
  font-weight: 700;
  margin-bottom: 6px;
}

.data-source-card-desc {
  color: #555;
  font-size: 13px;
  min-height: 38px;
}

.data-source-card-meta {
  margin-top: 10px;
  color: #666;
  font-size: 12px;
}

.data-source-actions {
  margin-top: 12px;
}

.data-source-search input {
  max-width: 420px;
}

.data-source-results {
  display: grid;
  gap: 10px;
}

.data-source-result {
  justify-content: space-between;
  padding: 12px;
  border: 1px solid #edf0f5;
  border-radius: 8px;
  background: #fafafa;
}

.data-source-modal {
  max-width: 780px;
  width: calc(100vw - 32px);
}

.data-source-context {
  max-height: 50vh;
  overflow: auto;
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
}

.data-source-message {
  margin-bottom: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #fff;
  white-space: pre-wrap;
  word-break: break-word;
}

.data-source-group-title {
  margin: 14px 0 6px;
  font-size: 12px;
  color: #6b7280;
  letter-spacing: .5px;
  text-transform: uppercase;
  font-weight: 600;
}

.data-source-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.data-source-card-icon {
  width: 32px;
  height: 32px;
  opacity: .8;
  flex-shrink: 0;
}

.data-source-card.is-planned {
  opacity: .7;
}

.data-source-card-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #6b7280;
}

.data-source-card.active .data-source-card-badge {
  background: #e0e7ff;
  color: #3730a3;
}

.data-source-wechat-hint {
  margin: 8px 0 0;
  font-size: 13px;
}
</style>
