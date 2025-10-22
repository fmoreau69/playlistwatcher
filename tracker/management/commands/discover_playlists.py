import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from spotipy.exceptions import SpotifyException

from tracker.models import Playlist, TaskStatus, SpotifyToken
from tracker.spotify import get_client, search_discover_playlists


class Command(BaseCommand):
    help = "Découvre de nouvelles playlists Spotify (sans vérifier les morceaux encore)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Nombre maximum de playlists à découvrir (toutes requêtes confondues).",
        )
        parser.add_argument(
            "--per-query",
            type=int,
            default=200,
            help="Nombre maximum de résultats par mot-clé (offset).",
        )

    def handle(self, *args, **opts):
        token_obj = SpotifyToken.objects.first()
        if not token_obj:
            self.stdout.write(self.style.ERROR("Aucun token Spotify trouvé dans la base !"))
            return

        sp = get_client()
        max_total = opts["limit"]
        max_per_query = opts["per_query"]

        self.stdout.write(f"🔍 Découverte de playlists (max_total={max_total}, max_per_query={max_per_query})")

        try:
            found = 0
            for pl in search_discover_playlists(sp, max_per_query=max_per_query, max_total=max_total):
                obj, created = Playlist.objects.update_or_create(
                    spotify_id=pl["id"],
                    defaults={
                        "name": pl["name"],
                        "url": pl["url"],
                        "owner_name": pl["owner_name"],
                        "owner_url": pl["owner_url"],
                        "followers": pl["followers"],
                        "description": pl["description"],
                        "snapshot_id": pl.get("snapshot_id"),
                        "last_discovered": timezone.now(),
                    },
                )

                if created and not obj.discovered_on:
                    obj.discovered_on = obj.last_discovered
                    obj.save(update_fields=["discovered_on"])

                found += 1
                followers = obj.followers if obj.followers is not None else "?"
                self.stdout.write(self.style.SUCCESS(f"🎵 {obj.name} ({followers} abonnés)"))
        except SpotifyException as e:
            self.stdout.write(self.style.ERROR(f"⚠️ Erreur Spotify: {e}"))

        self.stdout.write(self.style.SUCCESS(f"✅ Découverte terminée : {found} playlists ajoutées/mises à jour."))


        # # Initialisation du statut de tâche
        # task_status, _ = TaskStatus.objects.get_or_create(name="discover_playlists")
        # task_status.status = "running"
        # task_status.extra_info = "0 nouvelles, 0 maj, 0 explorées"
        # task_status.extra_json = {"created": 0, "updated": 0, "explored": 0}
        # task_status.save(update_fields=["status", "extra_info", "extra_json"])
        #
        # created, updated, explored = 0, 0, 0
        #
        # try:
        #     # Récupération des playlists candidates
        #     while True:  # gère les rate limits
        #         try:
        #             results = search_discover_playlists(sp, max_per_query=200)
        #             break
        #         except SpotifyException as e:
        #             if e.http_status == 429:
        #                 retry_after = int(e.headers.get("Retry-After", "5"))
        #                 self.stdout.write(self.style.WARNING(
        #                     f"Rate limit atteint. Attente de {retry_after} secondes..."
        #                 ))
        #                 time.sleep(retry_after + 1)
        #             else:
        #                 raise
        #
        #     results = list(search_discover_playlists(sp, max_per_query=200))
        #     print("Nb playlists trouvées:", len(results))
        #     if results:
        #         print("Exemple:", results[0])
        #
        #     # Traitement des playlists
        #     for pl in results:
        #         explored += 1
        #         playlist, was_created = Playlist.objects.update_or_create(
        #             spotify_id=pl["id"],
        #             defaults=dict(
        #                 name=pl["name"],
        #                 url=pl["url"],
        #                 owner_name=pl["owner_name"],
        #                 owner_url=pl["owner_url"],
        #                 followers=pl["followers"],
        #                 description=pl["description"],
        #                 last_scanned=timezone.now()
        #             )
        #         )
        #
        #         if was_created:
        #             created += 1
        #         else:
        #             updated += 1
        #
        #         # Mise à jour périodique
        #         if explored % 10 == 0 or was_created:
        #             task_status.extra_info = f"{created} nouvelles, {updated} maj, {explored} explorées"
        #             task_status.extra_json.update({
        #                 "created": created,
        #                 "updated": updated,
        #                 "explored": explored
        #             })
        #             task_status.save(update_fields=["extra_info", "extra_json"])
        #
        # except Exception as e:
        #     task_status.status = "error"
        #     task_status.extra_info = str(e)
        #     task_status.extra_json.update({"explored": explored})
        #     task_status.save(update_fields=["status", "extra_info", "extra_json"])
        #     raise
        # finally:
        #     if task_status.status != "error":
        #         task_status.status = "done"
        #         task_status.extra_info = f"{created} nouvelles, {updated} maj, {explored} explorées"
        #         task_status.extra_json.update({"created": created, "updated": updated, "explored": explored})
        #         task_status.save(update_fields=["status", "extra_info", "extra_json"])
        #
        # self.stdout.write(self.style.SUCCESS(
        #     f"Découverte terminée : {created} nouvelles, {updated} mises à jour, {explored} explorées"
        # ))
