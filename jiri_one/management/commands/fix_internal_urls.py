from django.core.management.base import BaseCommand
from datetime import datetime
from jiri_one.models import Post
from bs4 import BeautifulSoup

class Command(BaseCommand):
    help = 'Fix internal URLs in posts'

    def fix_local_urls_in_posts_content(self):
        for post in Post.objects.all():
            soup = BeautifulSoup(post.content_cze, 'html.parser')
            for tag in soup.find_all():
                if 'src' in tag.attrs:
                    if 'soubory' in tag['src']:
                        index = tag['src'].index('soubory') + 7 # end of soubory
                        tag['src'] = f"/files{tag['src'][index:]}"
                if 'href' in tag.attrs:
                    if 'soubory' in tag['href']:
                        index = tag['href'].index('soubory') + 7 # end of soubory
                        tag['href'] = f"/files{tag['href'][index:]}"
                if 'poster' in tag.attrs:
                    if 'soubory' in tag['poster']:
                        index = tag['poster'].index('soubory') + 7 # end of soubory
                        tag['poster'] = f"/files{tag['poster'][index:]}"

            soup = str(soup)
            if 'soubory/' in soup:
                soup = soup.replace('soubory/', 'files/')

            post.content_cze = soup
            post.save()


    def handle(self, *args, **options):
        start_time = datetime.now()
        self.fix_local_urls_in_posts_content()
        time = datetime.now() - start_time
        self.stdout.write(self.style.SUCCESS(f'Successfully fixed URLs in posts and it takes {time.seconds//60} minutes and {time.seconds%60} seconds.'))
        # NOTE: it will be nice to handle some exceptions in the future 
