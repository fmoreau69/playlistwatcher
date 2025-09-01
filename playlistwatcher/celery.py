import os
from celery import Celery

# Définit le module de settings Django par défaut
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playlistwatcher.settings")

app = Celery("playlistwatcher")

# Charger les settings de Django, namespace CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Découvrir automatiquement les tâches dans les apps Django
app.autodiscover_tasks()
