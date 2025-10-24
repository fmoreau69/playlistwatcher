from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from posts.models import Post, PostTarget


class Command(BaseCommand):
    help = "Process scheduled/queued posts (providers stubbed)."

    def handle(self, *args, **options):
        now = timezone.now()
        to_process = PostTarget.objects.select_related("post").filter(
            status__in=[PostTarget.STATUS_QUEUED, PostTarget.STATUS_SCHEDULED],
        )
        processed = 0
        for target in to_process:
            # Check schedule
            if target.scheduled_at and target.scheduled_at > now:
                continue

            # Stub provider: mark as sent immediately
            target.status = PostTarget.STATUS_SENT
            target.published_at = now
            target.save(update_fields=["status", "published_at"])

            # Refresh parent post status
            target.post.refresh_status_from_targets()
            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} target(s)."))
