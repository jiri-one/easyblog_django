from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views import View
from django.db.models import Q
from django.shortcuts import redirect
from django.http import HttpResponseForbidden, HttpResponseServerError, HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils.encoding import force_bytes
from django.conf import settings
from hashlib import sha256
import hmac
from ipaddress import ip_address, ip_network
import httpx
import json
# internal imports
from jiri_one.models import Post, Comment, Tag
from jiri_one.management.commands.redeploy import Command


class PostDetailView(DetailView):
    """Class for showing one post/entry."""
    model = Post
    slug_field = 'url_cze'
    slug_url_kwarg = 'url_cze'
    template_name = 'post.html'

    def post(self, request, *args, **kwargs):
        """POST method for save comment."""
        # antispam comment part
        try:
            five = int(request.POST.get('antispam'))
            if five != 5:
                raise ValueError
        except ValueError:
            return HttpResponseForbidden("Musíte správně vyplnit pole Anitspam!")
        # comment save part
        header = request.POST.get('comment_header')
        nick = request.POST.get('comment_nick')
        content = request.POST.get('comment_content')
        Comment.objects.create(post=self.get_object(),
                               title=header, nick=nick,
                               content=content)
        return redirect(request.path)


class PostListView(ListView):
    """Main and the only one class to show index, tags and search results."""
    model = Post
    template_name = 'index.html'
    paginate_by = 10

    def get(self, request: HttpRequest, *args, **kwargs):
        if 'strana' in kwargs:
            self.page_kwarg = 'strana'
        if 'tag' in kwargs:
            self.tag = Tag.objects.get(url_cze=kwargs["tag"])
            self.queryset = self.model.objects.filter(tags__url_cze=kwargs["tag"]).all()
        if 'search' in kwargs or 'hledej' in kwargs:
            if kwargs.get("search"):
                self.searched_word = kwargs.get("search")
            elif kwargs.get("hledej"):
                self.searched_word = kwargs.get("hledej")
            self.queryset = self.model.objects.filter(
                Q(content_cze__icontains=self.searched_word) | Q(title_cze__icontains=self.searched_word))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self, "tag"):
            context["tag"] = self.tag
        elif hasattr(self, "searched_word"):
            context["searched_word"] = self.searched_word
        return context

    def post(self, request: HttpRequest, *args, **kwargs):
        searched_word = request.POST.get('search')
        return redirect(f'hledej/{searched_word}')

# I need to desable csrf tokens for this class, bacause it is POST from Github, not from protected form. In class based Views, the dispatch method is responsible for csrf.
@method_decorator(csrf_exempt, name='dispatch')
class DeployApiView(View):
    """Class for automatic deployment new code from GitHub repository."""
    def post(self, request: HttpRequest, *args, **kwargs):
        # if I don't have SECRET_GITHUB_KEY, I can't compare anything
        if not hasattr(settings, "SECRET_GITHUB_KEY"):
            return HttpResponseServerError('Problem on server side!', status=501)
        # Verify if request came from GitHub
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        req_ip_address = ip_address(forwarded_for) # get real IP adress
        whitelist = httpx.get('https://api.github.com/meta').json()['hooks']
        # check if req_ip_adress is in ip network range
        for valid_ip in whitelist:
            if req_ip_address in ip_network(valid_ip):
                break
        else:
            return HttpResponseForbidden('Bad IP address! Permission denied.')
        # check if request is signed with GITHUB_WEBHOOK_KEY
        header_signature = request.META.get('HTTP_X_HUB_SIGNATURE_256')
        if header_signature is None:
            return HttpResponseForbidden('Bad signature! Permission denied.')
        sha_name, signature = header_signature.split('=')
        if sha_name != 'sha256':
            return HttpResponseServerError('Operation not supported!', status=501)
        mac = hmac.new( force_bytes(settings.SECRET_GITHUB_KEY),
                        msg=force_bytes(request.body),
                        digestmod=sha256)
        if not hmac.compare_digest(force_bytes(mac.hexdigest()), force_bytes(signature)):
            return HttpResponseForbidden('Incorrect signature! Permission denied.')
        # implement ping/pong with GitHub
        event = request.META.get('HTTP_X_GITHUB_EVENT', 'ping')
        if event == 'ping':
            return HttpResponse('pong')
        elif event == 'push':
            request_body = json.loads(request.body)
            if "tags" in request_body["refs"]:
                commit_with_tag = request_body["after"]
                #call redeploy command
                redeploy = Command()
                redeploy.handle(commit=commit_with_tag)
                return HttpResponse("redeploy called")
            else:
                return HttpResponse("Noticed, but it is not new tag to redeploy code.")
 
