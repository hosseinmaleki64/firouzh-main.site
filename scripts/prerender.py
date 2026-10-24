import html, json, re, urllib.request

API = "https://api.firouzehco.com/api/products/public"
API_ORIGIN = "https://api.firouzehco.com"
INDEX = "index.html"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "firouzeh-prerender/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def esc(s):
    return html.escape(str(s or ""), quote=True)


def media(path):
    if not path:
        return "image1/logo.png"
    return path if path.startswith("http") else API_ORIGIN + path


def toman(n):
    s = f"{int(round(float(n))):,}".replace(",", "٬")
    return s.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")) + " تومان"


def category_html(c):
    img = ""
    if c.get("image"):
        img = f'<img src="{esc(media(c["image"]))}" alt="{esc(c["name"])}" loading="lazy">'
    return (
        '<div class="category-card">'
        f'<div class="image-placeholder">{img}</div>'
        f'<strong>{esc(c["name"])}</strong>'
        f'<a href="finger-food.html?cat={esc(c["id"])}" class="category-button">مشاهده محصولات</a>'
        '</div>'
    )


def product_html(p):
    imgs = p.get("images") or []
    src = media(imgs[0]["image"]) if imgs else "image1/logo.png"
    alt = (imgs[0].get("alt_text") if imgs else "") or p["name"]
    desc = p.get("description") or ""
    short = desc[:50] + ("..." if len(desc) > 50 else "")
    price = p.get("final_price") or p.get("price") or 0
    return (
        '<div class="best-seller-card">'
        f'<a href="product.html?id={esc(p["id"])}" class="bs-link">'
        f'<div class="best-seller-image"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy"></div>'
        f'<h3 class="best-seller-name">{esc(p["name"])}</h3>'
        f'<p class="best-seller-description">{esc(short)}</p>'
        f'<div class="best-seller-price">{toman(price)}</div>'
        '</a></div>'
    )


def inject(page, name, content):
    pattern = re.compile(rf"(<!--PRERENDER:{name}-->)(.*?)(<!--/PRERENDER:{name}-->)", re.S)
    if not pattern.search(page):
        raise SystemExit(f"marker {name} not found in {INDEX}")
    return pattern.sub(lambda m: m.group(1) + "\n" + content + "\n" + m.group(3), page)


def main():
    cats = get(f"{API}/categories/")
    if isinstance(cats, dict):
        cats = cats.get("results", [])
    data = get(f"{API}/?page_size=30&ordering=-created_at")
    prods = [p for p in data.get("results", []) if p.get("is_active", True)]
    chosen = [p for p in prods if float(p.get("discount_percent") or 0) > 0] or prods
    chosen = chosen[:12]
    if not cats or not chosen:
        raise SystemExit("API returned no data; index.html left unchanged")

    with open(INDEX, encoding="utf-8") as f:
        page = f.read()
    page = inject(page, "CATEGORIES", "\n".join(category_html(c) for c in cats))
    page = inject(page, "BESTSELLERS", "\n".join(product_html(p) for p in chosen))
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"OK: {len(cats)} categories, {len(chosen)} products")


main()