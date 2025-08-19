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

class Track(models.Model):
    name = models.CharField(max_length=255)
    spotify_id = models.CharField(max_length=64, unique=True)   # ex: 3n3Ppam7vgaVa1iaRUc9Lp
    spotify_url = models.URLField(blank=True)

    def __str__(self): return self.name

class Playlist(models.Model):
    name = models.CharField(max_length=255)
    spotify_id = models.CharField(max_length=64, unique=True)
    url = models.URLField()
    owner_name = models.CharField(max_length=255, blank=True)
    owner_url = models.URLField(blank=True)
    followers = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True)

    def __str__(self): return self.name

class Appearance(models.Model):
    """Ligne ‘Titre / Playlist / Curateur / Contact / Abonnés / Date d'ajout / Etat / Description / Mise à jour’"""
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    contact = models.EmailField(blank=True)
    state = models.CharField("État", max_length=120, blank=True)
    added_on = models.DateField("Date d'ajout", null=True, blank=True)
    updated_on = models.DateField("Mise à jour", null=True, blank=True)

    class Meta:
        unique_together = ("track", "playlist")

class TaskStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default="idle")  # idle, running, done
    stop_requested = models.BooleanField(default=False)
    updated_on = models.DateTimeField(auto_now=True)
    extra_info = models.TextField(blank=True, null=True)  # pour stocker nb playlists trouvées, logs, etc.

    def __str__(self):
        return f"{self.name}: {self.status}"
