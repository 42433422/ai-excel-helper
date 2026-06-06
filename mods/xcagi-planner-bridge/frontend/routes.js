/**
 * 里程碑 K / O+ / P：主对话 + 智能生态 / 智脑 — 物理视图在 Mod 包内。
 */

import { modView } from '@/router/modViews'

const MOD_ID = 'xcagi-planner-bridge'
const PREFIX = `/mod/${MOD_ID}`

const modRoutes = [
  {
    path: `${PREFIX}/chat`,
    name: 'mod-planner-chat',
    component: modView(MOD_ID, 'ChatView.vue'),
    meta: { title: '智能对话', mod: MOD_ID },
  },
  {
    path: `${PREFIX}/ai-ecosystem`,
    name: 'mod-planner-ai-ecosystem',
    component: modView(MOD_ID, 'AIEcosystemView.vue'),
    meta: { title: '智能生态', mod: MOD_ID },
  },
  {
    path: `${PREFIX}/brain`,
    name: 'mod-planner-brain',
    component: modView(MOD_ID, 'BrainView.vue'),
    meta: { title: '智脑集成', mod: MOD_ID },
  },
  {
    path: `${PREFIX}/chat-debug`,
    name: 'mod-planner-chat-debug',
    component: modView(MOD_ID, 'ChatDebugView.vue'),
    meta: { title: '对话调试', mod: MOD_ID },
  },
]

const modMenu = [
  { id: 'mod-planner-chat', label: '智能对话', icon: 'fa-comments', path: `${PREFIX}/chat` },
  { id: 'mod-planner-ai-ecosystem', label: '智能生态', icon: 'fa-sitemap', path: `${PREFIX}/ai-ecosystem` },
  { id: 'mod-planner-brain', label: '智脑集成', icon: 'fa-brain', path: `${PREFIX}/brain` },
]

export { modRoutes, modMenu }
