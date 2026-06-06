/**
 * Service Worker 注册与管理模块
 * 
 * 功能：
 * - 自动注册/更新Service Worker
 * - 离线状态检测
 * - 缓存管理
 * - 与Service Worker通信
 */

export interface SWStatus {
  supported: boolean;
  registered: boolean;
  controller: boolean;
  offline: boolean;
  lastUpdate: number | null;
}

type SWEventListener = (status: SWStatus) => void;

function shouldSkipServiceWorkerRegistration(): boolean {
  if (import.meta.env.DEV) return true;
  if (typeof window === 'undefined') return false;
  const host = window.location.hostname;
  if (host === '127.0.0.1' || host === 'localhost') return true;
  const port = window.location.port;
  if (port === '5000' || port === '5001') return true;
  return false;
}

/** 开发/本机端口不注册 SW；若此前访问过生产环境，需注销残留 controller。 */
export async function unregisterStaleServiceWorkers(): Promise<void> {
  if (!('serviceWorker' in navigator)) return;
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((reg) => reg.unregister()));
  } catch (error) {
    console.warn('[SW Manager] Failed to unregister stale workers:', error);
  }
}

class ServiceWorkerManager {
  private _registration: ServiceWorkerRegistration | null = null;
  private _status: SWStatus = {
    supported: 'serviceWorker' in navigator,
    registered: false,
    controller: !!navigator.serviceWorker?.controller,
    offline: !navigator.onLine,
    lastUpdate: null,
  };
  private _listeners: Set<SWEventListener> = new Set();
  private _updateInterval: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this._initEventListeners();
  }

  get status(): SWStatus {
    return { ...this._status };
  }

  /**
   * 注册Service Worker
   */
  async register(): Promise<boolean> {
    if (!this._status.supported) {
      console.warn('[SW Manager] Service Worker not supported');
      return false;
    }

    // 开发 / 本机直连后端打包页：不注册 SW，避免 sw.js 与 HMR、SPA 兜底冲突
    if (shouldSkipServiceWorkerRegistration()) {
      await unregisterStaleServiceWorkers();
      return false;
    }

    try {
      // 取消之前的定时器（如果存在）
      this._stopUpdateChecker();

      console.log('[SW Manager] Registering Service Worker...');
      this._registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/',
        updateViaCache: 'all',
      });

      this._status.registered = true;
      this._status.lastUpdate = Date.now();

      // 监听更新
      this._registration.addEventListener('updatefound', () => {
        const newWorker = this._registration!.installing;
        
        newWorker?.addEventListener('statechange', () => {
          if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
            console.log('[SW Manager] New version available, refresh to activate');
            this._notifyListeners();
          }
        });
      });

      // 启动定期检查更新（每小时）
      this._startUpdateChecker();

      this._notifyListeners();
      
      console.log('[SW Manager] Service Worker registered successfully');
      return true;
    } catch (error) {
      console.error('[SW Manager] Registration failed:', error);
      return false;
    }
  }

  /**
   * 检查是否有新版本可用
   */
  async checkForUpdate(): Promise<boolean> {
    if (!this._registration) return false;

    try {
      await this._registration.update();
      return true;
    } catch (error) {
      console.warn('[SW Manager] Update check failed:', error);
      return false;
    }
  }

  /**
   * 激活新的Service Worker（需要刷新页面）
   */
  async activateUpdate(): Promise<void> {
    const controller = navigator.serviceWorker?.controller;
    if (!this._status.controller || !controller) return;

    // 发送消息让SW跳过等待
    controller.postMessage({ type: 'SKIP_WAITING' });
    
    // 监听controllerchange事件
    await new Promise<void>((resolve) => {
      navigator.serviceWorker.addEventListener('controllerchange', () => resolve(), { once: true });
    });

    window.location.reload();
  }

  /**
   * 清除所有缓存
   */
  async clearCache(): Promise<boolean> {
    const controller = navigator.serviceWorker?.controller;
    if (!this._status.supported || !controller) return false;

    return new Promise((resolve) => {
      const channel = new MessageChannel();

      channel.port1.onmessage = (event) => {
        if (event.data.type === 'CACHE_CLEARED') {
          console.log('[SW Manager] Cache cleared successfully');
          resolve(true);
        } else {
          resolve(false);
        }
      };

      controller.postMessage(
        { type: 'CLEAR_CACHE' },
        [channel.port2]
      );

      setTimeout(() => resolve(false), 5000); // 5秒超时
    });
  }

  /**
   * 获取缓存状态信息
   */
  async getCacheStatus(): Promise<object | null> {
    const controller = navigator.serviceWorker?.controller;
    if (!this._status.supported || !controller) return null;

    return new Promise((resolve) => {
      const channel = new MessageChannel();

      channel.port1.onmessage = (event) => {
        if (event.data.type === 'STATUS') {
          resolve(event.data);
        } else {
          resolve(null);
        }
      };

      controller.postMessage(
        { type: 'GET_STATUS' },
        [channel.port2]
      );

      setTimeout(() => resolve(null), 3000); // 3秒超时
    });
  }

  /**
   * 状态变化监听
   */
  onChange(listener: SWEventListener): () => void {
    this._listeners.add(listener);
    
    // 返回取消订阅函数
    return () => {
      this._listeners.delete(listener);
    };
  }

  /**
   * 获取当前离线状态
   */
  isOffline(): boolean {
    return this._status.offline;
  }

  /**
   * 销毁管理器
   */
  destroy(): void {
    this._stopUpdateChecker();
    this._listeners.clear();
  }

  private _notifyListeners(): void {
    this._listeners.forEach(listener => {
      try {
        listener(this.status);
      } catch (e) {
        console.error('[SW Manager] Listener error:', e);
      }
    });
  }

  private _initEventListeners(): void {
    // 在线/离线状态监听
    window.addEventListener('online', () => {
      this._status.offline = false;
      console.log('[SW Manager] Back online');
      this._notifyListeners();
    });

    window.addEventListener('offline', () => {
      this._status.offline = true;
      console.log('[SW Manager] Went offline');
      this._notifyListeners();
    });

    // Service Worker controller 变化
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        this._status.controller = true;
        console.log('[SW Manager] New controller activated');
        this._notifyListeners();
      });
    }
  }

  private _startUpdateChecker(): void {
    this._stopUpdateChecker();
    
    // 每小时检查一次更新
    this._updateInterval = setInterval(() => {
      this.checkForUpdate().catch(() => {});
    }, 60 * 60 * 1000);
  }

  private _stopUpdateChecker(): void {
    if (this._updateInterval) {
      clearInterval(this._updateInterval);
      this._updateInterval = null;
    }
  }
}

// 全局单例实例
export const swManager = new ServiceWorkerManager();

/**
 * 初始化Service Worker（在应用启动时调用）
 */
export async function initServiceWorker(): Promise<SWStatus> {
  const registered = await swManager.register();
  
  if (registered) {
    console.log('[SW Init] Service Worker initialized successfully');
  } else {
    console.warn('[SW Init] Service Worker initialization skipped or failed');
  }
  
  return swManager.status;
}
