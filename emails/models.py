from __future__ import annotations

from django.db import models
from django.utils import timezone


class Contact(models.Model):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=120, blank=True)
    region = models.CharField(max_length=120, blank=True)
    country = models.CharField(max_length=120, blank=True)
    unsubscribed = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        name = (self.first_name + " " + self.last_name).strip() or self.email
        return name


class EmailCredential(models.Model):
    label = models.CharField(max_length=120)
    from_email = models.EmailField()
    smtp_host = models.CharField(max_length=180, blank=True)
    smtp_port = models.PositiveIntegerField(default=587)
    use_tls = models.BooleanField(default=True)
    username = models.CharField(max_length=180, blank=True)
    password = models.CharField(max_length=255, blank=True)
    extra = models.JSONField(blank=True, null=True)

    class Meta:
        unique_together = ("label", "from_email")

    def __str__(self) -> str:
        return f"{self.label} <{self.from_email}>"


class EmailMessage(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_QUEUED = "queued"
    STATUS_SCHEDULED = "scheduled"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_QUEUED, "Queued"),
        (STATUS_SCHEDULED, "Scheduled"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    )

    credential = models.ForeignKey(EmailCredential, on_delete=models.PROTECT, related_name="emails")
    subject = models.CharField(max_length=255)
    body_html = models.TextField(blank=True)
    body_text = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    def __str__(self) -> str:
        return self.subject


class EmailTarget(models.Model):
    email = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name="targets")
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT, related_name="email_targets")
    to_kind = models.CharField(max_length=8, choices=(("to", "To"), ("cc", "Cc"), ("bcc", "Bcc")), default="to")
    status = models.CharField(max_length=20, choices=EmailMessage.STATUS_CHOICES, default=EmailMessage.STATUS_QUEUED)
    sent_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"{self.email_id} -> {self.contact.email} ({self.to_kind})"


class Attachment(models.Model):
    email = models.ForeignKey(EmailMessage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="emails/")
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "file"):
            self.size_bytes = self.file.size
        super().save(*args, **kwargs)
