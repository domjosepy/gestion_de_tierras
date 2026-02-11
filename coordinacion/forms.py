from django import forms
from django.utils import timezone
from .models import EquipoRelevamiento, OrdenTrabajo, RegistroCampo


class GenerarOrdenForm(forms.ModelForm):
    """Formulario simplificado para generar orden"""

    class Meta:
        model = OrdenTrabajo
        fields = ['coordinador_responsable', 'fecha_inicio_planeada',
                  'fecha_fin_planeada', 'meta_encuestas', 'observaciones']
        widgets = {
            'fecha_inicio_planeada': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin_planeada': forms.DateInput(attrs={'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Establecer fechas por defecto
        if not self.instance.pk:
            hoy = timezone.now().date()
            self.initial.setdefault('fecha_inicio_planeada', hoy)
            self.initial.setdefault(
                'fecha_fin_planeada', hoy + timezone.timedelta(days=7))


class CrearEquipoForm(forms.ModelForm):
    """Formulario simplificado para crear equipo"""

    class Meta:
        model = EquipoRelevamiento
        fields = ['nombre', 'tipo', 'coordinador_campo',
                  'subcoordinadores', 'encuestadores', 'choferes',
                  'vehiculos', 'equipos', 'max_encuestadores']
        widgets = {
            'vehiculos': forms.Textarea(attrs={'rows': 2}),
            'equipos': forms.Textarea(attrs={'rows': 3}),
        }


class RegistroCampoForm(forms.ModelForm):
    """Formulario simplificado para registro de campo"""

    class Meta:
        model = RegistroCampo
        fields = ['tipo', 'actividades_realizadas', 'encuestas_completadas',
                  'problemas_encontrados', 'hora_inicio', 'hora_fin']
        widgets = {
            'actividades_realizadas': forms.Textarea(attrs={'rows': 4}),
            'problemas_encontrados': forms.Textarea(attrs={'rows': 3}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        self.orden = kwargs.pop('orden', None)
        self.usuario = kwargs.pop('usuario', None)
        super().__init__(*args, **kwargs)

        # Filtrar equipos de esta orden
        if self.orden:
            self.fields['equipo'].queryset = self.orden.equipos_asignados.all()
            self.fields['equipo'].initial = self.orden.equipos_asignados.first()
