from django.contrib import admin
from .models import Radio

@admin.register(Radio)
class RadioAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "state", "tags", "homepage", "emails")
    search_fields = ("name", "country", "state", "tags", "emails")
    list_filter = ("country", "state", "tags")
