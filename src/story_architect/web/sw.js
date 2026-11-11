// Story Architect service worker.
//
// No caching: the dashboard is a live local app, and a cached copy would go
// stale between runs. The fetch handler is here because Chrome requires one
// before it will offer Install.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {});
