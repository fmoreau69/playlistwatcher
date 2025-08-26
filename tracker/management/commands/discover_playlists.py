import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from spotipy.exceptions import SpotifyException

from tracker.models import Playlist, TaskStatus, SpotifyToken
from tracker.spotify import client, search_discover_playlists


class Command(BaseCommand):
    help = "Découvre de nouvelles playlists Spotify (sans vérifier les morceaux encore)."

    def handle(self, *args, **opts):
        token_obj = SpotifyToken.objects.first()
        if not token_obj:
            self.stdout.write(self.style.ERROR("Aucun token Spotify trouvé dans la base !"))
            return

        sp = client()

        # Initialisation du statut de tâche
        task_status, _ = TaskStatus.objects.get_or_create(name="discover_playlists")
        task_status.status = "running"
        task_status.extra_info = "0 nouvelles, 0 maj, 0 explorées"
        task_status.extra_json = {"created": 0, "updated": 0, "explored": 0}
        task_status.save(update_fields=["status", "extra_info", "extra_json"])

        created, updated, explored = 0, 0, 0

        try:
            # Récupération des playlists candidates
            while True:  # gère les rate limits
                try:
                    results = search_discover_playlists(sp, max_per_query=200)
                    break
                except SpotifyException as e:
                    if e.http_status == 429:
                        retry_after = int(e.headers.get("Retry-After", "5"))
                        self.stdout.write(self.style.WARNING(
                            f"Rate limit atteint. Attente de {retry_after} secondes..."
                        ))
                        time.sleep(retry_after + 1)
                    else:
                        raise

            # Traitement des playlists
            for pl in results:
                explored += 1
                playlist, was_created = Playlist.objects.update_or_create(
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

                if was_created:
                    created += 1
                else:
                    updated += 1

                # Mise à jour périodique
                if explored % 10 == 0 or was_created:
                    task_status.extra_info = f"{created} nouvelles, {updated} maj, {explored} explorées"
                    task_status.extra_json.update({
                        "created": created,
                        "updated": updated,
                        "explored": explored
                    })
                    task_status.save(update_fields=["extra_info", "extra_json"])

        except Exception as e:
            task_status.status = "error"
            task_status.extra_info = str(e)
            task_status.extra_json.update({"explored": explored})
            task_status.save(update_fields=["status", "extra_info", "extra_json"])
            raise
        finally:
            if task_status.status != "error":
                task_status.status = "done"
                task_status.extra_info = f"{created} nouvelles, {updated} maj, {explored} explorées"
                task_status.extra_json.update({"created": created, "updated": updated, "explored": explored})
                task_status.save(update_fields=["status", "extra_info", "extra_json"])

        self.stdout.write(self.style.SUCCESS(
            f"Découverte terminée : {created} nouvelles, {updated} mises à jour, {explored} explorées"
        ))
