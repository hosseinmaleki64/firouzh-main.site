from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Article, News, Category, Tag
from .serializers import (
    CategorySerializer,
    TagSerializer,
    ArticleListSerializer,
    ArticleDetailSerializer,
    ArticleCreateSerializer,
    ArticleUpdateSerializer,
    NewsListSerializer,
    NewsDetailSerializer,
    NewsCreateSerializer,
    NewsUpdateSerializer,
)
from .selectors import (
    get_categories,
    get_tags,
    get_articles_queryset,
    get_article_by_slug,
    get_news_queryset,
    get_news_by_slug,
)
from .permissions import IsAdminOrReadOnly, IsContentManager
from .pagination import ContentPagination


def _is_staff_view(user):
    return bool(
        user
        and user.is_authenticated
        and getattr(user, "role", None) in ("ADMIN", "SUPER_ADMIN")
    )


# ---------------------------------------------------------------------------
# Categories / Tags
# ---------------------------------------------------------------------------

class CategoryListAPIView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    queryset = get_categories()


class TagListAPIView(generics.ListAPIView):
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    queryset = get_tags()


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

class ArticleListCreateAPIView(generics.ListCreateAPIView):
    """
    GET  /api/content/articles/  -> لیست عمومی (فقط PUBLISHED) یا لیست کامل برای ادمین
    POST /api/content/articles/  -> ساخت مقاله (فقط ADMIN / SUPER_ADMIN)
    """
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ContentPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status", "author", "is_featured"]
    search_fields = ["title", "slug", "tags__name"]
    ordering_fields = ["created_at", "published_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return get_articles_queryset(is_staff_view=_is_staff_view(self.request.user))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ArticleCreateSerializer
        return ArticleListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class ArticleDetailAPIView(generics.RetrieveAPIView):
    """GET /api/content/articles/{slug}/ -> جزئیات مقاله برای فرانت"""
    serializer_class = ArticleDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return get_articles_queryset(is_staff_view=_is_staff_view(self.request.user))


class ArticleUpdateAPIView(generics.UpdateAPIView):
    """PATCH /api/content/articles/{id}/ -> ویرایش مقاله (فقط ادمین)"""
    serializer_class = ArticleUpdateSerializer
    permission_classes = [IsContentManager]
    queryset = Article.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"
    http_method_names = ["patch", "put"]


class ArticlePublishAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        article = get_object_or_404(Article, id=id)
        article.publish()
        return Response(ArticleDetailSerializer(article).data, status=status.HTTP_200_OK)


class ArticleDraftAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        article = get_object_or_404(Article, id=id)
        article.unpublish_to_draft()
        return Response(ArticleDetailSerializer(article).data, status=status.HTTP_200_OK)


class ArticleArchiveAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        article = get_object_or_404(Article, id=id)
        article.archive()
        return Response(ArticleDetailSerializer(article).data, status=status.HTTP_200_OK)


class ArticleDeleteAPIView(generics.DestroyAPIView):
    """DELETE /api/content/articles/{id}/delete/ -> حذف مقاله (فقط ادمین)"""
    permission_classes = [IsContentManager]
    queryset = Article.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

class NewsListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ContentPagination

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "author", "is_breaking"]
    search_fields = ["title", "slug"]
    ordering_fields = ["created_at", "published_at", "title"]
    ordering = ["-created_at"]

    def get_queryset(self):
        return get_news_queryset(is_staff_view=_is_staff_view(self.request.user))

    def get_serializer_class(self):
        if self.request.method == "POST":
            return NewsCreateSerializer
        return NewsListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class NewsDetailAPIView(generics.RetrieveAPIView):
    serializer_class = NewsDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    lookup_url_kwarg = "slug"

    def get_queryset(self):
        return get_news_queryset(is_staff_view=_is_staff_view(self.request.user))


class NewsUpdateAPIView(generics.UpdateAPIView):
    serializer_class = NewsUpdateSerializer
    permission_classes = [IsContentManager]
    queryset = News.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"
    http_method_names = ["patch", "put"]


class NewsPublishAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        news = get_object_or_404(News, id=id)
        news.publish()
        return Response(NewsDetailSerializer(news).data, status=status.HTTP_200_OK)


class NewsDraftAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        news = get_object_or_404(News, id=id)
        news.unpublish_to_draft()
        return Response(NewsDetailSerializer(news).data, status=status.HTTP_200_OK)


class NewsArchiveAPIView(APIView):
    permission_classes = [IsContentManager]

    def post(self, request, id):
        news = get_object_or_404(News, id=id)
        news.archive()
        return Response(NewsDetailSerializer(news).data, status=status.HTTP_200_OK)


class NewsDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsContentManager]
    queryset = News.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"  
    

class CategoryCreateAPIView(generics.CreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsContentManager]
    queryset = Category.objects.all()

class CategoryUpdateDeleteAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsContentManager]
    queryset = Category.objects.all()
    lookup_field = "id"
    lookup_url_kwarg = "id"