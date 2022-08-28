from django.urls import path
from . import views

app_name = "jiri_one"
urlpatterns = [
    path('', views.index, name='index'),
    path('<slug:url_cze>/', views.PostDetailView.as_view(), name='post'),
]
