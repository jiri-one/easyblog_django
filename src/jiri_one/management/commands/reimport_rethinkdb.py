from django.core.management.base import BaseCommand, CommandError
from django.db.utils import OperationalError
from datetime import datetime
from zoneinfo import ZoneInfo
from rethinkdb import RethinkDB
from rethinkdb.errors import ReqlDriverError
from jiri_one.models import Post, Tag, Author


class Command(BaseCommand):
    help = "Import/update new data from RethinkDB"
    europe_prague = ZoneInfo("Europe/Prague")

    def update_django_from_rethinkdb(self, options):
        # create RethinkDB connection and settings
        rdb_ip = options["rdb_ip"]
        rdb_port = options["rdb_port"]
        db_name = "blog_jirione"  # hardcoded, because on all machines it is this name
        r = RethinkDB()
        conn = r.connect(rdb_ip, rdb_port, db=db_name)

        topics = r.table("topics")
        posts = r.table("posts")
        for post in posts.order_by(r.asc("when")).run(conn):
            dict_row = {}
            dict_row["title_cze"] = post["header"]["cze"]
            dict_row["content_cze"] = post["content"]["cze"]
            dict_row["pub_time"] = datetime.strptime(
                post["when"], "%Y-%m-%d %H:%M:%S"
            ).astimezone(self.europe_prague)
            # dict_row["mod_time"] = ...
            dict_row["author"], _ = Author.objects.get_or_create(
                nick="Jiří",
                defaults={"nick": "Jiří", "first_name": "Jiří", "last_name": "Němec"},
            )
            tags = []
            for tag in post["topics"]["cze"].split(";")[:-1]:
                topic = list(topics.filter(r.row["topic"]["cze"] == tag).run(conn))[0]
                tag_to_add, _ = Tag.objects.get_or_create(
                    name_cze=tag,
                    defaults={
                        "name_cze": tag,
                        "desc_cze": topic["description"]["cze"],
                        "order": topic["order"],
                    },
                )
                tags.append(tag_to_add)
            django_post, _ = Post.objects.update_or_create(
                title_cze=dict_row["title_cze"], defaults={**dict_row}
            )
            django_post.save()
            django_post.tags.add(*tags)

    def add_arguments(self, parser):
        parser.add_argument("--rdb_ip", type=str, default="localhost")
        parser.add_argument("--rdb_port", type=int, default=28015)

    def handle(self, *args, **options):
        try:
            start_time = datetime.now()
            self.update_django_from_rethinkdb(options)
            time = datetime.now() - start_time
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully imported/updated RethinkDB to Django and it takes {time.seconds//60} minutes and {time.seconds%60} seconds."
                )
            )
        except ReqlDriverError as e:
            self.stdout.write(self.style.ERROR("Unable to connect to RethinkDB!"))
            raise CommandError(e)
        except OperationalError as e:
            self.stdout.write(self.style.ERROR("Unable to connect to Django DB!"))
            raise CommandError(e)
        # NOTE: it will be nice to handle more exceptions in the future
