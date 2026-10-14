import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

UPLOAD_URL = "/prose/attachment/"


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/files/"
    return tmp_path


def phone_photo(size=(4000, 3000)):
    """A JPEG as a phone takes it: lying on its side (EXIF orientation 6), with a GPS position."""
    exif = Image.Exif()
    exif[0x0112] = 6
    exif[0x8825] = {1: "N", 2: (50.0, 20.0, 5.0), 3: "E", 4: (12.0, 44.0, 46.0)}
    out = io.BytesIO()
    Image.new("RGB", size, "teal").save(out, "JPEG", exif=exif)
    return out.getvalue()


def post_file(client, name="page.html", data=b"<script>alert(1)</script>", content_type="text/html"):
    return client.post(UPLOAD_URL, {"file": SimpleUploadedFile(name, data, content_type=content_type)})


def stored(media_root, response):
    return (media_root / response.json()["url"].removeprefix("/files/")).read_bytes()


@pytest.mark.django_db
def test_anonymous_upload_is_refused(client, media_root):
    """The editor's upload is for the admin only, not for anyone with a CSRF token."""
    response = post_file(client)
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")
    assert not list(media_root.rglob("*"))


@pytest.mark.django_db
def test_other_files_are_kept_as_they_are(admin_client, media_root):
    response = post_file(admin_client)
    assert response.status_code == 201
    assert response.json()["url"].startswith("/files/prose/")
    assert response.json()["url"].endswith(".html")
    assert stored(media_root, response) == b"<script>alert(1)</script>"


@pytest.mark.django_db
def test_photo_is_upright_smaller_and_without_gps(admin_client, media_root):
    response = post_file(admin_client, "IMG_1234.JPG", phone_photo(), "image/jpeg")
    assert response.status_code == 201
    assert response.json()["url"].endswith(".jpg")
    with Image.open(io.BytesIO(stored(media_root, response))) as im:
        assert im.size == (1920, 2560)  # turned upright, at most 2560 px
        exif = im.getexif()
        assert not exif.get_ifd(0x8825)  # no GPS
        assert exif.get(0x0112, 1) == 1  # nothing left to turn


@pytest.mark.django_db
def test_png_is_turned_upright_too(admin_client, media_root):
    exif = Image.Exif()
    exif[0x0112] = 6
    out = io.BytesIO()
    Image.new("RGB", (100, 50), "teal").save(out, "PNG", exif=exif)
    response = post_file(admin_client, "screen.png", out.getvalue(), "image/png")
    with Image.open(io.BytesIO(stored(media_root, response))) as im:
        assert im.size == (50, 100)
        assert not im.getexif()


@pytest.mark.django_db
def test_jpeg_without_metadata_is_not_encoded_again(admin_client, media_root):
    out = io.BytesIO()
    Image.new("RGB", (600, 981), "teal").save(out, "JPEG", quality=95)
    response = post_file(admin_client, "cover.jpg", out.getvalue(), "image/jpeg")
    assert stored(media_root, response) == out.getvalue()


@pytest.mark.django_db
def test_upload_url_takes_only_post(admin_client, media_root):
    assert admin_client.get(UPLOAD_URL).status_code == 405
