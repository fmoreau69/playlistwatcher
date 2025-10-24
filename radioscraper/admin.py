from django.contrib import admin
from .models import Radio

@admin.register(Radio)
class RadioAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "station_type",
        "country",
        "state",
        "tags",
        "homepage",
        "contact_name",
        "contact_email",
        "contact_phone",
        "last_contact_date",
    )
    search_fields = (
        "name",
        "stationuuid",
        "country",
        "state",
        "tags",
        "emails",
        "contact_name",
        "contact_email",
        "contact_phone",
        "show_name",
        "account_owner",
    )
    list_filter = ("station_type", "country", "state")
