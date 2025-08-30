import time
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.db import transaction, OperationalError
import pandas as pd
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table
from .models import Radio
from .utils import fetch_stations_by_country, BATCH_SIZE


def safe_update_or_create(defaults, stationuuid, max_retries=5):
    """
    Retry pour éviter les erreurs SQLite 'database is locked'.
    """
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


def radio_search(request):
    """
    Recherche des radios avec filtrage multi-sélection.
    Affiche uniquement les radios déjà en base.
    """
    radios = Radio.objects.all()
    selected_countries = request.GET.getlist('country')
    selected_states = request.GET.getlist('state')
    selected_tags = request.GET.getlist('tag')

    if selected_countries:
        radios = radios.filter(country__in=selected_countries)
    if selected_states:
        radios = radios.filter(state__in=selected_states)
    if selected_tags:
        query = None
        for tag in selected_tags:
            q = radios.filter(tags__icontains=tag)
            query = q if query is None else query | q
        radios = query.distinct()

    # Extraire pays, états et tags pour le multi-select
    countries = Radio.objects.values_list('country', flat=True).distinct().order_by('country')
    states = Radio.objects.values_list('state', flat=True).distinct().order_by('state')
    all_tags = []
    for t in Radio.objects.values_list('tags', flat=True):
        if t:
            all_tags.extend([tag.strip() for tag in t.split(',')])
    tags = sorted(list(set(all_tags)))

    return render(request, "radioscraper/radio_search.html", {
        "radios": radios,
        "countries": list(countries),
        "states": list(states),
        "tags": tags,
        "selected_countries": selected_countries,
        "selected_states": selected_states,
        "selected_tags": selected_tags,
        "radios_count": Radio.objects.count()
    })


def radio_refresh(request):
    """
    Page principale d'actualisation : bouton + barre de progression
    """
    radios_count = Radio.objects.count()
    return render(
        request,
        "radioscraper/radio_refresh.html",
        {"radios_count": radios_count}
    )


@csrf_exempt
def radio_refresh_ajax(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    selected_countries = request.POST.getlist("country") or [None]
    country_index = int(request.POST.get("country_index", 0))
    offset = int(request.POST.get("offset", 0))
    BATCH_SIZE = 50

    # Vérifier si tous les pays ont été traités
    if country_index >= len(selected_countries):
        return JsonResponse({"finished": True})

    country = selected_countries[country_index]

    # Récupération par batch
    stations = fetch_stations_by_country(country=country)
    total = len(stations)
    batch_stations = stations[offset:offset+BATCH_SIZE]

    created, updated = 0, 0
    messages_list = []

    # Écriture batch par batch pour éviter les verrous
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
        action = "Créée" if was_created else "Mise à jour"
        messages_list.append(f"[{i}/{total}] {action} : {radio.name} (Pays : {country})")

        if was_created:
            created += 1
        else:
            updated += 1

    remaining = total - (offset + len(batch_stations))

    # Préparer les indices pour le prochain batch ou pays
    next_offset = offset + BATCH_SIZE if remaining > 0 else 0
    next_country_index = country_index if remaining > 0 else country_index + 1

    return JsonResponse({
        "total": total,
        "processed": offset + len(batch_stations),
        "remaining": remaining,
        "messages": messages_list,
        "created": created,
        "updated": updated,
        "current_country": country,
        "next_offset": next_offset,
        "next_country_index": next_country_index
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
