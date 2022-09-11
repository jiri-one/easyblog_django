from jiri_one.models import Post, Comment, Tag
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.db.models import Q
from django.shortcuts import redirect
from django.http import HttpResponseForbidden


class PostDetailView(DetailView):
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
    model = Post
    template_name = 'index.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
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

    def post(self, request, *args, **kwargs):
        searched_word = request.POST.get('search')
        return redirect(f'hledej/{searched_word}')
