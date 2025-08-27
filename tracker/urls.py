from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # ----- Artiste & track management -----
    path("manage/", views.artist_track_manage, name="artist_track_manage"),
    path("artists/", views.artist_list, name="artist_list"),
    path("artists/add/", views.artist_create, name="artist_create"),
    path("artists/<int:pk>/edit/", views.artist_update, name="artist_update"),
    path("artist/<int:pk>/delete/", views.artist_delete, name="artist_delete"),
    path("tracks/", views.track_list, name="track_list"),
    path("tracks/add/", views.track_create, name="track_create"),
    path("tracks/<int:pk>/edit/", views.track_update, name="track_update"),
    path("tracks/<int:pk>/delete/", views.track_delete, name="track_delete"),
    path('artist/<int:artist_id>/tracks/', views.tracks_by_artist, name='tracks_by_artist'),

    # ----- Discover & Scan playlists management -----
    path("discover_status/", views.discover_status, name="discover_status"),
    path("discover_playlists/", views.run_discover_playlists, name="discover_playlists"),
    path("stop_discover_playlists/", views.stop_discover_playlists, name="stop_discover_playlists"),
    path("scan_status/", views.scan_status, name="scan_status"),
    path("scan_playlists/", views.run_scan_playlists, name="scan_playlists"),
    path("stop_scan_playlists/", views.stop_scan_playlists, name="stop_scan_playlists"),
    path("spotify_status/", views.spotify_status, name="spotify_status"),

    # ----- Import & Export management -----
    path("import_export/", views.import_export, name="import_export"),
    path("export/excel/", views.export_excel, name="export_excel"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
    path("confirm-import/", views.confirm_import, name="confirm_import"),

    # ----- Login & credentials management -----
    path("login/", views.spotify_login, name="spotify_login"),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("spotify/credentials/", views.spotify_credentials, name="spotify_credentials"),
    path("spotify/callback/", views.spotify_callback, name="spotify_callback"),
]
