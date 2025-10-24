from django import forms


class RadiosUploadForm(forms.Form):
    file = forms.FileField(label="Choose CSV/XLSX file of radios")
