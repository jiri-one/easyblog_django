import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from PIL.PngImagePlugin import PngInfo

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
def test_mpo_photo_loses_its_gps_too(admin_client, media_root):
    """A multi-picture JPEG (MPO), as some phones take them."""
    exif = Image.Exif()
    exif[0x8825] = {1: "N", 2: (50.0, 20.0, 5.0), 3: "E", 4: (12.0, 44.0, 46.0)}
    out = io.BytesIO()
    first, second = Image.new("RGB", (400, 300), "teal"), Image.new("RGB", (400, 300), "red")
    first.save(out, "MPO", save_all=True, append_images=[second], exif=exif)
    response = post_file(admin_client, "IMG_1234.JPG", out.getvalue(), "image/jpeg")
    with Image.open(io.BytesIO(stored(media_root, response))) as im:
        assert not im.getexif().get_ifd(0x8825)


@pytest.mark.django_db
def test_png_loses_xmp_without_exif_too(admin_client, media_root):
    info = PngInfo()
    info.add_itxt("XML:com.adobe.xmp", '<x:xmpmeta xmlns:x="adobe:ns:meta/">GPSLatitude 50,20.1N</x:xmpmeta>')
    out = io.BytesIO()
    Image.new("RGB", (50, 50), "teal").save(out, "PNG", pnginfo=info)
    response = post_file(admin_client, "screen.png", out.getvalue(), "image/png")
    assert b"xmpmeta" not in stored(media_root, response)


@pytest.mark.django_db
def test_only_the_first_picture_of_a_jpeg_is_kept(admin_client, media_root):
    """An MPO with something only in its second picture, and a JPEG with a photo appended (as
    in some motion photos)."""
    second = Image.new("RGB", (400, 300), "red")
    second.info["comment"] = b"GPS 50N 12E"  # Pillow writes it into the second picture
    mpo = io.BytesIO()
    Image.new("RGB", (400, 300), "teal").save(mpo, "MPO", save_all=True, append_images=[second])
    plain = io.BytesIO()
    Image.new("RGB", (400, 300), "teal").save(plain, "JPEG")
    for data in (mpo.getvalue(), plain.getvalue() + phone_photo((40, 30))):
        kept = stored(media_root, post_file(admin_client, "IMG_1234.JPG", data, "image/jpeg"))
        assert kept.count(b"\xff\xd8\xff") == 1 and b"GPS 50N" not in kept
        with Image.open(io.BytesIO(kept)) as im:
            assert im.size == (400, 300) and not im.getexif()


@pytest.mark.django_db
def test_jpeg_comment_goes_too(admin_client, media_root):
    comment = b"Nad Vltavou 50.08N 14.42E"
    out = io.BytesIO()
    Image.new("RGB", (400, 300), "teal").save(out, "JPEG", comment=comment)
    in_header = out.getvalue()
    out = io.BytesIO()
    Image.new("RGB", (400, 300), "teal").save(out, "JPEG", progressive=True)
    # after the scans, where Pillow does not look for metadata
    at_end = out.getvalue()[:-2] + b"\xff\xfe" + (len(comment) + 2).to_bytes(2, "big") + comment + b"\xff\xd9"
    for data in (in_header, at_end):
        assert b"Vltavou" not in stored(media_root, post_file(admin_client, "photo.jpg", data, "image/jpeg"))


@pytest.mark.django_db
def test_picture_that_cannot_be_cleaned_is_refused(admin_client, media_root, monkeypatch):
    photo = phone_photo((1600, 1200))
    cut = photo[: len(photo) // 3]  # the header with the GPS position reads, the picture does not
    before_scan = photo[: photo.index(b"\xff\xda")]  # too little for Pillow to tell it is a JPEG
    for data in (cut, before_scan):
        response = post_file(admin_client, "IMG_1234.JPG", data, "image/jpeg")
        assert response.status_code == 400 and "nenahrál" in response.json()["error"]
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1000)  # a 200 MP photo, for Pillow
    response = post_file(admin_client, "IMG_1234.JPG", photo, "image/jpeg")
    assert response.status_code == 400 and "nenahrál" in response.json()["error"]
    assert not [path for path in media_root.rglob("*") if path.is_file()]


@pytest.mark.django_db
def test_upload_url_takes_only_post(admin_client, media_root):
    assert admin_client.get(UPLOAD_URL).status_code == 405
