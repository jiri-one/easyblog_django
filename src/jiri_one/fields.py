import nh3
from prose.fields import RichTextField

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


def clean_editor_html(html):
    """The HTML without what the editor never writes: scripts, styles, event handlers..."""
    return nh3.clean(
        html,
        tags=TRIX_TAGS,
        attributes=TRIX_ATTRIBUTES,
        clean_content_tags={"script", "style"},
        url_schemes={"http", "https", "mailto"},
        link_rel=None,
    )


class PostContentField(RichTextField):
    """django-prose's field, with the cleaning above instead of its own, and pictures that get
    previews when the post is saved (jiri_one.pictures). A post written as HTML
    (Post.edit_as_html) is not cleaned at all: it is the author's own HTML, as on the old
    server, with styles, videos and all."""

    def pre_save(self, model_instance, add):
        html = getattr(model_instance, self.attname)
        if html:
            if not getattr(model_instance, "edit_as_html", False):
                html = clean_editor_html(html)
            html = process_pictures(html)
            setattr(model_instance, self.attname, html)
        return html
