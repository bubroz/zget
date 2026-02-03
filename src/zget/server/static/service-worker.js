// zget Service Worker
// Provides offline support and intelligent caching for the Portal PWA

const CACHE_VERSION = 'zget-v1-family';
const APP_SHELL_CACHE = 'app-shell-v2';
const THUMBNAILS_CACHE = 'thumbnails-v1';
const API_CACHE = 'api-cache-v1';

// App shell files to precache
const APP_SHELL_FILES = [
    '/',
    '/manifest.json',
    '/icon.png',
    '/offline.html'
];

// Install event: precache app shell
self.addEventListener('install', (event) => {
    console.log('[SW] Installing service worker...');
    event.waitUntil(
        caches.open(APP_SHELL_CACHE)
            .then(cache => {
                console.log('[SW] Precaching app shell');
                return cache.addAll(APP_SHELL_FILES);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event: clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating service worker...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== APP_SHELL_CACHE &&
                        name !== THUMBNAILS_CACHE &&
                        name !== API_CACHE)
                    .map(name => {
                        console.log('[SW] Deleting old cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event: apply caching strategies
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Strategy: Cache-First for thumbnails (30 day expiry)
    if (url.pathname.startsWith('/api/thumbnails')) {
        event.respondWith(cacheFirst(event.request, THUMBNAILS_CACHE));
        return;
    }

    // Strategy: Stale-While-Revalidate for library API
    if (url.pathname === '/api/library') {
        event.respondWith(staleWhileRevalidate(event.request, API_CACHE));
        return;
    }

    // Strategy: Network-First for other API calls
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(networkFirst(event.request, API_CACHE));
        return;
    }

    // Strategy: Network-Only for media files (too large to cache)
    if (url.pathname.startsWith('/api/media/')) {
        return; // Let browser handle normally
    }

    // Strategy: Cache-First with network fallback for static assets
    if (url.pathname.match(/\.(js|css|png|jpg|svg|ico|woff2?)$/)) {
        event.respondWith(cacheFirst(event.request, APP_SHELL_CACHE));
        return;
    }

    // Default: Network-First with offline fallback for navigation
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .catch(() => caches.match('/offline.html'))
        );
        return;
    }

    // Default: try network, fall back to cache
    event.respondWith(networkFirst(event.request, APP_SHELL_CACHE));
});

// Cache-First strategy: Check cache, fall back to network
async function cacheFirst(request, cacheName) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
        return cachedResponse;
    }

    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        console.log('[SW] Network request failed:', request.url);
        return new Response('Offline', { status: 503 });
    }
}

// Stale-While-Revalidate: Return cached immediately, update in background
async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cachedResponse = await cache.match(request);

    // Fetch fresh data in background
    const fetchPromise = fetch(request).then(networkResponse => {
        if (networkResponse.ok) {
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    }).catch(() => null);

    // Return cached response immediately if available
    return cachedResponse || fetchPromise;
}

// Network-First strategy: Try network, fall back to cache
async function networkFirst(request, cacheName) {
    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch (error) {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) {
            return cachedResponse;
        }
        return new Response('Offline', { status: 503 });
    }
}
