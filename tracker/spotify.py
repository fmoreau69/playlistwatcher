import os, time
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from typing import Iterable, Dict

load_dotenv()

def client():
    auth = SpotifyClientCredentials(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    )
    return spotipy.Spotify(client_credentials_manager=auth, requests_timeout=20, retries=3)

def playlist_contains_track(sp: spotipy.Spotify, playlist_id: str, track_id: str) -> bool:
    offset = 0
    while True:
        items = sp.playlist_items(playlist_id, fields="items.track.id,total,next", offset=offset, additional_types=["track"])
        for it in items["items"]:
            t = it.get("track") or {}
            if t and t.get("id") == track_id:
                return True
        if items.get("next"):
            offset += 100
        else:
            return False

def search_playlists_for_track(sp: spotipy.Spotify, track_id: str, track_name: str, artist_hint: str = "Donkey Shots") -> Iterable[Dict]:
    """
    ⚠️ Limitation Spotify : pas d’endpoint 'toutes les playlists contenant X'.
    Stratégie : on effectue plusieurs recherches de playlists par mots-clés,
    puis on vérifie le contenu de chacune.
    """
    queries = [
        f'"{track_name}" "{artist_hint}"',
        f'{track_name} {artist_hint}',
        f'"{artist_hint}"',
    ]
    seen = set()
    for q in queries:
        results = sp.search(q=q, type="playlist", limit=50)
        for pl in results["playlists"]["items"]:
            pid = pl["id"]
            if pid in seen:
                continue
            seen.add(pid)
            # Vérif contenu
            if playlist_contains_track(sp, pid, track_id):
                # enrichissement
                full = sp.playlist(pid, fields="id,name,external_urls.spotify,owner(display_name,external_urls.spotify),followers.total,description")
                yield {
                    "id": full["id"],
                    "name": full["name"],
                    "url": full["external_urls"]["spotify"],
                    "owner_name": (full.get("owner") or {}).get("display_name") or "",
                    "owner_url": ((full.get("owner") or {}).get("external_urls") or {}).get("spotify",""),
                    "followers": (full.get("followers") or {}).get("total", 0),
                    "description": full.get("description") or "",
                }
        time.sleep(0.4)  # douceur sur l’API
