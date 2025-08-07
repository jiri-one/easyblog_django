import json
import logging
import random
import string
from typing import Any

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
    return posts, tags


@pytest.mark.django_db
def test_all_posts_graphql_query(create_random_posts):
    random_posts, _ = create_random_posts
    posts = list[dict[str, str]]()
    for post in random_posts:
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
    posts, _ = create_random_posts
    for post in posts:
        query = """
        query {
            postByUrl(url: "POST_URL") {
                titleCze
                contentCze
                tags {
                    nameCze
                }
            }
        }
        """.replace("POST_URL", post.url_cze)
        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_post = response["data"]["postByUrl"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze


@pytest.mark.django_db
def test_random_post_by_id_graphql_query(create_random_posts):
    client = Client(schema)
    posts, _ = create_random_posts
    for post in posts:
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
def test_random_post_by_tags_graphql_query(create_random_posts):
    client = Client(schema)
    _, tags = create_random_posts
    for _ in range(3):
        tags_to_filter = random.choices(tags, k=2)
        filtered_posts = Post.objects.filter(tags__in=tags_to_filter).distinct()
        post_data_list = list[dict[str, Any]]()
        for post in filtered_posts:
            post_data_list.append(
                dict(
                    id=post.id,
                    titleCze=post.title_cze,
                    contentCze=post.content_cze,
                    tags=[{"urlCze": tag.url_cze} for tag in post.tags.all()],
                )
            )
        query = """
        query {
            postsByTagsUrl(tagUrls: ["TAG1", "TAG2"]) {
                titleCze
                contentCze
                id
                tags {
                    urlCze
                }
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
    # Use the first post from the fixture
    posts, _ = create_random_posts
    first_post = posts[0]
    client = Client(schema)
    mutation = """
    mutation CreateComment {
        createComment(
            postId: POST_ID,
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
    """.replace("POST_ID", str(first_post.id))
    with caplog.at_level(logging.INFO, logger="jiri_one"):
        response = client.execute(mutation)
        assert (
            f"Comment created successfully for Post ID {first_post.id} by JohnDoe."
            in caplog.text
        )

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
                "pubTime": "PUB_TIME",
                "post": {
                "id": 1,
                "titleCze": "TITLE_CZE"
                }
            }
            }
        }
    }
    """.replace("TITLE_CZE", first_post.title_cze).replace(
            "PUB_TIME", Comment.objects.filter(post=first_post)[0].pub_time.isoformat()
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

    if expected_log is not None:
        with caplog.at_level(logging.ERROR, logger="jiri_one"):
            response = client.execute(tested_mutation)
            assert expected_log in caplog.text
    else:
        response = client.execute(tested_mutation)

    assert response is not None and "errors" in response
    assert response["errors"][0]["message"] == expected_error_msg
