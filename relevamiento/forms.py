from django import forms

from .models import EQUIPAMIENTOS_CHOICES, MOD_POST_CHOICES, USO_LOTE_CHOICES, MEJORAS_CHOICES,  Relevamiento


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
