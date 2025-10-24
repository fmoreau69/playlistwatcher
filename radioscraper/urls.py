from django.urls import path
from . import views

urlpatterns = [
    path("", views.radio_search, name="radio_search"),
    path("refresh/", views.radio_refresh, name="radio_refresh"),
    path('refresh/start/', views.radio_refresh_start, name='radio_refresh_start'),
    # Import/Export
    path("import-export/", views.radios_import_export, name="radios_import_export"),
    path("export/csv/", views.export_radios_csv, name="export_radios_csv"),
    path("export/xlsx/", views.export_radios_xlsx, name="export_radios_xlsx"),
    path("export/pdf/", views.export_radios_pdf, name="export_radios_pdf"),
]
