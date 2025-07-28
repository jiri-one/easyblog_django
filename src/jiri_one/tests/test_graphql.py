from graphene.test import Client
import pytest
import random
import string

# internal imports
from jiri_one.schema import schema
from jiri_one.models import Post, Tag
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


@pytest.fixture
def create_random_tags():
    tags = list[Tag]()
    for order_int in range(1,11):
        random_name = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        random_desc = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        )
        tag = Tag.objects.create(
        name_cze=random_name, desc_cze=random_desc, order=order_int
    )
        tags.append(tag)
    yield tags


@pytest.mark.django_db
def test_all_posts_graphql_query(create_random_posts):
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
    assert response is not None and "data" in response
    graphql_posts = sorted(response["data"]["allPosts"], key=lambda k: k["id"])
    assert graphql_posts == sorted(posts, key=lambda k: k["id"])


@pytest.mark.django_db
def test_random_post_by_url_graphql_query(create_random_posts):
    client = Client(schema)
    for post in create_random_posts:
        query = """
        query {
            postByUrl(url: "XXX") {
                titleCze
                contentCze
            }
        }
        """.replace("XXX", post.url_cze)
        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_post = response["data"]["postByUrl"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze


@pytest.mark.django_db
def test_random_post_by_id_graphql_query(create_random_posts):
    client = Client(schema)
    for post in create_random_posts:
        query = """
        query {
            postById(id: XXX) {
                titleCze
                contentCze
            }
        }
        """.replace("XXX", str(post.id))
        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_post = response["data"]["postById"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze


@pytest.mark.django_db
def test_all_tags_graphql_query(create_random_tags):
    tags = list[dict[str, str]]()
    for tag in create_random_tags:
        tags.append(
            dict(
                nameCze=tag.name_cze,
                descCze=tag.desc_cze,
                order=tag.order,
            )
        )
    client = Client(schema)
    query = """
    query {
        allTags {
            nameCze
            descCze
            order
        }
    }
    """
    response = client.execute(query)
    assert response is not None and "data" in response
    graphql_tags = sorted(response["data"]["allTags"], key=lambda k: k["order"])
    assert graphql_tags == sorted(tags, key=lambda k: k["order"])
