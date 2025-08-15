import hashlib
import hmac
from logging import getLogger

import graphene
from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from graphene_django import DjangoObjectType
from graphql import GraphQLError

# internal imports
from jiri_one.models import Comment, Post, Tag

logger = getLogger("jiri_one")
POSTS_ON_PAGE = settings.POSTS_ON_PAGE

# helper functions
get_offset = lambda page: (page - 1) * POSTS_ON_PAGE


def get_client_ip(info) -> str:
    """Extract client IP from GraphQL request info"""
    try:
        request = info.context
        if request and hasattr(request, "META"):
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                return x_forwarded_for.split(",")[0].strip()
            return request.META.get("REMOTE_ADDR", "unknown")
    except (AttributeError, TypeError):
        pass

    # Fallback for test environment
    return "test_client"


def check_comment_rate_limit(ip_address: str) -> None:
    """Check if IP has exceeded comment creation rate limit"""
    cache_key = f"comment_rate_{ip_address}"
    requests = cache.get(cache_key, 0)

    if requests >= 5:  # max 5 comments per hour
        logger.warning(f"Comment rate limit exceeded for IP {ip_address}")
        raise GraphQLError("Too many comments. Please try again in an hour.")

    # Increment counter with 1 hour expiry
    cache.set(cache_key, requests + 1, 3600)


class PostType(DjangoObjectType):
    comments_count = graphene.Int()

    class Meta:
        model = Post
        fields = ("id", "pub_time", "title_cze", "content_cze", "url_cze", "tags")

    # Custom resolver for count field
    def resolve_comments_count(post_instance, info):
        return post_instance.comments.count()  # type: ignore


class TagType(DjangoObjectType):
    class Meta:
        model = Tag
        fields = ("name_cze", "desc_cze", "url_cze", "order")


class CommentType(DjangoObjectType):
    class Meta:
        model = Comment
        fields = ("id", "title", "content", "nick", "pub_time", "post")


class Query(graphene.ObjectType):
    post_by_id = graphene.Field(PostType, id=graphene.Int(required=True))
    post_by_url = graphene.Field(PostType, url=graphene.String(required=True))
    all_posts = graphene.List(PostType, page=graphene.Int(required=False))
    posts_by_tags_url = graphene.List(
        PostType,
        tag_urls=graphene.List(graphene.String),
        required=True,
        page=graphene.Int(required=False),
    )
    posts_by_search = graphene.List(
        PostType, text=graphene.String(required=True), page=graphene.Int(required=False)
    )
    all_tags = graphene.List(TagType)
    # TODO: think about pagination (it can be handled in frontend, but to save DB connections it can be handled here too)

    def resolve_post_by_id(root, info, id):
        try:
            return Post.objects.get(id=id)
        except Post.DoesNotExist:
            logger.error(f"Post with ID {id} does not exist.")
            return None

    def resolve_post_by_url(root, info, url):
        try:
            return Post.objects.get(url_cze=url)
        except Post.DoesNotExist:
            logger.error(f"Post with URL {url} does not exist.")
            return None

    def resolve_all_posts(root, info, page=1):
        if page < 1:
            logger.info("Someone tried to put bad page number")
            page = 1
        offset = get_offset(page)
        return (
            Post.objects.select_related("author")
            .annotate(comments_count=Count("comments"))
            .order_by("-id")
            .all()[offset : offset + POSTS_ON_PAGE]
        )

    def resolve_posts_by_tags_url(root, info, tag_urls, page=1):
        if page < 1:
            logger.info("Someone tried to put bad page number")
            page = 1
        # Fetch all Tag objects for the provided tag_urls
        tags = Tag.objects.filter(url_cze__in=tag_urls)

        # Log missing tags
        found_tag_urls = {tag.url_cze for tag in tags}
        for tag_url in tag_urls:
            if tag_url not in found_tag_urls:
                logger.error(f"Tag with URL {tag_url} does not exist.")

        # Filter posts by the fetched tags
        offset = get_offset(page)
        return (
            Post.objects.select_related("author")
            .annotate(comments_count=Count("comments"))
            .order_by("-id")
            .filter(tags__in=tags)
            .distinct()[offset : offset + POSTS_ON_PAGE]
        )

    def resolve_posts_by_search(root, info, text, page=1):
        if page < 1:
            logger.info("Someone tried to put bad page number")
            page = 1
        offset = get_offset(page)
        return (
            Post.objects.select_related("author")
            .annotate(comments_count=Count("comments"))
            .order_by("-id")
            .filter(Q(content_cze__icontains=text) | Q(title_cze__icontains=text))
            .distinct()[offset : offset + POSTS_ON_PAGE]
        )

    def resolve_all_tags(root, info):
        return Tag.objects.order_by("order").all()

    # TODO: implement search in posts!


class CreateComment(graphene.Mutation):
    class Arguments:
        post_id = graphene.Int(required=True)
        title = graphene.String(required=True)
        content = graphene.String(required=True)
        nick = graphene.String(required=True)
        # API authentication
        api_key = graphene.String(required=True)
        timestamp = graphene.String(required=True)
        signature = graphene.String(required=True)

    # The response of the mutation
    comment = graphene.Field(lambda: CommentType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(
        self, info, post_id, title, content, nick, api_key, timestamp, signature
    ):
        # Verify API key
        if api_key != settings.FLUTTER_API_KEY:
            logger.warning(f"Invalid API key from IP {get_client_ip(info)}")
            raise GraphQLError("Unauthorized access.")

        # Verify timestamp (prevent replay attacks)
        try:
            request_time = int(timestamp)
            current_time = int(timezone.now().timestamp())
            if abs(current_time - request_time) > 300:  # 5 minutes tolerance
                raise GraphQLError("Request expired.")
        except ValueError as e:
            raise GraphQLError("Invalid timestamp.") from e

        # Verify signature (prevent tampering)
        expected_signature = hmac.new(
            settings.FLUTTER_API_SECRET.encode(),
            f"{post_id}{title}{content}{nick}{timestamp}".encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            logger.warning(f"Invalid signature from IP {get_client_ip(info)}")
            raise GraphQLError("Invalid request signature.")

        # Rate limiting per IP (stále užitečné)
        check_comment_rate_limit(get_client_ip(info))

        # Validate inputs
        if not title.strip():
            raise GraphQLError("Title cannot be empty.")
        if len(title.strip()) > 200:
            raise GraphQLError("Title is too long.")

        if not content.strip():
            raise GraphQLError("Content cannot be empty.")
        if len(content.strip()) > 2000:
            raise GraphQLError("Content is too long.")

        if not nick.strip():
            raise GraphQLError("Nick cannot be empty.")
        if len(nick.strip()) > 50:
            raise GraphQLError("Nick is too long.")

        try:
            post = Post.objects.get(id=post_id)
        except Post.DoesNotExist as exc:
            logger.error(
                f"Failed to create comment for Post ID {post_id}, post doesn't exist."
            )
            raise GraphQLError("Failed to create comment. Please try again.") from exc
        try:
            comment = Comment.objects.create(
                post=post,
                title=title.strip(),
                content=content.strip(),
                nick=nick.strip(),
            )
            logger.info(
                f"Comment created successfully for Post ID {post_id} by {nick}."
            )
            return CreateComment(
                comment=comment,  # type: ignore[call-arg]
                success=True,  # type: ignore[call-arg]
                message="Comment created successfully.",  # type: ignore[call-arg]
            )
        except Exception as e:
            logger.error(f"Failed to create comment for Post ID {post_id}: {str(e)}")
            raise GraphQLError("Failed to create comment. Please try again.") from e


class Mutation(graphene.ObjectType):
    create_comment = CreateComment.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
