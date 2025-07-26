from django.template import Library

register = Library()


@register.filter
def rm_pg_nr(path: str):
    """From url path remove the last part, which is page number"""
    return "/".join(list(filter(None, path.split("/")))[:-1])
    # return "/".join([x for x in path.split("/") if x != ""][:-1])
