from django.urls import path
from . import views

urlpatterns = [
    path("", views.radio_search, name="radio_search"),
    path("refresh/", views.radio_refresh, name="radio_refresh"),
    path('refresh/start/', views.radio_refresh_start, name='radio_refresh_start'),
    path("export/xlsx/", views.export_xlsx, name="export_xlsx"),
    path("export/pdf/", views.export_pdf, name="export_pdf"),
]
