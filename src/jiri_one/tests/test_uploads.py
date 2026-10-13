import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

UPLOAD_URL = "/prose/attachment/"


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/files/"
    return tmp_path


def post_file(client):
    file = SimpleUploadedFile("page.html", b"<script>alert(1)</script>", content_type="text/html")
    return client.post(UPLOAD_URL, {"file": file})


@pytest.mark.django_db
def test_anonymous_upload_is_refused(client, media_root):
    """The editor's upload is for the admin only, not for anyone with a CSRF token."""
    response = post_file(client)
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")
    assert not list(media_root.rglob("*"))


@pytest.mark.django_db
def test_staff_upload_is_saved(admin_client, media_root):
    response = post_file(admin_client)
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith("/files/prose/")
    assert (media_root / url.removeprefix("/files/")).read_bytes() == b"<script>alert(1)</script>"


@pytest.mark.django_db
def test_upload_url_takes_only_post(admin_client, media_root):
    assert admin_client.get(UPLOAD_URL).status_code == 405
