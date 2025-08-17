from django.db import models

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
    followers = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    def __str__(self): return self.name

class Appearance(models.Model):
    """Ligne ‘Titre / Playlist / Curateur / Contact / Abonnés / Date d'ajout / Etat / Description / Mise à jour’"""
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    contact = models.EmailField(blank=True)
    state = models.CharField("État", max_length=120, blank=True)
    added_on = models.DateField("Date d'ajout", auto_now_add=True)
    updated_on = models.DateField("Mise à jour", auto_now=True)

    class Meta:
        unique_together = ("track", "playlist")
