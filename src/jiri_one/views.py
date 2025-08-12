import hmac
import json
from hashlib import sha256
from ipaddress import ip_address, ip_network
from subprocess import Popen

import httpx
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q, QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseServerError,
)
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.views import View
from django.views.decorators.csrf import csrf_exempt

# internal imports
from jiri_one.models import Comment, Post, Tag

# helper variables
TagDoesNotExist = Tag.DoesNotExist


async def get_post_html_tags(post_tags: QuerySet[Tag]):
    """From tags of post create HTML"""
    tags_links = []
    async for tag in post_tags.values():
        tags_links.append(f"""<a href="/tag/{tag["url_cze"]}">{tag["name_cze"]}</a>""")
    return ", ".join(tags_links)


async def get_all_html_tags():
    nr_of_tags: int = await Tag.objects.acount()
    html_tags: str = ""
    index = 0
    async for tag in Tag.objects.all():
        if index == nr_of_tags - 1:
            html_tags += f'<a href="/tag/{tag.url_cze}">{tag.name_cze}</a>'
        else:
            html_tags += f'<a style="border-bottom: 1px solid #3c67be;" href="/tag/{tag.url_cze}">{tag.name_cze}</a>'
        index += 1
    return html_tags


class PostView(View):
    """Class for showing one post/entry."""

    template_name = "post.html"

    async def get(self, request, url_cze, *args, **kwargs):
        """GET method to show one Post."""
        try:
            post = await Post.objects.select_related("author").aget(url_cze=url_cze)
        except Post.DoesNotExist:
            return HttpResponseServerError("This post does not exist.", status=404)
        all_tags_html = await get_all_html_tags()
        post.html_tags = await get_post_html_tags(Tag.objects.filter(post=post))
        comments = [comment async for comment in Comment.objects.filter(post=post)]
        return render(
            request,
            self.template_name,
            {"post": post, "comments": comments, "all_tags": all_tags_html},
        )

    async def post(self, request, url_cze, *args, **kwargs):
        """POST method for save comment."""
        # antispam comment part
        try:
            five = int(request.POST.get("antispam"))
            if five != 5:
                raise ValueError
        except ValueError:
            return HttpResponseForbidden("Musíte správně vyplnit pole Antispam!")

        try:
            post = await Post.objects.select_related("author").aget(url_cze=url_cze)
        except Post.DoesNotExist:
            return HttpResponseServerError(
                "You are trying to send comment for non existent Post.", status=404
            )
        # comment save part
        header = request.POST.get("comment_header")
        nick = request.POST.get("comment_nick")
        content = request.POST.get("comment_content")
        await Comment.objects.acreate(
            post=post, title=header, nick=nick, content=content
        )
        return redirect(request.path)


class IndexView(View):
    """Main and the only one class to show index, tags and search results."""

    template_name = "index.html"

    async def get(self, request: HttpRequest, *args, **kwargs):
        queryset: QuerySet = (
            Post.objects.select_related("author")
            .annotate(Count("comments"))
            .order_by("-id")
        )  # lazy object - will not access DB
        all_tags_html = await get_all_html_tags()

        # get tag
        tag: None | Tag = None
        if "tag" in kwargs:
            try:  # try to find Tag in czech url
                tag = await Tag.objects.aget(url_cze=kwargs["tag"])
            except TagDoesNotExist:
                # we didn't find Tag by czech, we will try english
                try:
                    tag = await Tag.objects.aget(url_eng=kwargs["tag"])
                except TagDoesNotExist:
                    assert tag is None
                    # TODO: some log here
            if tag is not None:
                queryset = queryset.filter(tags=tag)
                # TODO: now we are handle only one tag, in the future, we should handle combinations

        # get search
        if "search" in kwargs or "hledej" in kwargs:
            search_cze: str | None = kwargs.get("hledej")
            search_eng: str | None = kwargs.get("search")
            default_search = None
            search: str | None = search_cze or search_eng or default_search
            if search is not None:
                queryset = queryset.filter(
                    Q(content_cze__icontains=search) | Q(title_cze__icontains=search)
                )
        # get the page number
        page_cze: int | None = kwargs.get("strana")
        page_eng: int | None = kwargs.get("page")
        default_page: int = 1
        current_page = page_cze or page_eng or default_page

        # get posts from current_page
        post_id_list = [id async for id in queryset.values_list("id", flat=True)]
        paginator = Paginator(post_id_list, settings.POSTS_ON_PAGE)
        page_obj = paginator.get_page(current_page)
        post_ids_on_current_page = page_obj.object_list
        queryset = queryset.filter(id__in=post_ids_on_current_page)
        posts = list[Post]()
        async for post in queryset.all():
            post.html_tags = await get_post_html_tags(post.tags)
            posts.append(post)

        return render(
            request,
            self.template_name,
            {"page_obj": page_obj, "posts": posts, "all_tags": all_tags_html},
        )

    async def post(self, request: HttpRequest, *args, **kwargs):
        searched_word = request.POST.get("search")
        return redirect(f"hledej/{searched_word}")


# I need to disable csrf tokens for this class, because it is POST from Github, not from protected form. In class based Views, the dispatch method is responsible for csrf.
@method_decorator(csrf_exempt, name="dispatch")
class DeployApiView(View):
    """Class for automatic deployment new code from GitHub repository."""

    def post(self, request: HttpRequest, *args, **kwargs):
        # if I don't have SECRET_GITHUB_KEY, I can't compare anything
        if not hasattr(settings, "SECRET_GITHUB_KEY"):
            return HttpResponseServerError("Problem on server side!", status=501)
        # Verify if request came from GitHub
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        assert forwarded_for is not None
        req_ip_address = ip_address(forwarded_for)  # get real IP adress
        whitelist = httpx.get("https://api.github.com/meta").json()["hooks"]
        # check if req_ip_address is in ip network range
        for valid_ip in whitelist:
            if req_ip_address in ip_network(valid_ip):
                break
        else:
            return HttpResponseForbidden("Bad IP address! Permission denied.")
        # check if request is signed with GITHUB_WEBHOOK_KEY
        header_signature = request.META.get("HTTP_X_HUB_SIGNATURE_256")
        if header_signature is None:
            return HttpResponseForbidden("Bad signature! Permission denied.")
        sha_name, signature = header_signature.split("=")
        if sha_name != "sha256":
            return HttpResponseServerError("Operation not supported!", status=501)
        mac = hmac.new(
            force_bytes(settings.SECRET_GITHUB_KEY),
            msg=force_bytes(request.body),
            digestmod=sha256,
        )
        if not hmac.compare_digest(
            force_bytes(mac.hexdigest()), force_bytes(signature)
        ):
            return HttpResponseForbidden("Incorrect signature! Permission denied.")
        # implement ping/pong with GitHub
        event = request.META.get("HTTP_X_GITHUB_EVENT", "ping")
        if event == "ping":
            return HttpResponse("pong")
        elif event == "push":
            request_body = json.loads(request.body)
            if "tags" in request_body["ref"]:
                commit_with_tag = request_body["after"]
                Popen(
                    f"poetry run python manage.py redeploy {commit_with_tag}",
                    shell=True,
                )
                return HttpResponse("redeploy called")
            else:
                return HttpResponse("Noticed, but it is not new tag to redeploy code.")
        # In case we receive an event that's not ping or push
        return HttpResponse(status=204)
