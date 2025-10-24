from django.db import models


STATION_TYPE_CHOICES = (
    ("fm", "FM"),
    ("web", "Web"),
    ("dab", "DAB"),
    ("am", "AM"),
    ("satellite", "Satellite"),
    ("other", "Other"),
)


class Radio(models.Model):
    stationuuid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=255, blank=True, null=True)
    tags = models.CharField(max_length=500, blank=True, null=True)
    homepage = models.URLField(blank=True, null=True)
    stream_url = models.URLField(blank=True, null=True)
    emails = models.TextField(blank=True, null=True)
    favicon = models.URLField(blank=True)
    language = models.CharField(max_length=50, blank=True)

    # New fields (English)
    station_type = models.CharField(max_length=30, choices=STATION_TYPE_CHOICES, blank=True)
    show_name = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    account_owner = models.CharField(max_length=255, blank=True)  # internal referent/owner
    last_contact_date = models.DateField(blank=True, null=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        return self.name
