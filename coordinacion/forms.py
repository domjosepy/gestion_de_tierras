from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from coordinacion.models import OrdenTrabajo, EquipoRelevamiento, RegistroCampo
from administrador.models import User
from django.conf import settings


class GenerarOrdenForm(forms.ModelForm):
    # Campos para equipo de campo
    coordinador_campo = forms.ModelChoiceField(
        queryset=User.objects.filter(
            groups__name__icontains='Rol_COORDINADOR',
            is_active=True
        ).order_by('username'),
        required=False,
        label='Coordinador de campo',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subcoordinadores = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            groups__name__icontains='Rol_SUBCOORDINADOR',
            is_active=True
        ).order_by('username'),
        required=False,
        label='Subcoordinadores',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    encuestadores = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            groups__name__icontains='Rol_ENCUESTADOR',
            is_active=True
        ).order_by('username'),
        required=False,
        label='Encuestadores',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    choferes = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(
            groups__name__icontains='Rol_CHOFER',
            is_active=True
        ).order_by('username'),
        required=False,
        label='Choferes',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )

    class Meta:
        model = OrdenTrabajo
        fields = [
            'coordinador_responsable',
            'fecha_inicio_planeada',
            'fecha_fin_planeada',
            'meta_encuestas',
            'observaciones'
        ]
        widgets = {
            'fecha_inicio_planeada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'fecha_fin_planeada': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'meta_encuestas': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'coordinador_responsable': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request and not self.instance.pk:
            self.fields['coordinador_responsable'].initial = self.request.user
            # Ocultar el campo (ya que lo mostramos como texto)
            self.fields['coordinador_responsable'].widget = forms.HiddenInput()

    # --- VALIDACIONES DE FECHAS ---

    def clean_fecha_inicio_planeada(self):
        fecha = self.cleaned_data.get('fecha_inicio_planeada')
        hoy = timezone.now().date()

        if fecha < hoy:
            raise ValidationError('La fecha de inicio no puede ser pasada.')
        if fecha.weekday() >= 5:  # 5 = sábado, 6 = domingo
            raise ValidationError(
                'La fecha de inicio debe ser un día hábil (lunes a viernes).')
        return fecha

    def clean_fecha_fin_planeada(self):
        fecha = self.cleaned_data.get('fecha_fin_planeada')
        inicio = self.cleaned_data.get('fecha_inicio_planeada')
        hoy = timezone.now().date()

        if fecha < hoy:
            raise ValidationError('La fecha de fin no puede ser pasada.')
        if fecha.weekday() >= 5:
            raise ValidationError(
                'La fecha de fin debe ser un día hábil (lunes a viernes).')

        # Validar rango de 3 a 5 días hábiles
        if inicio:
            dias_habiles = self._contar_dias_habiles(inicio, fecha)
            if dias_habiles < 3:
                raise ValidationError(
                    f'El período debe ser de al menos 3 días hábiles (actual: {dias_habiles}).')
            if dias_habiles > 5:
                raise ValidationError(
                    f'El período no puede exceder 5 días hábiles (actual: {dias_habiles}).')
        return fecha

    def _contar_dias_habiles(self, inicio, fin):
        """Cuenta días de lunes a viernes entre dos fechas (inclusive)"""
        dias = 0
        dia = inicio
        while dia <= fin:
            if dia.weekday() < 5:
                dias += 1
            dia += timedelta(days=1)
        return dias


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
