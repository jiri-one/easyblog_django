from django.template import Library

register = Library()


@register.filter
def tags_html(tags):
    """From tags of post create HTML"""
    tags_links = []
    for tag in tags.values():
        tags_links.append(f"""<a href="/tag/{tag["url_cze"]}">{tag["name_cze"]}</a>""")
    return ", ".join(tags_links)


@register.filter
def rm_pg_nr(path: str):
    """From url path remove the last part, which is page number"""
    return "/".join(list(filter(None, path.split("/")))[:-1])
    # return "/".join([x for x in path.split("/") if x != ""][:-1])
