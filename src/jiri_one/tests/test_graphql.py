from graphene.test import Client
import pytest
import random
import string

# internal imports
from jiri_one.schema import schema
from jiri_one.models import Post
from test_views import create_post


@pytest.fixture
def create_random_posts():
    posts = list[Post]()
    for _ in range(10):
        random_title = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        random_content = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        )
        post = create_post(random_title, random_content)
        posts.append(post)
    yield posts


@pytest.mark.django_db
def test_graphql_query(create_random_posts):
    posts = list[dict[str, str]]()
    for post in create_random_posts:
        posts.append(
            dict(
                id=post.id,
                titleCze=post.title_cze,
                contentCze=post.content_cze,
            )
        )
    client = Client(schema)
    query = """
    query {
        allPosts(page: 1) {
            id
            titleCze
            contentCze
        }
    }
    """
    response = client.execute(query)
    assert "data" in response
    graphql_posts = sorted(response["data"]["allPosts"], key=lambda k: k["id"])
    assert graphql_posts == sorted(posts, key=lambda k: k["id"])
