#!/usr/bin/env python3
"""
Firouzeh static build (GitHub Actions)
- پیش‌رندر دسته‌ها و محصولات صفحه اصلی (index.html)
- ساخت صفحه ثابت برای هر محصول:  /product/<slug>/
- ساخت صفحه ثابت برای هر دسته:   /category/<slug>/
- ساخت sitemap.xml و products-map.json
نکته: پوشه‌های product/ و category/ و assets/ کاملاً خودکارند؛ دستی چیزی داخلشان نگذارید.
"""
import html
import json
import os
import re
import shutil
import sys
import time
import urllib.request
from urllib.parse import quote

SITE = "https://firouzehco.com"
API_ORIGIN = "https://api.firouzehco.com"
API = API_ORIGIN + "/api/products/public"
ARTICLES = API_ORIGIN + "/api/content/articles/?status=PUBLISHED&ordering=-created_at&page_size=100"
INDEX = "index.html"
WA = "989142830328"
PHONE = "۰۴۱-۳۳۳۶۷۰۵۲"
MOBILE = "۰۹۱۴۲۸۳۰۳۲۸"
ADDRESS = "تبریز، چهارراه منصور، کوچه سیدلر"
CLARITY_ID = "ui7uv46wvy"

STATIC_PAGES = [
    "/", "/finger-food.html", "/drinks.html", "/about.html", "/contact.html",
    "/FAQ.html", "/cooperation.html", "/vip-customers.html", "/blogs.html", "/terms.html",
]

# ---------------------------------------------------------------- helpers

def get(url):
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "firouzeh-build/2.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa
            last = e
            time.sleep(2 * (i + 1))
    raise last


def fetch_all(url):
    out, pages = [], 0
    while url and pages < 60:
        d = get(url)
        if isinstance(d, list):
            return out + d
        out += d.get("results", [])
        url = d.get("next")
        pages += 1
    return out


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def ld(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA)


def toman(n):
    try:
        v = int(round(float(n)))
    except Exception:  # noqa
        v = 0
    return fa(f"{v:,}".replace(",", "٬")) + " تومان"


def media(path):
    if not path:
        return SITE + "/image1/logo.png"
    return path if str(path).startswith("http") else API_ORIGIN + path


def trim(s, n=155):
    s = re.sub(r"\s+", " ", s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1].rsplit(" ", 1)[0] + "…"


def clean_slug(slug, fallback):
    s = (slug or "").strip()
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"[/\\?#%&\"'<>]", "", s)
    return s or fallback


def url_path(kind, slug):
    return f"/{kind}/{quote(slug, safe='-._~')}/"


def prices(p):
    base = float(p.get("price") or 0)
    disc = float(p.get("discount_percent") or 0)
    fp = p.get("final_price")
    final = float(fp) if fp not in (None, "") else base * (100 - disc) / 100
    return base, final, disc


def day(s):
    return (s or "")[:10]


def names(items):
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append(it)
        elif isinstance(it, dict):
            v = it.get("name") or it.get("title")
            if v:
                out.append(str(v))
    return out


UNITS = {"g": "گرم", "kg": "کیلوگرم", "ml": "میلی‌لیتر", "l": "لیتر", "gram": "گرم"}

# ---------------------------------------------------------------- assets

CSS = """
:root{--p:#26A69A;--s:#1A7A6F;--bg:#fff;--n:#dadee6;--t:#4B5563;--d:#064d3b;--shadow:0 4px 6px rgba(0,0,0,.1)}
*{margin:0;padding:0;box-sizing:border-box}
html{overflow-x:hidden}
body{font-family:'Shabnam','IRANSans','Vazir',Arial,sans-serif;background:var(--bg);color:var(--t);line-height:1.9;overflow-x:hidden}
a{color:var(--s);text-decoration:none}
img{max-width:100%;height:auto;display:block}
.top{background:var(--d);color:#edebeb;position:sticky;top:0;z-index:50}
.top .in{max-width:1200px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}
.top a{color:#edebeb}
.top .logo{font-weight:700;display:flex;align-items:center;gap:8px;text-transform:uppercase}
.top .logo img{height:28px;width:auto}
.top nav{display:flex;gap:16px;flex:1;flex-wrap:wrap;font-size:.95rem}
.top .cart{position:relative;padding:4px 8px}
.badge{position:absolute;top:-6px;right:-6px;background:#e63946;color:#fff;border-radius:50%;padding:0 6px;font-size:.7rem}
.wrap{max-width:1200px;margin:0 auto;padding:24px 20px 60px}
.crumbs{font-size:.9rem;margin-bottom:18px;color:#6b7280}
.crumbs a{color:#6b7280}
.product{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:start}
.gallery .main{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:16px;box-shadow:var(--shadow);background:var(--n)}
.thumbs{display:flex;gap:10px;margin-top:12px;flex-wrap:wrap}
.thumbs img{width:72px;height:72px;object-fit:cover;border-radius:10px;border:2px solid transparent;cursor:pointer;background:var(--n)}
.thumbs img.on{border-color:var(--p)}
.info h1{font-size:1.7rem;line-height:1.5;color:#1f2937;margin-bottom:10px}
.price{font-size:1.6rem;font-weight:700;color:var(--p);margin:8px 0}
.price del{font-size:1rem;color:#9ca3af;margin-inline-start:10px;font-weight:400}
.price .off{font-size:.85rem;background:#e63946;color:#fff;border-radius:8px;padding:2px 8px;margin-inline-start:8px;font-weight:600}
.meta{margin:6px 0;font-size:.98rem}
.buy{display:flex;gap:12px;align-items:center;margin:20px 0 12px;flex-wrap:wrap}
.qty{display:flex;align-items:center;gap:8px}
.qty button{width:36px;height:36px;border-radius:50%;border:none;background:var(--p);color:#fff;font-size:1.2rem;cursor:pointer}
.qty input{width:52px;text-align:center;border:2px solid var(--n);border-radius:8px;padding:6px;font-size:1.05rem;font-family:inherit}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 26px;border-radius:12px;border:none;background:var(--p);color:#fff;font-weight:700;font-size:1.05rem;cursor:pointer;font-family:inherit;box-shadow:var(--shadow)}
.btn:hover{background:var(--s)}
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn.wa{background:#25D366;color:#fff}
.trust{list-style:none;margin-top:18px;font-size:.95rem}
.trust li{padding:3px 0}
.trust li:before{content:"✓";color:var(--p);margin-inline-end:8px;font-weight:700}
section.block{margin-top:44px}
section.block h2{font-size:1.4rem;color:#1f2937;margin-bottom:12px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:24px}
.card{display:block;border:1px solid var(--n);border-radius:14px;overflow:hidden;background:#fff;color:inherit;box-shadow:var(--shadow);transition:transform .2s}
.card:hover{transform:translateY(-4px);border-color:var(--p)}
.card img{width:100%;aspect-ratio:1/1;object-fit:cover;background:var(--n)}
.card h3{font-size:1rem;padding:10px 14px 0;color:#1f2937;line-height:1.5}
.card .price{font-size:1.05rem;padding:0 14px 14px;margin:4px 0 0}
.foot{background:linear-gradient(135deg,var(--s),#2E2A3F);color:#edebeb;text-align:center;padding:36px 20px;margin-top:40px}
.foot a{color:#edebeb;margin:0 8px}
.foot p{margin:6px 0}
#toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1A1A1A;color:#fff;padding:12px 22px;border-radius:10px;z-index:100;display:none}
@media(max-width:768px){.product{grid-template-columns:1fr;gap:22px}.info h1{font-size:1.35rem}.wrap{padding:16px 14px 50px}}
"""

JS = r"""
(function(){
  var API="https://api.firouzehco.com",CART=API+"/api/cart";
  function tok(){try{return localStorage.getItem("access")}catch(e){return null}}
  async function refreshTok(){
    var r;try{r=localStorage.getItem("refresh")}catch(e){}
    if(!r)return false;
    try{
      var res=await fetch(API+"/api/auth/refresh/",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({refresh:r})});
      if(!res.ok)return false;
      var d=await res.json();if(!d.access)return false;
      localStorage.setItem("access",d.access);return true;
    }catch(e){return false}
  }
  async function cartFetch(path,opts,retry){
    opts=opts||{};
    var h=Object.assign({},opts.headers||{});
    if(opts.body)h["Content-Type"]="application/json";
    var t=tok();if(t)h["Authorization"]="Bearer "+t;
    var res=await fetch(CART+path,Object.assign({},opts,{headers:h,credentials:"include"}));
    if(res.status===401&&!retry){
      if(await refreshTok())return cartFetch(path,opts,true);
      try{localStorage.removeItem("access");localStorage.removeItem("refresh")}catch(e){}
      return cartFetch(path,opts,true);
    }
    if(!res.ok){var err=await res.json().catch(function(){return{}});throw err}
    return res.json();
  }
  function toast(msg){
    var t=document.getElementById("toast");if(!t)return;
    t.innerHTML=msg;t.style.display="block";
    clearTimeout(toast._t);toast._t=setTimeout(function(){t.style.display="none"},3500);
  }
  function badge(){
    var b=document.getElementById("cartBadge");if(!b)return;
    cartFetch("/").then(function(c){b.textContent=c.total_items||0}).catch(function(){});
  }
  badge();
  var q=document.getElementById("qtyInput");
  var dec=document.getElementById("qtyDec"),inc=document.getElementById("qtyInc");
  if(q&&dec&&inc){
    dec.addEventListener("click",function(){q.value=Math.max(1,Number(q.value)-1)});
    inc.addEventListener("click",function(){q.value=Number(q.value)+1});
  }
  var add=document.getElementById("addBtn");
  if(add){
    add.addEventListener("click",async function(){
      add.disabled=true;var old=add.innerHTML;add.textContent="در حال افزودن...";
      try{
        await cartFetch("/items/",{method:"POST",body:JSON.stringify({product_id:add.dataset.id,quantity:Number(q?q.value:1)||1})});
        badge();
        toast('به سبد خرید اضافه شد. <a href="/checkout.html" style="color:#7ee0d6">ثبت سفارش</a>');
      }catch(e){toast((e&&e.detail)||"خطا در افزودن به سبد خرید")}
      add.disabled=false;add.innerHTML=old;
    });
  }
  var main=document.getElementById("mainImg");
  document.querySelectorAll(".thumbs img").forEach(function(im){
    im.addEventListener("click",function(){
      if(main){main.src=im.dataset.full}
      document.querySelectorAll(".thumbs img").forEach(function(x){x.classList.remove("on")});
      im.classList.add("on");
    });
  });
})();
"""

# ---------------------------------------------------------------- page parts

def head(title, desc, canon, image, schemas):
    sch = "".join(f'<script type="application/ld+json">{ld(s)}</script>\n' for s in schemas)
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canon)}">
<meta property="og:type" content="website">
<meta property="og:locale" content="fa_IR">
<meta property="og:site_name" content="فینگرفود فیروزه">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canon)}">
<meta property="og:image" content="{esc(image)}">
<link rel="stylesheet" href="/fonts.css">
<link rel="stylesheet" href="/assets/shop.css">
<link rel="icon" href="/image1/favicon.ico" type="image/x-icon">
<link rel="apple-touch-icon" sizes="180x180" href="/image1/apple-touch-icon.png">
<link rel="preconnect" href="{API_ORIGIN}" crossorigin>
<script>(function(c,l,a,r,i,t,y){{c[a]=c[a]||function(){{(c[a].q=c[a].q||[]).push(arguments)}};t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);}})(window,document,"clarity","script","{CLARITY_ID}");</script>
{sch}</head>
<body>
<header class="top"><div class="in">
  <a class="logo" href="/"><img src="/image1/logo.png" alt="لوگوی فینگرفود فیروزه" width="28" height="28">FIROUZEH</a>
  <nav>
    <a href="/">خانه</a>
    <a href="/finger-food.html">همه محصولات</a>
    <a href="/blogs.html">مقالات</a>
    <a href="/contact.html">تماس با ما</a>
  </nav>
  <a class="cart" href="/checkout.html" aria-label="سبد خرید">🛒<span class="badge" id="cartBadge">0</span></a>
</div></header>
"""


def foot():
    return f"""<footer class="foot">
  <p><strong>فینگرفود فیروزه تبریز</strong></p>
  <p>{esc(ADDRESS)}</p>
  <p>تماس: {PHONE} | واتساپ: {MOBILE}</p>
  <p><a href="/about.html">درباره ما</a><a href="/contact.html">تماس با ما</a><a href="/FAQ.html">سوالات متداول</a><a href="/terms.html">قوانین و مقررات</a></p>
  <p>© ۱۴۰۵ فیروزه - کلیه حقوق محفوظ است.</p>
</footer>
<div id="toast" role="status"></div>
<script src="/assets/shop.js" defer></script>
</body>
</html>
"""


def card(p):
    imgs = p.get("images") or []
    src = media(imgs[0]["image"]) if imgs else SITE + "/image1/logo.png"
    alt = (imgs[0].get("alt_text") if imgs else "") or p["name"]
    _, final, _ = prices(p)
    return (f'<a class="card" href="{esc(p["_path"])}">'
            f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" width="400" height="400">'
            f'<h3>{esc(p["name"])}</h3><div class="price">{toman(final)}</div></a>')


def breadcrumb_ld(trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
            for i, (n, u) in enumerate(trail)
        ],
    }


# ---------------------------------------------------------------- product page

def product_page(p, cat, related):
    name = p["name"]
    base, final, disc = prices(p)
    imgs = [media(i.get("image")) for i in (p.get("images") or []) if i.get("image")]
    alts = [(i.get("alt_text") or "") for i in (p.get("images") or []) if i.get("image")]
    canon = SITE + p["_path"]
    cat_name = cat["name"] if cat else "محصولات"
    cat_path = cat["_path"] if cat else "/finger-food.html"

    raw = names(p.get("raw_materials"))
    comps = names(p.get("components"))
    desc_txt = (p.get("description") or "").strip()
    if not desc_txt:
        desc_txt = f"{name} از محصولات {cat_name} فیروزه است. برای سفارش می‌توانید از همین صفحه یا واتساپ اقدام کنید."
    meta_desc = (p.get("meta_description") or "").strip() or \
        f"سفارش آنلاین {name} در تبریز؛ قیمت {toman(final)}. {desc_txt}"
    meta_desc = trim(meta_desc)
    title = f"{name} | سفارش آنلاین در تبریز | فیروزه"

    offer = {
        "@type": "Offer",
        "url": canon,
        "priceCurrency": "IRR",
        "price": str(int(round(final * 10))),
        "availability": "https://schema.org/InStock",
        "itemCondition": "https://schema.org/NewCondition",
    }
    prod_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": trim(desc_txt, 300),
        "sku": str(p["id"]),
        "category": cat_name,
        "brand": {"@type": "Brand", "name": "فیروزه"},
        "offers": offer,
    }
    if imgs:
        prod_ld["image"] = imgs
    crumbs = [("خانه", "/"), (cat_name, cat_path), (name, p["_path"])]

    main_img = imgs[0] if imgs else SITE + "/image1/logo.png"
    main_alt = (alts[0] if alts else "") or name
    thumbs = ""
    if len(imgs) > 1:
        thumbs = '<div class="thumbs">' + "".join(
            f'<img src="{esc(u)}" data-full="{esc(u)}" alt="{esc(alts[i] or name)}" loading="lazy" '
            f'width="72" height="72"' + (' class="on"' if i == 0 else '') + '>'
            for i, u in enumerate(imgs)) + "</div>"

    price_html = f'<span>{toman(final)}</span>'
    if disc > 0:
        price_html += f'<del>{toman(base)}</del><span class="off">{fa(int(disc))}٪ تخفیف</span>'

    meta_lines = ""
    if p.get("weight_value"):
        unit = UNITS.get(str(p.get("weight_unit") or "").lower(), p.get("weight_unit") or "")
        try:
            wv = fa(("%g" % float(p["weight_value"])))
        except Exception:  # noqa
            wv = esc(p["weight_value"])
        meta_lines += f'<p class="meta">وزن: {wv} {esc(unit)}</p>'
    if raw:
        meta_lines += f'<p class="meta">مواد اولیه: {esc("، ".join(raw))}</p>'
    if comps:
        meta_lines += f'<p class="meta">شامل: {esc("، ".join(comps))}</p>'

    wa_text = quote(f"سلام، می‌خواهم «{name}» را سفارش بدهم.")
    rel_html = ""
    if related:
        rel_html = ('<section class="block"><h2>محصولات مشابه</h2><div class="grid">'
                    + "".join(card(r) for r in related) + "</div></section>")

    crumbs_html = (f'<a href="/">خانه</a> › <a href="{esc(cat_path)}">{esc(cat_name)}</a> › '
                   f'<span>{esc(name)}</span>')

    body = f"""<main class="wrap">
<nav class="crumbs" aria-label="مسیر صفحه">{crumbs_html}</nav>
<article class="product">
  <div class="gallery">
    <img id="mainImg" class="main" src="{esc(main_img)}" alt="{esc(main_alt)}" width="800" height="800" fetchpriority="high">
    {thumbs}
  </div>
  <div class="info">
    <h1>{esc(name)}</h1>
    <div class="price">{price_html}</div>
    {meta_lines}
    <div class="buy">
      <div class="qty"><button type="button" id="qtyDec" aria-label="کم کردن">−</button><input id="qtyInput" type="number" value="1" min="1" readonly><button type="button" id="qtyInc" aria-label="زیاد کردن">+</button></div>
      <button type="button" class="btn" id="addBtn" data-id="{esc(p['id'])}">افزودن به سبد خرید</button>
    </div>
    <a class="btn wa" href="https://wa.me/{WA}?text={wa_text}" target="_blank" rel="noopener">سفارش از طریق واتساپ</a>
    <ul class="trust">
      <li>ارسال سریع در تبریز و شهرستان‌های اطراف</li>
      <li>آماده‌سازی بر اساس سفارش شما، با مواد تازه</li>
      <li>بسته‌بندی مرتب و آماده پذیرایی</li>
    </ul>
  </div>
</article>
<section class="block">
  <h2>درباره {esc(name)}</h2>
  <p>{esc(desc_txt)}</p>
  <p>برای سفارش گروهی، مراسم و پذیرایی سازمانی در تبریز می‌توانید با شماره {PHONE} یا از طریق واتساپ ({MOBILE}) مشاوره بگیرید.</p>
</section>
{rel_html}
</main>
"""
    return head(title, meta_desc, canon, main_img, [prod_ld, breadcrumb_ld(crumbs)]) + body + foot()


# ---------------------------------------------------------------- category page

def category_page(c, items):
    name = c["name"]
    canon = SITE + c["_path"]
    title = f"{name} | سفارش آنلاین در تبریز | فیروزه"
    desc = trim(f"سفارش آنلاین {name} در تبریز از فیروزه؛ مشاهده قیمت و سفارش {fa(len(items))} محصول با ارسال سریع در تبریز و شهرستان‌های اطراف.")
    img = media(c.get("image")) if c.get("image") else SITE + "/image1/heder21.jpg"
    crumbs = [("خانه", "/"), (name, c["_path"])]
    lst = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": SITE + p["_path"], "name": p["name"]}
            for i, p in enumerate(items)
        ],
    }
    body = f"""<main class="wrap">
<nav class="crumbs" aria-label="مسیر صفحه"><a href="/">خانه</a> › <span>{esc(name)}</span></nav>
<h1 style="font-size:1.7rem;color:#1f2937;margin-bottom:8px">سفارش آنلاین {esc(name)} در تبریز</h1>
<p style="margin-bottom:24px">همه محصولات دسته «{esc(name)}» فیروزه را با قیمت ببینید و آنلاین یا از طریق واتساپ سفارش دهید. ارسال سریع در تبریز و شهرستان‌های اطراف.</p>
<div class="grid">{''.join(card(p) for p in items)}</div>
<p style="margin-top:32px"><a href="/finger-food.html">مشاهده همه محصولات فیروزه ←</a></p>
</main>
"""
    return head(title, desc, canon, img, [lst, breadcrumb_ld(crumbs)]) + body + foot()


# ---------------------------------------------------------------- home prerender

def home_category(c):
    img = ""
    if c.get("image"):
        img = f'<img src="{esc(media(c["image"]))}" alt="{esc(c["name"])}" loading="lazy">'
    return ('<div class="category-card">'
            f'<div class="image-placeholder">{img}</div>'
            f'<strong>{esc(c["name"])}</strong>'
            f'<a href="{esc(c["_path"])}" class="category-button">مشاهده محصولات</a>'
            '</div>')


def home_product(p):
    imgs = p.get("images") or []
    src = media(imgs[0]["image"]) if imgs else "image1/logo.png"
    alt = (imgs[0].get("alt_text") if imgs else "") or p["name"]
    desc = p.get("description") or ""
    short = desc[:50] + ("..." if len(desc) > 50 else "")
    _, final, _ = prices(p)
    return ('<div class="best-seller-card">'
            f'<a href="{esc(p["_path"])}" class="bs-link">'
            f'<div class="best-seller-image"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"></div>'
            f'<h3 class="best-seller-name">{esc(p["name"])}</h3>'
            f'<p class="best-seller-description">{esc(short)}</p>'
            f'<div class="best-seller-price">{toman(final)}</div>'
            '</a></div>')


def inject(page, name, content):
    pattern = re.compile(rf"(<!--PRERENDER:{name}-->)(.*?)(<!--/PRERENDER:{name}-->)", re.S)
    if not pattern.search(page):
        raise SystemExit(f"marker {name} not found in {INDEX}")
    return pattern.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(3), page)


# ---------------------------------------------------------------- sitemap

def sitemap(entries):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lm in entries:
        out.append("  <url>")
        out.append(f"    <loc>{html.escape(loc)}</loc>")
        if lm:
            out.append(f"    <lastmod>{lm}</lastmod>")
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def write(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------- main

def main():
    cats_raw = get(f"{API}/categories/")
    if isinstance(cats_raw, dict):
        cats_raw = cats_raw.get("results", [])
    products = fetch_all(f"{API}/?page_size=50&ordering=-created_at")
    products = [p for p in products if p.get("is_active", True) is not False]
    if not cats_raw or not products:
        raise SystemExit("API returned no data; nothing changed")

    # --- slugs & paths
    cats, seen = {}, set()
    for c in cats_raw:
        s = clean_slug(c.get("slug"), str(c["id"])[:8])
        if s in seen:
            s = f"{s}-{str(c['id'])[:6]}"
        seen.add(s)
        c["_slug"], c["_path"] = s, url_path("category", s)
        cats[c["id"]] = c

    seen = set()
    for p in products:
        s = clean_slug(p.get("slug"), str(p["id"])[:8])
        if s in seen:
            s = f"{s}-{str(p['id'])[:6]}"
        seen.add(s)
        p["_slug"], p["_path"] = s, url_path("product", s)

    by_cat = {}
    for p in products:
        cid = (p.get("category") or {}).get("id")
        by_cat.setdefault(cid, []).append(p)

    # --- clean generated dirs
    for d in ("product", "category"):
        shutil.rmtree(d, ignore_errors=True)

    write("assets/shop.css", CSS.strip() + "\n")
    write("assets/shop.js", JS.strip() + "\n")

    # --- product pages
    for p in products:
        cid = (p.get("category") or {}).get("id")
        cat = cats.get(cid)
        related = [r for r in by_cat.get(cid, []) if r["id"] != p["id"]][:4]
        write(os.path.join("product", p["_slug"], "index.html"), product_page(p, cat, related))

    # --- category pages
    for cid, c in cats.items():
        items = by_cat.get(cid, [])
        if not items:
            continue
        write(os.path.join("category", c["_slug"], "index.html"), category_page(c, items))

    # --- home prerender
    with open(INDEX, encoding="utf-8") as f:
        page = f.read()
    chosen = [p for p in products if float(p.get("discount_percent") or 0) > 0] or products
    chosen = chosen[:12]
    page = inject(page, "CATEGORIES", "\n".join(home_category(c) for c in cats.values() if by_cat.get(c["id"])))
    page = inject(page, "BESTSELLERS", "\n".join(home_product(p) for p in chosen))
    write(INDEX, page)

    # --- id -> new url map (for redirecting old product.html?id=...)
    write("products-map.json", json.dumps({p["id"]: p["_path"] for p in products}, ensure_ascii=False))

    # --- sitemap
    newest = max((day(p.get("updated_at") or p.get("created_at")) for p in products), default="")
    entries = []
    for sp in STATIC_PAGES:
        entries.append((SITE + sp, newest if sp == "/" else ""))
    for cid, c in cats.items():
        items = by_cat.get(cid, [])
        if items:
            lm = max(day(p.get("updated_at") or p.get("created_at")) for p in items)
            entries.append((SITE + c["_path"], lm))
    for p in products:
        entries.append((SITE + p["_path"], day(p.get("updated_at") or p.get("created_at"))))
    try:
        arts = fetch_all(ARTICLES)
        for a in arts:
            if a.get("slug"):
                entries.append((f"{SITE}/blog.html?slug={quote(a['slug'])}",
                                day(a.get("updated_at") or a.get("created_at"))))
    except Exception as e:  # noqa
        print("articles skipped:", e)
    write("sitemap.xml", sitemap(entries))

    print(f"OK: {len(products)} products, {len(cats)} categories, {len(entries)} sitemap urls")


if __name__ == "__main__":
    main()