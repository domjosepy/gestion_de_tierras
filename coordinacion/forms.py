from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from coordinacion.models import OrdenTrabajo, EquipoRelevamiento, RegistroCampo
from administrador.models import User
from django.conf import settings
from .utils import contar_dias_habiles


class UsuarioPorGrupoField(forms.ModelMultipleChoiceField):
    """
    Campo MultipleChoice para usuarios filtrados por nombre de grupo (icontains).
    """

    def __init__(self, grupo_nombre, *args, **kwargs):
        queryset = User.objects.filter(
            groups__name__icontains=grupo_nombre,
            is_active=True
        ).order_by('username')
        super().__init__(queryset=queryset, *args, **kwargs)


class UsuarioPorGrupoSimpleField(forms.ModelChoiceField):
    """
    Campo SimpleChoice para usuarios filtrados por nombre de grupo (icontains).
    """

    def __init__(self, grupo_nombre, *args, **kwargs):
        queryset = User.objects.filter(
            groups__name__icontains=grupo_nombre,
            is_active=True
        ).order_by('username')
        super().__init__(queryset=queryset, *args, **kwargs)


class GenerarOrdenForm(forms.ModelForm):
    # Reemplazamos los campos manuales por los personalizados
    coordinador_campo = UsuarioPorGrupoSimpleField(
        grupo_nombre='Rol_COORDINADOR',
        required=False,
        label='Coordinador de campo',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    subcoordinadores = UsuarioPorGrupoField(
        grupo_nombre='Rol_SUBCOORDINADOR',
        required=False,
        label='Subcoordinadores',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    encuestadores = UsuarioPorGrupoField(
        grupo_nombre='Rol_ENCUESTADOR',
        required=False,
        label='Encuestadores',
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': 5})
    )
    choferes = UsuarioPorGrupoField(
        grupo_nombre='Rol_CHOFER',
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
            self.fields['coordinador_responsable'].widget = forms.HiddenInput()

    def clean_fecha_inicio_planeada(self):
        fecha = self.cleaned_data.get('fecha_inicio_planeada')
        hoy = timezone.now().date()
        if fecha < hoy:
            raise ValidationError('La fecha de inicio no puede ser pasada.')
        if fecha.weekday() >= 5:
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
        if inicio:
            dias_habiles = contar_dias_habiles(
                inicio, fecha)
            if dias_habiles < 1:
                raise ValidationError(
                    f'El período debe ser de al menos 1 día hábil (actual: {dias_habiles}).')
            if dias_habiles > 5:
                raise ValidationError(
                    f'El período no puede exceder 5 días hábiles (actual: {dias_habiles}).')
        return fecha


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
