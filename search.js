/* =========================================================
   جستجوی واقعی فیروزه — مشترک برای همه صفحه‌ها
   استفاده: قبل از </body> این خط را بگذارید:
   <script src="/search.js" defer></script>
   ========================================================= */
(function () {
  'use strict';

  var API_ORIGIN = 'https://api.firouzehco.com';
  var PRODUCTS_URL = API_ORIGIN + '/api/products/public/?page_size=100';
  var CATEGORIES_URL = API_ORIGIN + '/api/products/public/categories/';
  var ARTICLES_URL = API_ORIGIN + '/api/content/articles/?status=PUBLISHED&ordering=-created_at&page_size=100';

  // ---- حذف لیسنرهای قدیمیِ جستجو (با کلون کردن عنصرها) ----
  function stripListeners(el) {
    if (!el || !el.parentNode) return el;
    var c = el.cloneNode(true);
    el.parentNode.replaceChild(c, el);
    return c;
  }

  var input = stripListeners(document.getElementById('searchInput'));
  var box = stripListeners(document.getElementById('suggestionsBox'));

  // اگر صفحه جعبه نتایج نداشت (مثل vip-customers)، خودمان می‌سازیم
  if (!box && input) {
    var holder = input.closest('.search-box') || input.parentNode;
    box = document.createElement('div');
    box.id = 'suggestionsBox';
    box.className = 'sr-created';
    holder.appendChild(box);
    var st0 = document.createElement('style');
    st0.textContent =
      '#suggestionsBox.sr-created{display:none;position:absolute;top:42px;right:0;width:100%;min-width:260px;' +
      'max-height:320px;overflow-y:auto;background:#fff;color:#222;border:1px solid #dadee6;padding:8px;' +
      'z-index:1100;border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.15);text-align:right;direction:rtl}' +
      '#suggestionsBox.sr-created.active{display:block}';
    document.head.appendChild(st0);
  }
  var clearBtn = stripListeners(document.getElementById('clearSearch'));
  var iconBtn = stripListeners(document.querySelector('.search-box .search-icon'));
  if (!input || !box) return;

  // ---- استایل نتایج ----
  var st = document.createElement('style');
  st.textContent =
    '.sr-item{display:flex;align-items:center;gap:10px;padding:8px;border-radius:8px;text-decoration:none;color:#222;cursor:pointer}' +
    '.sr-item:hover,.sr-item.sr-active{background:#e8f5f3}' +
    '.sr-item img{width:44px;height:44px;object-fit:cover;border-radius:8px;background:#eee;flex-shrink:0}' +
    '.sr-info{flex:1;min-width:0}' +
    '.sr-name{font-size:.92rem;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}' +
    '.sr-sub{font-size:.8rem;color:#26A69A;font-weight:700}' +
    '.sr-old{color:#999;text-decoration:line-through;margin-inline-start:6px;font-weight:400}' +
    '.sr-head{font-size:.8rem;color:#777;margin:6px 4px 2px}' +
    '.sr-empty{padding:14px;text-align:center;color:#D32F2F;font-size:.9rem}' +
    '.sr-loading{padding:14px;text-align:center;color:#666;font-size:.9rem}';
  document.head.appendChild(st);

  // ---- نرمال‌سازی متن فارسی (ی/ک عربی، اعداد، نیم‌فاصله، حروف) ----
  function norm(s) {
    return String(s || '')
      .toLowerCase()
      .replace(/[يى]/g, 'ی')
      .replace(/ك/g, 'ک')
      .replace(/[ۀة]/g, 'ه')
      .replace(/[\u200c\u200f\u200e]/g, ' ')
      .replace(/[\u064B-\u065F\u0640]/g, '')
      .replace(/[۰-۹]/g, function (d) { return String(d.charCodeAt(0) - 1776); })
      .replace(/[٠-٩]/g, function (d) { return String(d.charCodeAt(0) - 1632); })
      .replace(/_/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function media(p) {
    if (!p) return 'image1/logo.png';
    return p.indexOf('http') === 0 ? p : API_ORIGIN + p;
  }
  function fa(n) { return Number(n || 0).toLocaleString('fa-IR'); }

  // ---- دریافت و کش همه محصولات و دسته‌ها (یک‌بار) ----
  var dataPromise = null;
  function fetchAllProducts(startUrl) {
    var all = [];
    function next(url) {
      return fetch(url).then(function (r) {
        if (!r.ok) throw new Error('status ' + r.status);
        return r.json();
      }).then(function (d) {
        var list = Array.isArray(d) ? d : (d.results || []);
        all = all.concat(list);
        if (d.next && all.length < 1000) {
          // اگر next آدرس http داد، به https تبدیل می‌شود
          return next(String(d.next).replace(/^http:\/\//, 'https://'));
        }
        return all;
      });
    }
    return next(startUrl || PRODUCTS_URL);
  }
  function loadData() {
    if (dataPromise) return dataPromise;
    dataPromise = Promise.all([
      fetchAllProducts().catch(function (e) { console.error('products', e); return []; }),
      fetch(CATEGORIES_URL).then(function (r) { return r.ok ? r.json() : []; })
        .then(function (c) { return Array.isArray(c) ? c : (c.results || []); })
        .catch(function () { return []; }),
      fetchAllProducts(ARTICLES_URL).catch(function (e) { console.error('articles', e); return []; })
    ]).then(function (res) {
      var products = res[0].map(function (p) {
        var disc = Number(p.discount_percent) || 0;
        var price = Number(p.price) || 0;
        var final = disc > 0 ? Math.round(price * (100 - disc) / 100) : price;
        var img = (p.images && p.images[0]) ? p.images[0].image : '';
        return {
          type: 'product',
          name: p.name || '',
          slug: p.slug,
          desc: p.description || '',
          image: media(img),
          price: final,
          oldPrice: disc > 0 ? price : 0,
          catName: p.category ? (p.category.name || '') : '',
          _n: norm((p.name || '') + ' ' + (p.description || '') + ' ' + (p.category ? p.category.name : '')),
          _nName: norm(p.name)
        };
      });
      var cats = res[1].map(function (c) {
        return { type: 'category', name: c.name || '', slug: c.slug, image: c.image ? media(c.image) : '', _n: norm(c.name), _nName: norm(c.name) };
      });
      var articles = res[2].map(function (a) {
        return {
          type: 'article',
          name: a.title || '',
          slug: a.slug,
          excerpt: a.excerpt || '',
          image: media(a.cover_image),
          _n: norm((a.title || '') + ' ' + (a.excerpt || '') + ' ' + (a.content || '')),
          _nName: norm(a.title)
        };
      });
      return { products: products, cats: cats, articles: articles };
    });
    return dataPromise;
  }

  // ---- منطق جستجو: همه کلمات باید پیدا شوند؛ امتیازدهی ----
  function score(item, words, q) {
    var s = 0;
    for (var i = 0; i < words.length; i++) {
      if (item._n.indexOf(words[i]) === -1) return 0;
    }
    if (item._nName === q) s += 100;
    else if (item._nName.indexOf(q) === 0) s += 60;
    else if (item._nName.indexOf(q) !== -1) s += 40;
    for (var j = 0; j < words.length; j++) {
      if (item._nName.indexOf(words[j]) !== -1) s += 10;
    }
    return s + 1;
  }
  function run(query, data) {
    var q = norm(query);
    var words = q.split(' ').filter(Boolean);
    if (!words.length) return { products: [], cats: [], articles: [] };
    function pick(arr) {
      return arr.map(function (it) { return { it: it, s: score(it, words, q) }; })
        .filter(function (x) { return x.s > 0; })
        .sort(function (a, b) { return b.s - a.s; })
        .map(function (x) { return x.it; });
    }
    return {
      products: pick(data.products).slice(0, 8),
      cats: pick(data.cats).slice(0, 3),
      articles: pick(data.articles).slice(0, 4)
    };
  }

  // ---- نمایش ----
  var activeIdx = -1;
  function links() { return box.querySelectorAll('a.sr-item'); }
  function setActive(i) {
    var l = links();
    if (!l.length) return;
    activeIdx = (i + l.length) % l.length;
    for (var k = 0; k < l.length; k++) l[k].classList.toggle('sr-active', k === activeIdx);
    l[activeIdx].scrollIntoView({ block: 'nearest' });
  }
  function url(it) {
    if (it.type === 'product') return '/product/' + encodeURIComponent(it.slug) + '/';
    if (it.type === 'article') return 'blog.html?slug=' + encodeURIComponent(it.slug);
    return '/category/' + encodeURIComponent(it.slug) + '/';
  }
  function render(res) {
    activeIdx = -1;
    if (!res.products.length && !res.cats.length && !res.articles.length) {
      box.innerHTML = '<div class="sr-empty">نتیجه‌ای پیدا نشد</div>';
      box.classList.add('active');
      return;
    }
    var h = '';
    if (res.cats.length) {
      h += '<div class="sr-head">دسته‌بندی‌ها</div>';
      res.cats.forEach(function (c) {
        h += '<a class="sr-item" href="' + url(c) + '">' +
          (c.image ? '<img src="' + esc(c.image) + '" alt="">' : '') +
          '<div class="sr-info"><div class="sr-name">' + esc(c.name) + '</div></div></a>';
      });
    }
    if (res.products.length) {
      h += '<div class="sr-head">محصولات</div>';
      res.products.forEach(function (p) {
        h += '<a class="sr-item" href="' + url(p) + '">' +
          '<img src="' + esc(p.image) + '" alt="" loading="lazy">' +
          '<div class="sr-info"><div class="sr-name">' + esc(p.name) + '</div>' +
          '<div class="sr-sub">' + fa(p.price) + ' تومان' +
          (p.oldPrice ? '<span class="sr-old">' + fa(p.oldPrice) + '</span>' : '') +
          '</div></div></a>';
      });
    }
    if (res.articles.length) {
      h += '<div class="sr-head">مقالات</div>';
      res.articles.forEach(function (a) {
        h += '<a class="sr-item" href="' + url(a) + '">' +
          '<img src="' + esc(a.image) + '" alt="" loading="lazy">' +
          '<div class="sr-info"><div class="sr-name">' + esc(a.name) + '</div></div></a>';
      });
    }
    box.innerHTML = h;
    box.classList.add('active');
  }

  var timer = null, lastQ = '';
  function doSearch() {
    var v = input.value;
    clearBtn && clearBtn.classList.toggle('active', v.length > 0);
    lastQ = v;
    if (!norm(v)) { box.classList.remove('active'); box.innerHTML = ''; return; }
    box.innerHTML = '<div class="sr-loading">در حال جستجو…</div>';
    box.classList.add('active');
    loadData().then(function (data) {
      if (lastQ !== v) return; // نتیجه قدیمی
      render(run(v, data));
    });
  }

  input.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(doSearch, 200);
  });
  input.addEventListener('focus', function () {
    loadData(); // پیش‌بارگذاری
    if (norm(input.value)) doSearch();
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(activeIdx + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(activeIdx - 1); }
    else if (e.key === 'Enter') {
      e.preventDefault();
      var l = links();
      if (activeIdx >= 0 && l[activeIdx]) { window.location.href = l[activeIdx].getAttribute('href'); }
      else if (l.length) { window.location.href = l[0].getAttribute('href'); }
      else doSearch();
    } else if (e.key === 'Escape') { box.classList.remove('active'); }
  });
  if (iconBtn) iconBtn.addEventListener('click', function () {
    var l = links();
    if (l.length) window.location.href = l[0].getAttribute('href');
    else { input.focus(); doSearch(); }
  });
  if (clearBtn) clearBtn.addEventListener('click', function () {
    input.value = '';
    clearBtn.classList.remove('active');
    box.classList.remove('active');
    box.innerHTML = '';
    input.focus();
  });
  document.addEventListener('click', function (e) {
    if (!input.contains(e.target) && !box.contains(e.target)) box.classList.remove('active');
  });
})();