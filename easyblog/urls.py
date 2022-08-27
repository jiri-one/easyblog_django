from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', include('jiri_one.urls')),
    path('admin/', admin.site.urls),
]
