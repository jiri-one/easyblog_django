from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from graphene_django.views import GraphQLView
from prose.views import upload_attachment

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('jiri_one.urls')),
    # the editor's file uploads; the route in prose.urls lets anyone put files on the site
    path(
        "prose/attachment/",
        staff_member_required(require_POST(upload_attachment)),
        name="prose_upload_attachment",
    ),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
