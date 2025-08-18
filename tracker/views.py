import pandas as pd
import threading
import json, os
from django.core.management import call_command
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from openpyxl import load_workbook, Workbook
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from spotipy.oauth2 import SpotifyOAuth
from .models import Appearance, Playlist, Track, TaskStatus, SpotifyCredentials, SpotifyToken
from .forms import TrackForm, ExcelUploadForm, SpotifyCredentialsForm


def dashboard(request):
    qs = Appearance.objects.select_related("track","playlist").order_by("-updated_on")
    scan_status = TaskStatus.objects.filter(name="scan_playlists").first()
    return render(request, "tracker/dashboard.html", {
        "rows": qs,
        "scan_status": scan_status
    })

def add_track(request):
    if request.method == "POST":
        form = TrackForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("dashboard"))
    else:
        form = TrackForm()
    return render(request, "tracker/track_form.html", {"form": form})

def export_excel(request):
    wb = Workbook()
    ws = wb.active
    ws.title = "Apparitions"

    headers = ["Titre", "Playlist", "Curateur", "Contact", "Abonnés", "Date d'ajout", "Etat", "Description", "Mise à jour"]
    ws.append(headers)

    for app in Appearance.objects.select_related("track", "playlist"):
        row = [
            app.track.name,
            app.playlist.name,
            app.playlist.owner_name,
            app.contact,
            app.playlist.followers,
            app.added_on,
            app.state,
            app.playlist.description,
            app.updated_on,
        ]
        ws.append(row)
        r = ws.max_row

        if app.playlist.url:
            ws.cell(row=r, column=2).hyperlink = app.playlist.url
        if app.playlist.owner_url:
            ws.cell(row=r, column=3).hyperlink = app.playlist.owner_url

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="export.xlsx"'
    wb.save(response)
    return response

def export_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'attachment; filename="export.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    y = height - 50
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Export des apparitions")
    y -= 30

    p.setFont("Helvetica", 10)
    for app in Appearance.objects.select_related("track", "playlist")[:100]:  # limiter pour test
        text = f"{app.track.name} - {app.playlist.name} ({app.playlist.followers or 'N/A'} abonnés)"
        p.drawString(50, y, text)
        y -= 15
        if y < 50:  # nouvelle page
            p.showPage()
            p.setFont("Helvetica", 10)
            y = height - 50

    p.showPage()
    p.save()
    return response

# Mapping colonnes Excel → champs du modèle Appearance
COLUMN_MAPPING = {
    'Titre': 'title',
    'Playlist': 'playlist',
    'Curateur': 'curator',
    'Contact': 'contact',
    'Abonnés': 'followers',
    'Date d\'ajout': 'added_date',
    'Etat': 'status',
    'Description': 'description',
    'Mise à jour': 'updated_date'
}

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

def clean_preview(value):
    """Préparer les valeurs pour affichage dans la preview"""
    if pd.isna(value) or value == "":
        return ""
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)

def import_excel(request):
    if request.method == "POST":
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]

            # Charger workbook avec openpyxl
            wb = load_workbook(file)
            ws = wb.active

            # Convertir en DataFrame pandas
            data = list(ws.values)
            df = pd.DataFrame(data[1:], columns=data[0])

            # Colonnes obligatoires
            required_columns = [
                "Titre", "Playlist", "Curateur", "Contact", "Abonnés",
                "Date d'ajout", "Etat", "Description", "Mise à jour"
            ]
            for col in required_columns:
                if col not in df.columns:
                    messages.error(request, f"Colonne manquante : {col}")
                    return redirect("import_excel")

            # Construire la liste pour preview
            preview_data = []

            for row_index, row in df.iterrows():
                # Hyperliens
                excel_row = row_index + 2  # 1 = header, +1 pour passer en base 1 Excel
                playlist_cell = ws.cell(row=excel_row, column=list(df.columns).index("Playlist") + 1)
                curateur_cell = ws.cell(row=excel_row, column=list(df.columns).index("Curateur") + 1)
                playlist_url = playlist_cell.hyperlink.target if playlist_cell.hyperlink else ""
                curateur_url = curateur_cell.hyperlink.target if curateur_cell.hyperlink else ""

                preview_data.append({
                    "Titre": row.get("Titre") or "",
                    "Playlist": row.get("Playlist") or "",
                    "PlaylistURL": playlist_url,
                    "Curateur": row.get("Curateur") or "",
                    "CurateurURL": curateur_url,
                    "Contact": row.get("Contact") or "",
                    "Abonnés": (str(row.get("Abonnés")).replace("\u202f", "").replace(" ", "").strip() if row.get("Abonnés") not in [None, ""] else ""),
                    "Date d'ajout": clean_preview(row.get("Date d'ajout")),
                    "Etat": row.get("Etat") or "",
                    "Description": row.get("Description") or "",
                    "Mise à jour": clean_preview(row.get("Mise à jour")),
                })

            # Stocker dans la session
            request.session["import_preview"] = preview_data

            return render(request, "tracker/import_preview.html", {"preview_data": preview_data, "total": len(preview_data)})

    else:
        form = ExcelUploadForm()

    return render(request, "tracker/import_excel.html", {"form": form})

def confirm_import(request):
    data = request.session.get("import_preview")
    if not data:
        messages.error(request, "Aucune donnée à importer.")
        return redirect("import_excel")

    mode = request.POST.get("mode", "complete")  # par défaut compléter
    imported, updated = 0, 0

    for row in data:
        track, _ = Track.objects.get_or_create(
            name=row.get("Titre") or "Inconnu",
            defaults={"spotify_id": f"temp_{(row.get('Titre') or 'unk')}"[:64]}
        )

        playlist, _ = Playlist.objects.get_or_create(
            name=row.get("Playlist") or "Sans nom",
            defaults={
                "spotify_id": f"temp_{(row.get('Playlist') or 'unk')}"[:64],
                "followers": int(row.get("Abonnés")) if row.get("Abonnés") not in ("", None) else None,
                "description": row.get("Description") or "",
                "url": row.get("PlaylistURL") or "",
                "owner_name": row.get("Curateur") or "",
                "owner_url": row.get("CurateurURL") or "",
            }
        )

        added_on = clean_date(row.get("Date d'ajout"))
        updated_on = clean_date(row.get("Mise à jour")) or datetime.today().date()

        appearance, created = Appearance.objects.get_or_create(
            track=track,
            playlist=playlist,
            defaults={
                "contact": row.get("Contact") or "",
                "state": row.get("Etat") or "",
                "added_on": added_on,
                "updated_on": updated_on,
            }
        )

        if created:
            imported += 1
        else:
            if mode == "overwrite":
                appearance.contact = row.get("Contact") or appearance.contact
                appearance.state = row.get("Etat") or appearance.state
                appearance.added_on = added_on or appearance.added_on
                appearance.updated_on = updated_on
                appearance.save()
                updated += 1
            elif mode == "complete":
                changed = False
                if not appearance.contact and row.get("Contact"):
                    appearance.contact = row.get("Contact")
                    changed = True
                if not appearance.state and row.get("Etat"):
                    appearance.state = row.get("Etat")
                    changed = True
                if not appearance.added_on and added_on:
                    appearance.added_on = added_on
                    changed = True
                if changed:
                    appearance.updated_on = updated_on
                    appearance.save()
                    updated += 1

    del request.session["import_preview"]

    messages.success(request, f"{imported} apparitions importées, {updated} mises à jour.")
    return redirect("dashboard")

def run_scan_playlists_async():
    status, _ = TaskStatus.objects.get_or_create(name="scan_playlists")
    status.status = "running"
    status.stop_requested = False
    status.save()

    try:
        # Exemple d'itération sur des playlists
        from tracker.models import Playlist
        playlists = Playlist.objects.all()
        for pl in playlists:
            status.refresh_from_db()
            if status.stop_requested:
                status.status = "stopped"
                status.save()
                return  # arrêt propre
            # ici on fait le scan normal pour la playlist pl
            call_command("scan_playlist", str(pl.id))  # si ton management command accepte un ID
        status.status = "done"
    except Exception:
        status.status = "error"
    finally:
        status.save()

def run_scan_playlists(request):
    threading.Thread(target=run_scan_playlists_async).start()
    messages.info(request, "Scan des playlists lancé en arrière-plan ⏳")
    return redirect("dashboard")

def stop_scan_playlists(request):
    status = TaskStatus.objects.filter(name="scan_playlists").first()
    if status and status.status == "running":
        status.stop_requested = True
        status.save()
        messages.info(request, "Demande d’arrêt du scan envoyée ⏹️")
    else:
        messages.warning(request, "Aucun scan en cours")
    return redirect("dashboard")

def scan_status(request):
    status = TaskStatus.objects.filter(name="scan_playlists").first()
    data = {
        "status": status.status if status else "idle",
    }
    return JsonResponse(data)


CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "https://localhost:8000/spotify/callback"
SCOPE = "playlist-read-private"

# @login_required
def spotify_login(request):
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@csrf_exempt
def spotify_callback(request):
    code = request.GET.get("code")
    error = request.GET.get("error")

    if error:
        return HttpResponseBadRequest(f"Erreur Spotify: {error}")
    if not code:
        return HttpResponseBadRequest("Code d'autorisation manquant.")

    sp_oauth = SpotifyOAuth(
        client_id=os.getenv("SPOTIFY_CLIENT_ID"),
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/callback"),
        scope="playlist-read-private playlist-read-collaborative"
    )

    token_info = sp_oauth.get_access_token(code, as_dict=True)
    if not token_info:
        return HttpResponseBadRequest("Impossible d'obtenir un token Spotify.")

    expires_at = timezone.now() + timezone.timedelta(seconds=token_info["expires_in"])

    # Sauvegarde en base
    SpotifyToken.objects.update_or_create(
        user=request.user,
        defaults={
            "access_token": token_info["access_token"],
            "refresh_token": token_info["refresh_token"],
            "expires_at": expires_at,
        }
    )

    return HttpResponse("Authentification Spotify réussie ✅")

def spotify_credentials(request):
    # Essayer de charger depuis la base
    try:
        creds = SpotifyCredentials.objects.get(pk=1)
    except SpotifyCredentials.DoesNotExist:
        creds = SpotifyCredentials()

    if request.method == "POST":
        if "upload_file" in request.FILES:
            # Importer depuis un fichier JSON
            f = request.FILES["upload_file"]
            data = json.load(f)
            creds.client_id = data.get("client_id", "")
            creds.client_secret = data.get("client_secret", "")
            creds.redirect_uri = data.get("redirect_uri", "http://localhost:8000/callback")
            creds.save()
            messages.success(request, "Identifiants importés depuis le fichier.")
            return redirect("spotify_credentials")
        else:
            # Sauvegarde via formulaire
            form = SpotifyCredentialsForm(request.POST, instance=creds)
            if form.is_valid():
                form.save()
                messages.success(request, "Identifiants Spotify enregistrés.")
                return redirect("spotify_credentials")
    else:
        form = SpotifyCredentialsForm(instance=creds)

    return render(request, "tracker/spotify_credentials.html", {"form": form})
