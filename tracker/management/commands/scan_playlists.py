import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from spotipy.exceptions import SpotifyException

from tracker.models import Track, Playlist, Appearance, TaskStatus, SpotifyToken
from tracker.spotify import client, search_playlists_for_track


class Command(BaseCommand):
    help = "Scanne les playlists Spotify contenant chaque morceau et met à jour la base."

    def handle(self, *args, **opts):
        # Vérification du token global
        token_obj = SpotifyToken.objects.first()
        if not token_obj:
            self.stdout.write(self.style.ERROR("Aucun token Spotify trouvé dans la base !"))
            return

        sp = client()

        # Initialisation du statut de tâche
        task_status, _ = TaskStatus.objects.get_or_create(name="scan_playlists")
        task_status.status = "running"
        task_status.extra_info = "0 nouvelles apparitions, 0 mises à jour"
        task_status.extra_json = {"created": 0, "updated": 0, "total": 0, "current": 0}
        task_status.save(update_fields=["status", "extra_info", "extra_json"])

        tracks = Track.objects.all()
        total_tracks = tracks.count()
        created, updated = 0, 0
        current_track_index = 0

        try:
            for t in tracks:
                current_track_index += 1
                self.stdout.write(self.style.MIGRATE_HEADING(f"→ {t.name} ({t.spotify_id})"))

                while True:  # gestion des rate limits
                    try:
                        results = search_playlists_for_track(
                            sp, t.spotify_id, t.name, artist_hint=t.artist.name
                        )
                        break
                    except SpotifyException as e:
                        if e.http_status == 429:  # trop de requêtes
                            retry_after = int(e.headers.get("Retry-After", "5"))
                            self.stdout.write(self.style.WARNING(
                                f"Rate limit atteint. Attente de {retry_after} secondes..."
                            ))
                            time.sleep(retry_after + 1)
                        else:
                            raise

                # Traitement des playlists trouvées
                for pl in results:
                    playlist, _ = Playlist.objects.update_or_create(
                        spotify_id=pl["id"],
                        defaults=dict(
                            name=pl["name"],
                            url=pl["url"],
                            owner_name=pl["owner_name"],
                            owner_url=pl["owner_url"],
                            followers=pl["followers"],
                            description=pl["description"],
                            last_scanned=timezone.now()
                        )
                    )

                    app, was_created = Appearance.objects.update_or_create(
                        track=t, playlist=playlist,
                        defaults={"state": "found", "updated_on": timezone.now()}
                    )

                    if was_created:
                        created += 1
                    else:
                        updated += 1

                    # Mise à jour périodique du statut
                    task_status.extra_info = f"{created} nouvelles apparitions, {updated} mises à jour"
                    task_status.extra_json.update({
                        "created": created,
                        "updated": updated,
                        "current": current_track_index,
                        "total": total_tracks
                    })
                    task_status.save(update_fields=["extra_info", "extra_json"])

        except Exception as e:
            task_status.status = "error"
            task_status.extra_info = str(e)
            task_status.extra_json.update({"current": current_track_index, "total": total_tracks})
            task_status.save(update_fields=["status", "extra_info", "extra_json"])
            raise
        finally:
            if task_status.status != "error":
                task_status.status = "done"
                task_status.extra_info = f"{created} nouvelles apparitions, {updated} mises à jour"
                task_status.extra_json.update({"created": created, "updated": updated, "current": total_tracks, "total": total_tracks})
                task_status.save(update_fields=["status", "extra_info", "extra_json"])

        self.stdout.write(self.style.SUCCESS(
            f"Terminé. Nouvelles apparitions: {created}, mises à jour: {updated}"
        ))
