from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Value
from django.db.models.functions import Concat
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table
from radioscraper.utils import refresh_radios, refresh_radios_progress
from django.db import transaction, OperationalError
from .models import Radio
from .utils import fetch_all_stations

def radio_search(request):
    radios = Radio.objects.all()

    # Extraire tous les pays et états distincts
    countries = Radio.objects.values_list('country', flat=True).distinct().order_by('country')
    states = Radio.objects.values_list('state', flat=True).distinct().order_by('state')

    # Pour les tags, séparer les virgules et obtenir la liste unique
    all_tags = []
    for t in Radio.objects.values_list('tags', flat=True):
        if t:
            all_tags.extend([tag.strip() for tag in t.split(',')])
    tags = sorted(list(set(all_tags)))

    # Récupérer les valeurs sélectionnées
    selected_countries = request.GET.getlist('country')
    selected_states = request.GET.getlist('state')
    selected_tags = request.GET.getlist('tag')

    # Filtrage
    if selected_countries:
        radios = radios.filter(country__in=selected_countries)
    if selected_states:
        radios = radios.filter(state__in=selected_states)
    if selected_tags:
        # Filtrer les radios contenant au moins un tag sélectionné
        query = None
        for tag in selected_tags:
            q = radios.filter(tags__icontains=tag)
            query = q if query is None else query | q
        radios = query.distinct()

    return render(request, "radioscraper/radio_search.html", {
        "radios": radios,
        "countries": list(countries),
        "states": list(states),
        "tags": tags,
        "selected_countries": selected_countries,
        "selected_states": selected_states,
        "selected_tags": selected_tags,
    })

def radio_refresh(request):
    """
    Page principale d'actualisation : affiche le bouton et la barre de progression.
    """
    radios_count = Radio.objects.count()

    if request.method == "POST" and request.is_ajax():
        # Si la requête est AJAX, on traite par lot
        offset = int(request.POST.get("offset", 0))
        limit = int(request.POST.get("limit", 50))
        progress_data = refresh_radios_progress(offset=offset, limit=limit)
        return JsonResponse(progress_data)

    return render(
        request,
        "radioscraper/radio_refresh.html",
        {"radios_count": radios_count}
    )

def safe_update_or_create(defaults, stationuuid, max_retries=5):
    for attempt in range(max_retries):
        try:
            return Radio.objects.update_or_create(
                stationuuid=stationuuid,
                defaults=defaults
            )
        except OperationalError as e:
            if 'database is locked' in str(e):
                time.sleep(0.5)
            else:
                raise
    raise OperationalError(f"Impossible d'écrire la station {stationuuid} après {max_retries} tentatives.")

@csrf_exempt
def radio_refresh_ajax(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        offset = int(request.GET.get("offset", 0))
        limit = int(request.GET.get("limit", BATCH_SIZE))
    except ValueError:
        offset = 0
        limit = BATCH_SIZE

    stations = fetch_all_stations()
    total = len(stations)
    batch_stations = stations[offset:offset+limit]

    created, updated = 0, 0
    messages = []

    with transaction.atomic():
        for i, s in enumerate(batch_stations, start=offset+1):
            defaults = {
                "name": s.get("name", ""),
                "country": s.get("country", ""),
                "state": s.get("state", ""),
                "tags": s.get("tags", ""),
                "homepage": s.get("homepage", ""),
                "emails": s.get("email", ""),
                "favicon": s.get("favicon", ""),
                "language": s.get("language", ""),
                "stream_url": s.get("url", ""),
            }

            radio, was_created = safe_update_or_create(defaults=defaults, stationuuid=s["stationuuid"])

            if was_created:
                created += 1
                messages.append(f"[{i}/{total}] Créée : {radio.name}")
            else:
                updated += 1
                messages.append(f"[{i}/{total}] Mise à jour : {radio.name}")

    remaining = max(0, total - (offset + len(batch_stations)))

    return JsonResponse({
        "total": total,
        "processed": offset + len(batch_stations),
        "remaining": remaining,
        "messages": messages,
        "created": created,
        "updated": updated
    })

def export_xlsx(request):
    radios = Radio.objects.all().values()
    df = pd.DataFrame(radios)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Radios")
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=radios.xlsx"
    return response

def export_pdf(request):
    radios = Radio.objects.all().values_list("name", "country", "state", "tags", "homepage", "emails")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    table = Table([["Nom", "Pays", "Région", "Style", "Site web", "Emails"]] + list(radios))
    doc.build([table])
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=radios.pdf"
    return response
