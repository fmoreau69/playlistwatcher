from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from emails.models import EmailMessage, EmailTarget


class Command(BaseCommand):
    help = "Process queued/scheduled emails (stub)."

    def handle(self, *args, **options):
        now = timezone.now()
        to_process = EmailTarget.objects.select_related("email").filter(
            status__in=[EmailMessage.STATUS_QUEUED, EmailMessage.STATUS_SCHEDULED]
        )
        processed = 0
        for target in to_process:
            if target.email.scheduled_at and target.email.scheduled_at > now:
                continue
            target.status = EmailMessage.STATUS_SENT
            target.sent_at = now
            target.save(update_fields=["status", "sent_at"])
            processed += 1
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} email target(s)."))
