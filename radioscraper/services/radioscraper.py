import requests
import re
from bs4 import BeautifulSoup
from radioscraper.models import Radio

API_BASE = "https://de1.api.radio-browser.info/json/stations"

def fetch_radios(country=None, state=None, tag=None):
    params = {}
    if country:
        params["country"] = country
    if state:
        params["state"] = state
    if tag:
        params["tag"] = tag

    response = requests.get(API_BASE, params=params, timeout=10)
    response.raise_for_status()
    return response.json()

def extract_emails(url):
    emails = set()
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text()
            found = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            emails.update(found)
    except Exception as e:
        print(f"Erreur email pour {url}: {e}")
    return ", ".join(emails)

def update_database(radios):
    new_count = 0
    for r in radios:
        radio, created = Radio.objects.get_or_create(
            stationuuid=r.get("stationuuid"),
            defaults={
                "name": r.get("name", ""),
                "country": r.get("country", ""),
                "state": r.get("state", ""),
                "tags": r.get("tags", ""),
                "homepage": r.get("homepage", ""),
                "stream_url": r.get("url", ""),
                "favicon": r.get("favicon", ""),
                "language": r.get("language", ""),
                "emails": "",
            }
        )
        if created and r.get("homepage"):
            radio.emails = extract_emails(r["homepage"])
            radio.save()
            new_count += 1
    return new_count
