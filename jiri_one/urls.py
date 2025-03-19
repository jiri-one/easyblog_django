from django.urls import path
from . import views

app_name = "jiri_one"
urlpatterns = [
    path("", views.IndexView.as_view()),
    path("page/<int:page>/", views.IndexView.as_view()),
    path("strana/<int:strana>/", views.IndexView.as_view()),
    path("tag/<str:tag>/", views.IndexView.as_view()),
    path("tag/<str:tag>/strana/<int:strana>/", views.IndexView.as_view()),
    path("tag/<str:tag>/page/<int:page>/", views.IndexView.as_view()),
    path("search/<str:search>/", views.IndexView.as_view()),
    path("hledej/<str:hledej>/", views.IndexView.as_view()),
    path("search/<str:search>/strana/<int:strana>/", views.IndexView.as_view()),
    path("search/<str:search>/page/<int:page>/", views.IndexView.as_view()),
    path("hledej/<str:hledej>/strana/<int:strana>/", views.IndexView.as_view()),
    path("hledej/<str:hledej>/page/<int:page>/", views.IndexView.as_view()),
    path("deploy_api/", views.DeployApiView.as_view()),
    path("<slug:url_cze>/", views.PostView.as_view()),
]
