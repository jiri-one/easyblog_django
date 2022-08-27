from django.shortcuts import render
from django.http import HttpResponse
from jiri_one.models import Post, Tag, Comment


def index(request):
    posts = Post.objects.all()
    context = {'posts': posts}
    return render(request, 'index.html', context)
