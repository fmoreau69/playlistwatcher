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


def safe_update_or_create(defaults, stationuuid, max_retries=5):
    for attempt in range(max_retries):
        try:
            return Radio.objects.update_or_create(
                stationuuid=stationuuid,
                defaults=defaults
            )
        except OperationalError as e:
            if 'database is locked' in str(e):
                time.sleep(0.5)
            else:
                raise
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                # Chercher l'objet par (name, country, state)
                obj = Radio.objects.filter(
                    name=defaults["name"],
                    country=defaults["country"],
                    state=defaults["state"]
                ).first()
                if obj:
                    for k, v in defaults.items():
                        setattr(obj, k, v)
                    obj.save()
                    return obj, False
            else:
                raise
    raise OperationalError(f"Impossible d'écrire la station {stationuuid} après {max_retries} tentatives.")



def save_stations_batch(stations, batch_size=BATCH_SIZE):
    """
    Sauvegarde les stations par lots pour éviter les verrous SQLite.
    Affiche une barre de progression console.
    """
    total_created, total_updated = 0, 0
    total = len(stations)

    for offset in range(0, total, batch_size):
        batch = stations[offset:offset+batch_size]
        with transaction.atomic():
            for i, s in enumerate(batch, start=offset+1):
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
                radio, created = safe_update_or_create(defaults=defaults, stationuuid=s["stationuuid"])
                if created:
                    total_created += 1
                else:
                    total_updated += 1

                # Barre de progression console
                progress = (i / total) * 100
                print(f"\r[{i}/{total}] {radio.name[:30]:30} - {progress:5.1f}% ", end="", flush=True)
        print()  # nouvelle ligne après batch
    print(f"Total créées: {total_created}, mises à jour: {total_updated}")
    return total_created, total_updated


def refresh_radios_progress(country=None):
    """
    Récupère les radios et met à jour la base locale avec messages de progression.
    """
    stations = fetch_stations_by_country(country=country)
    total_created, total_updated = 0, 0
    messages = []

    for batch_start in range(0, len(stations), BATCH_SIZE):
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
                action = "Créée" if was_created else "Mise à jour"
                messages.append(f"[{i}/{len(stations)}] {action} : {radio.name}")
                if was_created:
                    total_created += 1
                else:
                    total_updated += 1

    return {
        "total": len(stations),
        "created": total_created,
        "updated": total_updated,
        "messages": messages
    }
