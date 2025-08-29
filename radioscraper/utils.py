import requests
import time
from django.db import transaction, OperationalError
from radioscraper.models import Radio

API_URL = "https://de1.api.radio-browser.info/json/stations"

def fetch_all_stations(limit=1000):
    """
    Récupère toutes les radios depuis Radio Browser en paginant.
    """
    all_stations = []
    offset = 0

    while True:
        response = requests.get(API_URL, params={"limit": limit, "offset": offset}, timeout=30)
        response.raise_for_status()
        stations = response.json()
        if not stations:
            break
        all_stations.extend(stations)
        offset += limit

    return all_stations

def refresh_radios():
    """
    Récupère toutes les radios et met à jour la base locale.
    """
    stations = fetch_all_stations()
    created, updated = 0, 0

    for s in stations:
        radio, was_created = Radio.objects.update_or_create(
            stationuuid=s["stationuuid"],
            defaults={
                "name": s.get("name", ""),
                "country": s.get("country", ""),
                "state": s.get("state", ""),
                "tags": s.get("tags", ""),
                "homepage": s.get("homepage", ""),
                "emails": s.get("email", ""),
                "favicon": s.get("favicon", ""),
                "language": s.get("language", ""),
                "stream_url": s.get("url", ""),
            }
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {"created": created, "updated": updated, "total": len(stations)}

def safe_update_or_create(defaults, stationuuid, max_retries=5):
    """
    Update or create avec retry si la DB est verrouillée.
    """
    for attempt in range(max_retries):
        try:
            return Radio.objects.update_or_create(
                stationuuid=stationuuid,
                defaults=defaults
            )
        except OperationalError as e:
            if 'database is locked' in str(e):
                time.sleep(0.5)  # attendre 500ms et réessayer
            else:
                raise
    # Si on n'a pas réussi après max_retries
    raise OperationalError(f"Impossible d'écrire la station {stationuuid} après {max_retries} tentatives.")

def refresh_radios_progress():
    """
    Actualisation avec messages progressifs et protection contre les verrous SQLite.
    """
    stations = fetch_all_stations()
    total = len(stations)
    created, updated = 0, 0
    messages = []

    with transaction.atomic():  # tout est dans une transaction unique
        for i, s in enumerate(stations, start=1):
            defaults = {
                "name": s.get("name", ""),
                "country": s.get("country", ""),
                "state": s.get("state", ""),
                "tags": s.get("tags", ""),
                "homepage": s.get("homepage", ""),
                "emails": s.get("email", ""),
                "favicon": s.get("favicon", ""),
                "language": s.get("language", ""),
                "stream_url": s.get("url", ""),
            }

            radio, was_created = safe_update_or_create(defaults=defaults, stationuuid=s["stationuuid"])

            if was_created:
                created += 1
                messages.append(f"[{i}/{total}] Créée : {radio.name}")
            else:
                updated += 1
                messages.append(f"[{i}/{total}] Mise à jour : {radio.name}")

    return {
        "total": total,
        "created": created,
        "updated": updated,
        "messages": messages
    }
