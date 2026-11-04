import io
import os
import re

from django.core.files.base import ContentFile
from PIL import Image

from .utils import limpiar_nombre_carpeta, extension_segura

from django import forms
from django.forms import inlineformset_factory

from .models import (
    EQUIPAMIENTOS_CHOICES, TIPO_CULTIVO_CHOICES, TIPO_GANADERIA_CHOICES,
    TIPO_GANADERIA_CHOICES, USO_LOTE_OCUPANTE_CHOICES,
    MEJORAS_CHOICES,USO_LOTE_SERVICIO_CHOICES,
    Relevamiento, Pretendiente, Vivienda, Miembro,
    Cultivo, ProduccionGanadera, InstitucionEnLote, FotoRelevamiento,
)


class MultipleFileInput(forms.FileInput):
    """Input de archivos con 'multiple', según el patrón oficial de Django 5.0."""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Campo que devuelve una LISTA con todos los archivos elegidos."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            return []
        limpiar_uno = super().clean
        if isinstance(data, (list, tuple)):
            return [limpiar_uno(d, initial) for d in data]
        return [limpiar_uno(data, initial)]

##################################
# MANEJO DE RELEVAMIENTO OCUPANTE
##################################    
class RelevamientoParte1Form(forms.ModelForm):
    """Parte 1 del wizard (modo Ocupante): datos geográficos básicos +
    identificación del ocupante. Es un subconjunto deliberadamente chico
    de los campos de Relevamiento — cada parte del wizard va a tener su
    propio ModelForm acotado así, en vez de reutilizar el RelevamientoForm
    gigante de una sola vez."""

    class Meta:
        model = Relevamiento
        fields = [
            "distrito",
            "manzana", "lote_indert",
            "frente_aprox", "fondo_aprox",
            "superficie_ha", "dimensiones", "tipo_lote",
            "quien_es_el_ocupante", "cedula_ocupante", "sexo_ocupante", "estado_civil_ocupante", "telefono_ocupante",
            "quien_es_el_conyuge", "cedula_conyuge", "sexo_conyuge", "estado_civil_conyuge",
        ]
        widgets = {
            "distrito": forms.Select(attrs={"class": "form-select"}),
            "dimensiones": forms.HiddenInput(),
            "superficie_ha": forms.HiddenInput(),
            "tipo_lote": forms.HiddenInput(),
            "quien_es_el_conyuge": forms.HiddenInput(),
            "cedula_conyuge": forms.HiddenInput(),
            "sexo_conyuge": forms.HiddenInput(),
            "estado_civil_conyuge": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        colonia = kwargs.pop("colonia", None)
        super().__init__(*args, **kwargs)

        # ── Lógica de distrito condicional ──
        if colonia is None and self.instance.colonia_id:
            colonia = self.instance.colonia

        if colonia is not None:
            distritos_qs = colonia.distritos.all()
            if distritos_qs.count() <= 1:
                # 0 o 1 distritos: no mostrar, derivar_geografia lo resuelve
                self.fields.pop("distrito", None)
            else:
                # 2+ distritos: mostrar select acotado y obligatorio
                self.fields["distrito"].queryset = distritos_qs
                self.fields["distrito"].required = True
                if self.instance.distrito_id:
                    self.initial["distrito"] = self.instance.distrito_id
        else:
            # Sin colonia no hay de dónde elegir
            self.fields.pop("distrito", None)

        # ── Bootstrap (tu loop actual) ──
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.HiddenInput):
                continue
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

    def clean_manzana(self):
        data = self.cleaned_data.get('manzana')
        if not data or (isinstance(data, str) and not data.strip()):
            raise forms.ValidationError("El campo manzana no puede estar vacío.")
        return data

    def clean_lote_indert(self):
        data = self.cleaned_data.get('lote_indert')
        if not data or (isinstance(data, str) and not data.strip()):
            raise forms.ValidationError("El campo lote no puede estar vacío.")
        return data

    def _validar_nombre_letras_enie(self, nombre, campo_nombre):
        if nombre:
            nombre = nombre.strip()
            if not re.match(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$', nombre):
                raise forms.ValidationError(f"El {campo_nombre} debe contener solo letras y Ñ.")
        return nombre.upper() if nombre else nombre

    def clean_quien_es_el_ocupante(self):
        data = self.cleaned_data.get('quien_es_el_ocupante')
        return self._validar_nombre_letras_enie(data, "nombre del ocupante")

    def clean_cedula_ocupante(self):
        data = self.cleaned_data.get('cedula_ocupante')
        if data:
            data = data.strip()
            if not data.isdigit():
                raise forms.ValidationError("La cédula debe contener solo números.")
            if len(data) > 8:
                raise forms.ValidationError("La cédula no debe tener más de 8 dígitos.")
        return data

    def clean_telefono_ocupante(self):
        data = self.cleaned_data.get('telefono_ocupante')
        if data:
            data = data.strip()
            if not data.isdigit():
                raise forms.ValidationError("El teléfono debe contener solo números.")
            if len(data) > 10:
                raise forms.ValidationError("El teléfono no debe tener más de 10 dígitos.")
        return data

    def clean_quien_es_el_conyuge(self):
        data = self.cleaned_data.get('quien_es_el_conyuge')
        return self._validar_nombre_letras_enie(data, "nombre del cónyuge")

    def clean_cedula_conyuge(self):
        data = self.cleaned_data.get('cedula_conyuge')
        if data:
            data = data.strip()
            if not data.isdigit():
                raise forms.ValidationError("La cédula del cónyuge debe contener solo números.")
            if len(data) > 8:
                raise forms.ValidationError("La cédula del cónyuge no debe tener más de 8 dígitos.")
        return data

    def clean(self):
        cleaned_data = super().clean()
        frente = cleaned_data.get("frente_aprox")
        fondo = cleaned_data.get("fondo_aprox")
        if frente and fondo:
            superficie_ha = round((frente * fondo) / 10000, 4)
            cleaned_data["dimensiones"] = f"{frente}x{fondo}"
            cleaned_data["superficie_ha"] = superficie_ha
            if superficie_ha <= 0.25:
                cleaned_data["tipo_lote"] = "urbano"
            elif superficie_ha <= 2.0:
                cleaned_data["tipo_lote"] = "quinta"
            else:
                cleaned_data["tipo_lote"] = "agricola"
        return cleaned_data

class RelevamientoParte2Form(forms.ModelForm):
    """Parte 2 del wizard (modo Ocupante): condición de la vivienda,
    si el ocupante vive en el lote, y uso del lote. Al guardar esta parte
    se define la RUTA del wizard (ver continuar_encuesta en views.py)."""

    uso_lote_ocupante = forms.MultipleChoiceField(
        choices=USO_LOTE_OCUPANTE_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Relevamiento
        fields = [
            "condicion_vivienda", "vive_en_lote", "uso_lote_ocupante",
            "residencia_manzana", "residencia_lote", "encargado_residencia", "relacion_con_lote",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.SelectMultiple, forms.CharField)):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

        # Este wizard es siempre modo Ocupante: "Servicio" no corresponde acá.
        self.fields['condicion_vivienda'].choices = [
            choice for choice in self.fields['condicion_vivienda'].choices
            if choice[0] != 'servicio'
        ]

    def clean_uso_lote_ocupante(self):
        return list(self.cleaned_data.get("uso_lote_ocupante", []))

##################################
# MANEJO DE RELEVAMIENTO CONFLICTO
##################################    
class RelevamientoConflictoParte1Form(RelevamientoParte1Form):
    """Conflicto, Parte 1: solo identificación del lote. Hereda el cálculo
    frente x fondo → dimensiones/superficie/tipo de lote."""

    class Meta(RelevamientoParte1Form.Meta):
        fields = [
            "distrito",
            "manzana", "lote_indert",
            "frente_aprox", "fondo_aprox",
            "superficie_ha", "dimensiones", "tipo_lote",
        ]
        widgets = {
            "distrito": forms.Select(attrs={"class": "form-select"}),
            "dimensiones": forms.HiddenInput(),
            "superficie_ha": forms.HiddenInput(),
            "tipo_lote": forms.HiddenInput(),
        }

class PretendienteIdentificacionForm(forms.ModelForm):
    """Conflicto, pantalla de identificación de UN pretendiente: datos
    personales, relación con el ocupante actual y condición de vivienda.
    La producción y la vivienda se cargan en pantallas aparte (C3/C4)."""

    class Meta:
        model = Pretendiente
        fields = [
            "nombre_pretendiente", "ci_pretendiente",
            "sexo_pretendiente", "estado_civil_pretendiente", "telefono_pretendiente",
            "encargado_residencia", "condicion_vivienda", "vive_en_lote", 
            "residencia_manzana", "residencia_lote", "relacion_con_lote",
            "observaciones",
        ]
        labels = {
            "nombre_pretendiente": "Nombre y Apellido",
            "ci_pretendiente": "Cédula",
            "telefono_pretendiente": "Teléfono",
            "encargado_residencia": "Encargado del lote", 
            "relacion_con_lote": "Relación con el lote",
        }
        widgets = {"observaciones": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

        # "Servicio" no corresponde en Conflicto y la condición es obligatoria acá.
        cond = self.fields["condicion_vivienda"]
        cond.required = True
        cond.choices = [c for c in cond.choices if c[0] != "servicio"]

    def _validar_nombre_letras_enie(self, nombre, campo_nombre):
        if nombre:
            nombre = nombre.strip()
            if not re.match(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$', nombre):
                raise forms.ValidationError(f"El {campo_nombre} debe contener solo letras y Ñ.")
        return nombre.upper() if nombre else nombre

    def clean_nombre_pretendiente(self):
        data = self.cleaned_data.get("nombre_pretendiente")
        if data:
            data = data.strip()
        return self._validar_nombre_letras_enie(data, "nombre")

    def clean_ci_pretendiente(self):
        data = (self.cleaned_data.get("ci_pretendiente") or "").strip()
        if data and not data.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        if len(data) > 8:
            raise forms.ValidationError("La cédula no debe tener más de 8 dígitos.")
        return data

    def clean_telefono_pretendiente(self):
        data = self.cleaned_data.get('telefono_pretendiente')
        if data:
            data = data.strip()
            if not data.isdigit():
                raise forms.ValidationError("El teléfono debe contener solo números.")
            if len(data) > 10:
                raise forms.ValidationError("El teléfono no debe tener más de 10 dígitos.")
        return data

    def clean(self):
        cleaned = super().clean()
        condicion = cleaned.get("condicion_vivienda")
        if condicion == "presente":
            cleaned["vive_en_lote"] = True
        elif condicion in ("sin_vivienda", "en_construccion", "ausente", "desocupada"):
            cleaned["vive_en_lote"] = False
        if cleaned.get("vive_en_lote"):
            cleaned["residencia_manzana"] = ""
            cleaned["residencia_lote"] = ""
            cleaned["encargado_residencia"] = ""
            cleaned["relacion_con_lote"] = ""
        return cleaned

        
class RelevamientoCierreForm(forms.ModelForm):
    """Formulario unificado para el cierre de CUALQUIER tipo de relevamiento.
    Maneja el estado, la firma y las observaciones finales."""
    
    class Meta:
        model = Relevamiento
        fields = ["estado_entrevista", "firmo_solicitud", "observacion_encuesta", "firmo_solicitud"]
        widgets = {"observacion_encuesta": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()
                
        # Opcional: Si quieres que por defecto aparezca "en_conflicto" solo si es conflicto
        # (Si no, Django usará el valor por defecto del modelo).
        if self.instance and self.instance.tipo_registro == 'conflicto':
             if not self.initial.get("estado_entrevista"):
                 self.initial["estado_entrevista"] = "en_conflicto"

class RelevamientoServicioParte1Form(RelevamientoParte1Form):
    """Servicio, Parte 1: lote + responsable + uso del lote."""

    uso_lote_servicio = forms.MultipleChoiceField(
        choices=USO_LOTE_SERVICIO_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    """Servicio, Parte 2: mejoras + estado de la entrevista, firma y observaciones.
        El campo 'formulario' no se pide: lo asigna Relevamiento.save()."""
    
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta(RelevamientoParte1Form.Meta):
        model = Relevamiento
        fields = [
            "manzana", "lote_indert",
            "frente_aprox", "fondo_aprox",
            "superficie_ha", "dimensiones", "tipo_lote",
            "quien_es_el_ocupante", "cedula_ocupante", "telefono_ocupante",
            "uso_lote_servicio", "mejoras"
        ]
        
    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for field in self.fields.values():
                widget = field.widget
                existing = widget.attrs.get("class", "")
                if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                    widget.attrs["class"] = (existing + " form-check-input").strip()
                elif isinstance(widget, forms.Select):
                    widget.attrs["class"] = (existing + " form-select").strip()
                else:
                    widget.attrs["class"] = (existing + " form-control").strip()

    def _validar_nombre_letras_enie(self, nombre, campo_nombre):
            if nombre:
                nombre = nombre.strip()
                if not re.match(r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s]+$', nombre):
                    raise forms.ValidationError(f"El {campo_nombre} debe contener solo letras y Ñ.")
            return nombre.upper() if nombre else nombre
    
    def clean_quien_es_el_ocupante(self):
            data = self.cleaned_data.get('nombre_servicio')
            return self._validar_nombre_letras_enie(data, "nombre del servicio")
    
    def clean_uso_lote_servicio(self):
        return list(self.cleaned_data.get("uso_lote_servicio", []))

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

##################################
# MANEJO DE VIVIENDA
##################################

class ViviendaForm(forms.ModelForm):
    equipamientos = forms.MultipleChoiceField(
        choices=EQUIPAMIENTOS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Vivienda
        fields = [
            "es_principal",
            "paredes", "piso", "techo", "piezas",
            "agua_proviene", "tipo_bano", "equipamientos",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            elif isinstance(widget, forms.HiddenInput):
                pass
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

        if 'es_principal' in self.fields:
            existing = self.fields['es_principal'].widget.attrs.get('class', '')
            self.fields['es_principal'].widget.attrs['class'] = (existing + ' es-principal-checkbox').strip()

    def clean_equipamientos(self):
        return list(self.cleaned_data.get("equipamientos", []))

##################################
# MANEJO DE POBLACION
##################################

class MiembroForm(forms.ModelForm):
    class Meta:
        model = Miembro
        fields = [
            "nombre_miembro", "ci_miembro", "edad_miembro", "sexo_miembro", "estado_civil_miembro",
            "relacion_con_lote","escolaridad", "grado_ano",
            "vivienda", "pretendiente", "relevamiento",
        ]
        widgets = {
            "vivienda": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
            "relevamiento": forms.HiddenInput(),
            "relacion_con_lote": forms.Select(),
            "escolaridad": forms.Select(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select form-select-sm").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

    def clean_nombre_miembro(self):
        data = self.cleaned_data.get("nombre_miembro")
        if data:
            return data.strip().upper()
        return data

class InstitucionEnLoteForm(forms.ModelForm):
    class Meta:
        model = InstitucionEnLote
        fields = ["nombre_servicio", "ruc_servicio", "descripcion_servicio"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")
            widget.attrs["class"] = (existing + " form-control").strip()
            # Hacer que nombre_servicio sea opcional en formsets para permitir filas vacías
            if name == 'nombre_servicio':
                field.required = False

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre_servicio')
        ruc = cleaned_data.get('ruc_servicio')
        descripcion = cleaned_data.get('descripcion_servicio')

        # Si todos los campos están vacíos, marcar como permitido estar vacío
        if not nombre and not ruc and not descripcion:
            self.empty_permitted = True

        return cleaned_data

    def full_clean(self):
        # Validar solo los campos del formulario, sin validar las restricciones del modelo
        # El relevamiento_id se asignará después en la vista
        super().full_clean()
        # Limpiar errores relacionados con relevamiento_id/pretendiente_id si están vacíos
        if '__all__' in self.errors:
            self.errors['__all__'] = [
                e for e in self.errors['__all__']
                if 'asociada' not in str(e).lower()
            ]
            if not self.errors['__all__']:
                del self.errors['__all__']

class RelevamientoMejorasForm(forms.ModelForm):
    """Parte 3 del wizard: mejoras/infraestructura observadas en el lote.
    Es el único campo de Relevamiento que falta cubrir en esta etapa —
    Cultivos y Ganadería son modelos aparte, con sus propios formsets."""

    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Relevamiento
        fields = ["mejoras"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mejoras'].widget.attrs['class'] = 'form-check-input'

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

##################################
# MANEJO DE CULTIVOS
##################################
class CultivoForm(forms.ModelForm):
    tipo_cultivo = forms.ChoiceField(
        choices=[("", "Seleccione un tipo de cultivo")] + list(TIPO_CULTIVO_CHOICES), required=True,
    )

    class Meta:
        model = Cultivo
        fields = ["tipo_cultivo", "tipo_siembra", "hectareas", "relevamiento", "pretendiente"]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

##################################
# MANEJO DE GANADOS
##################################
class ProduccionGanaderaForm(forms.ModelForm):
    # Igual que con tipo_cultivo: agregamos la opción vacía explícitamente,
    # si no, el navegador selecciona la primera opción real por defecto.
    tipo_ganaderia = forms.ChoiceField(
        choices=[("", "Seleccione...")] + list(TIPO_GANADERIA_CHOICES), required=True,
    )

    class Meta:
        model = ProduccionGanadera
        fields = ["tipo_ganaderia", "cantidad", "relevamiento", "pretendiente"]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.HiddenInput):
                continue
            existing = widget.attrs.get("class", "")
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

class PretendienteMejorasForm(forms.ModelForm):
    """Conflicto: mejoras/infraestructura observadas en el lote de UN pretendiente.
    Los cultivos y la ganadería son formsets aparte."""

    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Pretendiente
        fields = ["mejoras"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["mejoras"].widget.attrs["class"] = "form-check-input"

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

class FotosRelevamientoForm(forms.Form):
    """Sube fotos de un relevamiento, agrupadas en 4 categorías.
    Cada campo acepta varios archivos y cleaned_data trae la lista completa."""

    # campo -> (tipo_foto del modelo, descripcion, slug para el nombre de archivo)
    CATEGORIAS = {
        'fotos_recibo':    ('otro',            'Recibo', 'recibo'),
        'fotos_vivienda':  ('vivienda_frente', '',       'vivienda'),
        'fotos_documento': ('documento',       '',       'ci'),
        'fotos_lote':      ('lote_general',    '',       'lote'),
    }

    fotos_recibo    = MultipleFileField(required=False, label='Fotos de Recibo')
    fotos_vivienda  = MultipleFileField(required=False, label='Fotos de Vivienda')
    fotos_documento = MultipleFileField(required=False, label='Fotos de Documento de Identidad')
    fotos_lote      = MultipleFileField(required=False, label='Fotos del Lote')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'accept': 'image/*',
                'capture': 'environment',
            })

    # ─────────────────────────────────────────────────────────────
    # GUARDADO
    # ─────────────────────────────────────────────────────────────
    def guardar(self, relevamiento, usuario):
        """Crea una FotoRelevamiento por archivo aplicando:
          - limpieza de manzana/lote_sirt
          - nombre: relevamiento_{manzana}_{lote_sirt}_{slug}_{indice}.{ext}
          - conversión a JPG optimizado (si es imagen)
          - índice continuo por categoría (no pisa archivos ya subidos)
        Devuelve la cantidad de archivos guardados.
        """
        manzana   = limpiar_nombre_carpeta(relevamiento.manzana   or 'sin_manzana')
        lote_sirt = limpiar_nombre_carpeta(relevamiento.lote_sirt or 'sin_lote')

        total = 0

        for campo, (tipo, descripcion, slug) in self.CATEGORIAS.items():
            archivos = self.cleaned_data.get(campo, [])
            if not archivos:
                continue

            # Continuar la numeración desde lo que ya existe en este relevamiento
            # para la misma categoría, así no pisamos archivos previos.
            ya_existentes = FotoRelevamiento.objects.filter(
                relevamiento=relevamiento,
                tipo_foto=tipo,
            ).count()
            indice = ya_existentes + 1

            for archivo in archivos:
                try:
                    ext = extension_segura(archivo.name, default='.jpg')
                    nombre_base = f"relev_{manzana}_{lote_sirt}_{slug}_{indice}"
                    content_file, nombre_archivo = self._preparar_archivo(archivo, nombre_base, ext)
                    foto = FotoRelevamiento(relevamiento=relevamiento, encuestador=usuario,
                                            tipo_foto=tipo, descripcion=descripcion)
                    foto.foto.save(nombre_archivo, content_file, save=True)

                    total += 1
                    indice += 1

                except Exception as e:
                    print(f"Error al procesar {archivo.name}: {e}")
                    continue

        return total

    # ─────────────────────────────────────────────────────────────
    # Helper: convierte a JPG optimizado o devuelve el original
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _preparar_archivo(archivo, nombre_base, ext):
        """Devuelve (ContentFile, nombre_final). Si convierte a JPEG, el nombre termina en .jpg."""
        if ext in ('.jpg', '.jpeg', '.png', '.gif'):
            try:
                img = Image.open(archivo)
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    mask = img.split()[-1] if img.mode in ('RGBA', 'LA') else None
                    rgb_img.paste(img, mask=mask)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                return ContentFile(buffer.getvalue()), f"{nombre_base}.jpg"
            except Exception:
                pass  
        archivo.seek(0)
        return ContentFile(archivo.read()), f"{nombre_base}{ext}"

