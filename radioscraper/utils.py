import requests
import time
from django.db import transaction, OperationalError
from radioscraper.models import Radio

API_URL = "https://de1.api.radio-browser.info/json/stations"
BATCH_SIZE = 50

def fetch_stations_by_country(country=None, limit=1000, offset=0):
    """
    Récupère les radios depuis Radio Browser pour un pays précis.
    Paginer si nécessaire.
    """
    params = {"limit": limit, "offset": offset}
    if country:
        params["country"] = country

    all_stations = []
    while True:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        stations = response.json()
        if not stations:
            break
        all_stations.extend(stations)
        offset += limit
        params["offset"] = offset
    return all_stations

def refresh_radios():
    """
    Récupère toutes les radios et met à jour la base locale.
    """
    stations = fetch_stations_by_country()
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
    stations = fetch_stations_by_country()
    total = len(stations)
    created, updated = 0, 0
    messages = []

    for batch_start in range(0, total, BATCH_SIZE):
        batch = stations[batch_start:batch_start+BATCH_SIZE]
        with transaction.atomic():
            for i, s in enumerate(batch, start=batch_start+1):
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

