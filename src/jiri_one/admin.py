from django.contrib import admin
from django.contrib.admin.widgets import AdminTextareaWidget

from .models import Author, Comment, Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, change=change, **kwargs)
        if obj is not None and obj.edit_as_html:
            # a plain text area instead of the editor, which would rebuild the HTML
            for name in ("content_cze", "content_eng"):
                if name in form.base_fields:  # not there for staff who may only view posts
                    form.base_fields[name].widget = AdminTextareaWidget(attrs={"rows": 30})
        return form


for model in [Author, Comment, Tag]:
    admin.site.register(model)
