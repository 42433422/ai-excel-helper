/**
 * XCAGI Service Worker（纯 JS，勿写 TypeScript 语法）
 */
const CACHE_NAME = 'xcagi-v6';
const STATIC_CACHE = 'xcagi-static-v3';
const API_CACHE = 'xcagi-api-v2';

const PRECACHE_URLS = ['/', '/index.html'];

const API_PATTERNS = [/\/api\//, /\/api-market/];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then((cache) =>
        cache.addAll(PRECACHE_URLS).catch((err) => {
          console.warn('[SW] Pre-cache failed:', err);
          return undefined;
        }),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME, STATIC_CACHE, API_CACHE];
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) =>
        Promise.all(
          cacheNames.map((cacheName) => {
            if (!cacheWhitelist.includes(cacheName)) {
              return caches.delete(cacheName);
            }
            return undefined;
          }),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;

  // 字体/Range 请求不走缓存逻辑，避免 206 Partial Content 触发 cache.put 异常
  if (shouldBypassCache(request, url)) {
    event.respondWith(fetch(request));
    return;
  }

  if (isAPIRequest(url)) {
    event.respondWith(handleAPIRequest(request));
  } else if (isStaticResource(url)) {
    event.respondWith(handleStaticRequest(request));
  } else {
    event.respondWith(handleGeneralRequest(request));
  }
});

function isAPIRequest(url) {
  return API_PATTERNS.some((pattern) => pattern.test(url.pathname));
}

/** 会话/鉴权类接口禁止写入 API 缓存，避免 502/401 被长期命中。 */
function isNonCacheableApiPath(pathname) {
  const p = String(pathname || '').toLowerCase();
  return (
    p.indexOf('/api/market/session-handoff') !== -1 ||
    p.indexOf('/api/auth/') !== -1 ||
    p.indexOf('/api/market/login') !== -1 ||
    p.indexOf('/api/market/register') !== -1
  );
}

function shouldBypassCache(request, url) {
  try {
    if (request.headers && (request.headers.has('range') || request.headers.has('if-range'))) {
      return true;
    }
  } catch (_err) {
    /* ignore */
  }
  const p = url.pathname.toLowerCase();
  return (
    p.endsWith('.woff') ||
    p.endsWith('.woff2') ||
    p.endsWith('.ttf') ||
    p.endsWith('.eot') ||
    p.indexOf('/assets/fonts/') !== -1
  );
}

/** Cache Storage 仅支持完整 200；206 Partial Content 会触发 put() 异常。 */
function isCacheableResponse(response) {
  if (!response) return false;
  if (response.status === 206) return false;
  if (response.status !== 200) return false;
  const t = response.type;
  if (t === 'opaque' || t === 'opaqueredirect') return false;
  return true;
}

function putInCache(cacheName, request, response) {
  if (!isCacheableResponse(response)) return Promise.resolve();
  return caches
    .open(cacheName)
    .then((cache) => cache.put(request, response.clone()))
    .catch((err) => {
      console.warn('[SW] cache.put skipped:', request && request.url, err);
    });
}

function isStaticResource(url) {
  const staticExtensions = [
    '.js',
    '.css',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.ico',
    '.woff',
    '.woff2',
    '.ttf',
    '.eot',
  ];
  return (
    staticExtensions.some((ext) => url.pathname.endsWith(ext)) ||
    url.pathname.startsWith('/static/') ||
    url.pathname.startsWith('/font-awesome/') ||
    url.pathname.startsWith('/assets/')
  );
}

async function handleStaticRequest(request) {
  if (shouldBypassCache(request, new URL(request.url))) {
    return fetch(request);
  }
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      updateCacheInBackground(request, STATIC_CACHE);
      return cachedResponse;
    }
    const networkResponse = await fetch(request);
    putInCache(STATIC_CACHE, request, networkResponse);
    return networkResponse;
  } catch (error) {
    const fallbackResponse = await caches.match(request);
    if (fallbackResponse && isCacheableResponse(fallbackResponse)) return fallbackResponse;
    return createOfflineResponse('资源加载失败，请检查网络连接');
  }
}

async function handleAPIRequest(request) {
  const url = new URL(request.url);
  const skipCache = isNonCacheableApiPath(url.pathname);
  try {
    const networkResponse = await fetch(request);
    if (!skipCache && isCacheableResponse(networkResponse)) {
      putInCache(API_CACHE, request, networkResponse);
    }
    if (isCacheableResponse(networkResponse)) {
      const modifiedHeaders = new Headers(networkResponse.headers);
      modifiedHeaders.set('X-Data-Source', 'network');
      return new Response(networkResponse.body, {
        status: networkResponse.status,
        statusText: networkResponse.statusText,
        headers: modifiedHeaders,
      });
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      const modifiedHeaders = new Headers(cachedResponse.headers);
      modifiedHeaders.set('X-Data-Source', 'cache');
      return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers: modifiedHeaders,
      });
    }
    return createOfflineJSONResponse({
      success: false,
      message: '网络连接不可用，请检查网络后重试',
      code: 'OFFLINE',
      data: null,
    });
  }
}

function isSpaNavigationRequest(request) {
  if (request.mode === 'navigate') return true;
  const accept = request.headers.get('accept') || '';
  return accept.includes('text/html');
}

/** Vue History 深链（如 /traditional-mode）失败时回退到 index.html，避免整页 503。 */
async function getSpaShellResponse() {
  const shellUrls = ['/index.html', '/'];
  for (const url of shellUrls) {
    const cached = await caches.match(url);
    if (cached) return cached;
  }
  for (const url of shellUrls) {
    try {
      const res = await fetch(url, { cache: 'no-cache' });
      if (isCacheableResponse(res)) return res;
    } catch (_err) {
      /* try next */
    }
  }
  return null;
}

async function handleGeneralRequest(request) {
  const spaNav = isSpaNavigationRequest(request);

  try {
    const networkResponse = await fetch(request);
    putInCache(CACHE_NAME, request, networkResponse);
    if (isCacheableResponse(networkResponse)) {
      return networkResponse;
    }
    if (spaNav && (networkResponse.status === 404 || networkResponse.status === 503)) {
      const shell = await getSpaShellResponse();
      if (shell) return shell;
    }
    return networkResponse;
  } catch (error) {
    if (spaNav) {
      const shell = await getSpaShellResponse();
      if (shell) return shell;
    }
    const cachedResponse = await caches.match(request);
    if (cachedResponse) return cachedResponse;
    return createOfflineResponse('无法访问该页面');
  }
}

function updateCacheInBackground(request, cacheName) {
  fetch(request)
    .then((response) => {
      putInCache(cacheName, request, response);
    })
    .catch(() => {});
}

function createOfflineResponse(message) {
  const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>离线</title></head><body><p>${message}</p></body></html>`;
  return new Response(html, {
    status: 503,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
  });
}

function createOfflineJSONResponse(data) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'X-Data-Source': 'offline-fallback',
    },
  });
}

self.addEventListener('message', (event) => {
  if (!event.data || !event.data.type) return;
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
