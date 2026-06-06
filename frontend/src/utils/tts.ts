/**
 * 统一 TTS 入口，支持多种引擎：
 *   - system：浏览器 `speechSynthesis`（零成本，音质取决于操作系统里装的语音包）
 *   - online：经本机后端 `POST /api/tts` 调用 Microsoft Edge TTS（edge-tts），需联网，
 *     默认神经网络音色如 zh-CN-XiaoxiaoNeural；失败时 `speakText` 自动回退 offline/system
 *   - offline：transformers.js + MMS-TTS 中文 ONNX 模型（首次下载约 60MB，
 *     之后通过 Cache API / IndexedDB 离线可用，全平台统一音质）
 *
 * 默认策略（auto）：
 *   - 优先使用 online
 *   - 离线包默认不后台预热，避免受限网络启动时刷屏失败；用户点击下载或显式启用后再缓存
 *   - online 不可用时优先用 offline，最后才回退 system
 */

import { getApiBase } from './apiBase'
import { readCsrfTokenFromCookie, shouldAttachCsrfHeader } from './csrfCookie'
import { playOfflinePcm, synthesizeOffline, ensureOfflineReady, isOfflineReady, isOfflineLoading, getOfflineProgress, stopOffline } from './offlineTts'

const VOICE_PREF_KEY = 'xcagi_tts_voice'
const ENGINE_PREF_KEY = 'xcagi_tts_engine' // 'auto' | 'system' | 'offline' | 'online'
const BANNER_DISMISSED_KEY = 'xcagi_tts_banner_dismissed'
const SPEECH_RATE_KEY = 'xcagi_tts_rate'
const DEFAULT_SPEECH_RATE = 1.15
/** Edge TTS voice id，须匹配后端 ``^[a-z]{2,3}-[A-Z]{2,3}-[A-Za-z]+Neural$``，默认与 ``app/services/tts_service.DEFAULT_EDGE_VOICE`` 一致 */
const ONLINE_VOICE_KEY = 'xcagi_tts_online_voice'
const DEFAULT_ONLINE_VOICE_ID = 'zh-CN-XiaoxiaoNeural'
const AUTO_PRELOAD_OFFLINE_TTS = String(import.meta.env.VITE_PRELOAD_OFFLINE_TTS || '').toLowerCase() === 'true'

export type TtsEngineMode = 'auto' | 'system' | 'offline' | 'online'

let onlineAudioEl: HTMLAudioElement | null = null
let offlineWarmupStarted = false

function stopOnlinePlayback(): void {
  if (!onlineAudioEl) return
  const el = onlineAudioEl
  onlineAudioEl = null
  try {
    el.pause()
    // Setting src to empty releases the media resource without calling load(),
    // which avoids triggering Windows audio-session teardown (and the resulting
    // volume-restore "pop" from OS audio ducking).
    el.src = ''
  } catch {
    /* ignore */
  }
}

const NEURAL_KEYWORDS = [
  'Yunxi', 'Yunyang', 'Yunjian', 'Yunhao', 'Yunxia',
  'Xiaoxiao', 'Xiaoyi', 'Xiaohan', 'Xiaomeng', 'Xiaomo',
  '云希', '云扬', '云健', '云皓', '云夏',
  '晓晓', '晓伊', '晓涵', '晓萌', '晓墨',
]
const CLASSIC_KEYWORDS = ['Huihui', 'Yaoyao', 'Kangkang', '慧慧', '瑶瑶', '康康']

let voicesCache: SpeechSynthesisVoice[] = []
let voicesReady = false
let voicesReadyPromise: Promise<SpeechSynthesisVoice[]> | null = null
let debugExposed = false

type Listener = () => void
const listeners = new Set<Listener>()

function emitChange() {
  for (const fn of listeners) {
    try { fn() } catch { /* ignore */ }
  }
}

export function onTtsStatusChange(cb: Listener): () => void {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

function readPreferredVoiceName(): string {
  try { return String(localStorage.getItem(VOICE_PREF_KEY) || '').trim() } catch { return '' }
}

function writePreferredVoiceName(name: string): void {
  try {
    if (name) localStorage.setItem(VOICE_PREF_KEY, name)
    else localStorage.removeItem(VOICE_PREF_KEY)
  } catch { /* ignore */ }
  emitChange()
}

export function getEngineMode(): TtsEngineMode {
  try {
    const v = String(localStorage.getItem(ENGINE_PREF_KEY) || 'online').toLowerCase()
    if (v === 'system' || v === 'offline' || v === 'online') return v
    return 'online'
  } catch { return 'online' }
}

export function getOnlineVoiceId(): string {
  try {
    const v = String(localStorage.getItem(ONLINE_VOICE_KEY) || '').trim()
    return v || DEFAULT_ONLINE_VOICE_ID
  } catch {
    return DEFAULT_ONLINE_VOICE_ID
  }
}

export function setOnlineVoiceId(id: string): void {
  try {
    const t = String(id || '').trim()
    if (t) localStorage.setItem(ONLINE_VOICE_KEY, t)
    else localStorage.removeItem(ONLINE_VOICE_KEY)
  } catch { /* ignore */ }
  emitChange()
}

export function setEngineMode(mode: TtsEngineMode): void {
  try { localStorage.setItem(ENGINE_PREF_KEY, mode) } catch { /* ignore */ }
  emitChange()
}

export function isBannerDismissed(): boolean {
  try { return localStorage.getItem(BANNER_DISMISSED_KEY) === '1' } catch { return false }
}

export function dismissBanner(): void {
  try { localStorage.setItem(BANNER_DISMISSED_KEY, '1') } catch { /* ignore */ }
  emitChange()
}

export function getSpeechRate(): number {
  try {
    const v = localStorage.getItem(SPEECH_RATE_KEY)
    if (v) {
      const n = parseFloat(v)
      if (!isNaN(n) && n >= 0.5 && n <= 2.0) return n
    }
  } catch { /* ignore */ }
  return DEFAULT_SPEECH_RATE
}

export function setSpeechRate(rate: number): void {
  const clamped = Math.max(0.5, Math.min(2.0, rate))
  try { localStorage.setItem(SPEECH_RATE_KEY, String(clamped)) } catch { /* ignore */ }
  emitChange()
}

const PUNCTUATION_NOISE = /[，。！？；：、""''（）【】《》「」『』·•○●※◆■□…——,.!:;!?~-]+/g
const WHITESPACE_NORMALIZE = /\s+/g
const NEWLINE_NORMALIZE = /[\r\n]+/g

export function cleanTextForSpeech(text: string): string {
  return text
    .replace(PUNCTUATION_NOISE, ' ')
    .replace(NEWLINE_NORMALIZE, ' ')
    .replace(WHITESPACE_NORMALIZE, ' ')
    .trim()
}

function hasSpeechSynthesis(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window
}

function loadVoicesOnce(): Promise<SpeechSynthesisVoice[]> {
  if (!hasSpeechSynthesis()) return Promise.resolve([])
  if (voicesReady) return Promise.resolve(voicesCache)
  if (voicesReadyPromise) return voicesReadyPromise

  voicesReadyPromise = new Promise<SpeechSynthesisVoice[]>((resolve) => {
    const tryResolve = () => {
      const v = window.speechSynthesis.getVoices() || []
      if (v.length > 0) {
        voicesCache = v
        voicesReady = true
        exposeDebugHelpers()
        emitChange()
        resolve(v)
        return true
      }
      return false
    }
    if (tryResolve()) return

    const onChanged = () => {
      if (tryResolve()) {
        try { window.speechSynthesis.removeEventListener('voiceschanged', onChanged) } catch { /* ignore */ }
      }
    }
    try { window.speechSynthesis.addEventListener('voiceschanged', onChanged) } catch { /* ignore */ }

    setTimeout(() => {
      if (!voicesReady) {
        const v = window.speechSynthesis.getVoices() || []
        voicesCache = v
        voicesReady = true
        exposeDebugHelpers()
        emitChange()
        resolve(v)
      }
    }, 2000)
  })

  return voicesReadyPromise
}

function scoreVoice(v: SpeechSynthesisVoice): number {
  const lang = (v.lang || '').toLowerCase()
  const name = v.name || ''
  let score = 0
  if (lang === 'zh-cn' || lang === 'zh_cn') score += 100
  else if (lang === 'zh-sg') score += 70
  else if (lang === 'zh-tw' || lang === 'zh-hk') score += 40
  else if (lang.startsWith('zh')) score += 30
  else return -1

  if ((v as any).localService) score += 50

  // Yunxi 优先级拉满（默认偏好）
  if (/yunxi|云希/i.test(name)) score += 60
  if (NEURAL_KEYWORDS.some((k) => name.toLowerCase().includes(k.toLowerCase()))) score += 25
  if (CLASSIC_KEYWORDS.some((k) => name.toLowerCase().includes(k.toLowerCase()))) score += 10
  if (/natural|neural|online/i.test(name)) score += 10
  if (/^google/i.test(name) && !(v as any).localService) score += 5

  return score
}

export function pickBestChineseVoice(voices?: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const list = voices && voices.length ? voices : voicesCache
  if (!list || !list.length) return null
  const preferred = readPreferredVoiceName()
  if (preferred) {
    const match = list.find((v) => v.name === preferred)
    if (match) return match
  }
  let best: SpeechSynthesisVoice | null = null
  let bestScore = -Infinity
  for (const v of list) {
    const s = scoreVoice(v)
    if (s > bestScore) { bestScore = s; best = v }
  }
  return bestScore > 0 ? best : null
}

export function pickBestChineseVoiceSync(): SpeechSynthesisVoice | null {
  if (!hasSpeechSynthesis()) return null
  if (!voicesReady) {
    void loadVoicesOnce()
    const v = window.speechSynthesis.getVoices() || []
    if (v.length) {
      voicesCache = v
      voicesReady = true
      exposeDebugHelpers()
    }
  }
  return pickBestChineseVoice()
}

export function ensureVoicesLoaded(): Promise<SpeechSynthesisVoice[]> {
  return loadVoicesOnce()
}

export function hasYunxiOrXiaoxiaoAvailable(): boolean {
  const list = voicesCache || []
  return list.some((v) => /yunxi|xiaoxiao|云希|晓晓|natural|neural/i.test(v.name) && (v.lang || '').toLowerCase().startsWith('zh'))
}

export function hasAnyChineseLocalVoice(): boolean {
  const list = voicesCache || []
  return list.some((v) => (v.lang || '').toLowerCase().startsWith('zh') && (v as any).localService === true)
}

export interface TtsStatus {
  engineMode: TtsEngineMode
  effectiveEngine: 'system' | 'offline' | 'online'
  onlineVoiceId: string
  systemVoice: string | null
  yunxiAvailable: boolean
  neuralAvailable: boolean
  anyChineseLocal: boolean
  offlineReady: boolean
  offlineLoading: boolean
  offlineProgress: number
  bannerDismissed: boolean
}

export function getTtsStatus(): TtsStatus {
  const engineMode = getEngineMode()
  const v = pickBestChineseVoiceSync()
  const neural = hasYunxiOrXiaoxiaoAvailable()
  const offlineReadyNow = isOfflineReady()
  const anyLocalZh = hasAnyChineseLocalVoice()
  const onlineVid = getOnlineVoiceId()
  let effective: 'system' | 'offline' | 'online'
  if (engineMode === 'online') effective = 'online'
  else if (engineMode === 'offline') effective = offlineReadyNow ? 'offline' : 'system'
  else if (engineMode === 'system') effective = 'system'
  else {
    effective = offlineReadyNow ? 'offline' : 'online'
  }
  return {
    engineMode,
    effectiveEngine: effective,
    onlineVoiceId: onlineVid,
    systemVoice: v ? `${v.name} (${v.lang})` : null,
    yunxiAvailable: !!v && /yunxi|云希/i.test(v.name),
    neuralAvailable: neural,
    anyChineseLocal: hasAnyChineseLocalVoice(),
    offlineReady: offlineReadyNow,
    offlineLoading: isOfflineLoading(),
    offlineProgress: getOfflineProgress(),
    bannerDismissed: isBannerDismissed(),
  }
}

function configureUtterance(u: SpeechSynthesisUtterance): SpeechSynthesisUtterance {
  u.lang = 'zh-CN'
  u.rate = getSpeechRate()
  u.pitch = 1
  const v = pickBestChineseVoiceSync()
  if (v) {
    u.voice = v
    if (v.lang) u.lang = v.lang
  }
  return u
}

export function createChineseUtterance(text: string): SpeechSynthesisUtterance {
  const u = new SpeechSynthesisUtterance(text)
  return configureUtterance(u)
}

async function fetchOnlineTtsDataUri(text: string): Promise<string> {
  const base = getApiBase().replace(/\/$/, '')
  const voice = getOnlineVoiceId()
  const rate = getSpeechRate()
  const ratePercent = Math.round(rate * 100)
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (shouldAttachCsrfHeader('POST', headers)) {
    const tok = readCsrfTokenFromCookie()
    if (tok) headers['X-CSRF-Token'] = tok
  }
  const res = await fetch(`${base}/api/tts`, {
    method: 'POST',
    headers,
    credentials: 'include',
    body: JSON.stringify({ text, lang: 'zh', voice, rate: `+${ratePercent - 100}%` }),
  })
  let json: any = {}
  try {
    json = await res.json()
  } catch {
    json = {}
  }
  if (!res.ok || !json.success) {
    throw new Error(json.message || `在线 TTS 失败（HTTP ${res.status}）`)
  }
  const uri = json.data?.audioBase64
  if (!uri || typeof uri !== 'string') {
    throw new Error('在线 TTS 响应缺少音频')
  }
  return uri
}

async function playOnlineTts(text: string): Promise<void> {
  stopOnlinePlayback()
  const uri = await fetchOnlineTtsDataUri(text)
  await new Promise<void>((resolve, reject) => {
    const a = new Audio(uri)
    onlineAudioEl = a
    const cleanup = () => {
      if (onlineAudioEl === a) onlineAudioEl = null
    }
    a.onended = () => {
      cleanup()
      resolve()
    }
    a.onerror = () => {
      cleanup()
      reject(new Error('音频播放失败'))
    }
    void a.play().catch((err) => {
      cleanup()
      reject(err)
    })
  })
}

async function speakWithBrowserTts(
  plain: string,
  options?: { onEnd?: () => void; onError?: (e: unknown) => void },
): Promise<void> {
  if (!hasSpeechSynthesis()) {
    options?.onEnd?.()
    return
  }
  await ensureVoicesLoaded()
  return new Promise<void>((resolve) => {
    const u = createChineseUtterance(plain)
    u.onend = () => {
      options?.onEnd?.()
      resolve()
    }
    u.onerror = (e) => {
      options?.onError?.(e)
      resolve()
    }
    window.speechSynthesis.speak(u)
  })
}

/**
 * 高层 API：朗读一段文本，自动按引擎模式分发。
 * 返回 Promise 在播完/出错时 resolve。
 */
export async function speakText(text: string, options?: { onEnd?: () => void; onError?: (e: unknown) => void }): Promise<void> {
  const plain = String(text || '').trim()
  if (!plain) { options?.onEnd?.(); return }

  const status = getTtsStatus()
  if (status.effectiveEngine === 'offline') {
    try {
      const { audio, samplingRate } = await synthesizeOffline(plain)
      await playOfflinePcm(audio, samplingRate)
      options?.onEnd?.()
    } catch (e) {
      options?.onError?.(e)
      options?.onEnd?.()
    }
    return
  }

  if (status.effectiveEngine === 'online') {
    try {
      await playOnlineTts(plain)
      options?.onEnd?.()
    } catch (e) {
      options?.onError?.(e)
      if (isOfflineReady()) {
        try {
          const { audio, samplingRate } = await synthesizeOffline(plain)
          await playOfflinePcm(audio, samplingRate)
          options?.onEnd?.()
          return
        } catch {
          // Fall through to system TTS.
        }
      }
      await speakWithBrowserTts(plain, { onEnd: options?.onEnd })
    }
    return
  }

  await speakWithBrowserTts(plain, options)
}

export function stopSpeaking(): void {
  stopOnlinePlayback()
  // Only cancel speechSynthesis when it is actually active; unconditional cancel
  // releases the Windows "communications" audio session even when idle, which
  // causes other apps' volumes to snap back (OS audio-ducking restore).
  try {
    if (hasSpeechSynthesis() && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
      window.speechSynthesis.cancel()
    }
  } catch { /* ignore */ }
  try { stopOffline() } catch { /* ignore */ }
}

/** 启动离线包下载（包装 offlineTts.ensureOfflineReady，加状态广播）。 */
export async function startOfflineDownload(onProgress?: (p: number) => void): Promise<void> {
  await ensureOfflineReady((p) => {
    onProgress?.(p)
    emitChange()
  })
  emitChange()
}

/** 后台预热离线语音包；失败只记录日志，不打扰聊天界面。 */
export async function preloadOfflineTts(): Promise<void> {
  if (offlineWarmupStarted || isOfflineReady() || isOfflineLoading()) return
  offlineWarmupStarted = true
  try {
    await startOfflineDownload()
  } catch (e) {
    offlineWarmupStarted = false
    console.warn('[tts] offline preload failed:', e)
    emitChange()
  }
}

function exposeDebugHelpers(): void {
  if (debugExposed) return
  if (typeof window === 'undefined') return
  debugExposed = true
  try {
    ;(window as any).__xcagiTts = {
      list(): Array<{ name: string; lang: string; localService: boolean; default: boolean }> {
        return (voicesCache || []).map((v) => ({
          name: v.name,
          lang: v.lang,
          localService: (v as any).localService === true,
          default: (v as any).default === true,
        }))
      },
      current(): string | null {
        const v = pickBestChineseVoice()
        return v ? `${v.name} (${v.lang})` : null
      },
      status(): TtsStatus { return getTtsStatus() },
      preferred(): string { return readPreferredVoiceName() },
      set(name: string): string {
        writePreferredVoiceName(String(name || ''))
        const v = pickBestChineseVoice()
        return v ? `已切换到：${v.name} (${v.lang})` : '未找到指定语音，已保存偏好'
      },
      reset(): string { writePreferredVoiceName(''); const v = pickBestChineseVoice(); return v ? `已重置，自动选用：${v.name} (${v.lang})` : '已重置' },
      setEngine: setEngineMode,
      onlineVoice: getOnlineVoiceId,
      setOnlineVoice: setOnlineVoiceId,
      download: startOfflineDownload,
      getRate: getSpeechRate,
      setRate: setSpeechRate,
      clean: cleanTextForSpeech,
      debug: {
        getStatus: () => getTtsStatus(),
        getEngineMode: getEngineMode,
        isOfflineReady,
        isOfflineLoading,
        getOfflineProgress,
      },
    }
  } catch { /* ignore */ }
}

// 模块加载时预热
if (hasSpeechSynthesis()) {
  void loadVoicesOnce()
}
if (typeof window !== 'undefined' && AUTO_PRELOAD_OFFLINE_TTS) {
  window.setTimeout(() => {
    void preloadOfflineTts()
  }, 1500)
}

