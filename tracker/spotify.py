import os, time, datetime, requests, json
from django.utils import timezone
from django.conf import settings
from dotenv import load_dotenv
from typing import Iterable, Dict
from cryptography.fernet import Fernet

import spotipy
from spotipy.oauth2 import SpotifyOAuth, SpotifyClientCredentials
from tracker.models import SpotifyToken, SpotifyCredentials, Playlist, PlaylistItemsCache

load_dotenv()


# Charger la clé de chiffrement depuis le fichier .env
FERNET_KEY = os.getenv("SPOTIFY_CREDENTIALS_KEY")
fernet = Fernet(FERNET_KEY) if FERNET_KEY else None

def get_spotify_credentials():
    """
    Retourne les credentials Spotify (client_id, client_secret, redirect_uri, scope)
    en déchiffrant si nécessaire.
    """
    try:
        creds = SpotifyCredentials.objects.get(pk=1)
        client_id = creds.decrypted_client_id if fernet else creds.client_id
        client_secret = creds.decrypted_client_secret if fernet else creds.client_secret
        redirect_uri = creds.redirect_uri or os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8000/spotify/callback"
        )
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

def get_client() -> spotipy.Spotify | None:
    """
    Retourne un client Spotipy si un token ou des credentials valides existent.
    - Si un token utilisateur existe : on l'utilise et on le refresh si expiré
    - Sinon fallback sur credentials en base ou dans les variables d'environnement
    - Retourne None si rien de valide
    """
    token_obj = SpotifyToken.objects.first()
    now = timezone.now()

    if token_obj:
        if token_obj.expires_at <= now:
            # Token expiré → refresh
            creds = SpotifyCredentials.objects.first()
            client_id = creds.decrypted_client_id if creds and fernet else (creds.client_id if creds else os.getenv("SPOTIFY_CLIENT_ID"))
            client_secret = creds.decrypted_client_secret if creds and fernet else (creds.client_secret if creds else os.getenv("SPOTIFY_CLIENT_SECRET"))

            try:
                url = "https://accounts.spotify.com/api/token"
                data = {
                    "grant_type": "refresh_token",
                    "refresh_token": token_obj.refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
                resp = requests.post(url, data=data, timeout=10)
                resp.raise_for_status()
                payload = resp.json()

                token_obj.access_token = payload["access_token"]
                expires_in = payload.get("expires_in", 3600)
                token_obj.expires_at = now + datetime.timedelta(seconds=expires_in)
                token_obj.save()
            except Exception:
                # Refresh échoué → suppression du token pour forcer nouvel OAuth
                token_obj.delete()
                return None

        return spotipy.Spotify(auth=token_obj.access_token, requests_timeout=20, retries=3)

    # Fallback avec credentials en base
    creds = SpotifyCredentials.objects.first()
    if creds:
        client_id = creds.decrypted_client_id if fernet else creds.client_id
        client_secret = creds.decrypted_client_secret if fernet else creds.client_secret
        auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        return spotipy.Spotify(client_credentials_manager=auth, requests_timeout=20, retries=3)

    # Fallback avec env
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        return None

    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(client_credentials_manager=auth, requests_timeout=20, retries=3)

def safe_spotify_call(func, *args, **kwargs):
    """
    Exécute un appel Spotipy en gérant les rate limits (429).
    - func : fonction Spotipy à appeler
    - args, kwargs : arguments de la fonction
    """
    while True:
        try:
            return func(*args, **kwargs)
        except spotipy.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", "5"))
                print(f"⚠️ Rate limit atteint. Attente de {retry_after} secondes...")
                time.sleep(retry_after + 1)
            else:
                raise

def _get_playlist_snapshot_id(sp: spotipy.Spotify, playlist_id: str) -> str | None:
    try:
        data = safe_spotify_call(sp.playlist, playlist_id, fields="id,snapshot_id")
    except Exception:
        return None
    return data.get("snapshot_id") if data else None


def _fetch_playlist_track_ids(sp: spotipy.Spotify, playlist_id: str) -> set[str]:
    """
    Récupère tous les track IDs d'une playlist via l'API Spotify.
    """
    track_ids: set[str] = set()
    offset = 0
    limit = 100
    while True:
        items = safe_spotify_call(
            sp.playlist_items,
            playlist_id,
            fields="items.track.id,next",
            offset=offset,
            limit=limit,
            additional_types=["track"],
        )
        if not items:
            break
        for it in (items.get("items") or []):
            t = (it or {}).get("track") or {}
            tid = t.get("id")
            if tid:
                track_ids.add(tid)
        if items.get("next"):
            offset += limit
        else:
            break
    return track_ids


def playlist_contains_track(sp: spotipy.Spotify, playlist_id: str, track_id: str) -> bool:
    """
    Version optimisée avec cache basé sur snapshot_id.
    - Essaie d'utiliser un cache d'items si snapshot inchangé
    - Sinon, reconstruit le cache puis vérifie
    """
    playlist_obj: Playlist | None = Playlist.objects.filter(spotify_id=playlist_id).first()

    # Si on a déjà un snapshot en base et un cache correspondant, vérifie immédiatement
    if playlist_obj and playlist_obj.snapshot_id:
        cache = PlaylistItemsCache.objects.filter(
            playlist=playlist_obj, snapshot_id=playlist_obj.snapshot_id
        ).first()
        if cache and cache.track_ids:
            return track_id in set(cache.track_ids)

    # Récupère le snapshot actuel (1 seul appel)
    current_snapshot = _get_playlist_snapshot_id(sp, playlist_id)

    # Si playlist existe, compare et tente d'utiliser le cache
    cache: PlaylistItemsCache | None = None
    if playlist_obj and current_snapshot:
        if playlist_obj.snapshot_id == current_snapshot:
            cache = PlaylistItemsCache.objects.filter(
                playlist=playlist_obj, snapshot_id=current_snapshot
            ).first()
            if cache and cache.track_ids:
                return track_id in set(cache.track_ids)

    # Pas de cache exploitable → fetch complet et (si possible) persister
    track_ids = _fetch_playlist_track_ids(sp, playlist_id)

    # Persistance du cache si on a un objet Playlist
    if playlist_obj and current_snapshot:
        # met à jour snapshot si changé
        if playlist_obj.snapshot_id != current_snapshot:
            playlist_obj.snapshot_id = current_snapshot
            playlist_obj.save(update_fields=["snapshot_id"])
        # enregistre le cache pour ce snapshot
        PlaylistItemsCache.objects.update_or_create(
            playlist=playlist_obj,
            snapshot_id=current_snapshot,
            defaults={"track_ids": list(track_ids)},
        )

    return track_id in track_ids

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
        try:
            results = safe_spotify_call(sp.search, q=q, type="playlist", limit=50)
        except Exception as e:
            print(f"⚠️ Recherche échouée pour '{q}': {e}")
            continue
        for pl in results.get("playlists", {}).get("items", []):
            pl.get("id")
            pid = pl["id"]
            if pid in seen:
                continue
            seen.add(pid)
            # Vérif contenu
            if safe_spotify_call(playlist_contains_track, sp, pid, track_id):
                try:
                    full = safe_spotify_call(
                        sp.playlist,
                        pid,
                        fields="id,name,snapshot_id,external_urls.spotify,owner(display_name,external_urls.spotify),followers.total,description",
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
                    "snapshot_id": full.get("snapshot_id"),
                }
        time.sleep(0.4)  # douceur sur l’API


def search_discover_playlists(sp: spotipy.Spotify, max_per_query: int = 200, max_total: int = 50) -> Iterable[Dict]:
    """
    Recherche générique de playlists Spotify pour peupler la base.
    - max_per_query : limite par mot-clé
    - max_total : limite globale (toutes requêtes confondues)
    """
    keywords = [
        "music", "playlist", "hits", "mix", "best", "favorites", "indie", "rock", "pop", "electro"
    ]
    seen = set()
    total_found = 0

    for q in keywords:
        offset = 0
        while offset < max_per_query and total_found < max_total:
            try:
                results = safe_spotify_call(sp.search, q=q, type="playlist", limit=50, offset=offset)
            except Exception as e:
                print(f"⚠️ Recherche échouée pour '{q}': {e}")
                break

            items = results.get("playlists", {}).get("items", [])
            if not items:
                break

            for pl in items:
                if not pl or not pl.get("id"):
                    continue
                pid = pl["id"]
                if pid in seen:
                    continue
                seen.add(pid)

                # Utilise directement le document 'search' (évite 1 appel par playlist)
                owner = (pl.get("owner") or {})
                external_urls = (pl.get("external_urls") or {})

                total_found += 1
                yield {
                    "id": pl.get("id"),
                    "name": pl.get("name"),
                    "url": external_urls.get("spotify", ""),
                    "owner_name": owner.get("display_name") or "",
                    "owner_url": (owner.get("external_urls") or {}).get("spotify", ""),
                    "followers": None,  # non dispo dans la réponse search
                    "description": pl.get("description") or "",
                    "snapshot_id": pl.get("snapshot_id"),
                }

                if total_found >= max_total:
                    print(f"⏹️ Limite globale atteinte : {max_total} playlists.")
                    return

            offset += 50
            time.sleep(0.4)  # limiter les appels

    print(f"✅ Découverte terminée : {total_found} playlists uniques trouvées.")

