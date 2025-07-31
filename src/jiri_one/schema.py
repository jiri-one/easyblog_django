import graphene
from graphene_django import DjangoObjectType
from logging import getLogger
from django.conf import settings

# internal imports
from jiri_one.models import Post, Tag, Comment


logger = getLogger('jiri_one')
POSTS_ON_PAGE = settings.POSTS_ON_PAGE

#helper functions
get_offset = lambda page : (page - 1) * POSTS_ON_PAGE

class PostType(DjangoObjectType):
    class Meta:
        model = Post
        fields = ("id", "title_cze", "content_cze", "url_cze")

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
    posts_by_tags_url = graphene.List(PostType, tag_urls=graphene.List(graphene.String), required=True, page=graphene.Int(required=False))
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
            page=1
        offset = get_offset(page)
        return Post.objects.all()[offset:offset+POSTS_ON_PAGE]
    

    def resolve_posts_by_tags_url(root, info, tag_urls, page=1):
        if page < 1:
            logger.info("Someone tried to put bad page number")
            page=1
        # Fetch all Tag objects for the provided tag_urls
        tags = Tag.objects.filter(url_cze__in=tag_urls)
        
        # Log missing tags
        found_tag_urls = {tag.url_cze for tag in tags}
        for tag_url in tag_urls:
            if tag_url not in found_tag_urls:
                logger.error(f"Tag with URL {tag_url} does not exist.")
        
        # Filter posts by the fetched tags
        offset = get_offset(page)
        return Post.objects.filter(tags__in=tags).distinct()[offset:offset+POSTS_ON_PAGE]

    def resolve_all_tags(root, info):
        return Tag.objects.all()


class CreateComment(graphene.Mutation):
    class Arguments:
        post_id = graphene.Int(required=True)
        title = graphene.String(required=True)
        content = graphene.String(required=True)
        nick = graphene.String(required=True)

    # The response of the mutation
    comment = graphene.Field(lambda: CommentType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, post_id, title, content, nick):# Validate inputs
        if not title.strip():
            raise graphene.GraphQLError("Title cannot be empty.")
        if len(title.strip()) > 200:  # Adjust based on your model
            raise graphene.GraphQLError("Title is too long.")
        
        if not content.strip():
            raise graphene.GraphQLError("Content cannot be empty.")
        if len(content.strip()) > 2000:  # Adjust based on your model
            raise graphene.GraphQLError("Content is too long.")
        
        if not nick.strip():
            raise graphene.GraphQLError("Nick cannot be empty.")
        if len(nick.strip()) > 50:  # Adjust based on your model
            raise graphene.GraphQLError("Nick is too long.")

        try:
            Post.objects.get(id=post_id)
        except Post.DoesNotExist:
            logger.error(f"Failed to create comment for Post ID {post_id}, post doesn't exists.")
            raise graphene.GraphQLError("Failed to create comment. Please try again.")
        try:
            comment = Comment.objects.create(
                post=Post.objects.get(id=post_id),
                title=title.strip(),
                content=content.strip(),
                nick=nick.strip(),
            )
            logger.info(f"Comment created successfully for Post ID {post_id} by {nick}.")
            return CreateComment(comment=comment, success=True, message="Comment created successfully.") # type: ignore
        except Exception as e:
            logger.error(f"Failed to create comment for Post ID {post_id}: {str(e)}")
            raise graphene.GraphQLError("Failed to create comment. Please try again.")


class Mutation(graphene.ObjectType):
    create_comment = CreateComment.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
