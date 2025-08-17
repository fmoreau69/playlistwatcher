from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tracks/new/", views.add_track, name="add_track"),
    path("export/", views.export_excel, name="export_excel"),
]
