import datetime
import requests
from django.db import models
from django.conf import settings
from django.utils import timezone

class SpotifyCredentials(models.Model):
    client_id = models.CharField(max_length=200, blank=True, null=True)
    client_secret = models.CharField(max_length=200, blank=True, null=True)
    redirect_uri = models.URLField(default="http://127.0.0.1:8000/spotify/callback", blank=True)

    # Tu peux forcer un seul enregistrement
    singleton = models.BooleanField(default=True, editable=False, unique=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # impose qu’il n’existe qu’un enregistrement
        super().save(*args, **kwargs)

    def __str__(self):
        return "Identifiants Spotify"


class SpotifyToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def refresh(self):
        """
        Rafraîchit le token en utilisant le refresh_token.
        """
        url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": settings.SPOTIFY_CLIENT_ID,
            "client_secret": settings.SPOTIFY_CLIENT_SECRET,
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        payload = resp.json()

        self.access_token = payload["access_token"]
        # Spotify ne renvoie pas toujours un refresh_token → on garde l’ancien
        expires_in = payload.get("expires_in", 3600)
        self.expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)
        self.save()


class Artist(models.Model):
    name = models.CharField(max_length=200, unique=True)
    spotify_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    spotify_url = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        if self.spotify_id and not self.spotify_url:
            self.spotify_url = f"https://open.spotify.com/artist/{self.spotify_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Track(models.Model):
    name = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="tracks", default=1)
    spotify_id = models.CharField(max_length=100, unique=True)
    spotify_url = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        if self.spotify_id and not self.spotify_url:
            self.spotify_url = f"https://open.spotify.com/track/{self.spotify_id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.artist.name})"


class Playlist(models.Model):
    spotify_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    owner_name = models.CharField(max_length=255, blank=True)
    owner_url = models.URLField(blank=True)
    followers = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    discovered_on = models.DateTimeField(blank=True, null=True)
    last_discovered = models.DateTimeField(blank=True, null=True)
    last_scanned = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name


class Appearance(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="appearances")
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="appearances")
    added_on = models.DateTimeField(blank=True, null=True)
    updated_on = models.DateTimeField(blank=True, null=True)
    state = models.CharField(max_length=50, default="new")  # new, confirmed, lost…
    contact = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ("track", "playlist")


class TaskStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default="idle")  # idle, running, done
    stop_requested = models.BooleanField(default=False)
    updated_on = models.DateTimeField(auto_now=True)
    extra_info = models.TextField(blank=True, null=True)  # pour stocker nb playlists trouvées, logs, etc.
    extra_json = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.name}: {self.status}"
