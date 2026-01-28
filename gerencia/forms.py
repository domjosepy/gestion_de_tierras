from django import forms
from django.core.exceptions import ValidationError
from .models import SolicitudRelevamiento


class CrearSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario específico para CREAR una nueva solicitud"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["prioridad", "observaciones"]  # AGREGAR prioridad
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones adicionales (opcional)"
            }),
            "prioridad": forms.Select(attrs={
                "class": "form-select",
            })
        }

    def __init__(self, *args, colonia=None, **kwargs):
        # Extraer colonia del kwargs antes de pasar al padre
        self.colonia = colonia
        super().__init__(*args, **kwargs)

        # Configurar opciones de prioridad
        self.fields['prioridad'].initial = 'media'

        # Si tenemos una colonia, podemos inicializar la instancia con ella
        if colonia and self.instance:
            self.instance.colonia = colonia

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


class SolicitudRelevamientoForm(forms.ModelForm):
    """Formulario para CREAR una nueva solicitud"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["prioridad", "observaciones"]  # AGREGAR prioridad
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones adicionales (opcional)"
            }),
            "prioridad": forms.Select(attrs={
                'class': 'form-select',
            })
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
        self.fields['prioridad'].initial = 'media'


class EditarSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario solo para editar observaciones y prioridad"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["prioridad", "observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),
            "prioridad": forms.Select(attrs={
                'class': 'form-select',
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar etiquetas
        self.fields['prioridad'].label = "Prioridad"
        self.fields['prioridad'].help_text = "Seleccione la urgencia de la solicitud"
