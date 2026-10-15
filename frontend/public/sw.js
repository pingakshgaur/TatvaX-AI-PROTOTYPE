// TatvaX service worker: installable app shell and offline study notes.
// Build assets have content hashes in their names, so they are cached forever on first use.
const VERSION = "tatvax-2.0.0";
const PRECACHE = ["/", "/manifest.webmanifest", "/theme-boot.js", "/icons/icon.svg", "/icons/icon-192.png"];
// API reads that may be served from cache while offline.
const OFFLINE_API = ["/api/bootstrap", "/api/library", "/api/me", "/api/progress"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(VERSION).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key !== VERSION).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

async function networkFirst(request, fallbackUrl) {
  const cache = await caches.open(VERSION);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch {
    const cached = (await cache.match(request)) || (fallbackUrl && (await cache.match(fallbackUrl)));
    if (cached) return cached;
    return new Response(JSON.stringify({ error: "You're offline." }), { status: 503, headers: { "Content-Type": "application/json" } });
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(VERSION);
  const cached = await cache.match(request);
  if (cached) return cached;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, "/"));
  } else if (url.pathname.startsWith("/assets/")) {
    event.respondWith(cacheFirst(request));
  } else if (url.pathname.startsWith("/api/")) {
    if (OFFLINE_API.some((path) => url.pathname.startsWith(path))) event.respondWith(networkFirst(request));
  } else {
    event.respondWith(networkFirst(request));
  }
});
