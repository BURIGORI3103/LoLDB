// LoLDBのHTML内容検証付き2層キャッシュ __VER_HASH__
const CACHE_PREFIX = 'loldb-';
const CORE_CACHE = '__DYNAMIC_CORE_CACHE__';
const HTML_HASH = '__HTML_HASH__';
const IMAGE_CACHE = 'loldb-images-v1';
const ASSETS_TO_CACHE = ['./index.html', './manifest.json', './icon.png', './icon-512.png'];

async function matchesHtml(response) {
  if (!response || !response.ok) return false;
  const text = (await response.clone().text()).replace(/\r\n/g, '\n');
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hash = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
  return hash === HTML_HASH;
}

function freshUrl(value) {
  const url = new URL(value, self.registration.scope);
  url.searchParams.set('__loldb_build', HTML_HASH.slice(0, 8));
  url.searchParams.set('__loldb_refresh', Date.now() + '-' + Math.random());
  return url.href;
}

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const assets = await Promise.all(ASSETS_TO_CACHE.map(async asset => {
      const response = await fetch(freshUrl(asset), {cache: 'no-store'});
      if (!response.ok) throw new Error('コア取得失敗: ' + asset);
      if (asset === './index.html' && !await matchesHtml(response)) throw new Error('HTMLハッシュ不一致');
      return [asset, response];
    }));
    const cache = await caches.open(CORE_CACHE);
    for (const [asset, response] of assets) {
      if (asset === './index.html') await cache.put('./', response.clone());
      await cache.put(asset, response);
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith(CACHE_PREFIX) && key !== CORE_CACHE && key !== IMAGE_CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const inScope = url.href.startsWith(self.registration.scope);
  if (inScope && (event.request.mode === 'navigate' || url.pathname.endsWith('index.html') || url.pathname.endsWith('/'))) {
    event.respondWith((async () => {
      const cache = await caches.open(CORE_CACHE);
      try {
        const response = await fetch(freshUrl(event.request.url), {cache: 'no-store'});
        if (!response.ok) throw new Error('HTML取得失敗');
        // 新版のオンライン表示は許し、別ビルドの内容を現キャッシュへ混入させない。
        if (await matchesHtml(response)) {
          await cache.put('./index.html', response.clone());
          await cache.put('./', response.clone());
        }
        return response;
      } catch {
        return await cache.match('./index.html') || await cache.match('./')
          || new Response('オフライン用データが未取得です。オンラインで開き直してください。', {status: 503, headers: {'Content-Type':'text/plain; charset=utf-8'}});
      }
    })());
    return;
  }
  const isImage = event.request.destination === 'image' || /\.(png|jpg|jpeg|svg|webp|ico)$/i.test(url.pathname)
    || url.hostname === 'ddragon.leagueoflegends.com';
  event.respondWith((async () => {
    const cache = await caches.open(isImage ? IMAGE_CACHE : CORE_CACHE);
    const cached = await cache.match(event.request);
    if (cached) return cached;
    try {
      const response = await fetch(event.request);
      if (response.ok || isImage && response.type === 'opaque') await cache.put(event.request, response.clone());
      return response;
    } catch {
      if (isImage) return await (await caches.open(CORE_CACHE)).match('./icon.png') || Response.error();
      return Response.error();
    }
  })());
});
