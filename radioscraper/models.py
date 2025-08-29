from django.db import models


class Radio(models.Model):
    stationuuid = models.CharField(max_length=50, unique=True, blank=True)  # nouveau champ
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)  # région
    tags = models.CharField(max_length=500, blank=True, null=True)  # styles/genres
    homepage = models.URLField(blank=True, null=True)
    stream_url = models.URLField(blank=True, null=True)
    emails = models.TextField(blank=True, null=True)
    favicon = models.URLField(blank=True)
    language = models.CharField(max_length=50, blank=True)

    class Meta:
        unique_together = ("name", "country", "state")

    def __str__(self):
        return self.name
