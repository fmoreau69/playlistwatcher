from __future__ import annotations

from typing import List
from django import forms
from django.utils import timezone

from .models import Contact, EmailCredential, EmailMessage, EmailTarget, Attachment


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class SendEmailForm(forms.ModelForm):
    to = forms.CharField(label="Destinataires (emails séparés par ,)")
    cc = forms.CharField(label="Cc", required=False)
    bcc = forms.CharField(label="Cci", required=False)
    scheduled_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        label="Date/heure d'envoi",
    )
    attachments = forms.FileField(required=False, widget=MultiFileInput(attrs={"multiple": True}))
    action = forms.CharField(widget=forms.HiddenInput(), initial="queue")

    class Meta:
        model = EmailMessage
        fields = ["credential", "subject", "body_text", "body_html"]
        labels = {
            "credential": "Expéditeur",
            "subject": "Objet",
            "body_text": "Corps (texte)",
            "body_html": "Corps (HTML)",
        }
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "body_text": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
            "body_html": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
        }

    def _split_emails(self, field: str) -> List[str]:
        raw = (self.cleaned_data.get(field) or "").replace(";", ",")
        parts = [x.strip() for x in raw.split(",") if x.strip()]
        return parts

    def get_recipients(self):
        return {
            "to": self._split_emails("to"),
            "cc": self._split_emails("cc"),
            "bcc": self._split_emails("bcc"),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = [
            "email",
            "first_name",
            "last_name",
            "phone",
            "address",
            "city",
            "region",
            "country",
            "unsubscribed",
        ]
