from django.contrib import admin

from .models import *

for model in [Post, Author, Comment, Tag]:
    admin.site.register(model)
