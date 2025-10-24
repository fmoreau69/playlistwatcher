import re, requests, time
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.db import transaction, OperationalError
from django.core.paginator import Paginator
from django.core.cache import cache
import pandas as pd
from tqdm import tqdm
from io import BytesIO, StringIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from reportlab.platypus import SimpleDocTemplate, Table
from .forms import RadiosUploadForm
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


def save_stations_batch(stations, batch_size=BATCH_SIZE, task_id=None, force=False):
    """
    Ajoute la récupération d'email depuis la homepage/contact si disponible.
    Sauvegarde les stations par lots pour éviter les verrous SQLite.
    Met à jour la progression en cache si task_id fourni.
    """
    total_created, total_updated = 0, 0
    messages_list = []
    total = len(stations)

    for offset in range(0, len(stations), batch_size):
        batch = stations[offset:offset + batch_size]
        total_batches = (len(stations) + batch_size - 1) // batch_size

        for s in tqdm(batch, desc=f"Batch {offset // batch_size + 1}/{total_batches}", unit="station"):
            with transaction.atomic():
                homepage = s.get("homepage", "")
                api_email = s.get("email", "")

                try:
                    existing_radio = Radio.objects.get(stationuuid=s["stationuuid"])
                    if existing_radio.emails and not force:
                        scraped_email = ""  # on garde l'existant
                    else:
                        scraped_email = extract_email_from_homepage(homepage)
                except Radio.DoesNotExist:
                    scraped_email = extract_email_from_homepage(homepage)

                combined_email = ", ".join(filter(None, {api_email, scraped_email}))

                defaults = {
                    "name": s.get("name", "")[:255],
                    "country": s.get("country", ""),
                    "state": s.get("state", ""),
                    "tags": s.get("tags", ""),
                    "homepage": homepage,
                    "emails": combined_email,
                    "favicon": s.get("favicon", ""),
                    "language": s.get("language", ""),
                    "stream_url": s.get("url", ""),
                }
                radio, created = safe_update_or_create(defaults=defaults, stationuuid=s["stationuuid"])
                action = "Créée" if created else "Mise à jour"
                messages_list.append(f"{action} : {radio.name} ({radio.country})")

                if created:
                    total_created += 1
                else:
                    total_updated += 1

        if task_id:
            cache.set(
                f"refresh_progress_{task_id}",
                {
                    "processed": offset + len(batch),
                    "total": total,
                    "created": total_created,
                    "updated": total_updated,
                    "messages": messages_list[-5:],
                },
                timeout=3600
            )

    return total_created, total_updated, messages_list


def radio_search(request):
    """
    Recherche des radios avec filtrage multi-sélection et pagination.
    """
    radios = Radio.objects.all()
    selected_countries = request.GET.getlist('country')
    selected_states = request.GET.getlist('state')
    selected_tags = request.GET.getlist('tag')

    # Filtrage
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

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(radios.order_by('name'), 100)  # 100 radios par page
    page_obj = paginator.get_page(page_number)

    # Options multi-select
    countries = Radio.objects.values_list('country', flat=True).distinct().order_by('country')
    states = Radio.objects.values_list('state', flat=True).distinct().order_by('state')
    all_tags = []
    for t in Radio.objects.values_list('tags', flat=True):
        if t:
            all_tags.extend([tag.strip() for tag in t.split(',')])
    tags = sorted(list(set(all_tags)))

    return render(request, "radioscraper/radio_search.html", {
        "radios": page_obj.object_list,  # radios à afficher sur cette page
        "page_obj": page_obj,
        "countries": list(countries),
        "states": list(states),
        "tags": tags,
        "selected_countries": selected_countries,
        "selected_states": selected_states,
        "selected_tags": selected_tags,
        "radios_count": Radio.objects.count(),
        "displayed_count": page_obj.end_index(),  # Nombre affiché sur la page courante
    })


def radio_refresh(request):
    """
    Page principale d'actualisation : bouton + barre de progression (popup).
    """
    radios_count = Radio.objects.count()
    return render(
        request,
        "radioscraper/radio_refresh.html",
        {"radios_count": radios_count}
    )


@csrf_exempt
def radio_refresh_start(request):
    """
    Lance l’actualisation et enregistre l’état dans le cache.
    """
    selected_countries = request.POST.getlist("country") or [None]
    force = request.POST.get("force") == "on"
    task_id = str(int(time.time()))

    # Init du cache
    cache.set(
        f"refresh_progress_{task_id}",
        {"processed": 0, "total": 0, "created": 0, "updated": 0, "messages": []},
        timeout=3600
    )

    # Exécution synchrone (pour async il faudrait Celery/RQ)
    for country in selected_countries:
        stations = fetch_stations_by_country(country=country)
        save_stations_batch(stations, batch_size=BATCH_SIZE, task_id=task_id, force=force)

    return JsonResponse({"task_id": task_id})


def radio_refresh_progress(request, task_id):
    """
    Renvoie la progression pour affichage côté front (AJAX polling).
    """
    data = cache.get(f"refresh_progress_{task_id}")
    if not data:
        return JsonResponse({"error": "Task not found"}, status=404)
    return JsonResponse(data)


def extract_email_from_homepage(url):
    if not url:
        return None

    headers = {"User-Agent": "Mozilla/5.0"}
    emails_found = set()

    def fetch_and_extract(target_url):
        try:
            resp = requests.get(target_url, headers=headers, timeout=10)
            resp.raise_for_status()

            # Extraire avec regex brute
            emails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resp.text)
            emails_found.update(emails)

            # Extraire les liens mailto
            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if a["href"].startswith("mailto:"):
                    emails_found.add(a["href"].replace("mailto:", "").strip())

        except Exception as e:
            print(f"⚠️ Impossible de récupérer {target_url}: {e}")

    # 1) Scraper la page d’accueil
    fetch_and_extract(url)

    # 2) Chercher un lien "Contact" dans la page
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if "contact" in text:
                contact_url = urljoin(url, a["href"])
                fetch_and_extract(contact_url)
                break
    except Exception:
        pass

    return ", ".join(emails_found) if emails_found else None


@csrf_exempt
def radio_refresh_ajax(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    selected_countries = request.POST.getlist("country") or [None]
    country_index = int(request.POST.get("country_index", 0))
    offset = int(request.POST.get("offset", 0))
    force = request.POST.get("force") == "on"

    if country_index >= len(selected_countries):
        return JsonResponse({"finished": True})

    country = selected_countries[country_index]
    stations = fetch_stations_by_country(country=country)
    total = len(stations)
    batch_stations = stations[offset:offset+BATCH_SIZE]

    created, updated, messages_list = save_stations_batch(
        batch_stations, batch_size=BATCH_SIZE, force=force
    )
    remaining = total - (offset + len(batch_stations))

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


def export_radios_xlsx(request):
    radios = Radio.objects.all().values()
    df = pd.DataFrame(radios)
    buffer = BytesIO()
    df.to_excel(buffer, index=False, sheet_name="Radios")
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = "attachment; filename=radios.xlsx"
    return response


def export_radios_pdf(request):
    radios = Radio.objects.all().values_list("name", "country", "state", "tags", "homepage", "emails")
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer)
    table = Table([["Nom", "Pays", "Région", "Style", "Site web", "Emails"]] + list(radios))
    doc.build([table])
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=radios.pdf"
    return response


def export_radios_csv(request):
    radios = Radio.objects.all().values(
        "stationuuid", "name", "country", "state", "tags", "homepage", "stream_url",
        "emails", "favicon", "language", "station_type", "show_name", "contact_name",
        "contact_email", "contact_phone", "account_owner", "last_contact_date", "comment",
    )
    df = pd.DataFrame(radios)
    buffer = StringIO()
    df.to_csv(buffer, index=False)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=radios.csv"
    return response


def radios_import_export(request):
    if request.method == "POST":
        form = RadiosUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data["file"]
            ext = (f.name.split(".")[-1] or "").lower()
            if ext in ("xlsx", "xls"):
                df = pd.read_excel(f)
            elif ext == "csv":
                df = pd.read_csv(f)
            else:
                return JsonResponse({"error": "Unsupported file format"}, status=400)

            for _, row in df.iterrows():
                defaults = {
                    "name": str(row.get("name", ""))[:255],
                    "country": row.get("country") or "",
                    "state": row.get("state") or "",
                    "tags": row.get("tags") or "",
                    "homepage": row.get("homepage") or "",
                    "stream_url": row.get("stream_url") or "",
                    "emails": row.get("emails") or "",
                    "favicon": row.get("favicon") or "",
                    "language": row.get("language") or "",
                    "station_type": row.get("station_type") or "",
                    "show_name": row.get("show_name") or "",
                    "contact_name": row.get("contact_name") or "",
                    "contact_email": row.get("contact_email") or "",
                    "contact_phone": row.get("contact_phone") or "",
                    "account_owner": row.get("account_owner") or "",
                    "last_contact_date": row.get("last_contact_date") or None,
                    "comment": row.get("comment") or "",
                }
                stationuuid = str(row.get("stationuuid") or "").strip()
                if not stationuuid:
                    continue
                Radio.objects.update_or_create(stationuuid=stationuuid, defaults=defaults)

            return render(request, "radioscraper/radios_import_export.html", {"form": RadiosUploadForm(), "import_done": True})
    else:
        form = RadiosUploadForm()

    return render(request, "radioscraper/radios_import_export.html", {"form": form})
