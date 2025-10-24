from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("tracker.urls")),
    path("radios/", include("radioscraper.urls")),
    path("posts/", include("posts.urls")),
    path(r'favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('favicon.ico'))),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
