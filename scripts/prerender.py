#!/usr/bin/env python3
"""
Firouzeh static build (GitHub Actions) - نسخه ۳: با ظاهر خودِ سایت
 
قالب‌ها:   product.html  و  finger-food.html   (همان فایل‌های خودتان)
خروجی‌ها:
  /product/<slug>/index.html     از روی product.html
  /category/<slug>/index.html    از روی finger-food.html
  index.html و finger-food.html  (پیش‌رندر دسته‌ها/محصولات بین علامت‌های PRERENDER)
  sitemap.xml  و  products-map.json
پوشه‌های product/ و category/ کاملاً خودکارند؛ دستی چیزی داخلشان نگذارید.
"""
import html
import json
import os
import re
import shutil
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import quote
 
SITE = "https://firouzehco.com"
API_ORIGIN = "https://api.firouzehco.com"
API = API_ORIGIN + "/api/products/public"
ARTICLES = API_ORIGIN + "/api/content/articles/?status=PUBLISHED&ordering=-created_at&page_size=100"
INDEX = "index.html"
PRODUCT_TPL = "product.html"
LIST_TPL = "finger-food.html"
CONTENT_FILE = "seo-content.json"
REVIEWS_API = API_ORIGIN + "/api/reviews/public"
HOME_ARTICLES = API_ORIGIN + "/api/content/articles/?status=PUBLISHED&ordering=-created_at&page_size=2"
PHONE = "۰۴۱-۳۳۳۶۷۰۵۲"
MOBILE = "۰۹۱۴۲۸۳۰۳۲۸"
 
UNITS = {"g": "گرم", "kg": "کیلوگرم", "ml": "میلی‌لیتر", "l": "لیتر", "gram": "گرم"}
STATIC_PAGES = [
    "/", "/finger-food.html", "/drinks.html", "/about.html", "/contact.html",
    "/FAQ.html", "/cooperation.html", "/vip-customers.html", "/blogs.html", "/terms.html",
]
WARNINGS = []
 
# ---------------------------------------------------------------- helpers
 
def get(url):
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "firouzeh-build/3.0", "Accept": "application/json"})
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
 
 
def num_fa(n):
    try:
        v = int(round(float(n)))
    except Exception:  # noqa
        v = 0
    return fa(f"{v:,}".replace(",", "٬"))
 
 
def toman(n):
    return num_fa(n) + " تومان"
 
 
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
 
 
def write(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
 
 
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()
 
 
def inject(page, name, content):
    pattern = re.compile(rf"(<!--PRERENDER:{name}-->)(.*?)(<!--/PRERENDER:{name}-->)", re.S)
    if not pattern.search(page):
        raise SystemExit(f"marker {name} not found")
    return pattern.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(3), page)
 
 
def rep(s, pattern, func, label):
    """جایگزینی یک‌باره؛ اگر الگو پیدا نشد هشدار می‌دهد (و فایل را خراب نمی‌کند)."""
    new, n = re.subn(pattern, func, s, count=1, flags=re.S)
    if n == 0:
        WARNINGS.append(label)
    return new
 
 
def breadcrumb_ld(trail):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u}
            for i, (n, u) in enumerate(trail)
        ],
    }
 
# ---------------------------------------------------------------- template surgery
 
def strip_head_seo(s):
    """حذف عنوان/توضیحات/canonical/og/اسکیماهای ثابتِ قالب تا مقدارهای درست جایگزین شوند."""
    s = re.sub(r"<title>.*?</title>\s*", "", s, flags=re.S | re.I)
    s = re.sub(r"<meta\s+name=[\"'](?:description|keywords|robots)[\"'][^>]*>\s*", "", s, flags=re.I)
    s = re.sub(r"<meta\s+(?:property|name)=[\"'](?:og|twitter):[^\"']*[\"'][^>]*>\s*", "", s, flags=re.I)
    s = re.sub(r"<link\s+rel=[\"']canonical[\"'][^>]*>\s*", "", s, flags=re.I)
    s = re.sub(r"<script\s+type=[\"']application/ld\+json[\"']>.*?</script>\s*", "", s, flags=re.S | re.I)
    # کد هدایت آدرس‌های قدیمی فقط برای خودِ product.html لازم است
    s = re.sub(r"<script>\s*\(function\(\)\{\s*var id=new URLSearchParams.*?</script>\s*", "", s, flags=re.S)
    return s
 
 
def head_block(title, desc, canon, image, schemas, js_var=""):
    sch = "".join(f'<script type="application/ld+json">{ld(x)}</script>\n' for x in schemas)
    return f"""<base href="/">
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
{js_var}{sch}"""
 
 
def insert_head(s, block):
    m = re.search(r"<meta\s+charset=[^>]*>", s, re.I)
    if m:
        return s[: m.end()] + "\n" + block + s[m.end():]
    m = re.search(r"<head[^>]*>", s, re.I)
    if m:
        return s[: m.end()] + "\n" + block + s[m.end():]
    raise SystemExit("no <head> found in template")
 
 
# ---------------------------------------------------------------- SEO content blocks
 
SEO_CSS = (".seo-block{max-width:1000px;margin:40px auto;padding:28px;background:#fff;border-radius:16px;"
           "box-shadow:0 4px 20px rgba(0,0,0,.08);line-height:2;text-align:right}"
           ".seo-block h2{color:var(--primary-color);font-size:1.5rem;margin-bottom:14px}"
           ".seo-block h3{font-size:1.15rem;margin:18px 0 6px;color:var(--text-dark)}"
           ".seo-block p{margin-bottom:12px}"
           ".seo-block a{color:var(--secondary-color);font-weight:600}"
           ".seo-spec{width:100%;border-collapse:collapse;margin:14px 0}"
           ".seo-spec th,.seo-spec td{padding:10px 12px;border-bottom:1px solid var(--neutral-color);text-align:right}"
           ".seo-spec th{width:32%;background:rgba(38,166,154,.06);color:var(--secondary-color)}"
           "@media(max-width:576px){.seo-block{padding:18px;margin:24px 0}.seo-spec th{width:40%}}")
 
 
def load_content():
    if not os.path.exists(CONTENT_FILE):
        return {}
    try:
        data = json.loads(read(CONTENT_FILE))
    except ValueError as e:
        raise SystemExit(f"{CONTENT_FILE} فرمت JSON درست ندارد ({e}). معمولاً یک ویرگول یا گیومه جا افتاده؛ "
                         "فایل را در jsonlint.com بررسی کنید. چیزی تغییر نکرد.")
    return data if isinstance(data, dict) else {}
 
 
def render_text(text):
    """پاراگراف‌ها با خط خالی جدا می‌شوند؛ خطی که با ## شروع شود تیتر کوچک است؛ [متن](آدرس) لینک می‌شود."""
    out = []
    for part in re.split(r"\n\s*\n", (text or "").strip()):
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            out.append(f"<h3>{esc(part[3:].strip())}</h3>")
            continue
        h = esc(part).replace("\n", "<br>")
        h = re.sub(r"\[([^\]]+)\]\((/[^)\s]*|https?://[^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', h)
        out.append(f"<p>{h}</p>")
    return "\n".join(out)
 
 
def render_faq(items, heading):
    rows = []
    for it in items or []:
        q, a = (it.get("q") or "").strip(), (it.get("a") or "").strip()
        if q and a:
            rows.append(f"<h3>{esc(q)}</h3><p>{esc(a)}</p>")
    return f"<h2>{esc(heading)}</h2>" + "".join(rows) if rows else ""
 
 
def order_paragraph(name):
    return (f"<h3>سفارش {esc(name)} در تبریز</h3>"
            f"<p>برای سفارش می‌توانید از همین صفحه به سبد خرید اضافه کنید یا با شماره {PHONE} و واتساپ {MOBILE} "
            f"تماس بگیرید. ارسال در تبریز و شهرستان‌های اطراف انجام می‌شود.</p>")
 
 
def put_block(s, anchor, name, content):
    """بلوک را بین علامت‌های SEO می‌گذارد؛ اگر از قبل بود جایگزین می‌کند (بدون تکرار)."""
    start, end = f"<!--SEO:{name}-->", f"<!--/SEO:{name}-->"
    block = f"{start}\n{content}\n{end}" if content else f"{start}{end}"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if pat.search(s):
        return pat.sub(lambda m: block, s, count=1)
    m = re.search(anchor, s)
    if not m:
        WARNINGS.append(f"محل قرار گرفتن بلوک SEO:{name} پیدا نشد")
        return s
    return s[: m.start()] + block + "\n" + s[m.start():]
 
 
def ensure_style(s):
    if 'id="seo-style"' in s:
        return s
    return s.replace("</head>", f'<style id="seo-style">{SEO_CSS}</style>\n</head>', 1)
 
 
def product_seo_block(p, cat, extra):
    extra = extra or {}
    name = p["name"]
    base, final, disc = prices(p)
    desc = (p.get("description") or "").strip()
    text = (extra.get("text") or "").strip() or (desc if len(desc) > 160 else "")
    rows = []
    if cat:
        rows.append(("دسته‌بندی", f'<a href="{esc(cat["_path"])}">{esc(cat["name"])}</a>'))
    price = toman(final) + (f' (قیمت قبل از تخفیف: {toman(base)})' if disc > 0 else "")
    rows.append(("قیمت", esc(price)))
    if p.get("weight_value"):
        unit = UNITS.get(str(p.get("weight_unit") or "").lower(), p.get("weight_unit") or "")
        try:
            wv = fa("%g" % float(p["weight_value"]))
        except Exception:  # noqa
            wv = str(p["weight_value"])
        rows.append(("وزن", esc(f"{wv} {unit}".strip())))
    raw = names(p.get("raw_materials"))
    comps = names(p.get("components"))
    if raw:
        rows.append(("مواد اولیه", esc("، ".join(raw))))
    if comps:
        rows.append(("محتویات پک", esc("، ".join(comps))))
    for k, v in (extra.get("specs") or {}).items():
        rows.append((esc(k), esc(v)))
    table = ('<table class="seo-spec">' + "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows) + "</table>")
    parts = [f"<h2>درباره {esc(name)}</h2>"]
    if text:
        parts.append(render_text(text))
    parts.append(f"<h3>مشخصات {esc(name)}</h3>")
    parts.append(table)
    faq = render_faq(extra.get("faq"), f"سوالات متداول درباره {name}")
    if faq:
        parts.append(faq)
    parts.append(order_paragraph(name))
    return '<section class="seo-block">\n' + "\n".join(parts) + "\n</section>"
 
 
def list_seo_block(name, extra):
    extra = extra or {}
    if not (extra.get("text") or extra.get("faq")):
        return ""
    parts = [f"<h2>{esc(extra.get('title') or 'درباره ' + name)}</h2>", render_text(extra.get("text"))]
    faq = render_faq(extra.get("faq"), "سوالات متداول")
    if faq:
        parts.append(faq)
    return '<section class="seo-block">\n' + "\n".join(parts) + "\n</section>"
 
 
# ---------------------------------------------------------------- product page
 
def related_card(p):
    imgs = p.get("images") or []
    src = media(imgs[0]["image"]) if imgs else SITE + "/image1/logo.png"
    _, final, _ = prices(p)
    return (f'<a href="{esc(p["_path"])}" style="text-decoration:none; color:inherit; display:block;">'
            f'<div class="rec-item"><img src="{esc(src)}" alt="{esc(p["name"])}" loading="lazy">'
            f'<div class="rec-content"><p>{esc(p["name"])}</p><span>{toman(final)}</span></div></div></a>')
 
 
def build_product(tpl, p, cat, related, extra=None):
    name = p["name"]
    base, final, disc = prices(p)
    imgs = [(media(i.get("image")), (i.get("alt_text") or "")) for i in (p.get("images") or []) if i.get("image")]
    canon = SITE + p["_path"]
    cat_name = cat["name"] if cat else "محصولات"
    cat_path = cat["_path"] if cat else "/finger-food.html"
    raw = names(p.get("raw_materials"))
    comps = names(p.get("components"))
    desc_txt = (p.get("description") or "").strip()
 
    meta_desc = (p.get("meta_description") or "").strip()
    if not meta_desc:
        meta_desc = f"سفارش آنلاین {name} در تبریز؛ قیمت {toman(final)}. " + (desc_txt or f"از محصولات {cat_name} فیروزه با ارسال سریع.")
    meta_desc = trim(meta_desc)
    title = f"{name} | سفارش آنلاین در تبریز | فیروزه"
    main_img = imgs[0][0] if imgs else SITE + "/image1/logo.png"
    main_alt = (imgs[0][1] if imgs else "") or name
 
    prod_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": trim(desc_txt or meta_desc, 300),
        "sku": str(p["id"]),
        "category": cat_name,
        "brand": {"@type": "Brand", "name": "فیروزه"},
        "offers": {
            "@type": "Offer",
            "url": canon,
            "priceCurrency": "IRR",
            "price": str(int(round(final * 10))),
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }
    if imgs:
        prod_ld["image"] = [u for u, _ in imgs]
    crumbs = [("خانه", "/"), (cat_name, cat_path), (name, p["_path"])]
 
    s = strip_head_seo(tpl)
    s = insert_head(s, head_block(title, meta_desc, canon, main_img,
                                  [prod_ld, breadcrumb_ld(crumbs)],
                                  js_var=f'<script>window.PRODUCT_ID="{esc(p["id"])}";</script>\n'))
 
    s = rep(s, r'(<h1[^>]*id="detail-title"[^>]*>)(.*?)(</h1>)',
            lambda m: m.group(1) + esc(name) + m.group(3), "h1#detail-title")
    if cat:
        s = rep(s, r'<div id="detail-category"[^>]*></div>',
                lambda m: f'<div id="detail-category" class="weight-badge" style="display:inline-block;">{esc(cat_name)}</div>',
                "#detail-category")
    s = rep(s, r'(<p[^>]*id="detail-desc"[^>]*>)(.*?)(</p>)',
            lambda m: m.group(1) + esc(desc_txt) + m.group(3), "p#detail-desc")
    if raw:
        s = rep(s, r'<li id="detail-ingredients"[^>]*></li>',
                lambda m: f'<li id="detail-ingredients" style="display:list-item;">مواد اولیه: {esc("، ".join(raw))}</li>',
                "#detail-ingredients")
    if comps:
        s = rep(s, r'<li id="detail-components"[^>]*></li>',
                lambda m: f'<li id="detail-components" style="display:list-item;">محتویات پک: {esc("، ".join(comps))}</li>',
                "#detail-components")
    s = rep(s, r'(<span id="detail-price"[^>]*>)(.*?)(</span>)',
            lambda m: m.group(1) + num_fa(final) + m.group(3), "#detail-price")
    s = rep(s, r'<img[^>]*id="detail-image"[^>]*>',
            lambda m: f'<img src="{esc(main_img)}" alt="{esc(main_alt)}" class="product-main-image" id="detail-image" fetchpriority="high">',
            "#detail-image")
    if len(imgs) > 1:
        thumbs = "".join(
            f'<img src="{esc(u)}" alt="{esc(a or name)}" class="product-thumbnail{" active" if i == 0 else ""}" loading="lazy">'
            for i, (u, a) in enumerate(imgs))
        s = rep(s, r'(<div class="product-thumbnails" id="thumbnails-container">)(.*?)(</div>)',
                lambda m: m.group(1) + thumbs + m.group(3), "#thumbnails-container")
    if related:
        cards = "".join(related_card(r) for r in related)
        s = rep(s, r'(<div class="rec-grid" id="complementaryGrid">)(.*?)(</div>)',
                lambda m: m.group(1) + cards + m.group(3), "#complementaryGrid")
    s = put_block(s, r'<section class="recommendations">', "PRODUCT", product_seo_block(p, cat, extra))
    return ensure_style(s)
 
# ---------------------------------------------------------------- category / list pages
 
def list_card(p):
    imgs = p.get("images") or []
    src = media(imgs[0]["image"]) if imgs else SITE + "/image1/logo.png"
    alt = (imgs[0].get("alt_text") if imgs else "") or p["name"]
    base, final, disc = prices(p)
    d = p.get("description") or ""
    short = d[:50] + ("..." if len(d) > 50 else "")
    badge = f'<div class="product-badge">٪{fa(int(disc))} تخفیف</div>' if disc > 0 else ""
    old = f' <span class="old-price">{num_fa(base)}</span>' if disc > 0 else ""
    return (f'<div class="product-card fade-in"><div class="product-image">'
            f'<img src="{esc(src)}" alt="{esc(alt)}" loading="lazy">{badge}</div>'
            f'<div class="product-content"><h3>{esc(p["name"])}</h3><p>{esc(short)}</p>'
            f'<div class="product-price"><i class="fas fa-tag"></i> {toman(final)}{old}</div>'
            f'<a href="{esc(p["_path"])}" class="add-to-cart" style="text-decoration:none; display:flex;">'
            f'<i class="fas fa-eye"></i> مشاهده و خرید</a></div></div>')
 
 
def build_category(tpl, c, items, extra=None):
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
    s = strip_head_seo(tpl)
    s = insert_head(s, head_block(title, desc, canon, img, [lst, breadcrumb_ld(crumbs)],
                                  js_var=f'<script>window.CATEGORY_ID="{esc(c["id"])}";</script>\n'))
    s = rep(s, r'(<h1[^>]*id="heroTitle"[^>]*>)(.*?)(</h1>)',
            lambda m: m.group(1) + f'<i class="fas fa-utensils"></i> سفارش آنلاین {esc(name)} در تبریز' + m.group(3),
            "#heroTitle")
    s = rep(s, r'(<p[^>]*id="heroDesc"[^>]*>)(.*?)(</p>)',
            lambda m: m.group(1) + f'محصولات دسته‌بندی «{esc(name)}» فیروزه را با قیمت ببینید و سفارش دهید؛ ارسال سریع در تبریز و شهرستان‌های اطراف.' + m.group(3),
            "#heroDesc")
    s = inject(s, "GRID", "\n".join(list_card(p) for p in items))
    s = put_block(s, r'<section class="contact-section">', "LIST", list_seo_block(name, extra))
    return ensure_style(s)
 
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
 
 
# ---------------------------------------------------------------- reviews & articles on home
 
def time_ago_fa(iso):
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        sec = int((datetime.now(timezone.utc) - d).total_seconds())
    except Exception:  # noqa
        return ""
    if sec < 60:
        return "همین الان"
    mins = sec // 60
    if mins < 60:
        return f"{fa(mins)} دقیقه پیش"
    hours = mins // 60
    if hours < 24:
        return f"{fa(hours)} ساعت پیش"
    days = hours // 24
    if days < 30:
        return f"{fa(days)} روز پیش"
    months = days // 30
    if months < 12:
        return f"{fa(months)} ماه پیش"
    return f"{fa(months // 12)} سال پیش"
 
 
def review_card(r):
    name = (r.get("customer_display_name") or "").strip() or "مشتری فیروزه"
    text = (r.get("comment") or "").strip()
    initial = name[:1] or "ف"
    try:
        n = int(round(float(r.get("rating") or 0)))
    except Exception:  # noqa
        n = 0
    stars = "".join("★" if i <= n else "☆" for i in range(1, 6))
    verified = ('<span class="review-verified"><i class="fas fa-check-circle"></i> خرید تایید‌شده</span>'
                if r.get("is_verified_purchase") else "")
    imgs = ""
    if r.get("images"):
        items = []
        for im in r["images"]:
            u = media(im.get("image"))
            items.append(f'<div class="review-image-item"><img src="{esc(u)}" '
                         f'alt="عکس ارسالی {esc(name)}" loading="lazy" onclick="openLightbox(\'{esc(u)}\')"></div>')
        imgs = '<div class="review-images">' + "".join(items) + "</div>"
    ago = time_ago_fa(r.get("created_at"))
    footer = f'<div class="review-footer"><i class="far fa-clock"></i><span>{ago}</span></div>' if ago else ""
    return ('<div class="user-review"><div class="review-header">'
            f'<div class="review-avatar">{esc(initial)}</div><div class="review-name-wrap">'
            f'<span class="review-name">{esc(name)}{verified}</span>'
            f'<div class="rating">{stars} ({esc(r.get("rating"))}/۵)</div></div></div>'
            f'<p>{esc(text)}</p>{imgs}{footer}</div>')
 
 
def home_blog_card(a):
    cover = media(a.get("cover_image")) if a.get("cover_image") else SITE + "/image1/logo.png"
    ex = (a.get("excerpt") or "")
    short = ex[:80] + ("..." if len(ex) > 80 else "")
    return (f'<a href="blog.html?slug={quote(a["slug"])}" class="blog-card">'
            f'<div class="blog-image"><img src="{esc(cover)}" alt="{esc(a["title"])}" loading="lazy"></div>'
            f'<strong>{esc(a["title"])}</strong><p>{esc(short)}</p></a>')
 
 
def inject_optional(page, name, content):
    try:
        return inject(page, name, content)
    except SystemExit:
        WARNINGS.append(f"علامت PRERENDER:{name} در index.html نیست (این بخش رد شد)")
        return page
 
 
def prerender_reviews_and_blogs(page):
    # نظرات مشتریان
    try:
        stats = get(f"{REVIEWS_API}/stats/")
        data = get(f"{REVIEWS_API}/?ordering=-rating&page_size=10")
        reviews = [r for r in (data.get("results") or []) if (r.get("comment") or "").strip()]
        total = int(stats.get("total_reviews") or 0)
        avg = float(stats.get("average_rating") or 0)
        if reviews:
            page = inject_optional(page, "REVIEWS", "\n".join(review_card(r) for r in reviews))
        if total > 0:
            avg_txt = fa(int(avg)) if avg == int(avg) else fa(f"{avg:.1f}".replace(".", "٫"))
            badge = f"میانگین {avg_txt} از ۵ — بر اساس {fa(total)} نظر مشتریان"
            page = re.sub(r'(<div class="reviews-badge" id="reviewsBadge">)(.*?)(</div>)',
                          lambda m: m.group(1) + badge + m.group(3), page, count=1, flags=re.S)
    except Exception as e:  # noqa
        WARNINGS.append(f"نظرات مشتریان دریافت نشد ({e}); محتوای قبلی دست‌نخورده ماند")
    # دو مقاله آخر
    try:
        arts = (get(HOME_ARTICLES).get("results") or [])
        arts = [a for a in arts if a.get("slug") and a.get("title")]
        if arts:
            page = inject_optional(page, "BLOGS", "\n".join(home_blog_card(a) for a in arts))
    except Exception as e:  # noqa
        WARNINGS.append(f"مقالات صفحه اصلی دریافت نشد ({e}); محتوای قبلی دست‌نخورده ماند")
    return page
 
 
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
 
# ---------------------------------------------------------------- validation
 
def load_templates():
    ptpl, ltpl, home = read(PRODUCT_TPL), read(LIST_TPL), read(INDEX)
    problems = []
    for key in ('id="detail-title"', 'id="detail-image"', 'id="detail-price"',
                'id="detail-desc"', 'id="complementaryGrid"'):
        if key not in ptpl:
            problems.append(f"{PRODUCT_TPL}: عنصر {key} پیدا نشد")
    if "window.PRODUCT_ID" not in ptpl:
        problems.append(f"{PRODUCT_TPL}: ویرایش جاوااسکریپت (window.PRODUCT_ID) انجام نشده")
    for key in ('id="heroTitle"', 'id="heroDesc"', "<!--PRERENDER:GRID-->", "<!--/PRERENDER:GRID-->"):
        if key not in ltpl:
            problems.append(f"{LIST_TPL}: {key} پیدا نشد")
    if "window.CATEGORY_ID" not in ltpl:
        problems.append(f"{LIST_TPL}: ویرایش جاوااسکریپت (window.CATEGORY_ID) انجام نشده")
    if '<section class="recommendations">' not in ptpl:
        WARNINGS.append(f"{PRODUCT_TPL}: بخش recommendations پیدا نشد؛ بلوک توضیحات محصول گذاشته نمی‌شود")
    if '<section class="contact-section">' not in ltpl:
        WARNINGS.append(f"{LIST_TPL}: بخش contact-section پیدا نشد؛ بلوک توضیحات دسته گذاشته نمی‌شود")
    for key in ("<!--PRERENDER:CATEGORIES-->", "<!--PRERENDER:BESTSELLERS-->"):
        if key not in home:
            problems.append(f"{INDEX}: علامت {key} پیدا نشد")
    if problems:
        raise SystemExit("قالب‌ها آماده نیستند؛ چیزی تغییر نکرد:\n - " + "\n - ".join(problems))
    return ptpl, ltpl, home
 
# ---------------------------------------------------------------- main
 
def main():
    ptpl, ltpl, home = load_templates()
    content = load_content()
    cont_prod = content.get("products") or {}
    cont_cat = content.get("categories") or {}
 
    cats_raw = get(f"{API}/categories/")
    if isinstance(cats_raw, dict):
        cats_raw = cats_raw.get("results", [])
    products = fetch_all(f"{API}/?page_size=50&ordering=-created_at")
    products = [p for p in products if p.get("is_active", True) is not False]
    if not cats_raw or not products:
        raise SystemExit("API returned no data; nothing changed")
 
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
        by_cat.setdefault((p.get("category") or {}).get("id"), []).append(p)
 
    for d in ("product", "category"):
        shutil.rmtree(d, ignore_errors=True)
 
    # --- product pages (قالب: product.html)
    for p in products:
        cid = (p.get("category") or {}).get("id")
        related = [r for r in by_cat.get(cid, []) if r["id"] != p["id"]][:4]
        write(os.path.join("product", p["_slug"], "index.html"),
              build_product(ptpl, p, cats.get(cid), related, cont_prod.get(p["_slug"])))
 
    # --- category pages (قالب: finger-food.html)
    for cid, c in cats.items():
        items = by_cat.get(cid, [])
        if items:
            extra = cont_cat.get(c["_slug"]) or cont_cat.get(c["name"])
            write(os.path.join("category", c["_slug"], "index.html"), build_category(ltpl, c, items, extra))
 
    # --- finger-food.html: پیش‌رندر همه محصولات
    base_page = inject(ltpl, "GRID", "\n".join(list_card(p) for p in products))
    base_page = put_block(base_page, r'<section class="contact-section">', "LIST", list_seo_block("محصولات", cont_cat.get("__all__")))
    write(LIST_TPL, ensure_style(base_page))
 
    # --- index.html
    chosen = [p for p in products if float(p.get("discount_percent") or 0) > 0] or products
    page = inject(home, "CATEGORIES", "\n".join(home_category(c) for c in cats.values() if by_cat.get(c["id"])))
    page = inject(page, "BESTSELLERS", "\n".join(home_product(p) for p in chosen[:12]))
    page = prerender_reviews_and_blogs(page)
    write(INDEX, page)
 
    write("products-map.json", json.dumps({p["id"]: p["_path"] for p in products}, ensure_ascii=False))
 
    # --- sitemap
    newest = max((day(p.get("updated_at") or p.get("created_at")) for p in products), default="")
    entries = [(SITE + sp, newest if sp == "/" else "") for sp in STATIC_PAGES]
    for cid, c in cats.items():
        items = by_cat.get(cid, [])
        if items:
            entries.append((SITE + c["_path"], max(day(p.get("updated_at") or p.get("created_at")) for p in items)))
    for p in products:
        entries.append((SITE + p["_path"], day(p.get("updated_at") or p.get("created_at"))))
    try:
        for a in fetch_all(ARTICLES):
            if a.get("slug"):
                entries.append((f"{SITE}/blog.html?slug={quote(a['slug'])}",
                                day(a.get("updated_at") or a.get("created_at"))))
    except Exception as e:  # noqa
        print("articles skipped:", e)
    write("sitemap.xml", sitemap(entries))
 
    for w in sorted(set(WARNINGS)):
        print("WARN: بخشی از قالب پیدا نشد ->", w)
    print(f"OK: {len(products)} products, {len(cats)} categories, {len(entries)} sitemap urls")
 
 
if __name__ == "__main__":
    main()
 