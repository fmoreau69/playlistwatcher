from django.contrib import admin
from .models import Post, PostTarget, MediaAsset, SocialCredential


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "status", "scheduled_at", "created_on")
    search_fields = ("title", "text")
    list_filter = ("status", "scheduled_at")


@admin.register(PostTarget)
class PostTargetAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "network", "status", "scheduled_at", "published_at")
    list_filter = ("network", "status")


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "file", "content_type", "size_bytes")


@admin.register(SocialCredential)
class SocialCredentialAdmin(admin.ModelAdmin):
    list_display = ("id", "network", "label", "created_on")
    list_filter = ("network",)
    search_fields = ("label",)
