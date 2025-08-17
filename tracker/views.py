from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.contrib import messages
from .models import Appearance, Playlist, Track
from .forms import TrackForm, ExcelUploadForm
import pandas as pd
from openpyxl import load_workbook, Workbook
from datetime import datetime, date


def dashboard(request):
    qs = Appearance.objects.select_related("track","playlist").order_by("-updated_on")
    return render(request, "tracker/dashboard.html", {"rows": qs})

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

    imported, skipped = 0, 0

    for row in data:
        # Track
        track, _ = Track.objects.get_or_create(
            name=row.get("Titre") or "Inconnu",
            defaults={"spotify_id": f"temp_{(row.get('Titre') or 'unk')}"[:64]}
        )

        # Playlist
        playlist, _ = Playlist.objects.get_or_create(
            name=row.get("Playlist") or "Sans nom",
            defaults={
                "spotify_id": f"temp_{(row.get('Playlist') or 'unk')}"[:64],
                "followers": clean_int(row.get("Abonnés")),
                "description": row.get("Description") or "",
                "url": row.get("PlaylistURL") or "",
                "owner_name": row.get("Curateur") or "",
                "owner_url": row.get("CurateurURL") or "",
            }
        )

        # Dates
        added_on = clean_date(row.get("Date d'ajout"))
        updated_on = clean_date(row.get("Mise à jour")) or datetime.today().date()

        # Appearance (éviter doublons)
        if not Appearance.objects.filter(track=track, playlist=playlist).exists():
            Appearance.objects.create(
                track=track,
                playlist=playlist,
                contact=row.get("Contact") or "",
                state=row.get("Etat") or "",
                added_on=added_on,
                updated_on=updated_on
            )
            imported += 1
        else:
            skipped += 1

    # Nettoyer la session
    del request.session["import_preview"]

    messages.success(request, f"{imported} apparitions importées, {skipped} ignorées (doublons).")
    return redirect("dashboard")
