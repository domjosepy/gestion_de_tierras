from django import forms
from django.core.exceptions import ValidationError
from .models import SolicitudRelevamiento, Objetivo
from administrador.models import TipoObjetivo


class CrearSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario para CREAR una nueva solicitud, con colonia predefinida"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["prioridad", "observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observaciones adicionales (opcional)",
                "style": "text-transform: uppercase;"
            }),
            "prioridad": forms.Select(attrs={"class": "form-select"})
        }

    def clean_observaciones(self):
        observaciones = self.cleaned_data.get("observaciones")
        if observaciones:
            return observaciones.upper()
        return observaciones

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


class EditarSolicitudRelevamientoForm(forms.ModelForm):
    """Formulario solo para editar observaciones y prioridad"""
    class Meta:
        model = SolicitudRelevamiento
        fields = ["prioridad", "observaciones"]
        widgets = {
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "style": "text-transform: uppercase;"
            }),
            "prioridad": forms.Select(attrs={
                'class': 'form-select',
            })
        }

    def clean_observaciones(self):
        observaciones = self.cleaned_data.get("observaciones")
        if observaciones:
            return observaciones.upper()
        return observaciones

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar etiquetas
        self.fields['prioridad'].label = "Prioridad"
        self.fields['prioridad'].help_text = "Seleccione la urgencia de la solicitud"


class ObjetivoForm(forms.ModelForm):
    """
    Formulario para crear y editar objetivos.
    El grupo es recibido como parámetro y no es editable en el formulario.
    """
    
    tipo_objetivo = forms.ModelChoiceField(
        queryset=TipoObjetivo.objects.none(),  # Se filtra dinámicamente
        empty_label="Seleccione un tipo de objetivo",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'required': True
        }),
        label="Tipo de Objetivo"
    )
    
    class Meta:
        model = Objetivo
        fields = ['tipo_objetivo', 'fecha_fin', 'meta', 'avance_actual', 'descripcion', 'activo']
        widgets = {
            'fecha_fin': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'meta': forms.NumberInput(attrs={
                'class': 'form-control',
                'required': True,
                'min': 1,
                'placeholder': 'Meta a alcanzar'
            }),
            'avance_actual': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0,
                'placeholder': '0'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción o detalles adicionales del objetivo (opcional)'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, grupo=None, **kwargs):
        """
        Inicializa el formulario con un grupo específico.
        
        Args:
            grupo: Instancia de Grupo (opcional pero recomendado para crear)
        """
        self.grupo = grupo
        super().__init__(*args, **kwargs)
        
        # Inicializar etiquetas
        self.fields['tipo_objetivo'].label = "Tipo de Objetivo"
        self.fields['fecha_fin'].label = "Fecha Final de la Meta"
        self.fields['meta'].label = "Meta"
        self.fields['avance_actual'].label = "Avance Actual"
        self.fields['descripcion'].label = "Descripción"
        self.fields['activo'].label = "Activo"
        
        # Filtrar tipos_objetivo según el grupo
        if self.grupo:
            # Si se proporcionó un grupo, filtrar tipos de objetivo por ese grupo
            self.fields['tipo_objetivo'].queryset = TipoObjetivo.objects.filter(
                grupo=self.grupo,
                activo=True
            ).select_related('grupo').order_by('nombre')
        elif self.instance.pk and self.instance.grupo:
            # Si estamos editando, usar el grupo de la instancia
            self.grupo = self.instance.grupo
            self.fields['tipo_objetivo'].queryset = TipoObjetivo.objects.filter(
                grupo=self.grupo,
                activo=True
            ).select_related('grupo').order_by('nombre')
        else:
            # Sin grupo, no hay tipos de objetivo disponibles
            self.fields['tipo_objetivo'].queryset = TipoObjetivo.objects.none()
    
    def clean_meta(self):
        """Validar que la meta sea un número positivo"""
        meta = self.cleaned_data.get('meta')
        if meta is not None and meta <= 0:
            raise ValidationError("La meta debe ser un número mayor a 0")
        return meta
    
    def clean_avance_actual(self):
        """Validar que el avance actual no sea negativo"""
        avance_actual = self.cleaned_data.get('avance_actual')
        if avance_actual is not None and avance_actual < 0:
            raise ValidationError("El avance actual no puede ser negativo")
        return avance_actual
    
    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        tipo_objetivo = cleaned_data.get('tipo_objetivo')
        fecha_fin = cleaned_data.get('fecha_fin')
        
        # Validar que haya un grupo asignado
        if not self.grupo:
            raise ValidationError("No se ha especificado un grupo para el objetivo")
        
        # Validar que tipo_objetivo corresponda al grupo
        if tipo_objetivo:
            if tipo_objetivo.grupo_id != self.grupo.id:
                raise ValidationError(
                    f"El tipo de objetivo '{tipo_objetivo.nombre}' no pertenece al grupo '{self.grupo.nombre}'. "
                    f"Por favor, seleccione un tipo de objetivo válido para este grupo."
                )
        
        # Calcular año desde fecha_fin para validación de unicidad
        anio = fecha_fin.year if fecha_fin else None
        
        # Validar unicidad (grupo, tipo_objetivo, año)
        if tipo_objetivo and anio:
            qs = Objetivo.objects.filter(
                grupo=self.grupo,
                tipo_objetivo=tipo_objetivo,
                anio=anio
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"Ya existe un objetivo de '{tipo_objetivo.nombre}' para el grupo '{self.grupo.nombre}' en el año {anio}"
                )

        return cleaned_data
    
    def save(self, commit=True):
        """Guardar el objetivo asignando el grupo"""
        objetivo = super().save(commit=False)
        if self.grupo:
            objetivo.grupo = self.grupo
        if commit:
            objetivo.save()
        return objetivo