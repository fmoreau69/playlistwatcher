from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from .models import Appearance, Track
from .forms import TrackForm
import pandas as pd
from django.utils.timezone import now

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
    rows = Appearance.objects.select_related("track","playlist")
    data = []
    for a in rows:
        data.append({
            "Titre": a.track.name,
            "Playlist": f'=HYPERLINK("{a.playlist.url}","{a.playlist.name}")',
            "Curateur": f'=HYPERLINK("{a.playlist.owner_url}","{a.playlist.owner_name}")' if a.playlist.owner_url else a.playlist.owner_name,
            "Contact": a.contact,
            "Abonnés": a.playlist.followers,
            "Date d\'ajout": a.added_on.strftime("%Y-%m-%d"),
            "Etat": a.state,
            "Description": a.playlist.description,
            "Mise à jour": a.updated_on.strftime("%Y-%m-%d"),
        })
    df = pd.DataFrame(data, columns=["Titre","Playlist","Curateur","Contact","Abonnés","Date d'ajout","Etat","Description","Mise à jour"])
    path = f"Playlists_Spotify_{now().date()}.xlsx"
    df.to_excel(path, index=False)
    with open(path, "rb") as f:
        resp = HttpResponse(f.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        resp["Content-Disposition"] = f'attachment; filename="{path}"'
        return resp
