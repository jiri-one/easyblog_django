from sys import path as sys_path
from pathlib import Path
from contextlib import contextmanager
from os import environ
from datetime import datetime
from zoneinfo import ZoneInfo
from rethinkdb import RethinkDB
import asyncio

# timezone settings
europe_prague = ZoneInfo("Europe/Prague")

# RethinkDB settings
db_name = "blog_jirione"
r = RethinkDB()
rethinkdb_ip = "172.19.37.187"
rethinkdb_port = 28015
conn = r.connect(rethinkdb_ip, rethinkdb_port, db=db_name)
topics = r.table("topics")
posts = r.table("posts")
comments = r.table("comments")
authors = r.table("authors")


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

def migrate_db_from_rethinkdb_to_django():
    with django_context():
        from jiri_one.models import Post, Tag, Author
        Post.objects.all().delete()
        Tag.objects.all().delete()
        dict_row = {}
        id = posts.count().run(conn)
        for post in posts.order_by(r.desc("when")).run(conn):
            dict_row["id"] = id
            dict_row["title_cze"] = post["header"]["cze"]
            dict_row["content_cze"] = post["content"]["cze"]
            dict_row["pub_time"] = datetime.strptime(post["when"], "%Y-%m-%d %H:%M:%S").astimezone(europe_prague)
            # dict_row["mod_time"] = ...
            dict_row["author"] = Author.objects.get(id=1)
            tags = []
            for tag in post["topics"]["cze"].split(";")[:-1]:
                topic = list(topics.filter(r.row["topic"]["cze"] == tag).run(conn))[0]
                tag_to_add, _ = Tag.objects.get_or_create(name_cze=tag, defaults={"name_cze": tag, "desc_cze": topic["description"]["cze"], "order": topic["order"]})
                tags.append(tag_to_add)
            django_post, _ = Post.objects.update_or_create(title_cze=dict_row["title_cze"], defaults={**dict_row})
            django_post.save()
            django_post.tags.add(*tags)
            id = id - 1

migrate_db_from_rethinkdb_to_django()
