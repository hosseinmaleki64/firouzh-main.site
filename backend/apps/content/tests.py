from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.authentication.models import User, UserRole
from .models import Category, Tag, Article, PublishStatus


def _tiny_image():
    # 1x1 transparent gif, valid enough for ImageField during tests
    content = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9"
        b"\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02"
        b"\x02D\x01\x00;"
    )
    return SimpleUploadedFile("cover.gif", content, content_type="image/gif")


class ArticleModelTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            phone="09141234567", full_name="نویسنده تست", password="StrongPass123"
        )
        self.category = Category.objects.create(name="اخبار")

    def test_slug_auto_generated_from_title(self):
        article = Article.objects.create(
            title="مقاله تستی",
            excerpt="خلاصه",
            content="این یک متن آزمایشی است " * 10,
            cover_image=_tiny_image(),
            category=self.category,
            author=self.author,
        )
        self.assertTrue(article.slug)

    def test_reading_time_minimum_one_minute(self):
        article = Article.objects.create(
            title="مقاله کوتاه",
            excerpt="خلاصه",
            content="چند کلمه کوتاه",
            cover_image=_tiny_image(),
            category=self.category,
            author=self.author,
        )
        self.assertEqual(article.reading_time_minutes, 1)

    def test_publish_sets_published_at(self):
        article = Article.objects.create(
            title="مقاله دیگر",
            excerpt="خلاصه",
            content="متن نمونه",
            cover_image=_tiny_image(),
            category=self.category,
            author=self.author,
        )
        self.assertIsNone(article.published_at)
        article.publish()
        self.assertEqual(article.status, PublishStatus.PUBLISHED)
        self.assertIsNotNone(article.published_at)


class ArticleAPIPermissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.category = Category.objects.create(name="تولد")
        self.regular_user = User.objects.create_user(
            phone="09121112222", full_name="کاربر عادی", password="StrongPass123"
        )
        self.admin_user = User.objects.create_user(
            phone="09121113333",
            full_name="ادمین",
            password="StrongPass123",
            role=UserRole.ADMIN,
        )

    def test_public_can_list_articles(self):
        response = self.client.get("/api/content/articles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_create_article(self):
        self.client.force_authenticate(self.regular_user)
        response = self.client.post("/api/content/articles/", {
            "title": "تست",
            "excerpt": "خلاصه",
            "content": "متن",
            "category": self.category.id,
            "cover_image": _tiny_image(),
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_article(self):
        self.client.force_authenticate(self.admin_user)
        response = self.client.post("/api/content/articles/", {
            "title": "تست ادمین",
            "excerpt": "خلاصه",
            "content": "متن",
            "category": self.category.id,
            "cover_image": _tiny_image(),
        }, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)