export const STAR_REFRESH_STORAGE_KEY = 'xcagi_auto_refresh_starred_wechat'
export const PRO_INTENT_STORAGE_KEY = 'xcagi_pro_intent_experience'

export function isStarredChatAutoRefreshOn(): boolean {
  try {
    return localStorage.getItem(STAR_REFRESH_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function isProIntentExperienceOn(): boolean {
  try {
    return localStorage.getItem(PRO_INTENT_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function formatWorkflowHintTime(ts: number): string {
  try {
    return new Date(ts).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export function formatWorkflowClock(ts: number): string {
  try {
    return new Date(ts).toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return ''
  }
}
