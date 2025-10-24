from __future__ import annotations

from typing import Iterable
from django import forms
from django.utils import timezone

from .models import Post, MediaAsset, SocialCredential, SocialNetworks


class PublishPostForm(forms.ModelForm):
    networks = forms.MultipleChoiceField(
        choices=SocialNetworks.CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Réseaux sociaux",
    )
    action = forms.CharField(widget=forms.HiddenInput(), initial="queue")
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Date/heure de publication",
    )
    media_files = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={"multiple": True}),
        label="Images/Vidéo",
    )

    class Meta:
        model = Post
        fields = ["title", "text"]
        labels = {"title": "Post Title", "text": "Post Text"}

    def clean_networks(self):
        selected = set(self.cleaned_data.get("networks") or [])
        # Allow selecting all, but mark unsupported ones disabled in UI
        return list(selected)


class SocialCredentialForm(forms.ModelForm):
    class Meta:
        model = SocialCredential
        fields = [
            "network",
            "label",
            "client_id",
            "client_secret",
            "access_token",
            "refresh_token",
            "extra",
        ]


class ImportJsonForm(forms.Form):
    file = forms.FileField(label="Fichier JSON")
