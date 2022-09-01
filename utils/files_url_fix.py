from sys import path as sys_path
from pathlib import Path
from contextlib import contextmanager
from os import environ

@contextmanager
def django_context():
    try:
        django_dir = str(Path(__file__).parent.parent)
        sys_path.append(django_dir)
        from django.core.wsgi import get_wsgi_application
        environ["DJANGO_SETTINGS_MODULE"] = "easyblog.settings"
        application = get_wsgi_application()
        yield
    finally:
        sys_path.remove(django_dir)
        del application

def fix_local_urls_in_posts_content():
    with django_context():
        from jiri_one.models import Post
        for post in Post.objects.all():
            post.content_cze
        # django_post, _ = Post.objects.update_or_create(title_cze=dict_row["title_cze"], defaults={**dict_row})
        # django_post.save()
        # django_post.tags.add(*tags)


fix_local_urls_in_posts_content()
