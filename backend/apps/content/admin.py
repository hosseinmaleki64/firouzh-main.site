from django.contrib import admin
from .models import Category, Tag, Article, News


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "author",
        "status",
        "is_featured",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "category", "is_featured")
    search_fields = ("title", "slug", "excerpt")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "tags")
    readonly_fields = ("created_at", "updated_at")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "is_breaking",
        "status",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "is_breaking")
    search_fields = ("title", "slug", "summary")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")