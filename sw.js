// LoLDB Service Worker - Dual Cache Architecture v12
const CORE_CACHE = 'loldb-core-v12';
const IMAGE_CACHE = 'loldb-images-v1'; // チャンピオン・アイテム・スペル画像永続キャッシュ

const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json',
  './icon.png',
  './icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CORE_CACHE).then((cache) => {
      console.log('[SW] Pre-caching core offline assets');
      return cache.addAll(ASSETS_TO_CACHE);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) => {
      return Promise.all(keyList.map((key) => {
        // IMAGE_CACHE (loldb-images-v1) と 最新の CORE_CACHE 以外を破棄
        if (key !== CORE_CACHE && key !== IMAGE_CACHE) {
          console.log('[SW] Removing old core cache:', key);
          return caches.delete(key);
        }
      }));
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // 1. メインHTML（ナビゲーション）は Network-First（オンライン時は最新、オフライン時はキャッシュ）
  if (event.request.mode === 'navigate' || url.pathname.endsWith('index.html') || url.pathname === '/') {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseToCache = networkResponse.clone();
            caches.open(CORE_CACHE).then((cache) => cache.put(event.request, responseToCache));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match('./index.html') || caches.match('./');
        })
    );
    return;
  }

  // 2. 画像リクエスト（Data Dragon CDN および ローカル画像）は Cache-First (永続画像キャッシュ)
  const isImage = event.request.destination === 'image' ||
                  url.pathname.match(/\.(png|jpg|jpeg|svg|webp|ico)$/i) ||
                  url.hostname.includes('ddragon.leagueoflegends.com');

  if (isImage) {
    event.respondWith(
      caches.open(IMAGE_CACHE).then((imageCache) => {
        return imageCache.match(event.request).then((cachedResponse) => {
          if (cachedResponse) {
            return cachedResponse;
          }
          return fetch(event.request).then((networkResponse) => {
            // クロスオリジン（no-cors）画像レスポンスは status が 0 (type: 'opaque') になるため、
            // status === 200 に加えて type === 'opaque' も確実にキャッシュに保存する！
            if (networkResponse && (networkResponse.status === 200 || networkResponse.type === 'opaque')) {
              imageCache.put(event.request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => {
            // オフライン時のローカルアイコンフォールバック
            return caches.match('./icon.png');
          });
        });
      })
    );
    return;
  }

  // 3. その他の静的アセットは CORE_CACHE による Cache-First
  event.respondWith(
    caches.match(event.request).then((response) => {
      if (response) {
        return response;
      }
      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200 && event.request.method === 'GET') {
          const responseToCache = networkResponse.clone();
          caches.open(CORE_CACHE).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      });
    })
  );
});
