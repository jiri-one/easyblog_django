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


def put_picture(path, size, colour="teal", kind="JPEG"):
    out = io.BytesIO()
    Image.new("RGB", size, colour).save(out, kind)
    default_storage.save(path, ContentFile(out.getvalue()))
    return out.getvalue()


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
    assert '<img src="/files/nahledy/prose/2026/10/13/a.jpg-960x720.jpg" width="480" height="360">' in out
    assert '<a href="/files/prose/2026/10/13/a.jpg">' in out
    with Image.open(media_root / "nahledy/prose/2026/10/13/a.jpg-960x720.jpg") as preview:
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
        'src="/files/nahledy/pejsek/p.jpg-300x533.jpg" width="150"/></a></p>'
    )


def test_old_post_picture_without_a_link_gets_one(media_root):
    put_picture("big.jpg", (1600, 1200))
    html = '<p><img src="/files/big.jpg" style="float: left;" width="320"/></p>'
    assert process_pictures(html) == (
        '<p><a href="/files/big.jpg"><img src="/files/nahledy/big.jpg-640x480.jpg" '
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


def test_picture_that_does_not_decode_is_left_alone(media_root):
    data = put_picture("cut.jpg", (1600, 1200))
    (media_root / "cut.jpg").write_bytes(data[: len(data) // 3])  # the header reads, the rest is gone
    html = '<p><img src="/files/cut.jpg" width="320"/></p>'
    assert process_pictures(html) == html


def test_same_names_with_other_extensions_get_their_own_previews(media_root):
    put_picture("photo.jpg", (1600, 1200), "red")
    put_picture("photo.png", (1600, 1200), "blue", "PNG")
    out = process_pictures('<img src="/files/photo.jpg" width="320"/><img src="/files/photo.png" width="320"/>')
    assert "/files/nahledy/photo.jpg-640x480.jpg" in out and "/files/nahledy/photo.png-640x480.jpg" in out
    with Image.open(media_root / "nahledy/photo.png-640x480.jpg") as im:
        assert im.getpixel((10, 10))[2] > 200  # blue, not the red JPEG's preview


def test_very_narrow_picture(media_root):
    put_picture("prose/line.png", (1, 1000), kind="PNG")
    out = process_pictures(editor_figure("prose/line.png", (1, 1000)))
    assert 'width="1" height="400"' in out


def test_attribute_names_in_capitals(media_root):
    put_picture("big.jpg", (1600, 1200))
    out = process_pictures('<p><a href="/files/big.jpg"><IMG SRC="/files/big.jpg" WIDTH="320"></a></p>')
    assert out == '<p><a href="/files/big.jpg"><IMG SRC="/files/nahledy/big.jpg-640x480.jpg" WIDTH="320" height="240"></a></p>'


def test_attribute_like_text_in_a_value_stays_text(media_root):
    put_picture("big.jpg", (1600, 1200))
    html = '<p><img alt="photo src=x onload=alert(1)//" src="/files/big.jpg" width="320"/></p>'
    out = process_pictures(html)
    assert 'alt="photo src=x onload=alert(1)//"' in out and out.count("onload") == 1
    assert 'src="/files/nahledy/big.jpg-640x480.jpg"' in out


def test_broken_addresses_do_not_stop_a_save(media_root):
    assert process_pictures('<img src="https://[" width="100">') == '<img src="https://[" width="100">'
    data = "{&quot;url&quot;:&quot;https://[&quot;,&quot;width&quot;:300}"
    out = clean_editor_html(f'<figure data-trix-attachment="{data}"></figure>')
    assert "https://[" not in out and "&quot;width&quot;:300" in out


def test_attachment_json_nested_too_deep_is_dropped():
    data = "[" * 100000 + "]" * 100000
    assert "data-trix-attachment" not in clean_editor_html(f'<figure data-trix-attachment="{data}"></figure>')


def test_sizes_in_other_units_are_the_authors(media_root):
    put_picture("photo.jpg", (2400, 1800))
    html = '<p><img src="/files/photo.jpg" width="100%"/><img src="/files/photo.jpg" style="width: 20em"/></p>'
    assert process_pictures(html) == html


def test_sizes_that_are_no_numbers_or_hide_the_picture_are_the_authors(media_root):
    put_picture("photo.jpg", (2400, 1800))
    html = (
        '<p><img src="/files/photo.jpg" width="1..5"/><img src="/files/photo.jpg" style="width: .px"/>'
        '<img src="/files/photo.jpg" width="0" height="0"/></p>'
    )
    assert process_pictures(html) == html
    # a picture from the editor is sized by the picture itself, whatever its attributes say
    out = process_pictures(editor_figure("photo.jpg", (2400, 1800)).replace('width="2400"', 'width="1..5"'))
    assert 'width="480" height="360"' in out


def test_missing_preview_is_made_again(media_root):
    put_picture("photo.jpg", (2400, 1800))
    html = process_pictures('<p><img src="/files/photo.jpg" width="100"/></p>')
    (media_root / "nahledy/photo.jpg-200x150.jpg").unlink()
    assert process_pictures(html) == html
    assert (media_root / "nahledy/photo.jpg-200x150.jpg").exists()
    # an old preview, named without the extension, comes back under the new name
    put_picture("pejsek/p.jpg", (2322, 4128))
    old = '<a href="/files/pejsek/p.jpg"><img alt="" height="267" src="/files/nahledy/pejsek/p-300x533.jpg" width="150"/></a>'
    assert 'src="/files/nahledy/pejsek/p.jpg-300x533.jpg"' in process_pictures(old)


def test_preview_follows_a_new_size(media_root):
    put_picture("photo.jpg", (2400, 1800))
    small = process_pictures('<p><img src="/files/photo.jpg" width="100"/></p>')
    assert 'src="/files/nahledy/photo.jpg-200x150.jpg"' in small
    # the author makes it bigger in the HTML; the preview is made again from the original
    bigger = process_pictures(small.replace('width="100" height="75"', 'width="500" height="375"'))
    assert 'src="/files/nahledy/photo.jpg-1000x750.jpg"' in bigger
    assert process_pictures(bigger) == bigger
    # shown at 1000 px, the 2400 px original needs no preview any more
    big = process_pictures(bigger.replace('width="500" height="375"', 'width="1000" height="750"'))
    assert 'src="/files/photo.jpg"' in big


def test_old_previews_keep_their_names(media_root):
    """The previews made 2026-10-13 are named without the source's extension."""
    put_picture("pejsek/p.jpg", (2322, 4128))
    put_picture("nahledy/pejsek/p-300x533.jpg", (300, 533))
    html = '<a href="/files/pejsek/p.jpg"><img alt="" height="267" src="/files/nahledy/pejsek/p-300x533.jpg" width="150"/></a>'
    assert process_pictures(html) == html


def test_files_prefix_with_another_media_url(media_root, settings):
    settings.MEDIA_URL = "/media/"
    put_picture("big.jpg", (1600, 1200))
    assert "nahledy/big.jpg-640x480.jpg" in process_pictures('<img src="/files/big.jpg" width="320">')


def test_editor_html_cleaning():
    html = editor_figure("prose/a.jpg", (2400, 1800)) + '<script>alert(1)</script><img src="x.jpg" onerror="alert(2)">'
    out = clean_editor_html(html)
    assert "data-trix-attachment" in out and 'width="2400" height="1800"' in out
    assert "script" not in out and "onerror" not in out


def test_attachment_json_keeps_only_safe_keys():
    data = (
        "{&quot;contentType&quot;:&quot;image/png&quot;,"
        "&quot;content&quot;:&quot;&lt;img src=x onerror=alert(1)&gt;&quot;,"
        "&quot;url&quot;:&quot;javascript:alert(2)&quot;,"
        "&quot;href&quot;:&quot;/files/prose/a.png&quot;,&quot;width&quot;:300}"
    )
    out = clean_editor_html(f'<figure data-trix-attachment="{data}" class="attachment"></figure>')
    # Trix would render "content" as HTML when the post is opened in the editor
    assert "content&quot;" not in out and "onerror" not in out and "javascript" not in out
    assert "&quot;href&quot;:&quot;/files/prose/a.png&quot;" in out and "&quot;width&quot;:300" in out


def test_attachment_from_trix_passes_unchanged():
    html = editor_figure("prose/a.jpg", (2400, 1800), caption="Pejsek")
    assert clean_editor_html(html) == html


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
