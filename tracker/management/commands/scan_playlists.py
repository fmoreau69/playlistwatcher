import time
from django.core.management.base import BaseCommand
from tracker.models import Track, Playlist, Appearance, TaskStatus, SpotifyToken
from tracker.spotify import client, search_playlists_for_track
from spotipy.exceptions import SpotifyException

class Command(BaseCommand):
    help = "Scanne les playlists Spotify contenant chaque morceau et met à jour la base."

    def handle(self, *args, **opts):
        # Récupération du token global
        token_obj = SpotifyToken.objects.first()
        if not token_obj:
            self.stdout.write(self.style.ERROR("Aucun token Spotify trouvé dans la base !"))
            return

        sp = client()

        # Récupérer ou créer le TaskStatus
        task_status, _ = TaskStatus.objects.get_or_create(name="scan_playlists")
        task_status.status = "running"
        task_status.extra_info = "0"  # initialisation du compteur
        task_status.save(update_fields=["status", "extra_info"])

        tracks = Track.objects.all()
        created, updated = 0, 0

        try:
            for t in tracks:
                self.stdout.write(self.style.MIGRATE_HEADING(f"→ {t.name} ({t.spotify_id})"))

                while True:  # boucle pour retenter si rate limit
                    try:
                        results = search_playlists_for_track(sp, t.spotify_id, t.name, artist_hint="Donkey Shots")
                        break  # succès → on sort de la boucle
                    except SpotifyException as e:
                        if e.http_status == 429:  # Rate limit
                            retry_after = int(e.headers.get("Retry-After", "5"))
                            self.stdout.write(self.style.WARNING(
                                f"Rate limit atteint. Attente de {retry_after} secondes..."
                            ))
                            time.sleep(retry_after + 1)  # attente +1 sec de marge
                        else:
                            raise  # autre erreur → on arrête

                for pl in results:
                    playlist, _ = Playlist.objects.update_or_create(
                        spotify_id=pl["id"],
                        defaults=dict(
                            name=pl["name"],
                            url=pl["url"],
                            owner_name=pl["owner_name"],
                            owner_url=pl["owner_url"],
                            followers=pl["followers"],
                            description=pl["description"]
                        )
                    )
                    app, was_created = Appearance.objects.get_or_create(track=t, playlist=playlist)
                    created += int(was_created)
                    updated += int(not was_created)

                    # Mettre à jour TaskStatus.extra_info dès qu'une nouvelle apparition est créée
                    if was_created:
                        task_status.extra_info = str(created)
                        task_status.save(update_fields=["extra_info"])

        except Exception as e:
            task_status.status = "error"
            task_status.extra_info = str(e)
            task_status.save(update_fields=["status", "extra_info"])
            raise
        finally:
            if task_status.status != "error":  # éviter d’écraser si une erreur est déjà définie
                task_status.status = "done"
                task_status.extra_info = str(created)
                task_status.save(update_fields=["status", "extra_info"])

        self.stdout.write(self.style.SUCCESS(
            f"Terminé. Nouvelles apparitions: {created}, mises à jour: {updated}"
        ))
