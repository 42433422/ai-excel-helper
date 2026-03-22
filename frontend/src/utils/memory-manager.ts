export interface ResourceEntry {
  resource: any;
  type: string;
  createdAt: number;
  lastAccessed: number;
}

export interface ListenerEntry {
  target: EventTarget;
  event: string;
  handler: EventListenerOrEventListenerObject;
  options?: boolean | AddEventListenerOptions;
}

export interface ResourceStats {
  total: number;
  byType: Record<string, number>;
  oldest: string | null;
  newest: string | null;
  listeners: number;
  timers: number;
  observers: number;
}

export class ResourceManager {
  private resources: Map<string, ResourceEntry>;
  private listeners: Map<string, ListenerEntry>;
  private timers: Map<string, number>;
  private observers: MutationObserver[];
  public isDisposed: boolean;

  constructor() {
    this.resources = new Map();
    this.listeners = new Map();
    this.timers = new Map();
    this.observers = [];
    this.isDisposed = false;
  }

  register(id: string, resource: any, type: string = 'generic'): boolean {
    if (this.isDisposed) {
      console.warn(`ResourceManager: Cannot register resource "${id}" - manager is disposed`);
      return false;
    }

    if (this.resources.has(id)) {
      console.warn(`ResourceManager: Resource "${id}" already registered, replacing`);
      this.release(id);
    }

    this.resources.set(id, {
      resource,
      type,
      createdAt: Date.now(),
      lastAccessed: Date.now()
    });

    return true;
  }

  get(id: string): any {
    const entry = this.resources.get(id);
    if (entry) {
      entry.lastAccessed = Date.now();
      return entry.resource;
    }
    return null;
  }

  has(id: string): boolean {
    return this.resources.has(id);
  }

  release(id: string): boolean {
    const entry = this.resources.get(id);
    if (!entry) return false;

    const { resource, type } = entry;

    try {
      if (resource && typeof resource.dispose === 'function') {
        resource.dispose();
      } else if (resource && typeof resource.destroy === 'function') {
        resource.destroy();
      } else if (resource && typeof resource.cleanup === 'function') {
        resource.cleanup();
      } else if (resource instanceof HTMLElement && resource.remove) {
        resource.remove();
      } else if (resource && (resource as any) instanceof EventTarget && (resource as any).removeEventListener) {
        this.removeAllListeners(resource as EventTarget);
      }
    } catch (error) {
      console.error(`ResourceManager: Error releasing resource "${id}":`, error);
    }

    this.resources.delete(id);
    return true;
  }

  releaseByType(type: string): number {
    const toRelease: string[] = [];
    for (const [id, entry] of this.resources) {
      if (entry.type === type) {
        toRelease.push(id);
      }
    }
    toRelease.forEach(id => this.release(id));
    return toRelease.length;
  }

  releaseAll(): number {
    const count = this.resources.size;
    for (const [id] of this.resources) {
      this.release(id);
    }
    this.listeners.clear();
    this.timers.forEach(timer => clearInterval(timer));
    this.timers.clear();
    this.observers.forEach(obs => {
      if (obs.disconnect) obs.disconnect();
    });
    this.observers = [];
    return count;
  }

  dispose(): void {
    this.releaseAll();
    this.isDisposed = true;
  }

  addListener(
    target: EventTarget,
    event: string,
    handler: EventListenerOrEventListenerObject,
    options: boolean | AddEventListenerOptions = {}
  ): string {
    const key = `${target}-${event}-${Date.now()}`;
    target.addEventListener(event, handler, options);
    this.listeners.set(key, { target, event, handler, options });
    return key;
  }

  removeListener(key: string): boolean {
    const listener = this.listeners.get(key);
    if (!listener) return false;

    listener.target.removeEventListener(listener.event, listener.handler, listener.options);
    this.listeners.delete(key);
    return true;
  }

  removeAllListeners(target: EventTarget): void {
    const toRemove: string[] = [];
    for (const [key, listener] of this.listeners) {
      if (listener.target === target) {
        toRemove.push(key);
      }
    }
    toRemove.forEach(key => this.removeListener(key));
  }

  registerTimer(id: string, timer: number): void {
    if (this.timers.has(id)) {
      this.clearTimer(id);
    }
    this.timers.set(id, timer);
  }

  clearTimer(id: string): void {
    const timer = this.timers.get(id);
    if (timer) {
      clearInterval(timer);
      clearTimeout(timer);
      this.timers.delete(id);
    }
  }

  clearAllTimers(): void {
    this.timers.forEach(timer => {
      clearInterval(timer);
      clearTimeout(timer);
    });
    this.timers.clear();
  }

  registerObserver(observer: MutationObserver): void {
    this.observers.push(observer);
  }

  disconnectAllObservers(): void {
    this.observers.forEach(obs => {
      if (obs.disconnect) obs.disconnect();
    });
    this.observers = [];
  }
}

export const globalResourceManager = new ResourceManager();

export function createResourceManager(): ResourceManager {
  return new ResourceManager();
}

export interface CleanupFunctions {
  register: (fn: () => void) => void;
  cleanup: () => void;
}

export function useCleanup(): CleanupFunctions {
  const cleanupFns: (() => void)[] = [];

  const register = (fn: () => void) => {
    if (typeof fn === 'function') {
      cleanupFns.push(fn);
    }
  };

  const cleanup = () => {
    cleanupFns.forEach(fn => {
      try {
        fn();
      } catch (e) {
        console.error('Cleanup error:', e);
      }
    });
    cleanupFns.length = 0;
  };

  return { register, cleanup };
}

export function cleanupCanvas(ctx: CanvasRenderingContext2D | null): void {
  if (!ctx) return;

  const canvas = ctx.canvas;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (canvas.width !== 0) {
    canvas.width = 0;
    canvas.height = 0;
  }
}

export function cleanupAnimationFrame(id: number): void {
  if (id && typeof cancelAnimationFrame === 'function') {
    cancelAnimationFrame(id);
  }
}

export function cleanupInterval(id: number | undefined | null): void {
  if (id) {
    clearInterval(id);
  }
}

export function cleanupTimeout(id: number | undefined | null): void {
  if (id) {
    clearTimeout(id);
  }
}

export function cleanupEventListener(
  target: EventTarget | null,
  event: string | null,
  handler: EventListenerOrEventListenerObject | null
): void {
  if (target && event && handler) {
    target.removeEventListener(event, handler);
  }
}

export function cleanupObject(obj: Record<string, any>): void {
  if (!obj) return;

  for (const key in obj) {
    if (obj[key] && typeof obj[key] === 'object') {
      cleanupObject(obj[key]);
    }
    obj[key] = null;
  }
}
