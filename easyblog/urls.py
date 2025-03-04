from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('jiri_one.urls')),
    path('markdownx/', include('markdownx.urls')),
]
