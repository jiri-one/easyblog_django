"""Pictures in posts: previews made when a post is saved, and the editor's uploads.

A post shows a picture at some size: the one its HTML gives (width, height or style), or, for
pictures from the editor (Trix only records the picture's own size) and big pictures without
a size, at most BOX. When the file is at least WIDER times wider than that, the post gets a
preview at DENSITY times the shown size (sharp on phones too) in MEDIA_ROOT/PREVIEW_DIR, and
a link around it leads to the full picture. How a picture fits a narrow screen is up to the
stylesheet (max-width: 100%).

Only the <img> tags that change are rewritten; the rest of the HTML stays as it was written.
"""

import io
import os
import re
import urllib.parse
from dataclasses import dataclass
from html import escape
from html.parser import HTMLParser

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image, ImageOps

PREVIEW_DIR = "nahledy"
WIDER = 2.5  # a picture this many times wider than shown gets a preview
DENSITY = 2  # previews have twice the shown size, for phones and other sharp screens
BOX = (480, 400)  # the size of pictures that come without one
UPLOAD_MAX_SIDE = 2560  # uploaded photos are made at most this big; enough for any screen
UPLOAD_MAX_BYTES = 30 * 1024 * 1024
OLD_MEDIA_URL = "/soubory/"  # the media's old address, which Caddy still serves
# not a picture, not one Pillow knows, too big to open, or a path outside MEDIA_ROOT
UNUSABLE = (OSError, SyntaxError, ValueError, SuspiciousFileOperation, Image.DecompressionBombError)


@dataclass
class Tag:
    start: int  # offset of the tag in the HTML
    raw: str  # the tag as written
    attrs: dict


@dataclass
class Img(Tag):
    link: Tag | None  # the <a> the picture is in
    from_editor: bool  # in a picture attachment of Trix


class PictureFinder(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", html)]
        self.links = []  # the <a> elements open at this point
        self.figures = []  # the classes of the open <figure> elements
        self.imgs = []
        self.feed(html)
        self.close()

    def tag(self, attrs):
        line, column = self.getpos()
        return Tag(self.line_starts[line - 1] + column, self.get_starttag_text(), dict(attrs))

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.links.append(self.tag(attrs))
        elif tag == "figure":
            self.figures.append((dict(attrs).get("class") or "").split())
        elif tag == "img":
            found = self.tag(attrs)
            from_editor = any("attachment--preview" in classes for classes in self.figures)
            link = self.links[-1] if self.links else None
            self.imgs.append(Img(found.start, found.raw, found.attrs, link, from_editor))

    def handle_startendtag(self, tag, attrs):
        if tag == "img":  # <img .../>; a self-closed <a/> or <figure/> opens nothing
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "a" and self.links:
            self.links.pop()
        elif tag == "figure" and self.figures:
            self.figures.pop()


def media_path(url):
    """The file in MEDIA_ROOT that a URL on the site points to, None for other sites."""
    try:
        parts = urllib.parse.urlsplit(url or "")
    except ValueError:  # e.g. "https://[" in a post written by hand
        return None
    if parts.netloc not in ("", "jiri.one", "www.jiri.one"):
        return None
    path = urllib.parse.unquote(parts.path)
    # the posts link /files/ (and the old /soubory/) whatever MEDIA_URL a setup has
    for prefix in (settings.MEDIA_URL, "/files/", OLD_MEDIA_URL):
        if path.startswith(prefix):
            return path[len(prefix) :]
    return None


def media_url(path):
    return settings.MEDIA_URL + urllib.parse.quote(path, safe="/-_.~")


def picture_size(path):
    """(width, height) as shown, after the EXIF orientation; None for animations, other files
    and missing ones."""
    try:
        with default_storage.open(path) as file, Image.open(file) as im:
            if getattr(im, "n_frames", 1) > 1:
                return None
            w, h = im.size
            if im.getexif().get(0x0112, 1) in (5, 6, 7, 8):  # turned by 90 degrees
                w, h = h, w
            return w, h
    except UNUSABLE:
        return None


# a size in pixels as posts write it: "320", "320px", "1.5px" or ".5px" (not "1..5")
PX = re.compile(r"\s*(\d+(?:\.\d+)?|\.\d+)\s*(?:px)?\s*", re.I)


def written_size(img, prop):
    """The picture's width or height as the post writes it: in its style, else in its
    attribute; None when it gives none."""
    css = re.search(rf"(?:^|;)\s*{prop}\s*:\s*([^;]*)", img.attrs.get("style") or "", re.I)
    return css.group(1) if css else img.attrs.get(prop)


def px(value):
    """The pixels in a written size; None for none, other units and what is no number."""
    m = PX.fullmatch(value or "")
    return float(m.group(1)) if m else None


def fit(size, box):
    """size scaled down to fit into box, keeping its proportions."""
    scale = min(1, box[0] / size[0], box[1] / size[1])
    return max(1, round(size[0] * scale)), max(1, round(size[1] * scale))


def height_for(width, size):
    """The height of a picture of this size shown this wide (at least 1 px)."""
    return max(1, round(width * size[1] / size[0]))


def other_units(img):
    """True when the post sizes the picture in something else than px (width="100%",
    style="width: 20em"), in no number at all or hides it (width="0"): the author's layout,
    which the picture keeps."""
    for prop in ("width", "height"):
        value = written_size(img, prop)
        if value is not None and not px(value):
            return True
    return False


def shown_size(img, size):
    """(width, height, given): how big the post shows the picture; given is False when the
    size comes from BOX."""
    w, h = (px(written_size(img, prop)) for prop in ("width", "height"))
    if img.from_editor or not (w or h):
        return *fit(size, BOX), False
    if w:
        return max(1, round(w)), height_for(w, size), True
    return max(1, round(h * size[0] / size[1])), max(1, round(h)), True


def make_preview(path, size):
    """The picture scaled to size, as JPEG, or PNG when it has see-through parts; returns the
    preview's path (an existing one is used again)."""
    with default_storage.open(path) as file, Image.open(file) as im:
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        see_through = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
        if see_through:
            im = im.convert("RGBA")
            see_through = im.getchannel("A").getextrema()[0] < 255
        # the source's whole name, extension included: photo.jpg and photo.png get their own
        name = f"{PREVIEW_DIR}/{path}-{size[0]}x{size[1]}.{'png' if see_through else 'jpg'}"
        if default_storage.exists(name):
            return name
        im = im.convert("RGBA" if see_through else "RGB").resize(size, Image.LANCZOS, reducing_gap=3.0)
        out = io.BytesIO()
        if see_through:
            im.save(out, "PNG", optimize=True, icc_profile=icc)
        else:
            im.save(out, "JPEG", quality=85, optimize=True, progressive=True, icc_profile=icc)
    default_storage.save(name, ContentFile(out.getvalue()))
    return name


# one attribute of a start tag: its name and, if it has one, its value
ATTRIBUTE = re.compile(r"""\s+(?P<name>[^\s"'>/=]+)(?:\s*=\s*(?P<value>"[^"]*"|'[^']*'|[^\s>]+))?""")


def set_attr(tag, name, value):
    """The tag with the attribute set (replaced, or added after the last one). The attributes
    are walked one after another, so text inside a value that looks like an attribute
    (alt="a src=x onload=...") is never taken for one."""
    value = escape(str(value))
    pos = re.match(r"<[^\s/>]+", tag).end()
    while m := ATTRIBUTE.match(tag, pos):
        if m.group("name").lower() == name:
            if m.group("value") is None:  # a name without a value
                return f'{tag[: m.end("name")]}="{value}"{tag[m.end("name") :]}'
            return f'{tag[: m.start("value")]}"{value}"{tag[m.end("value") :]}'
        pos = m.end()
    return f'{tag[:pos]} {name}="{value}"{tag[pos:]}'


# Trix's caption of a picture that got none: the file's name and size
DEFAULT_CAPTION = re.compile(
    r'<figcaption class="attachment__caption">\s*(<span class="attachment__name">[^<]*</span>)?\s*'
    r'(<span class="attachment__size">[^<]*</span>)?\s*</figcaption>'
)
PICTURE_FIGURE = re.compile(r'<figure\b[^>]*\battachment--preview\b[^>]*>.*?</figure>', re.S)


PREVIEW_NAME = re.compile(rf"{PREVIEW_DIR}/(.+)-(\d+)x(\d+)\.(?:jpg|png)")


def original_of(preview, link):
    """The full picture of a preview: in the preview's name (since the names keep the source's
    extension), or where the link around it leads."""
    m = PREVIEW_NAME.fullmatch(preview)
    for path in (m and m.group(1), link and media_path(link.attrs.get("href"))):
        if path and not path.startswith(PREVIEW_DIR + "/") and default_storage.exists(path):
            return path
    return None


def process_pictures(html):
    """The post's HTML with previews, links to the full pictures and shown sizes."""
    edits = []  # (start, old text, new text)
    links_done = set()
    for img in PictureFinder(html).imgs:
        path = media_path(img.attrs.get("src"))
        if path is None or (other_units(img) and not img.from_editor):
            continue
        current = None  # the preview the picture shows now, if it does
        if path.startswith(PREVIEW_DIR + "/"):
            current, path = path, original_of(path, img.link)
            if path is None:
                continue
        size = picture_size(path)
        if size is None:
            continue
        w, h, given = shown_size(img, size)
        new = img.raw
        preview = size[0] >= WIDER * w
        if preview:
            wanted = (DENSITY * w, height_for(DENSITY * w, size))
            m = current and PREVIEW_NAME.fullmatch(current)
            if m and (int(m.group(2)), int(m.group(3))) == wanted and default_storage.exists(current):
                preview_path = current  # still the right size, whatever its name
            else:
                try:
                    preview_path = make_preview(path, wanted)
                except UNUSABLE:  # e.g. a JPEG cut short: the header reads, the picture does not
                    continue
            new = set_attr(new, "src", media_url(preview_path))
        elif current:
            new = set_attr(new, "src", media_url(path))  # shown big enough for the original
        if img.from_editor or "width" in img.attrs or "height" in img.attrs or (preview and not given):
            new = set_attr(set_attr(new, "width", w), "height", h)
        if img.link is None:
            if preview:
                new = f'<a href="{escape(media_url(path))}">{new}</a>'
        elif img.link.start not in links_done:
            # Trix links its attachments with ?content-disposition=attachment, which means
            # nothing to Caddy; the plain address is nicer
            href = img.link.attrs.get("href") or ""
            plain = href.removesuffix("?content-disposition=attachment")
            if plain != href:
                edits.append((img.link.start, img.link.raw, set_attr(img.link.raw, "href", plain)))
                links_done.add(img.link.start)
        if new != img.raw:
            edits.append((img.start, img.raw, new))
    for start, old, new in sorted(edits, reverse=True):  # from the end, offsets stay valid
        assert html[start : start + len(old)] == old
        html = html[:start] + new + html[start + len(old) :]
    # no "IMG_1234.jpg 3.2 MB" under the pictures; a caption that was written stays
    return PICTURE_FIGURE.sub(lambda m: DEFAULT_CAPTION.sub("", m.group(0)), html)


def prepare_upload(name, data):
    """(bytes, extension) to store for a file uploaded in the editor. A photo is turned
    upright, made at most UPLOAD_MAX_SIDE big and loses its EXIF, XMP and IPTC (the GPS
    position included); a PNG is saved again without any of that; other files, and JPEGs
    without metadata, are kept as they are."""
    ext = os.path.splitext(name)[1].lstrip(".").lower()
    if not re.fullmatch(r"[a-z0-9]{1,10}", ext):
        ext = "bin"
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except UNUSABLE:
        return data, ext
    out = io.BytesIO()
    # a phone's MPO (a JPEG with more pictures in it) is a photo too: only its first is kept
    if im.format in ("JPEG", "MPO"):
        metadata = im.getexif() or any(key in im.info for key in ("xmp", "photoshop"))
        if not metadata and max(im.size) <= UPLOAD_MAX_SIDE:
            return data, "jpg"  # nothing to remove: not encoded again, no quality lost
        icc = im.info.get("icc_profile")
        im = ImageOps.exif_transpose(im)
        im.thumbnail((UPLOAD_MAX_SIDE, UPLOAD_MAX_SIDE), Image.LANCZOS)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(out, "JPEG", quality=90, optimize=True, progressive=True, icc_profile=icc)
        return out.getvalue(), "jpg"
    if getattr(im, "n_frames", 1) > 1:
        return data, ext  # animations as they are
    if im.format == "PNG":
        # saved again, without its EXIF, XMP and text chunks; no quality is lost in a PNG
        icc = im.info.get("icc_profile")
        ImageOps.exif_transpose(im).save(out, "PNG", optimize=True, icc_profile=icc)
        return out.getvalue(), "png"
    return data, ext
