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
    page_kwarg = 'strana'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # print(context["paginator"].page())
        return context
