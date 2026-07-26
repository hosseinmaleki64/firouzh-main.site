const CACHE_NAME = 'firouzeh-admin-v1';

// فقط شِل استاتیک اپ رو کش کن، نه دیتای API!
const STATIC_ASSETS = [
  'dashboard.html',
  'articles.html',
  'products.html',
  'orders.html',
  'categories.html',
  'admin-login.html',
  'manifest.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // درخواست‌های API (api.firouzehco.com) رو اصلاً کش نکن — همیشه از شبکه بگیر
  if (url.origin === 'https://api.firouzehco.com') {
    return; // بذار مرورگر خودش عادی هندل کنه
  }

  // برای فایل‌های خود اپ: اول شبکه، اگه نبود کش (یا برعکس، بسته به سلیقه)
  event.respondWith(
    fetch(event.request)
      .then((res) => {
        const clone = res.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return res;
      })
      .catch(() => caches.match(event.request))
  );
});