from django import forms
from django.utils.safestring import mark_safe

from .models import EQUIPAMIENTOS_CHOICES, MOD_POST_CHOICES, USO_LOTE_CHOICES, MEJORAS_CHOICES,  Relevamiento


class MultipleFileInput(forms.FileInput):
    """Widget personalizado para permitir subida de múltiples archivos."""
    
    def render(self, name, value, attrs=None, renderer=None):
        """Override render to add 'multiple' attribute after widget creation."""
        if attrs is None:
            attrs = {}
        attrs['multiple'] = 'multiple'
        return super().render(name, value, attrs, renderer)


class MultipleFileField(forms.FileField):
    """Campo de formulario que maneja múltiples archivos."""
    
    widget = MultipleFileInput
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)
    
    def clean(self, data, initial=None):
        if isinstance(data, list):
            result = [super(MultipleFileField, self).clean(d, initial) for d in data]
            return result
        return super().clean(data, initial)


class RelevamientoForm(forms.ModelForm):
    """Form for creating/editing a `Relevamiento`.

    Maps ArrayFields to MultipleChoiceFields for user-friendly input.
    """

    uso_lote = forms.MultipleChoiceField(
        choices=USO_LOTE_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    modificaciones_post = forms.MultipleChoiceField(
        choices=MOD_POST_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    equipamientos = forms.MultipleChoiceField(
        choices=EQUIPAMIENTOS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Relevamiento
        fields = [
            "departamento",
            "distrito",
            "colonia",
            "manzana",
            "lote_indert",
            "lote_sirt",
            "formulario",
            "observacion_encuesta",
            "uso_lote",
            "nro_titulo",
            "tipo_lote",
            "condicion_vivienda",
            "condicion_encuestado",
            "superficie_ha",
            "dimensiones",
            "vive_en_lote",
            "residencia_manzana",
            "residencia_lote",
            "quien_es_el_ocupante",
            "cedula_ocupante",
            "sexo_ocupante",
            "parentesco",
            "produccion_agricola_ha",
            "produccion_ganadera_ha",
            "reforestado_ha",
            "bosque_natural_ha",
            "barbecho_ha",
            "mejoras",
            "estado_entrevista",
            "firmo_solicitud",
            "modificaciones_post",
            "equipamientos",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap classes to widgets depending on type
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            # checkboxes (single or multiple)
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            # selects (single/multiple)
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            # file inputs
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = (existing + " form-control").strip()
            else:
                # default to form-control for text/number/textarea
                widget.attrs["class"] = (existing + " form-control").strip()

    def clean_uso_lote(self):
        return list(self.cleaned_data.get("uso_lote", []))

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

    def clean_modificaciones_post(self):
        return list(self.cleaned_data.get("modificaciones_post", []))

    def clean_equipamientos(self):
        return list(self.cleaned_data.get("equipamientos", []))


class FotosRelevamientoForm(forms.Form):
    """Formulario para subir múltiples fotos en 4 categorías.
    
    Cada campo permite subir múltiples archivos de imagen.
    """
    fotos_recibo = MultipleFileField(
        required=False,
        label='Fotos de Recibo'
    )
    
    fotos_vivienda = MultipleFileField(
        required=False,
        label='Fotos de Vivienda'
    )
    
    fotos_documento = MultipleFileField(
        required=False,
        label='Fotos de Documento de Identidad'
    )
    
    fotos_lote = MultipleFileField(
        required=False,
        label='Fotos del Lote'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases Bootstrap y atributos HTML5 a todos los campos de archivo
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control',
                'accept': 'image/*',
                'capture': 'environment'
            })
