from __future__ import annotations

from django.db import models
from django.utils import timezone


class SocialNetworks:
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    BLUESKY = "bluesky"
    GOOGLE_BUSINESS = "google_business"
    PINTEREST = "pinterest"
    REDDIT = "reddit"
    SNAPCHAT = "snapchat"
    TELEGRAM = "telegram"
    THREADS = "threads"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"

    CHOICES = (
        (FACEBOOK, "Facebook"),
        (INSTAGRAM, "Instagram"),
        (LINKEDIN, "LinkedIn"),
        (TWITTER, "X/Twitter"),
        (BLUESKY, "Bluesky"),
        (GOOGLE_BUSINESS, "Google Business"),
        (PINTEREST, "Pinterest"),
        (REDDIT, "Reddit"),
        (SNAPCHAT, "Snapchat"),
        (TELEGRAM, "Telegram"),
        (THREADS, "Threads"),
        (TIKTOK, "TikTok"),
        (YOUTUBE, "YouTube"),
    )

    INITIALLY_SUPPORTED = {FACEBOOK, INSTAGRAM, LINKEDIN, TWITTER}


class Post(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PENDING = "pending"  # created and awaiting processing
    STATUS_SCHEDULED = "scheduled"  # scheduled in the future
    STATUS_SENT = "sent"  # all targets sent successfully
    STATUS_PARTIAL = "partial"  # some targets sent, some failed
    STATUS_FAILED = "failed"  # all targets failed

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_SENT, "Sent"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_FAILED, "Failed"),
    )

    title = models.CharField(max_length=200)
    text = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    def __str__(self) -> str:
        return f"{self.title}"

    def refresh_status_from_targets(self) -> None:
        targets = list(self.targets.all())
        if not targets:
            self.status = Post.STATUS_DRAFT
            self.save(update_fields=["status"])
            return

        num_sent = sum(1 for t in targets if t.status == PostTarget.STATUS_SENT)
        num_failed = sum(1 for t in targets if t.status == PostTarget.STATUS_FAILED)
        num_scheduled = sum(1 for t in targets if t.status == PostTarget.STATUS_SCHEDULED)
        num_pending = sum(1 for t in targets if t.status in (PostTarget.STATUS_PENDING, PostTarget.STATUS_QUEUED))

        if num_sent and num_sent == len(targets):
            self.status = Post.STATUS_SENT
        elif num_failed and num_failed == len(targets):
            self.status = Post.STATUS_FAILED
        elif num_scheduled:
            self.status = Post.STATUS_SCHEDULED
        elif num_pending:
            self.status = Post.STATUS_PENDING
        else:
            self.status = Post.STATUS_PARTIAL
        self.save(update_fields=["status"])


class PostTarget(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_PENDING = "pending"
    STATUS_SCHEDULED = "scheduled"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_QUEUED, "Queued"),
        (STATUS_PENDING, "Pending"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="targets")
    network = models.CharField(max_length=40, choices=SocialNetworks.CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ("post", "network")

    def __str__(self) -> str:
        return f"{self.post_id}@{self.network}"


class MediaAsset(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="media")
    file = models.FileField(upload_to="posts/")
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "file"):
            self.size_bytes = self.file.size
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Media#{self.id} for Post#{self.post_id}"


class SocialCredential(models.Model):
    network = models.CharField(max_length=40, choices=SocialNetworks.CHOICES)
    label = models.CharField(max_length=120, help_text="Nom lisible pour cette connexion")
    client_id = models.CharField(max_length=255, blank=True)
    client_secret = models.CharField(max_length=255, blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    extra = models.JSONField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("network", "label")

    def __str__(self) -> str:
        return f"{self.get_network_display()} - {self.label}"
