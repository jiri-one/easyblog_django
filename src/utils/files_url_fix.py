from sys import path as sys_path
from pathlib import Path
from contextlib import contextmanager
from os import environ
from bs4 import BeautifulSoup


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
            soup = BeautifulSoup(post.content_cze, "html.parser")
            for tag in soup.find_all():
                if "src" in tag.attrs:
                    if "soubory" in tag["src"]:
                        index = tag["src"].index("soubory") + 7  # end of soubory
                        tag["src"] = f"/files{tag['src'][index:]}"
                if "href" in tag.attrs:
                    if "soubory" in tag["href"]:
                        index = tag["href"].index("soubory") + 7  # end of soubory
                        tag["href"] = f"/files{tag['href'][index:]}"
                if "poster" in tag.attrs:
                    if "soubory" in tag["poster"]:
                        index = tag["poster"].index("soubory") + 7  # end of soubory
                        tag["poster"] = f"/files{tag['poster'][index:]}"

            soup = str(soup)
            if "soubory/" in soup:
                soup = soup.replace("soubory/", "files/")

            post.content_cze = soup
            post.save()


fix_local_urls_in_posts_content()
