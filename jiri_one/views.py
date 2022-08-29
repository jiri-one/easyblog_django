from django.shortcuts import render
from django.http import HttpResponse
from jiri_one.models import Post, Tag, Comment
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

class PostDetailView(DetailView):
    model = Post
    slug_field = 'url_cze'
    slug_url_kwarg = 'url_cze'
    template_name = 'post.html'


class PostListView(ListView):
    model = Post
    template_name = 'index.html'
    paginate_by = 10
    
    
    def get(self, request, *args, **kwargs):
        if 'strana' in kwargs:
            self.page_kwarg = 'strana'
        if 'tag' in kwargs:
            tag = Tag.objects.get(url_cze=kwargs["tag"])
            self.queryset = self.model.objects.filter(tags__exact=tag).all()
        return super().get(request, *args, **kwargs)
    
