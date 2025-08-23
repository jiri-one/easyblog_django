import logging
import random
import string
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, QuerySet
from graphene_django.utils.testing import graphql_query

# internal imports
from test_views import create_post

from jiri_one.models import Comment, Post, Tag
from jiri_one.schema import get_expected_signature as get_signature


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


@dataclass
class CommentMutationData:
    api_key: str = "fake_api_key"
    api_secret: str = "fake_api_secret"
    post_id: int = 1
    title: str = "TITLE"
    content: str = "CONTENT"
    nick: str = "NICK"
    timestamp: str = str(int(datetime.now().timestamp()))
    signature: str = get_signature(api_secret, post_id, title, content, nick, timestamp)
    query_text = """
            mutation CreateComment(
                    $post_id: Int!,
                    $title: String!,
                    $content: String!,
                    $nick: String!,
                    $api_key: String!,
                    $timestamp: String!,
                    $signature: String!) {
                createComment(
                    postId: $post_id,
                    title: $title,
                    content: $content,
                    nick: $nick,
                    apiKey: $api_key,
                    timestamp: $timestamp,
                    signature: $signature
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

    def refresh_signature(self):
        self.signature = get_signature(
            self.api_secret,
            self.post_id,
            self.title,
            self.content,
            self.nick,
            self.timestamp,
        )


# PyTest fixtures


# PyTest fixtures
@pytest.fixture
def cmd(monkeypatch):
    cmd = CommentMutationData()
    # we need to mock FLUTTER frontend keys
    monkeypatch.setattr(settings, "FLUTTER_API_KEY", cmd.api_key)
    monkeypatch.setattr(settings, "FLUTTER_API_SECRET", cmd.api_secret)
    return cmd


@pytest.fixture
def client_query(client):
    def func(*args, **kwargs):
        return graphql_query(*args, **kwargs, client=client)

    return func


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
def test_all_posts_graphql_query(client_query, create_random_posts):
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
    response_content = client_query("""
    query {
        allPosts {
            id
            titleCze
            contentCze
            commentsCount
        }
    }
    """).json()
    assert response_content is not None and "data" in response_content
    graphql_posts = sorted(response_content["data"]["allPosts"], key=lambda k: k["id"])
    assert graphql_posts == sorted(posts, key=lambda k: k["id"])


@pytest.mark.django_db
def test_random_post_by_url_graphql_query(client_query, create_random_posts):
    posts, _ = create_random_posts
    for post in posts:
        response_content = client_query(
            """
            query postByUrl($url: String!) {
                postByUrl(url: $url) {
                    titleCze
                    contentCze
                    tags {
                        nameCze
                    }
                    commentsCount
                }
            }
            """,
            variables={"url": post.url_cze},
        ).json()

        assert response_content is not None and "data" in response_content
        graphql_post = response_content["data"]["postByUrl"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze
        assert (
            graphql_post["commentsCount"] == Comment.objects.filter(post=post).count()
        )


@pytest.mark.django_db
def test_random_post_by_id_graphql_query(client_query, create_random_posts):
    posts, _ = create_random_posts
    for post in posts:
        response_content = client_query(
            """
            query postById($id: Int!) {
                postById(id: $id) {
                    titleCze
                    contentCze
                    tags {
                        nameCze
                    }
                    commentsCount
                }
            }
            """,
            variables={"id": post.id},
        ).json()

        assert response_content is not None and "data" in response_content
        graphql_post = response_content["data"]["postById"]
        assert graphql_post["titleCze"] == post.title_cze
        assert graphql_post["contentCze"] == post.content_cze


@pytest.mark.django_db
def test_random_post_by_tags_graphql_query(client_query, create_random_posts):
    _, tags = create_random_posts
    for _ in range(3):
        tags_to_filter = random.choices(tags, k=2)
        filtered_posts = (
            Post.objects.filter(tags__in=tags_to_filter)
            .prefetch_related("tags")
            .select_related("author")
            .distinct()
        )
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

        response_content = client_query(
            """
            query postsByTagsUrl($tagUrls: [String]!) {
                postsByTagsUrl(tagUrls: $tagUrls) {
                    id
                    titleCze
                    contentCze
                    tags {
                        urlCze
                    }
                }
            }
            """,
            variables={"tagUrls": [tag.url_cze for tag in tags_to_filter]},
        ).json()

        assert response_content is not None and "data" in response_content
        graphql_posts = sorted(
            response_content["data"]["postsByTagsUrl"], key=lambda post: post["id"]
        )
        assert graphql_posts == sorted(post_data_list, key=lambda post: post["id"])


@pytest.mark.django_db
def test_search_posts_by_graphql_query(client_query, create_random_posts):
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
        response_content = client_query(
            """
            query postsBySearch($text: String!) {
                postsBySearch(text: $text) {
                    id
                    titleCze
                    contentCze
                    tags {
                        urlCze
                    }
                }
            }
            """,
            variables={"text": text},
        ).json()

        assert response_content is not None and "data" in response_content
        graphql_posts = response_content["data"]["postsBySearch"]
        # I shouldn't do to compare directly graphql_posts with post because there can be more posts witch searched text in graphql_posts (they can contain same text). It is low probability, but it is possible
        assert post in graphql_posts


@pytest.mark.django_db
def test_all_tags_graphql_query(client_query, create_random_tags):
    tags = list[dict[str, Any]]()
    for tag in create_random_tags:
        tags.append(
            dict(
                nameCze=tag.name_cze,
                descCze=tag.desc_cze,
                order=tag.order,
            )
        )
    response_content = client_query(
        """
        query AllTags {
            allTags {
                nameCze
                descCze
                order
            }
        }
        """
    ).json()

    assert response_content is not None and "data" in response_content
    graphql_tags = sorted(response_content["data"]["allTags"], key=lambda k: k["order"])
    assert graphql_tags == sorted(tags, key=lambda k: k["order"])


@pytest.mark.django_db
def test_add_comment_with_graphql(
    cmd,  # CommentMutationData instance and api_key and api_secret env mock
    client_query,
    create_random_posts,
    caplog,
):
    # Use the first post from the fixture
    posts, _ = create_random_posts
    first_post = posts.last()  # first like with id 1, like the oldest
    comment_count = first_post.comments_count
    assert Comment.objects.filter(post=first_post).count() == comment_count

    with caplog.at_level(logging.INFO, logger="jiri_one"):
        response_content = client_query(
            cmd.query_text,
            variables=dict(
                post_id=cmd.post_id,
                title=cmd.title,
                content=cmd.content,
                nick=cmd.nick,
                timestamp=cmd.timestamp,
                api_key=cmd.api_key,
                signature=cmd.signature,
            ),
        ).json()
        assert (
            f"Comment created successfully for Post ID {cmd.post_id} by {cmd.nick}."
            in caplog.text
        )

    new_comment = Comment.objects.filter(post=first_post).order_by("pub_time").last()
    assert new_comment
    new_comment_id = str(new_comment.id)  # type: ignore
    expected_response = {
        "data": {
            "createComment": {
                "success": True,
                "message": "Comment created successfully.",
                "comment": {
                    "id": new_comment_id,
                    "title": cmd.title,
                    "content": cmd.content,
                    "nick": cmd.nick,
                    "pubTime": new_comment.pub_time.isoformat(),
                    "post": {"id": cmd.post_id, "titleCze": first_post.title_cze},
                },
            }
        }
    }

    assert response_content is not None and "data" in response_content
    assert response_content == expected_response
    assert Comment.objects.filter(post=first_post).count() == comment_count + 1


test_data: list[tuple[str, Any, str, str | None]] = [
    (
        "post_id",
        9999,
        "Failed to create comment. Please try again.",
        "Failed to create comment for Post ID 9999, post doesn't exist.",
    ),
    ("title", "", "Title cannot be empty.", None),
    ("title", 201 * "X", "Title is too long.", None),
    ("content", "", "Content cannot be empty.", None),
    ("content", 2001 * "X", "Content is too long.", None),
    ("nick", "", "Nick cannot be empty.", None),
    ("nick", 51 * "X", "Nick is too long.", None),
    ("api_key", "wrong_api_key", "Unauthorized access.", "Invalid API key from IP"),
    ("timestamp", "bad_timestamp", "Invalid timestamp.", None),
    (
        "timestamp",
        str(int((datetime.now() + timedelta(minutes=6)).timestamp())),
        "Request expired.",
        None,
    ),
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
        "wrong_api_key",
        "invalid_timestamp",
        "request_expired",
    ],
)
def test_add_comment_with_graphql_content_error(
    cmd,  # CommentMutationData instance and api_key and api_secret env mock
    client_query,
    create_random_posts,
    attr,
    value,
    expected_error_msg,
    expected_log,
    caplog,
):
    # there is the part, where PyTest use our parameters for test variants
    setattr(cmd, attr, value)
    cmd.refresh_signature()  # we need to build new signature after change of atribute

    if expected_log is not None:
        with caplog.at_level(logging.WARNING, logger="jiri_one"):
            response_content = client_query(
                cmd.query_text,
                variables=asdict(cmd),
            ).json()
            assert expected_log in caplog.text
    else:
        response_content = client_query(
            cmd.query_text,
            variables=asdict(cmd),
        ).json()

    assert response_content is not None and "errors" in response_content
    assert response_content["errors"][0]["message"] == expected_error_msg


@pytest.mark.django_db
def test_add_comment_with_graphql_many_comments_error(
    cmd,  # CommentMutationData instance and api_key and api_secret env mock
    client_query,
    create_random_posts,
    caplog,
):
    posts, _ = create_random_posts
    first_post = posts.last()  # first like with id 1, like the oldest
    comment_count = first_post.comments_count

    for i in range(1, 14):
        cmd.post_id = first_post.id
        cmd.title = "TITLE" + str(i)
        cmd.timestamp = str(int(datetime.now().timestamp()))
        cmd.refresh_signature()

        with caplog.at_level(logging.INFO, logger="jiri_one"):
            response_content = client_query(
                cmd.query_text,
                variables=asdict(cmd),
            ).json()

            if i > 12:
                assert response_content is not None and "errors" in response_content
                assert (
                    response_content["errors"][0]["message"]
                    == "Too many comments. Please try again in an hour."
                )
                assert "Comment rate limit exceeded for IP 127.0.0.1" in caplog.text
            if i <= 12:
                assert response_content is not None and "data" in response_content
                assert response_content["data"]["createComment"]["success"]
                assert (
                    comment_count + i == Comment.objects.filter(post=first_post).count()
                )
                assert (
                    f"Comment created successfully for Post ID {cmd.post_id} by {cmd.nick}."
                    in caplog.text
                )
