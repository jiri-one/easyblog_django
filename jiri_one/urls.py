from django.urls import path
from . import views

app_name = "jiri_one"
urlpatterns = [
    path('', views.PostListView.as_view()),
    path('page/<int:page>/', views.PostListView.as_view()),
    path('strana/<int:strana>/', views.PostListView.as_view()),
    path('tag/<str:tag>/', views.PostListView.as_view()),
    path('tag/<str:tag>/strana/<int:strana>/', views.PostListView.as_view()),
    path('tag/<str:tag>/page/<int:page>/', views.PostListView.as_view()),
    path('search/<str:search>/', views.PostListView.as_view()),
    path('hledej/<str:hledej>/', views.PostListView.as_view()),
    path('search/<str:search>/strana/<int:strana>/', views.PostListView.as_view()),
    path('search/<str:search>/page/<int:page>/', views.PostListView.as_view()),
    path('hledej/<str:hledej>/strana/<int:strana>/', views.PostListView.as_view()),
    path('hledej/<str:hledej>/page/<int:page>/', views.PostListView.as_view()),
    path('<slug:url_cze>/', views.PostDetailView.as_view()),
]
