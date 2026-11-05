// habitquest service worker: offline shell + cache-first for static assets.
const CACHE = "habitquest-v2";
const SHELL = ["/", "/manifest.json", "/static/style.css", "/static/app.js", "/static/icons/icon-192.png", "/static/icons/favicon.svg"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // Static assets + shell: cache-first (offline-friendly).
  if (url.origin === location.origin && (url.pathname.startsWith("/static/") || url.pathname === "/" || url.pathname === "/manifest.json")) {
    e.respondWith(
      caches.match(e.request).then((hit) =>
        hit || fetch(e.request).then((resp) => {
          const copy = resp.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return resp;
        })
      )
    );
    return;
  }
  // Navigations: network first, cached shell as offline fallback.
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => caches.match("/")));
  }
  // /api/* stays network-only: data must be fresh when online.
});
