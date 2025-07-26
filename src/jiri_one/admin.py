from django.contrib import admin

from .models import Post, Author, Comment, Tag

for model in [Post, Author, Comment, Tag]:
    admin.site.register(model)
