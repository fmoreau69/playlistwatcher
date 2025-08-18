from django.db import models
from django.contrib.auth.models import User

class SpotifyCredentials(models.Model):
    client_id = models.CharField(max_length=200, blank=True, null=True)
    client_secret = models.CharField(max_length=200, blank=True, null=True)
    redirect_uri = models.URLField(default="http://localhost:8000/callback", blank=True)

    # Tu peux forcer un seul enregistrement
    singleton = models.BooleanField(default=True, editable=False, unique=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # impose qu’il n’existe qu’un enregistrement
        super().save(*args, **kwargs)

    def __str__(self):
        return "Identifiants Spotify"

class SpotifyToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} Spotify Token"

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

    def __str__(self):
        return f"{self.name}: {self.status}"
