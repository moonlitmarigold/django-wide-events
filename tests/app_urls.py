from django.urls import path

from . import views

app_name = "tests"

urlpatterns = [
    path("ok/", views.ok, name="ok"),
    path("health", views.health, name="health"),
    path("boom/", views.boom, name="boom"),
    path("slow/", views.slow, name="slow"),
    path("error/", views.server_error, name="server-error"),
    path("forbidden/", views.forbidden, name="forbidden"),
    path("echo/", views.echo, name="echo"),
    path("pictures/<int:public_id>/download/", views.picture_download, name="picture-download"),
    path("redirect/", views.redirect_ish, name="redirect"),
]
