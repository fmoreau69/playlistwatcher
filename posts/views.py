from __future__ import annotations

import json
from typing import List
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from .forms import PublishPostForm, SocialCredentialForm, ImportJsonForm
from .models import Post, PostTarget, MediaAsset, SocialCredential, SocialNetworks


def _row_color_for_post(post: Post) -> str:
    # Green for sent, yellow for next scheduled, orange for later scheduled
    if post.status == Post.STATUS_SENT:
        return "#d1e7dd"  # Bootstrap success subtle
    if post.status in (Post.STATUS_SCHEDULED, Post.STATUS_PENDING):
        # Highlight the nearest future one in yellow; others orange will be set in template by index
        return "#fff3cd"  # Bootstrap warning subtle
    if post.status in (Post.STATUS_PARTIAL, Post.STATUS_FAILED):
        return "#f8d7da"  # danger subtle
    return "#ffffff"


def publish_post(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = PublishPostForm(request.POST, request.FILES)
        if form.is_valid():
            action = form.cleaned_data.get("action") or "queue"
            selected_networks = form.cleaned_data.get("networks") or []
            scheduled_at = form.cleaned_data.get("scheduled_at")
            if action == "publish_now":
                scheduled_at = timezone.now()

            with transaction.atomic():
                post = Post.objects.create(
                    title=form.cleaned_data["title"],
                    text=form.cleaned_data.get("text") or "",
                    scheduled_at=scheduled_at,
                    status=Post.STATUS_SCHEDULED if scheduled_at and scheduled_at > timezone.now() else Post.STATUS_PENDING,
                )

                # Media
                for f in request.FILES.getlist("media_files"):
                    MediaAsset.objects.create(post=post, file=f, content_type=getattr(f, "content_type", ""))

                # Targets
                for network in selected_networks:
                    PostTarget.objects.create(
                        post=post,
                        network=network,
                        status=(PostTarget.STATUS_SCHEDULED if scheduled_at and scheduled_at > timezone.now() else PostTarget.STATUS_QUEUED),
                        scheduled_at=scheduled_at,
                    )

                post.refresh_status_from_targets()

            return redirect(reverse("posts:publish"))
    else:
        form = PublishPostForm(initial={"networks": list(SocialNetworks.INITIALLY_SUPPORTED)})

    # Queue/history
    posts = Post.objects.order_by("-created_on").prefetch_related("targets", "media")

    context = {
        "form": form,
        "posts": posts,
        "row_color_for_post": _row_color_for_post,
        "supported_networks": SocialNetworks.INITIALLY_SUPPORTED,
    }
    return render(request, "posts/publish.html", context)


def credentials(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = SocialCredentialForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse("posts:credentials"))
    else:
        form = SocialCredentialForm()

    creds = SocialCredential.objects.all().order_by("network", "label")
    return render(request, "posts/credentials.html", {"form": form, "creds": creds})


def import_export(request: HttpRequest) -> HttpResponse:
    import_form = ImportJsonForm()
    creds_import_form = ImportJsonForm()
    posts = Post.objects.order_by("-created_on")[:50]
    creds = SocialCredential.objects.all()
    return render(
        request,
        "posts/import_export.html",
        {
            "import_form": import_form,
            "creds_import_form": creds_import_form,
            "posts": posts,
            "creds": creds,
        },
    )


def export_posts(request: HttpRequest) -> HttpResponse:
    data = []
    for p in Post.objects.all().prefetch_related("targets", "media"):
        data.append(
            {
                "title": p.title,
                "text": p.text,
                "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
                "targets": [t.network for t in p.targets.all()],
            }
        )
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    response = HttpResponse(payload, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=posts.json"
    return response


def export_credentials(request: HttpRequest) -> HttpResponse:
    data = []
    for c in SocialCredential.objects.all():
        data.append(
            {
                "network": c.network,
                "label": c.label,
                "client_id": c.client_id,
                "client_secret": c.client_secret,
                "access_token": c.access_token,
                "refresh_token": c.refresh_token,
                "extra": c.extra,
            }
        )
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    response = HttpResponse(payload, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = "attachment; filename=credentials.json"
    return response
