import pytest
from django.contrib.auth.models import Permission, User

from jiri_one.models import Author, Post


@pytest.fixture
def post_as_html(db):
    author = Author.objects.create(nick="Test", first_name="Test", last_name="Test")
    return Post.objects.create(title_cze="Starý", content_cze="<p>Text</p>", author=author, edit_as_html=True)


def test_post_written_as_html_gets_a_text_area(admin_client, post_as_html):
    page = admin_client.get(f"/admin/jiri_one/post/{post_as_html.id}/change/").content.decode()
    assert '<textarea name="content_cze"' in page
    assert "trix-editor" not in page


@pytest.mark.django_db
def test_new_post_gets_the_editor(admin_client):
    page = admin_client.get("/admin/jiri_one/post/add/").content.decode()
    assert "trix-editor" in page
    # Trix from the blog's static files, not the old 2.1.3 that prose loads from unpkg
    assert "trix/trix.umd.min.js" in page and "unpkg.com" not in page
    assert "js/editor.js" in page and "prose/editor.js" not in page


def test_staff_who_may_only_view_posts(client, post_as_html):
    viewer = User.objects.create_user("viewer", is_staff=True)
    viewer.user_permissions.add(Permission.objects.get(codename="view_post"))
    client.force_login(viewer)
    assert client.get(f"/admin/jiri_one/post/{post_as_html.id}/change/").status_code == 200
