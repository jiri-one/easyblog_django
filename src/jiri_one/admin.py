from django.contrib import admin

from .models import Author, Comment, Post, Tag

for model in [Post, Author, Comment, Tag]:
    admin.site.register(model)
