from __future__ import annotations

from typing import List
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from .models import Contact, EmailCredential, EmailMessage, EmailTarget, Attachment
from .forms import SendEmailForm, ContactForm


def send_email(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SendEmailForm(request.POST, request.FILES)
        if form.is_valid():
            action = form.cleaned_data.get("action") or "queue"
            scheduled_at = form.cleaned_data.get("scheduled_at")
            if action == "send_now":
                scheduled_at = timezone.now()

            recipients = form.get_recipients()
            with transaction.atomic():
                email = form.save(commit=False)
                email.scheduled_at = scheduled_at
                email.status = (
                    EmailMessage.STATUS_SCHEDULED
                    if scheduled_at and scheduled_at > timezone.now()
                    else EmailMessage.STATUS_QUEUED
                )
                email.save()

                # Attachments
                for f in request.FILES.getlist("attachments"):
                    Attachment.objects.create(email=email, file=f, content_type=getattr(f, "content_type", ""))

                # Targets: create contacts on the fly if not exist
                def ensure_contacts(addresses: List[str]) -> List[Contact]:
                    res = []
                    for addr in addresses:
                        c, _ = Contact.objects.get_or_create(email=addr)
                        res.append(c)
                    return res

                for kind, emails in recipients.items():
                    for c in ensure_contacts(emails):
                        EmailTarget.objects.create(email=email, contact=c, to_kind=kind, status=email.status)

            return redirect(reverse("emails:send"))
    else:
        form = SendEmailForm()

    emails = (
        EmailMessage.objects.order_by("-created_on").prefetch_related("targets", "attachments")
    )
    return render(request, "emails/send.html", {"form": form, "emails": emails})


def contacts(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("emails:contacts"))
    else:
        form = ContactForm()

    contacts_qs = Contact.objects.order_by("-created_on")[:200]
    return render(request, "emails/contacts.html", {"form": form, "contacts": contacts_qs})


def import_export(request: HttpRequest) -> HttpResponse:
    contacts_qs = Contact.objects.order_by("email")
    return render(request, "emails/import_export.html", {"contacts": contacts_qs})
