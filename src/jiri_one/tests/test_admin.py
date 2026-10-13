import pytest

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
