from django import forms
from .models import SolicitudRelevamiento

class SolicitudRelevamientoForm(forms.ModelForm):
    class Meta:
        model = SolicitudRelevamiento
        fields = ["colonia", "observaciones"]
        widgets = {
            "colonia": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }
        error_messages = {
            "colonia": {"required": "Debe seleccionar una colonia."},
            "observaciones": {"max_length": "Las observaciones son demasiado largas."},
        }
