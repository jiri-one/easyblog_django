from django.db import models
from django.utils.text import slugify
import re


class Post(models.Model):    
    title_cze = models.CharField("Post title CZE", max_length=100)
    title_eng = models.CharField("Post title ENG", max_length=100, blank=True, null=True)
    content_cze = models.TextField("Post content CZE")
    content_eng = models.TextField("Post content ENG", blank=True, null=True)
    url_cze = models.SlugField("Post URL CZE", max_length=100, unique=True, editable=False)
    url_eng = models.SlugField("Post URL ENG", max_length=100, unique=True, blank=True, null=True, editable=False)
    pub_time = models.DateTimeField("Fist release time", auto_now_add=True)
    mod_time = models.DateTimeField("Last modification time", auto_now=True)
    author = models.OneToOneField("Author", on_delete=models.PROTECT)
    tags = models.ManyToManyField("Tag")
    
    def save(self, *args, **kwargs):
        self.url_cze = slugify(self.title_cze)
        self.url_eng = slugify(self.title_eng)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title_cze


class Author(models.Model):
    nick = models.CharField("Author's nick", max_length=20)
    first_name = models.CharField("Author's firstname", max_length=20)
    last_name = models.CharField("Author's lastname", max_length=20)

    def __str__(self):
        return self.nick


class Comment(models.Model):
    title = models.CharField("Comment title", max_length=100)
    content = models.TextField("Comment content")
    nick = models.CharField("Comment author - nick", max_length=20)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.title} - {self.nick}"


class Tag(models.Model):
    name_cze = models.CharField("Tag name CZE", max_length=20)
    name_eng = models.CharField("Tag name ENG", max_length=20)
    desc_cze = models.CharField("Tag description CZE", max_length=100)
    desc_eng = models.CharField("Tag description ENG", max_length=100)

    def __str__(self):
        return f"{self.name_cze} ({self.name_eng})"
