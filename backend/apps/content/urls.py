from django.urls import path
from .views import (
    CategoryListAPIView,
    CategoryCreateAPIView,
    CategoryUpdateDeleteAPIView,
    TagListAPIView,
    ArticleListCreateAPIView,
    ArticleUpdateAPIView,
    ArticleDetailAPIView,
    ArticlePublishAPIView,
    ArticleDraftAPIView,
    ArticleArchiveAPIView,
    ArticleDeleteAPIView,
    NewsListCreateAPIView,
    NewsUpdateAPIView,
    NewsDetailAPIView,
    NewsPublishAPIView,
    NewsDraftAPIView,
    NewsArchiveAPIView,
    NewsDeleteAPIView,
)

urlpatterns = [
    # Taxonomy
    path("categories/", CategoryListAPIView.as_view(), name="content-categories"),
    path("tags/", TagListAPIView.as_view(), name="content-tags"),

    # Articles
    # NOTE: <int:id>/ patterns must stay above <slug:slug>/ so purely-numeric
    # slugs never get swallowed by the int converter's routes.
    path("articles/", ArticleListCreateAPIView.as_view(), name="articles-list-create"),
    path("articles/<int:id>/", ArticleUpdateAPIView.as_view(), name="articles-update"),
    path("articles/<int:id>/delete/", ArticleDeleteAPIView.as_view(), name="articles-delete"),
    path("articles/<int:id>/publish/", ArticlePublishAPIView.as_view(), name="articles-publish"),
    path("articles/<int:id>/draft/", ArticleDraftAPIView.as_view(), name="articles-draft"),
    path("articles/<int:id>/archive/", ArticleArchiveAPIView.as_view(), name="articles-archive"),
    path("articles/<slug:slug>/", ArticleDetailAPIView.as_view(), name="articles-detail"),

    # News
    path("news/", NewsListCreateAPIView.as_view(), name="news-list-create"),
    path("news/<int:id>/", NewsUpdateAPIView.as_view(), name="news-update"),
    path("news/<int:id>/delete/", NewsDeleteAPIView.as_view(), name="news-delete"),
    path("news/<int:id>/publish/", NewsPublishAPIView.as_view(), name="news-publish"),
    path("news/<int:id>/draft/", NewsDraftAPIView.as_view(), name="news-draft"),
    path("news/<int:id>/archive/", NewsArchiveAPIView.as_view(), name="news-archive"),
    path("news/<slug:slug>/", NewsDetailAPIView.as_view(), name="news-detail"),
    path("categories/create/", CategoryCreateAPIView.as_view(), name="content-categories-create"),
    path("categories/<int:id>/", CategoryUpdateDeleteAPIView.as_view(), name="content-categories-update"),
]