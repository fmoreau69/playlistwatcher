from django import forms
from .models import Track, SpotifyCredentials

class TrackForm(forms.ModelForm):
    class Meta:
        model = Track
        fields = ["name", "spotify_id", "spotify_url"]

class ExcelUploadForm(forms.Form):
    file = forms.FileField(label="Choisir un fichier Excel (Liste d'apparitions)")

class PlaylistUploadForm(forms.Form):
    file = forms.FileField(label="Choisir un fichier Excel (Liste de playlists)")

class SpotifyCredentialsForm(forms.ModelForm):
    class Meta:
        model = SpotifyCredentials
        fields = ["client_id", "client_secret", "redirect_uri"]