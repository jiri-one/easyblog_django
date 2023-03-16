from django.test import TestCase

# from django.db.models.query import QuerySet
from jiri_one.models import Post, Author


def create_post(title_cze: str, content_cze: str) -> Post:
    """Create a post with the given `post_title` and `post_content`."""
    author, _ = Author.objects.get_or_create(
        nick="Test",
        defaults={"nick": "Test", "first_name": "Test", "last_name": "Test"},
    )
    return Post.objects.create(
        title_cze=title_cze, content_cze=content_cze, author=author
    )


class PostModelTests(TestCase):
    def test_post_is_displayed(self):
        """Post is displayed on the index page."""
        post = create_post(title_cze="Test", content_cze="Test content.")
        assert isinstance(post, Post)
        response = self.client.get("/")
        self.assertQuerysetEqual(
            response.context["page_obj"],
            [post],
        )
