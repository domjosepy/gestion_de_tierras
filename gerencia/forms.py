from django import forms
from django.core.exceptions import ValidationError
from .models import SolicitudRelevamiento


class CrearSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario específico para CREAR una nueva solicitud"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones adicionales (opcional)"
            }),
        }

    def __init__(self, *args, colonia=None, **kwargs):
        # Extraer colonia del kwargs antes de pasar al padre
        self.colonia = colonia
        super().__init__(*args, **kwargs)

        # Si tenemos una colonia, podemos inicializar la instancia con ella
        if colonia and self.instance:
            self.instance.colonia = colonia

    def clean(self):
        cleaned_data = super().clean()

        # La validación de solicitudes activas la haremos en la vista
        # para evitar problemas con el acceso a self.colonia
        return cleaned_data


class SolicitudRelevamientoForm(forms.ModelForm):

    """Formulario para CREAR una nueva solicitud"""
    class Meta:
        model = SolicitudRelevamiento
        # SOLO observaciones, los demás campos se generan automáticamente
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones adicionales (opcional)"
            }),
        }
        error_messages = {
            "observaciones": {
                "max_length": "Las observaciones son demasiado largas."
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No mostrar labels innecesarios
        self.fields['observaciones'].label = ""


class EditarSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario solo para editar observaciones (NO incluye colonia)"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),
        }
