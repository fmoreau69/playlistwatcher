import math
from celery import shared_task
from django.core.cache import cache
from tqdm import tqdm  # barre de progression console
from .utils import fetch_stations_by_country, save_stations_batch

@shared_task(bind=True)
def refresh_radios_task(self, countries=None, batch_size=100):
    """
    Tâche Celery pour actualiser les radios.
    - countries : liste de pays à traiter
    - batch_size : nombre de radios par batch
    """

    if countries is None or len(countries) == 0:
        countries = ["France"]

    overall_created = 0
    overall_updated = 0
    overall_messages = []

    for country in countries:
        stations = fetch_stations_by_country(country)
        total = len(stations)
        total_batches = max(1, math.ceil(total / batch_size))

        # Initialiser le cache pour le suivi frontend
        cache.set(f"refresh_progress_{self.request.id}", {
            "processed": 0,
            "total": total,
            "created": overall_created,
            "updated": overall_updated,
            "messages": [],
            "current_country": country,
            "finished": False
        }, timeout=3600)

        # Traitement par batch avec barre console
        for batch_index in tqdm(range(total_batches), desc=f"Pays : {country}", unit="batch"):
            batch = stations[batch_index * batch_size:(batch_index + 1) * batch_size]
            created, updated, messages_list = save_stations_batch(
                batch, batch_size=batch_size, task_id=self.request.id
            )

            overall_created += created
            overall_updated += updated
            overall_messages.extend(messages_list)

            # Mettre à jour la progression dans le cache pour le front
            processed = min((batch_index + 1) * batch_size, total)
            cache.set(f"refresh_progress_{self.request.id}", {
                "processed": processed,
                "total": total,
                "created": overall_created,
                "updated": overall_updated,
                "messages": overall_messages[-5:],
                "current_country": country,
                "finished": False
            }, timeout=3600)

    # Marquer la tâche comme terminée
    cache.set(f"refresh_progress_{self.request.id}", {
        "processed": overall_created + overall_updated,
        "total": overall_created + overall_updated,
        "created": overall_created,
        "updated": overall_updated,
        "messages": overall_messages[-5:],
        "current_country": None,
        "finished": True
    }, timeout=3600)

    return {
        "status": "done",
        "total": overall_created + overall_updated,
        "created": overall_created,
        "updated": overall_updated,
        "messages": overall_messages
    }
