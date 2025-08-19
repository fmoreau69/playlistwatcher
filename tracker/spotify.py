import os, time, datetime, requests, json
from django.utils import timezone
from django.conf import settings
from dotenv import load_dotenv
import spotipy
from tracker.models import SpotifyToken, SpotifyCredentials
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from typing import Iterable, Dict

load_dotenv()

def get_spotify_credentials():
    try:
        creds = SpotifyCredentials.objects.get(pk=1)
        client_id = creds.client_id or os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = creds.client_secret or os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = creds.redirect_uri or os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/spotify/callback")
        scope = os.getenv("SPOTIFY_SCOPE", "playlist-read-private playlist-read-collaborative")
    except SpotifyCredentials.DoesNotExist:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/spotify/callback")
        scope = os.getenv("SPOTIFY_SCOPE", "playlist-read-private playlist-read-collaborative")

    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "scope": scope,
    }

def client() -> spotipy.Spotify:
    """
    Retourne un client Spotify prêt à l'emploi.
    Priorité :
      1. Token OAuth stocké en base (SpotifyToken)
      2. Credentials en base (SpotifyCredentials)
      3. Variables d'environnement
    """
    token_obj = SpotifyToken.objects.first()
    if token_obj:
        now = timezone.now()
        if token_obj.expires_at <= now:
            # Token expiré → refresh
            url = "https://accounts.spotify.com/api/token"
            data = {
                "grant_type": "refresh_token",
                "refresh_token": token_obj.refresh_token,
                "client_id": settings.SPOTIFY_CLIENT_ID or os.getenv("SPOTIFY_CLIENT_ID"),
                "client_secret": settings.SPOTIFY_CLIENT_SECRET or os.getenv("SPOTIFY_CLIENT_SECRET"),
            }
            resp = requests.post(url, data=data)
            resp.raise_for_status()
            payload = resp.json()

            token_obj.access_token = payload["access_token"]
            expires_in = payload.get("expires_in", 3600)
            token_obj.expires_at = now + datetime.timedelta(seconds=expires_in)
            token_obj.save()

        return spotipy.Spotify(auth=token_obj.access_token, requests_timeout=20, retries=3)

    # Fallback avec credentials en base
    creds = SpotifyCredentials.objects.first()
    if creds:
        auth = SpotifyClientCredentials(
            client_id=creds.client_id,
            client_secret=creds.client_secret,
        )
        return spotipy.Spotify(client_credentials_manager=auth, requests_timeout=20, retries=3)

    # Fallback avec env
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
        for pl in results.get("playlists", {}).get("items", []):
            if not pl or not pl.get("id"):  # ✅ sécurité anti-None
                continue
            pid = pl["id"]
            if pid in seen:
                continue
            seen.add(pid)
            # Vérif contenu
            if playlist_contains_track(sp, pid, track_id):
                try:
                    full = sp.playlist(
                        pid,
                        fields="id,name,external_urls.spotify,owner(display_name,external_urls.spotify),followers.total,description",
                    )
                except Exception as e:
                    print(f"⚠️ Impossible de récupérer playlist {pid}: {e}")
                    continue
                yield {
                    "id": full.get("id"),
                    "name": full.get("name"),
                    "url": (full.get("external_urls") or {}).get("spotify", ""),
                    "owner_name": (full.get("owner") or {}).get("display_name") or "",
                    "owner_url": ((full.get("owner") or {}).get("external_urls") or {}).get("spotify", ""),
                    "followers": (full.get("followers") or {}).get("total", 0),
                    "description": full.get("description") or "",
                }
        time.sleep(0.4)  # douceur sur l’API
