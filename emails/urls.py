from django.urls import path
from . import views

app_name = "emails"

urlpatterns = [
    path("send/", views.send_email, name="send"),
    path("contacts/", views.contacts, name="contacts"),
    path("import-export/", views.import_export, name="import_export"),
]
