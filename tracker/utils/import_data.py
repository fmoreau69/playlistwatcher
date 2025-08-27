import pandas as pd
from datetime import datetime, date
from ..models import Track, Playlist, Appearance

def import_preview_apparitions(data, mode):
    imported, updated = 0, 0
    for row in data:
        track, _ = Track.objects.get_or_create(name=row["Titre"] or "Inconnu",
                                               defaults={"spotify_id": f"temp_{row['Titre'][:64]}"})
        playlist, _ = Playlist.objects.get_or_create(
            name=row["Playlist"] or "Sans nom",
            defaults={
                "spotify_id": f"temp_{row['Playlist'][:64]}",
                "followers": clean_int(row["Abonnés"]),
                "description": row["Description"],
                "url": row["PlaylistURL"],
                "owner_name": row["Curateur"],
                "owner_url": row["CurateurURL"],
            }
        )
        added_on = clean_date(row["Date d'ajout"])
        updated_on = clean_date(row["Mise à jour"]) or datetime.today().date()
        appearance, created = Appearance.objects.get_or_create(
            track=track, playlist=playlist,
            defaults={
                "contact": row["Contact"], "state": row["Etat"],
                "added_on": added_on, "updated_on": updated_on
            }
        )
        if created:
            imported += 1
        else:
            if mode == "overwrite":
                appearance.contact = row["Contact"] or appearance.contact
                appearance.state = row["Etat"] or appearance.state
                appearance.added_on = added_on or appearance.added_on
                appearance.updated_on = updated_on
                appearance.save()
                updated += 1
            elif mode == "complete":
                changed = False
                if not appearance.contact and row["Contact"]:
                    appearance.contact = row["Contact"]
                    changed = True
                if not appearance.state and row["Etat"]:
                    appearance.state = row["Etat"]
                    changed = True
                if not appearance.added_on and added_on:
                    appearance.added_on = added_on
                    changed = True
                if changed:
                    appearance.updated_on = updated_on
                    appearance.save()
                    updated += 1
    return imported, updated

def import_preview_playlists(data, mode):
    imported, updated = 0, 0
    for row in data:
        playlist, created = Playlist.objects.get_or_create(
            name=row["Nom"] or "Sans nom",
            defaults={
                "spotify_id": f"temp_{row['Nom'][:64]}",
                "url": row["URL"],
                "owner_name": row["Curateur"],
                "followers": clean_int(row["Abonnés"]),
                "description": row["Description"]
            }
        )
        if created:
            imported += 1
        else:
            if mode == "overwrite":
                playlist.url = row["URL"] or playlist.url
                playlist.owner_name = row["Curateur"] or playlist.owner_name
                playlist.followers = clean_int(row["Abonnés"]) or playlist.followers
                playlist.description = row["Description"] or playlist.description
                playlist.save()
                updated += 1
            elif mode == "complete":
                changed = False
                if not playlist.url and row["URL"]:
                    playlist.url = row["URL"]
                    changed = True
                if not playlist.owner_name and row["Curateur"]:
                    playlist.owner_name = row["Curateur"]
                    changed = True
                if not playlist.followers and row["Abonnés"]:
                    playlist.followers = clean_int(row["Abonnés"])
                    changed = True
                if not playlist.description and row["Description"]:
                    playlist.description = row["Description"]
                    changed = True
                if changed:
                    playlist.save()
                    updated += 1
    return imported, updated

def clean_date(value):
    """Nettoyer une date venant de pandas/excel"""
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None

def clean_int(value):
    """Nettoie un entier venant d'Excel, retourne None si vide"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).replace("\u202f", "").replace(" ", "").strip()
    return int(s) if s.isdigit() else None
