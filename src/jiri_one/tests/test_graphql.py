import json
import logging
import random
import string

import pytest
from graphene.test import Client

# internal imports
from test_views import create_post

from jiri_one.models import Comment, Post, Tag
from jiri_one.schema import schema


@pytest.fixture
def create_random_tags():
    tags = list[Tag]()
    for order_int in range(1, 11):
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


@pytest.fixture
def create_random_posts(create_random_tags):
    tags: list[Tag] = create_random_tags
    posts = list[Post]()
    for _ in range(10):
        random_title = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        random_content = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        )
        post = create_post(random_title, random_content)
        post_tags = random.choices(tags, k=3)
        post.tags.add(*post_tags)
        post.save()
        posts.append(post)
    yield posts


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
def test_random_post_by_tags_graphql_query(create_random_tags):
    client = Client(schema)
    tags: list[Tag] = create_random_tags
    for _ in range(3):
        tags_to_filter = random.choices(tags, k=2)
        filtered_posts = Post.objects.filter(tags__in=tags_to_filter)
        post_data_list = list[dict[str, str]]()
        for post in filtered_posts:
            post_data_list.append(
                dict(
                    id=post.id,
                    titleCze=post.title_cze,
                    contentCze=post.content_cze,
                )
            )
        query = """
        query {
            postsByTagsUrl(tagUrls: ["TAG1", "TAG2"]) {
                titleCze
                contentCze
                id
            }
        }
        """.replace("TAG1", tags_to_filter[0].url_cze).replace(
            "TAG2", tags_to_filter[1].url_cze
        )
        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_posts = sorted(
            response["data"]["postsByTagsUrl"], key=lambda post: post["id"]
        )
        assert graphql_posts == sorted(post_data_list, key=lambda post: post["id"])


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


@pytest.mark.django_db
def test_add_comment_with_graphql(create_random_posts, caplog):
    client = Client(schema)
    mutation = """
    mutation CreateComment {
        createComment(
            postId: 1,
            title: "Great article!",
            content: "This is a very informative post. Thanks for sharing your insights on this topic.",
            nick: "JohnDoe"
        ) {
            success
            message
            comment {
            id
            title
            content
            nick
            pubTime
            post {
                id
                titleCze
            }
            }
        }
    }
    """
    with caplog.at_level(logging.INFO, logger="jiri_one"):
        response = client.execute(mutation)
        assert "Comment created successfully for Post ID 1 by JohnDoe." in caplog.text

    expected_response = json.loads(
        """
    {
        "data": {
            "createComment": {
            "success": true,
            "message": "Comment created successfully.",
            "comment": {
                "id": "1",
                "title": "Great article!",
                "content": "This is a very informative post. Thanks for sharing your insights on this topic.",
                "nick": "JohnDoe",
                "pubTime": "YYY",
                "post": {
                "id": 1,
                "titleCze": "XXX"
                }
            }
            }
        }
    }
    """.replace("XXX", Post.objects.get(id=1).title_cze).replace(
            "YYY", Comment.objects.get(id=1).pub_time.isoformat()
        )
    )

    assert response is not None and "data" in response
    assert response == expected_response


test_data = [
    (
        "1",  # correct post_id
        "9999",
        "Failed to create comment. Please try again.",
        "Failed to create comment for Post ID 9999, post doesn't exists.",
    ),
    ("TITLE", "", "Title cannot be empty.", None),
    ("TITLE", 201 * "X", "Title is too long.", None),
    ("CONTENT", "", "Content cannot be empty.", None),
    ("CONTENT", 2001 * "X", "Content is too long.", None),
    ("NICK", "", "Nick cannot be empty.", None),
    ("NICK", 51 * "X", "Nick is too long.", None),
]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "replace_what, replace_with, expected_error_msg, expected_log",
    test_data,
    ids=[
        "wrong_post_id",
        "empty_title",
        "long_title",
        "empty_content",
        "long_content",
        "empty_nick",
        "long_nick",
    ],
)
def test_add_comment_with_graphql_error(
    create_random_posts,
    replace_what,
    replace_with,
    expected_error_msg,
    expected_log,
    caplog,
):
    client = Client(schema)
    mutation = """
    mutation CreateComment {
        createComment(
            postId: 1,
            title: "TITLE",
            content: "CONTENT",
            nick: "NICK"
        ) {
            success
            message
            comment {
            id
            title
            content
            nick
            pubTime
            post {
                id
                titleCze
            }
            }
        }
    }
    """
    tested_mutation = mutation.replace(replace_what, replace_with)

    response = client.execute(tested_mutation)
    if expected_log is not None:
        caplog.set_level(logging.ERROR, logger="jiri_one")
        assert expected_log in caplog.text

    assert response is not None and "errors" in response
    assert response["errors"][0]["message"] == expected_error_msg
