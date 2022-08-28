from django.shortcuts import render
from django.http import HttpResponse
from jiri_one.models import Post, Tag, Comment
from django.views.generic.detail import DetailView

class PostDetailView(DetailView):
    model = Post
    slug_field = 'url_cze'
    slug_url_kwarg = 'url_cze'
    template_name = 'post.html'


def index(request):
    posts = Post.objects.all()
    context = {'posts': posts}
    return render(request, 'index.html', context)
