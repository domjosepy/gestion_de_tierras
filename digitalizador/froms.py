# digitalizador/forms.py
from django import forms
from gerencia.models import SolicitudRelevamiento
from django.contrib.auth.models import User


class AsignarDigitalizadorForm(forms.ModelForm):
    class Meta:
        model = SolicitudRelevamiento
        fields = ['digitalizador_asignado']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar solo usuarios del grupo Digitalizador
        self.fields['digitalizador_asignado'].queryset = User.objects.filter(
            groups__name='Digitalizador'
        )
        self.fields['digitalizador_asignado'].label = "Digitalizador"
        self.fields['digitalizador_asignado'].empty_label = "Seleccione un digitalizador"
