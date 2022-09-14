from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.utils import timezone


class Post(models.Model):
    def get_next_id(): # type: ignore
        return Post.objects.count() + 1

    id = models.IntegerField(primary_key=True, validators=[MinValueValidator(1)], editable=False, default=get_next_id)
    title_cze = models.CharField("Post title CZE", unique=True, max_length=100)
    title_eng = models.CharField("Post title ENG", unique=True, max_length=100, blank=True, null=True, default=None)
    content_cze = models.TextField("Post content CZE")
    content_eng = models.TextField("Post content ENG", blank=True, null=True, default=None)
    url_cze = models.SlugField("Post URL CZE", unique=True, max_length=100, editable=False)
    url_eng = models.SlugField("Post URL ENG", unique=True, max_length=100, blank=True, null=True, editable=False, default=None)
    pub_time = models.DateTimeField("Fist release time", editable=False, default=timezone.now)
    # for pub_time I can use auto_now_add , but it is not working for import, where is another time
    mod_time = models.DateTimeField("Last modification time", auto_now=True)
    author = models.ForeignKey("Author", on_delete=models.PROTECT)
    tags = models.ManyToManyField("Tag")

    def save(self, *args, **kwargs):
        self.url_cze = slugify(self.title_cze)
        if self.title_eng is not None:
            self.url_eng = slugify(self.title_eng)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title_cze

    class Meta:
        ordering = ["-pub_time"]


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
    pub_time = models.DateTimeField("Comment time", auto_now_add=True)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} - {self.nick}"


class Tag(models.Model):
    name_cze = models.CharField("Tag name CZE", unique=True, max_length=20, )
    name_eng = models.CharField("Tag name ENG", unique=True, max_length=20, blank=True, null=True, default=None)
    desc_cze = models.CharField("Tag description CZE", max_length=100)
    desc_eng = models.CharField("Tag description ENG", max_length=100, blank=True, null=True)
    url_cze = models.SlugField("Tag URL CZE", max_length=25, unique=True, editable=False)
    url_eng = models.SlugField("Tag URL ENG", max_length=25, blank=True, null=True, editable=False, default=None)
    order = models.IntegerField()

    def save(self, *args, **kwargs):
        self.url_cze = slugify(self.name_cze)
        if self.name_eng is not None:
            self.url_eng = slugify(self.name_eng)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name_cze

    class Meta:
        ordering = ["order"]
