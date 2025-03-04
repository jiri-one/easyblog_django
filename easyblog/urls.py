from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('jiri_one.urls')),
    path("prose/", include("prose.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
