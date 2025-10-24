from django.urls import path
from . import views

app_name = "posts"

urlpatterns = [
    path("publish/", views.publish_post, name="publish"),
    path("credentials/", views.credentials, name="credentials"),
    path("import-export/", views.import_export, name="import_export"),
    path("export/posts/", views.export_posts, name="export_posts"),
    path("export/credentials/", views.export_credentials, name="export_credentials"),
]
