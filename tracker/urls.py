from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("tracks/new/", views.add_track, name="add_track"),
    path("export/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path('import-excel/', views.import_excel, name='import_excel'),
    path("confirm-import/", views.confirm_import, name="confirm_import"),
    path("scan_status/", views.scan_status, name="scan_status"),
    path("scan_playlists/", views.run_scan_playlists, name="scan_playlists"),
    path("stop_scan_playlists/", views.stop_scan_playlists, name="stop_scan_playlists"),
    path("spotify/credentials/", views.spotify_credentials, name="spotify_credentials"),
    path("spotify/callback/", views.spotify_callback, name="spotify_callback"),
    path("login/", views.spotify_login, name="spotify_login"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
]
