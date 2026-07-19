from rest_framework import serializers

from .models import Category, Tag, Article, News


# ---------------------------------------------------------------------------
# Category / Tag
# ---------------------------------------------------------------------------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "created_at")
        read_only_fields = ("id", "slug", "created_at")


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "slug")


# ---------------------------------------------------------------------------
# Article
# ---------------------------------------------------------------------------

class AuthorMiniSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()


class ArticleListSerializer(serializers.ModelSerializer):
    """برای لیست عمومی مقالات و جدول ادمین."""

    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorMiniSerializer(read_only=True)
    reading_time_minutes = serializers.IntegerField(read_only=True)

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "cover_image",
            "category",
            "tags",
            "author",
            "status",
            "is_featured",
            "reading_time_minutes",
            "published_at",
            "created_at",
        )


class ArticleDetailSerializer(serializers.ModelSerializer):
    """برای صفحه فرانت مقاله + پیش نمایش زنده."""

    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    author = AuthorMiniSerializer(read_only=True)
    reading_time_minutes = serializers.IntegerField(read_only=True)
    related_articles = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "tags",
            "author",
            "status",
            "is_featured",
            "reading_time_minutes",
            "published_at",
            "created_at",
            "updated_at",
            "related_articles",
        )

    def get_related_articles(self, obj):
        from .selectors import get_related_articles

        related = get_related_articles(obj)
        return ArticleListSerializer(related, many=True).data


class ArticleCreateSerializer(serializers.ModelSerializer):
    """ساخت مقاله - نویسنده از request.user گرفته می‌شود، نه از بدنه درخواست."""

    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "tags",
            "status",
            "is_featured",
        )
        extra_kwargs = {
            "slug": {"required": False},
        }

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["author"] = request.user
        return super().create(validated_data)


class ArticleUpdateSerializer(serializers.ModelSerializer):
    """
    ویرایش مقاله.
    عمداً author و status اینجا نیستند: تغییر وضعیت فقط از طریق
    اکشن‌های publish / draft / archive انجام می‌شود.
    """

    class Meta:
        model = Article
        fields = (
            "title",
            "slug",
            "excerpt",
            "content",
            "cover_image",
            "category",
            "tags",
            "is_featured",
        )


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class NewsListSerializer(serializers.ModelSerializer):
    author = AuthorMiniSerializer(read_only=True)

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "image",
            "is_breaking",
            "status",
            "author",
            "published_at",
            "created_at",
        )


class NewsDetailSerializer(serializers.ModelSerializer):
    author = AuthorMiniSerializer(read_only=True)

    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "content",
            "image",
            "is_breaking",
            "status",
            "author",
            "published_at",
            "created_at",
            "updated_at",
        )


class NewsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = (
            "id",
            "title",
            "slug",
            "summary",
            "content",
            "image",
            "is_breaking",
            "status",
        )
        extra_kwargs = {
            "slug": {"required": False},
        }

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["author"] = request.user
        return super().create(validated_data)


class NewsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = (
            "title",
            "slug",
            "summary",
            "content",
            "image",
            "is_breaking",
        )