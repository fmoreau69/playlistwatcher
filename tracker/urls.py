from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tracks/new/", views.add_track, name="add_track"),
    path("export/", views.export_excel, name="export_excel"),
    path('import-excel/', views.import_excel, name='import_excel'),
    path("confirm-import/", views.confirm_import, name="confirm_import"),
    path("scan_playlists/", views.run_scan_playlists, name="scan_playlists"),
]
