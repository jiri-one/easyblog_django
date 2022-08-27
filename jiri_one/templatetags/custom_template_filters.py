from django.template import Library

register = Library()

@register.filter
def tags_html(tags):
    """From tags of post create HTML"""
    tags_links = []
    for tag in tags.values():
        tags_links.append(
             f"""<a href="/tag/{tag["url_cze"]}">{tag["name_cze"]}</a>"""
        )
    return ", ".join(tags_links)

@register.filter
def count(item):
    """Return count of item"""
    return item.count()
