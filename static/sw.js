/* Service Worker — 离线阅读
 * 策略：
 *   - app shell (css/js/manifest/offline.html): install 时预缓存，cache-first
 *   - 站内页面 (导航/HTML/json): stale-while-revalidate（秒开缓存 + 后台更新）
 *   - 图片 (含跨域): cache-first，容量上限兜底，失败放行
 * 缓存版本号变更时（部署新版本）activate 清理旧缓存。
 */
"use strict";

const VERSION = "v1";
const SHELL_CACHE = `shell-${VERSION}`;
const PAGE_CACHE = `pages-${VERSION}`;
const IMAGE_CACHE = `images-${VERSION}`;
const IMAGE_CACHE_MAX = 120;
const SHELL_ASSETS = [
  "static/style.css",
  "static/main.js",
  "manifest.webmanifest",
  "offline.html",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const base = new URL(self.registration.scope);
    const urls = SHELL_ASSETS.map((p) => new URL(p, base).href);
    const cache = await caches.open(SHELL_CACHE);
    await cache.addAll(urls);
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const valid = new Set([SHELL_CACHE, PAGE_CACHE, IMAGE_CACHE]);
    const names = await caches.keys();
    await Promise.all(
      names.filter((n) => !valid.has(n)).map((n) => caches.delete(n)));
    await self.clients.claim();
  })());
});

async function staleWhileRevalidate(request, cacheName, fallback) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(async (response) => {
    if (response && response.ok) {
      await cache.put(request, response.clone());
    }
    return response;
  }).catch(() => null);
  if (cached) {
    fetchPromise.catch(() => {}); // 后台更新，不影响展示
    return cached;
  }
  const fresh = await fetchPromise;
  if (fresh) return fresh;
  if (fallback) {
    const shell = await caches.open(SHELL_CACHE);
    const offline = await shell.match(fallback);
    if (offline) return offline;
  }
  return new Response("离线且未缓存此页面", { status: 503,
    headers: { "Content-Type": "text/plain; charset=utf-8" } });
}

async function cacheFirstImage(request) {
  const cache = await caches.open(IMAGE_CACHE);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const response = await fetch(request);
    if (response.ok || response.type === "opaque") {
      cache.put(request, response.clone());
      trimImageCache(cache);
    }
    return response;
  } catch (e) {
    return Response.error();
  }
}

async function trimImageCache(cache) {
  const keys = await cache.keys();
  if (keys.length > IMAGE_CACHE_MAX) {
    await cache.delete(keys[0]); // FIFO，足够简单
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;
  const scope = self.registration.scope;

  if (sameOrigin && url.href.startsWith(scope)) {
    if (request.mode === "navigate" ||
        request.destination === "document") {
      event.respondWith(staleWhileRevalidate(request, PAGE_CACHE,
        new URL("offline.html", scope).href));
      return;
    }
    if (request.destination === "image") {
      event.respondWith(cacheFirstImage(request));
      return;
    }
    // css/js/manifest/json 等子资源
    event.respondWith(staleWhileRevalidate(request, PAGE_CACHE));
    return;
  }
  if (request.destination === "image") {
    // 跨域文章配图
    event.respondWith(cacheFirstImage(request));
  }
});
