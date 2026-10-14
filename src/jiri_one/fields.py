import json
import re
import urllib.parse

import nh3
from django.db import models
from prose.fields import RichTextField
from prose.widgets import RichTextEditor

from jiri_one.pictures import process_pictures

# What the editor (Trix 2, through django-prose) writes. Unlike django-prose's own list this
# keeps Trix's data-trix-* attributes and the sizes of pictures, which Trix needs to open a
# post again the way it was saved.
TRIX_TAGS = {
    "a", "b", "blockquote", "br", "code", "del", "div", "em", "figcaption", "figure",
    "h1", "h2", "h3", "hr", "i", "img", "li", "ol", "p", "pre", "s", "span", "strong", "u", "ul",
}  # fmt: skip
TRIX_ATTRIBUTES = {
    "a": {"href", "title"},
    "div": {"class"},
    "figcaption": {"class"},
    "figure": {"class", "data-trix-attachment", "data-trix-attributes", "data-trix-content-type"},
    "img": {"alt", "height", "src", "title", "width"},
    "span": {"class"},
}
# The JSON Trix keeps in data-trix-attachment and data-trix-attributes: only these keys pass.
# Trix renders an attachment's "content" as HTML when it opens a post, so a post must never
# bring its own; and the addresses are only http(s) or on the site.
ATTACHMENT_KEYS = {
    "contentType": str, "filename": str, "filesize": int, "height": int, "href": "url",
    "previewable": bool, "url": "url", "width": int,
}  # fmt: skip
ATTACHMENT_ATTRIBUTE_KEYS = {"caption": str, "presentation": str}


def safe_url(value):
    if not isinstance(value, str):
        return False
    try:
        scheme = urllib.parse.urlsplit(value).scheme
    except ValueError:  # e.g. "https://[", which is no address at all
        return False
    return scheme in ("http", "https") if scheme else not value.startswith("//")


def clean_json(value, allowed):
    """The JSON object with only the allowed keys of the right type, in its own order."""
    try:
        data = json.loads(value)
    except (ValueError, RecursionError):  # RecursionError: JSON nested too deep
        return None
    if not isinstance(data, dict):
        return None
    kept = {}
    for key, item in data.items():
        kind = allowed.get(key)
        if kind == "url":
            ok = safe_url(item)
        elif kind is int:
            ok = isinstance(item, int) and not isinstance(item, bool)
        else:
            ok = kind is not None and isinstance(item, kind)
        if ok:
            kept[key] = item
    return json.dumps(kept, ensure_ascii=False, separators=(",", ":"))


def editor_attribute(tag, attribute, value):
    if tag == "figure" and attribute == "data-trix-attachment":
        return clean_json(value, ATTACHMENT_KEYS)
    if tag == "figure" and attribute == "data-trix-attributes":
        return clean_json(value, ATTACHMENT_ATTRIBUTE_KEYS)
    if tag == "figure" and attribute == "data-trix-content-type":
        return value if re.fullmatch(r"[\w.+-]+(/[\w.+-]+)?", value) else None
    if tag == "img" and attribute in ("width", "height"):
        return value if value.isdigit() else None
    return value


def clean_editor_html(html):
    """The HTML without what the editor never writes: scripts, styles, event handlers..."""
    return nh3.clean(
        html,
        tags=TRIX_TAGS,
        attributes=TRIX_ATTRIBUTES,
        attribute_filter=editor_attribute,
        clean_content_tags={"script", "style"},
        url_schemes={"http", "https", "mailto"},
        link_rel=None,
    )


class TrixEditor(RichTextEditor):
    """django-prose's editor with Trix 2.1.19 from the blog's static files: prose loads 2.1.3
    from unpkg, which has XSS bugs fixed in 2.1.4 to 2.1.18 (GitHub advisories of Trix). Its
    script is the blog's version of prose's editor.js, which tells when an upload fails."""

    class Media:
        extend = False
        css = {"all": ("trix/trix.css", "prose/editor.css")}
        js = ("trix/trix.umd.min.js", "js/editor.js")


class PostContentField(RichTextField):
    """django-prose's field, with the cleaning above instead of its own, and pictures that get
    previews when the post is saved (jiri_one.pictures). A post written as HTML
    (Post.edit_as_html) is not cleaned at all: it is the author's own HTML, as on the old
    server, with styles, videos and all."""

    def formfield(self, **kwargs):
        kwargs["widget"] = TrixEditor  # like prose's field, which puts in its own editor
        return models.TextField.formfield(self, **kwargs)

    def pre_save(self, model_instance, add):
        html = getattr(model_instance, self.attname)
        if html:
            if not getattr(model_instance, "edit_as_html", False):
                html = clean_editor_html(html)
            html = process_pictures(html)
            setattr(model_instance, self.attname, html)
        return html
