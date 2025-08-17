from django.core.management.base import BaseCommand
from tracker.models import Track, Playlist, Appearance
from tracker.spotify import client, search_playlists_for_track

class Command(BaseCommand):
    help = "Scanne les playlists Spotify contenant chaque morceau et met à jour la base."

    def handle(self, *args, **opts):
        sp = client()
        tracks = Track.objects.all()
        created, updated = 0, 0
        for t in tracks:
            self.stdout.write(self.style.MIGRATE_HEADING(f"→ {t.name} ({t.spotify_id})"))
            for pl in search_playlists_for_track(sp, t.spotify_id, t.name, artist_hint="Donkey Shots"):
                playlist, _ = Playlist.objects.update_or_create(
                    spotify_id=pl["id"],
                    defaults=dict(
                        name=pl["name"], url=pl["url"], owner_name=pl["owner_name"],
                        owner_url=pl["owner_url"], followers=pl["followers"], description=pl["description"]
                    )
                )
                app, was_created = Appearance.objects.get_or_create(track=t, playlist=playlist)
                created += int(was_created)
                updated += int(not was_created)
        self.stdout.write(self.style.SUCCESS(f"Terminé. Nouvelles apparitions: {created}, mises à jour: {updated}"))
