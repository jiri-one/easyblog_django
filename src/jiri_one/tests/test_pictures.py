import io

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

from jiri_one.fields import clean_editor_html
from jiri_one.models import Author, Post
from jiri_one.pictures import process_pictures


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/files/"
    return tmp_path


def put_picture(path, size):
    out = io.BytesIO()
    Image.new("RGB", size, "teal").save(out, "JPEG")
    default_storage.save(path, ContentFile(out.getvalue()))


def editor_figure(path, size, caption=None):
    """A picture dropped into the editor, as Trix 2 through django-prose writes it."""
    url = f"/files/{path}"
    data = (
        "{&quot;contentType&quot;:&quot;image/jpeg&quot;,&quot;filename&quot;:&quot;photo.jpg&quot;,"
        f"&quot;height&quot;:{size[1]},&quot;href&quot;:&quot;{url}?content-disposition=attachment&quot;,"
        f"&quot;url&quot;:&quot;{url}&quot;,&quot;width&quot;:{size[0]}}}"
    )
    if caption is None:
        figcaption = (
            '<figcaption class="attachment__caption"><span class="attachment__name">photo.jpg</span> '
            '<span class="attachment__size">2.52 MB</span></figcaption>'
        )
    else:
        figcaption = f'<figcaption class="attachment__caption attachment__caption--edited">{caption}</figcaption>'
    return (
        f'<figure data-trix-attachment="{data}" data-trix-content-type="image/jpeg" '
        'data-trix-attributes="{&quot;presentation&quot;:&quot;gallery&quot;}" '
        'class="attachment attachment--preview attachment--jpg">'
        f'<a href="{url}?content-disposition=attachment">'
        f'<img src="{url}" width="{size[0]}" height="{size[1]}">{figcaption}</a></figure>'
    )


def test_editor_picture_gets_a_preview(media_root):
    put_picture("prose/2026/10/13/a.jpg", (2400, 1800))
    html = "<div>Text</div>" + editor_figure("prose/2026/10/13/a.jpg", (2400, 1800))
    out = process_pictures(html)
    # at most 480x400 in the post, the preview twice that, the link to the full picture
    assert '<img src="/files/nahledy/prose/2026/10/13/a-960x720.jpg" width="480" height="360">' in out
    assert '<a href="/files/prose/2026/10/13/a.jpg">' in out
    with Image.open(media_root / "nahledy/prose/2026/10/13/a-960x720.jpg") as preview:
        assert preview.size == (960, 720)
    # Trix's own record of the attachment stays, so the editor opens it as before
    assert "&quot;url&quot;:&quot;/files/prose/2026/10/13/a.jpg&quot;" in out
    # no file name and size under the picture
    assert "figcaption" not in out


def test_processing_twice_changes_nothing(media_root):
    put_picture("prose/a.jpg", (2400, 1800))
    once = process_pictures(editor_figure("prose/a.jpg", (2400, 1800)))
    assert process_pictures(once) == once


def test_written_caption_stays(media_root):
    put_picture("prose/a.jpg", (2400, 1800))
    out = process_pictures(editor_figure("prose/a.jpg", (2400, 1800), caption="Pejsek"))
    assert '<figcaption class="attachment__caption attachment__caption--edited">Pejsek</figcaption>' in out


def test_small_editor_picture_is_only_sized(media_root):
    put_picture("prose/cover.jpg", (600, 981))
    out = process_pictures(editor_figure("prose/cover.jpg", (600, 981)))
    assert '<img src="/files/prose/cover.jpg" width="245" height="400">' in out
    assert not (media_root / "nahledy").exists()


def test_old_post_picture(media_root):
    put_picture("pejsek/p.jpg", (2322, 4128))
    html = '<p><a href="/files/pejsek/p.jpg"><img alt="" height="266" src="/files/pejsek/p.jpg" width="150"/></a></p>'
    assert process_pictures(html) == (
        '<p><a href="/files/pejsek/p.jpg"><img alt="" height="267" '
        'src="/files/nahledy/pejsek/p-300x533.jpg" width="150"/></a></p>'
    )


def test_old_post_picture_without_a_link_gets_one(media_root):
    put_picture("big.jpg", (1600, 1200))
    html = '<p><img src="/files/big.jpg" style="float: left;" width="320"/></p>'
    assert process_pictures(html) == (
        '<p><a href="/files/big.jpg"><img src="/files/nahledy/big-640x480.jpg" '
        'style="float: left;" width="320" height="240"/></a></p>'
    )


def test_left_alone(media_root):
    put_picture("small.jpg", (550, 341))
    html = (
        '<p><img src="/files/small.jpg"/></p>'  # small, no size given
        '<p><img src="https://example.com/x.jpg" width="100"/></p>'  # another site
        '<p><img src="/files/missing.jpg" width="100"/></p>'  # no such file
    )
    assert process_pictures(html) == html


def test_editor_html_cleaning():
    html = editor_figure("prose/a.jpg", (2400, 1800)) + '<script>alert(1)</script><img src="x.jpg" onerror="alert(2)">'
    out = clean_editor_html(html)
    assert "data-trix-attachment" in out and 'width="2400" height="1800"' in out
    assert "script" not in out and "onerror" not in out


def save_post(content, edit_as_html):
    author = Author.objects.create(nick="Test", first_name="Test", last_name="Test")
    return Post.objects.create(title_cze="Test", content_cze=content, author=author, edit_as_html=edit_as_html)


HAND_WRITTEN = '<p style="float: left">Text</p><video controls="" width="320"></video><script src="/x.js"></script>'


@pytest.mark.django_db
def test_post_written_as_html_is_saved_as_written(media_root):
    post = save_post(HAND_WRITTEN, edit_as_html=True)
    post.refresh_from_db()
    assert post.content_cze == HAND_WRITTEN


@pytest.mark.django_db
def test_post_from_the_editor_is_cleaned(media_root):
    post = save_post(HAND_WRITTEN, edit_as_html=False)
    post.refresh_from_db()
    assert post.content_cze == "<p>Text</p>"
