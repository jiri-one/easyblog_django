import pytest

# internal imports
from test_views import create_post


@pytest.mark.django_db
def test_new_post_id_after_deleting_older_post():
    first = create_post(title_cze="First", content_cze="First content.")
    create_post(title_cze="Second", content_cze="Second content.")
    first.delete()
    third = create_post(title_cze="Third", content_cze="Third content.")
    assert third.id == 3
