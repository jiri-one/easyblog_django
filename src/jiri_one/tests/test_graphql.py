import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any

import pytest
from attr import dataclass
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, QuerySet
from graphene.test import Client

# internal imports
from test_views import create_post

from jiri_one.models import Comment, Post, Tag
from jiri_one.schema import get_expected_signature as get_signature
from jiri_one.schema import schema


def get_random_part_of_string(string: str) -> str:
    """This function will return random part of string at minimum 3 chars length."""
    maximum_index = len(string)
    first = random.randrange(0, round(maximum_index / 2))
    second = random.randrange(first + 3, maximum_index)
    return string[first:second]


def create_random_comment(post: Post) -> Comment:
    return Comment.objects.create(
        post=post,
        title="".join(random.choices(string.ascii_letters + string.digits, k=10)),
        nick="".join(random.choices(string.ascii_letters + string.digits, k=10)),
        content="".join(random.choices(string.ascii_letters + string.digits, k=10)),
    )


def create_comment_mutation(
    post_id=1,
    title="TITLE",
    content="CONTENT",
    nick="NICK",
    api_key=None,
    timestamp=None,
    signature=None,
):
    return f"""
    mutation CreateComment {{
        createComment(
            postId: {post_id},
            title: "{title}",
            content: "{content}",
            nick: "{nick}",
            apiKey: "{api_key}",
            timestamp: "{timestamp}",
            signature: "{signature}"
        ) {{
            success
            message
            comment {{
                id
                title
                content
                nick
                pubTime
                post {{
                    id
                    titleCze
                }}
            }}
        }}
    }}
    """


# PyTest fixtures


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test"""
    cache.clear()
    yield
    cache.clear()  # clear after test too


@pytest.fixture
def create_random_tags() -> QuerySet[Tag]:
    for order_int in range(1, 11):
        random_name = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        random_desc = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        )
        Tag.objects.create(name_cze=random_name, desc_cze=random_desc, order=order_int)
    return Tag.objects.all()


@pytest.fixture
def create_random_posts(create_random_tags) -> tuple[QuerySet[Post], QuerySet[Tag]]:
    tags: QuerySet[Tag] = create_random_tags
    for _ in range(random.randint(1, 10)):
        random_title = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        random_content = "".join(
            random.choices(string.ascii_letters + string.digits, k=100)
        )
        post = create_post(random_title, random_content)
        post_tags = random.choices(tags, k=3)
        post.tags.add(*post_tags)
        [create_random_comment(post) for _ in range(random.randint(0, 10))]
        post.save()
    posts: QuerySet[Post] = (
        Post.objects.select_related("author")
        .annotate(comments_count=Count("comments"))
        .order_by("-id")
        .all()
    )
    return posts, tags


@pytest.mark.django_db
def test_all_posts_graphql_query(create_random_posts):
    random_posts, _ = create_random_posts
    posts = list[dict[str, Any]]()
    for post in random_posts:
        posts.append(
            dict(
                id=post.id,
                titleCze=post.title_cze,
                contentCze=post.content_cze,
                commentsCount=post.comments_count,
            )
        )
    client = Client(schema)
    query = """
    query {
        allPosts(page: 1) {
            id
            titleCze
            contentCze
            commentsCount
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
                commentsCount
            }
        }
        """.replace("POST_URL", post.url_cze)
        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_post = response["data"]["postByUrl"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze
        assert (
            graphql_post["commentsCount"] == Comment.objects.filter(post=post).count()
        )


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
    tags = list[dict[str, Any]]()
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
def test_add_comment_with_graphql(create_random_posts, caplog, monkeypatch):
    # we need to mock FLUTTER frontend keys
    api_key = "fake_api_key"
    api_secret = "fake_api_secret"
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", api_key)
    monkeypatch.setattr(settings, "FLUTTER_API_SECRET", api_secret)
    # Use the first post from the fixture
    posts, _ = create_random_posts
    first_post = posts.last()  # first like with id 1, like the oldest
    comment_count = first_post.comments_count
    assert Comment.objects.filter(post=first_post).count() == comment_count

    client = Client(schema)

    post_id = first_post.id
    title = "Great article!"
    content = "This is a very informative post. Thanks for sharing your insights on this topic."
    nick = "JohnDoe"
    timestamp = str(int(datetime.now().timestamp()))

    signature = get_signature(api_secret, post_id, title, content, nick, timestamp)

    client = Client(schema)
    mutation = create_comment_mutation(
        post_id=post_id,
        title=title,
        content=content,
        nick=nick,
        timestamp=timestamp,
        api_key=api_key,
        signature=signature,
    )
    with caplog.at_level(logging.INFO, logger="jiri_one"):
        response = client.execute(mutation)
        assert (
            f"Comment created successfully for Post ID {post_id} by JohnDoe."
            in caplog.text
        )

    new_comment = Comment.objects.filter(post=first_post).order_by("pub_time").last()
    assert new_comment is not None
    new_comment_id = str(new_comment.id)  # type: ignore
    expected_response = json.loads(
        f"""
    {{
        "data": {{
            "createComment": {{
            "success": true,
            "message": "Comment created successfully.",
            "comment": {{
                "id": "{new_comment_id}",
                "title": "{title}",
                "content": "{content}",
                "nick": "{nick}",
                "pubTime": "{new_comment.pub_time.isoformat()}",
                "post": {{
                "id": {post_id},
                "titleCze": "{first_post.title_cze}"
                }}
            }}
            }}
        }}
    }}
    """
    )

    assert response is not None and "data" in response
    assert response == expected_response
    assert Comment.objects.filter(post=first_post).count() == comment_count + 1


test_data: list[tuple[str, str, str, str | None]] = [
    (
        "post_id",
        "9999",
        "Failed to create comment. Please try again.",
        "Failed to create comment for Post ID 9999, post doesn't exist.",
    ),
    ("title", "", "Title cannot be empty.", None),
    ("title", 201 * "X", "Title is too long.", None),
    ("content", "", "Content cannot be empty.", None),
    ("content", 2001 * "X", "Content is too long.", None),
    ("nick", "", "Nick cannot be empty.", None),
    ("nick", 51 * "X", "Nick is too long.", None),
]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "attr, value, expected_error_msg, expected_log",
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
def test_add_comment_with_graphql_content_error(
    create_random_posts,
    attr,
    value,
    expected_error_msg,
    expected_log,
    caplog,
    monkeypatch,
):
    # we need to mock FLUTTER frontend keys
    api_key = "fake_api_key"
    api_secret = "fake_api_secret"
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", api_key)
    monkeypatch.setattr(settings, "FLUTTER_API_SECRET", api_secret)

    @dataclass
    class FakeComment:
        post_id = 1
        title = "TITLE"
        content = "CONTENT"
        nick = "NICK"
        timestamp = str(int(datetime.now().timestamp()))

    fc = FakeComment()
    setattr(fc, attr, value)
    signature = get_signature(
        api_secret, fc.post_id, fc.title, fc.content, fc.nick, fc.timestamp
    )

    client = Client(schema)
    mutation = create_comment_mutation(
        post_id=fc.post_id,
        title=fc.title,
        content=fc.content,
        nick=fc.nick,
        timestamp=fc.timestamp,
        api_key=api_key,
        signature=signature,
    )

    if expected_log is not None:
        with caplog.at_level(logging.ERROR, logger="jiri_one"):
            response = client.execute(mutation)
            assert expected_log in caplog.text
    else:
        response = client.execute(mutation)

    assert response is not None and "errors" in response
    assert response["errors"][0]["message"] == expected_error_msg


@pytest.mark.django_db
def test_add_comment_with_graphql_api_key_error(
    create_random_posts,
    monkeypatch,
):
    # we need to mock FLUTTER frontend keys
    api_key = "wrong_api_key"
    api_secret = "fake_api_secret"
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", "another_api_key")

    post_id = 1
    title = "TITLE"
    content = "CONTENT"
    nick = "NICK"
    timestamp = str(int(datetime.now().timestamp()))

    signature = get_signature(api_secret, post_id, title, content, nick, timestamp)

    client = Client(schema)
    mutation = create_comment_mutation(
        post_id=post_id,
        title=title,
        content=content,
        nick=nick,
        timestamp=timestamp,
        api_key=api_key,
        signature=signature,
    )

    response = client.execute(mutation)

    assert response is not None and "errors" in response
    assert response["errors"][0]["message"] == "Unauthorized access."


@pytest.mark.django_db
@pytest.mark.parametrize(
    "timestamp, expected_error_msg",
    [
        ("nonsense", "Invalid timestamp."),
        (
            str(int((datetime.now() + timedelta(minutes=6)).timestamp())),
            "Request expired.",
        ),
    ],
    ids=[
        "invalid_timestamp",
        "request_expired",
    ],
)
def test_add_comment_with_graphql_timestamp_error(
    create_random_posts,
    timestamp,
    expected_error_msg,
    monkeypatch,
):
    # we need to mock FLUTTER frontend keys
    api_key = "fake_api_key"
    api_secret = "fake_api_secret"
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", api_key)
    monkeypatch.setattr(settings, "FLUTTER_API_SECRET", api_secret)

    post_id = 1
    title = "TITLE"
    content = "CONTENT"
    nick = "NICK"

    signature = get_signature(api_secret, post_id, title, content, nick, timestamp)

    client = Client(schema)
    mutation = create_comment_mutation(
        post_id=post_id,
        title=title,
        content=content,
        nick=nick,
        timestamp=timestamp,
        api_key=api_key,
        signature=signature,
    )

    response = client.execute(mutation)

    assert response is not None and "errors" in response
    assert response["errors"][0]["message"] == expected_error_msg


@pytest.mark.django_db
def test_add_comment_with_graphql_many_comments_error(
    create_random_posts,
    caplog,
    monkeypatch,
):
    # we need to mock FLUTTER frontend keys
    api_key = "fake_api_key"
    api_secret = "fake_api_secret"
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", api_key)
    monkeypatch.setattr(settings, "FLUTTER_API_SECRET", api_secret)

    posts, _ = create_random_posts
    first_post = posts.last()  # first like with id 1, like the oldest
    comment_count = first_post.comments_count

    for i in range(1, 14):
        post_id = first_post.id
        title = "TITLE" + str(i)
        content = "CONTENT"
        nick = "NICK"
        timestamp = str(int(datetime.now().timestamp()))
        signature = get_signature(api_secret, post_id, title, content, nick, timestamp)

        client = Client(schema)
        mutation = create_comment_mutation(
            post_id=post_id,
            title=title,
            content=content,
            nick=nick,
            timestamp=timestamp,
            api_key=api_key,
            signature=signature,
        )
        with caplog.at_level(logging.INFO, logger="jiri_one"):
            response = client.execute(mutation)

            if i > 12:
                assert response is not None and "errors" in response
                assert (
                    response["errors"][0]["message"]
                    == "Too many comments. Please try again in an hour."
                )
                assert "Comment rate limit exceeded for IP test_client" in caplog.text
            if i <= 12:
                assert response is not None and "data" in response
                assert response["data"]["createComment"]["success"]
                assert (
                    comment_count + i == Comment.objects.filter(post=first_post).count()
                )
                assert (
                    f"Comment created successfully for Post ID {post_id} by {nick}."
                    in caplog.text
                )


@pytest.mark.django_db
def test_search_posts_by_graphql_query(create_random_posts):
    client = Client(schema)
    posts, _ = create_random_posts
    post_data_dict = dict[str, dict[str, Any]]()
    random_posts = random.choices(posts, k=3)

    for post in random_posts:
        where_to_search: str = random.choice([post.title_cze, post.content_cze])
        random_part_of_text: str = get_random_part_of_string(where_to_search)
        post_data_dict[random_part_of_text] = dict(
            id=post.id,
            titleCze=post.title_cze,
            contentCze=post.content_cze,
            tags=[{"urlCze": tag.url_cze} for tag in post.tags.all()],
        )

    for text, post in post_data_dict.items():
        query = """
        query {
            postsBySearch(text: "TEXT") {
                titleCze
                contentCze
                id
                tags {
                    urlCze
                }
            }
        }
        """.replace("TEXT", text)

        response = client.execute(query)
        assert response is not None and "data" in response
        graphql_posts = response["data"]["postsBySearch"]
        # I shouldn't do to compare directly graphql_posts with post because there can be more posts witch searched text in graphql_posts (they can contain same text). It is low probability, but it is possible
        assert post in graphql_posts
