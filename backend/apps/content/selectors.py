from .models import Article, News, Category, Tag, PublishStatus


# ---------------------------------------------------------------------------
# Categories / Tags
# ---------------------------------------------------------------------------

def get_categories():
    return Category.objects.all().order_by("name")


def get_tags():
    return Tag.objects.all().order_by("name")


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

def get_articles_queryset(*, is_staff_view: bool):
    """
    is_staff_view=True  -> پنل مدیریت: همه‌ی وضعیت‌ها قابل مشاهده است.
    is_staff_view=False -> سایت عمومی: فقط مقالات PUBLISHED نمایش داده می‌شوند.
    """
    qs = Article.objects.select_related("category", "author").prefetch_related("tags")

    if not is_staff_view:
        qs = qs.filter(status=PublishStatus.PUBLISHED)

    return qs


def get_article_by_slug(slug, *, is_staff_view: bool):
    qs = get_articles_queryset(is_staff_view=is_staff_view)
    return qs.get(slug=slug)


def get_related_articles(article, limit=4):
    return (
        Article.objects.filter(
            category=article.category,
            status=PublishStatus.PUBLISHED,
        )
        .exclude(id=article.id)
        .select_related("category", "author")
        .order_by("-published_at")[:limit]
    )


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def get_news_queryset(*, is_staff_view: bool):
    qs = News.objects.select_related("author")

    if not is_staff_view:
        qs = qs.filter(status=PublishStatus.PUBLISHED)

    return qs


def get_news_by_slug(slug, *, is_staff_view: bool):
    qs = get_news_queryset(is_staff_view=is_staff_view)
    return qs.get(slug=slug)