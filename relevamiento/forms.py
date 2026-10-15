import io
import os

from django.core.files.base import ContentFile
from PIL import Image

from .utils import limpiar_nombre_carpeta, extension_segura

from django import forms
from django.forms import inlineformset_factory

from .models import (
    EQUIPAMIENTOS_CHOICES, MODIFICACIONES_POSTADJUDICACION_CHOICES, TIPO_GANADERIA_CHOICES, USO_LOTE_OCUPANTE_CHOICES, MEJORAS_CHOICES,
    TIPO_CULTIVO_CHOICES, TIPO_GANADERIA_CHOICES, USO_LOTE_SERVICIO_CHOICES,
    Relevamiento, Pretendiente, Vivienda, Miembro,
    Cultivo, ProduccionGanadera, InstitucionEnLote, Documento, FotoRelevamiento,
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
    

class RelevamientoParte1Form(forms.ModelForm):
    """Parte 1 del wizard (modo Ocupante): datos geográficos básicos +
    identificación del ocupante. Es un subconjunto deliberadamente chico
    de los campos de Relevamiento — cada parte del wizard va a tener su
    propio ModelForm acotado así, en vez de reutilizar el RelevamientoForm
    gigante de una sola vez."""

    class Meta:
        model = Relevamiento
        fields = [
            "manzana", "lote_indert",
            "frente_aprox", "fondo_aprox",
            "superficie_ha", "dimensiones", "tipo_lote",
            "quien_es_el_ocupante", "cedula_ocupante", "sexo_ocupante", "estado_civil_ocupante",
            "quien_es_el_conyuge", "cedula_conyuge", "sexo_conyuge", "estado_civil_conyuge",
        ]
        widgets = {
            "dimensiones": forms.HiddenInput(),
            "superficie_ha": forms.HiddenInput(),
            "tipo_lote": forms.HiddenInput(),
            # Los 4 de Cónyuge no se muestran directamente en pantalla — se
            # editan a través del modal, pero SÍ necesitan viajar en el POST
            # para que el Relevamiento guarde esos datos. Por eso van ocultos,
            # no sacados del formulario.
            "quien_es_el_conyuge": forms.HiddenInput(),
            "cedula_conyuge": forms.HiddenInput(),
            "sexo_conyuge": forms.HiddenInput(),
            "estado_civil_conyuge": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    # Validación del nombre y CI del Ocupante
    def clean_quien_es_el_ocupante(self):
        data = self.cleaned_data.get('quien_es_el_ocupante')
        if data:
            data = data.strip().upper()
            if not data.replace(" ", "").isalpha():
                raise forms.ValidationError("El nombre del ocupante debe contener solo letras.")
        return data

    def clean_cedula_ocupante(self):
        data = self.cleaned_data.get('cedula_ocupante')
        if data and not data.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        if data and len(data) > 8:
            raise forms.ValidationError("La cédula no debe tener más de 8 dígitos.")
        return data


    def clean_quien_es_el_conyuge(self):
        data = self.cleaned_data.get('quien_es_el_conyuge')
        if data:
            data = data.strip().upper()
            if not data.replace(" ", "").isalpha():
                raise forms.ValidationError("El nombre del cónyuge debe contener solo letras.")
        return data

    def clean_cedula_conyuge(self):
        data = self.cleaned_data.get('cedula_conyuge')
        if data and not data.isdigit():
            raise forms.ValidationError("La cédula del cónyuge debe contener solo números.")
        if data and len(data) > 8:
            raise forms.ValidationError("La cédula del cónyuge no debe tener más de 8 dígitos.")
        return data


    def clean(self):
        # Mismo cálculo frente x fondo → dimensiones/superficie/tipo_lote
        # que ya tenías en RelevamientoForm.clean() — duplicado acá a
        # propósito porque cada parte del wizard es un form independiente.
        # Si en algún momento molesta la duplicación, se puede sacar a una
        # función compartida (ej. en un archivo utils.py), pero no es urgente ahora.
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
            "residencia_manzana", "residencia_lote", "encargado_residencia", "parentesco",
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
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

        # Este wizard es siempre modo Ocupante: "Servicio" no corresponde acá.
        self.fields['condicion_vivienda'].choices = [
            choice for choice in self.fields['condicion_vivienda'].choices
            if choice[0] != 'servicio'
        ]

    def clean_uso_lote_ocupante(self):
        return list(self.cleaned_data.get("uso_lote_ocupante", []))

    def clean(self):
        cleaned_data = super().clean()
        condicion = cleaned_data.get("condicion_vivienda")
        if condicion == "presente":
            cleaned_data["vive_en_lote"] = True
        elif condicion in ("sin_vivienda", "en_construccion", "ausente", "desocupada"):
            cleaned_data["vive_en_lote"] = False
        return cleaned_data
    
 # si afecta eliminar esta parte   

    
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
# MANEJO DE INSTITUCION/SERVICIOS
##################################
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


class RelevamientoForm(forms.ModelForm):
    """Form for creating/editing a `Relevamiento`.

    Maps ArrayFields to MultipleChoiceFields for user-friendly input.
    """

    uso_lote_ocupante = forms.MultipleChoiceField(
        choices=USO_LOTE_OCUPANTE_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    uso_lote_servicio = forms.MultipleChoiceField(
            choices=USO_LOTE_SERVICIO_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    modificaciones_post = forms.MultipleChoiceField(
        choices=MODIFICACIONES_POSTADJUDICACION_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Relevamiento
        fields = [
            "departamento", "distrito", "colonia",
            "manzana", "lote_indert", "lote_sirt", "formulario",
            "frente_aprox", "fondo_aprox", "superficie_ha", "dimensiones", "tipo_lote",
            "observacion_encuesta",
            "tipo_registro",
            "quien_es_el_ocupante", "cedula_ocupante", "sexo_ocupante", "estado_civil_ocupante",
            "quien_es_el_conyuge", "cedula_conyuge", "sexo_conyuge", "estado_civil_conyuge",
            "condicion_vivienda", "condicion_encuestado",
            "vive_en_lote", "uso_lote_ocupante", "uso_lote_servicio", "parent_lote",
            "residencia_manzana", "residencia_lote", "encargado_residencia", "parentesco",
            "produccion_agricola_ha","produccion_ganadera_ha",
            "reforestado_ha", "bosque_natural_ha", "barbecho_ha", "mejoras",
            "estado_entrevista",
            "firmo_solicitud",
            "modificaciones_post",
        ]
        widgets = {
            "dimensiones": forms.HiddenInput(),
            "superficie_ha": forms.HiddenInput(),
            "tipo_lote": forms.HiddenInput(),
        }

    #MANEJO DE DATOS PERSONALES DEL OCUPANTE Y CONYUGE

    def __init__(self, *args, **kwargs):
        modo = kwargs.pop('modo', None)
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
            # Apply Bootstrap classes to widgets depending on type (second pass)
            if isinstance(widget, forms.HiddenInput):
                pass
            # Second pass to ensure correct Bootstrap classes are applied
            elif isinstance(widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = (existing + " form-control").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

            # Si el relevamiento es modo "ocupante", la opción "Servicio" de
            # condicion_vivienda no tiene sentido (esa opción es solo para el
            # modo servicio). La sacamos de las choices para que ni aparezca
            # en el <select> ni se pueda mandar por POST.
            if modo == 'ocupante':
                self.fields['condicion_encuestado'].choices = [
                    choice for choice in self.fields['condicion_encuestado'].choices
                    if choice[0] == 'ocupante'
                ]
                self.fields['condicion_vivienda'].choices = [
                    choice for choice in self.fields['condicion_vivienda'].choices
                    if choice[0] != 'servicio'
                ]
            elif modo == 'servicio':
                self.fields['condicion_vivienda'].choices = [
                    choice for choice in self.fields['condicion_vivienda'].choices
                    if choice[0] == 'servicio'
                ]

        # --- si la instancia ya es servicio, deshabilitar condicion_vivienda ---
        if self.instance and self.instance.pk and self.instance.tipo_registro == "servicio":
            self.fields['condicion_vivienda'].disabled = True
            self.fields['condicion_vivienda'].help_text = "Condición establecida automáticamente por tipo 'Servicio'."
            # self.fields['condicion_vivienda'].initial = "servicio"
    
    def clean_quien_es_el_ocupante(self):
        data = self.cleaned_data.get('quien_es_el_ocupante')
        # Limpiar espacios en blanco al inicio y al final del nombre del ocupante.
        if data:
            data = data.strip()
        if data and not data.replace(" ", "").isalpha():
            raise forms.ValidationError("El nombre del ocupante debe contener solo letras.")
        if data and not data:
            raise forms.ValidationError("Este campo no puede estar vacío.")
        return data

    def clean_cedula_ocupante(self):
        data = self.cleaned_data.get('cedula_ocupante')
        if data and not data.isdigit():
            raise forms.ValidationError("La cédula debe contener solo números.")
        if data and len(data) > 8:
            raise forms.ValidationError("La cédula no debe tener más de 8 dígitos.")
        return data

    def clean_nombre_conyuge(self):
        data = self.cleaned_data.get('nombre_conyuge')
        # Limpiar espacios en blanco al inicio y al final del nombre del cónyuge.
        if data:
            data = data.strip()
        if data and not data.replace(" ", "").isalpha():
            raise forms.ValidationError("El nombre del cónyuge debe contener solo letras.")
        if data and not data:
            raise forms.ValidationError("Este campo no puede estar vacío.")
        return data

    def clean_cedula_conyuge(self):
        data = self.cleaned_data.get('cedula_conyuge')
        if data and not data.isdigit():
            raise forms.ValidationError("La cédula del cónyuge debe contener solo números.")
        if data and len(data) > 8:
            raise forms.ValidationError("La cédula del cónyuge no debe tener más de 8 dígitos.")
        return data

    def clean_uso_lote_ocupante(self):
        # si condicion_encuestado == "ocupante" y tipo_registro == "servicio", uso_lote debe estar vacío
        # entonces uso de lote solo muestra opciones relevantes 
        condicion_encuestado = self.cleaned_data.get("condicion_encuestado")
        tipo_registro = self.cleaned_data.get("tipo_registro")
        if condicion_encuestado == "ocupante":
            return []
        
        return list(self.cleaned_data.get("uso_lote_ocupante", []))

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

    def clean_modificaciones_post(self):
        return list(self.cleaned_data.get("modificaciones_post", []))

    def clean(self):
        cleaned_data = super().clean()
        # Regla existente: condicion_vivienda == presente -> vive_en_lote = True
        if cleaned_data.get("condicion_vivienda") == "presente":
            cleaned_data["vive_en_lote"] = True

        if cleaned_data.get("condicion_vivienda") == "sin vivienda":
            cleaned_data["vive_en_lote"] = False

        # --- NUEVA REGLA: tipo_registro == servicio -> condicion_vivienda = servicio ---
        if cleaned_data.get("tipo_registro") == "servicio":
            cleaned_data["condicion_vivienda"] = "servicio"

        # ── Dimensión del lote (frente x fondo) ──────────────────────────────
        # Se recalcula siempre acá, ignorando lo que haya en los campos ocultos
        # dimensiones/superficie_ha/tipo_lote del POST — esos son solo para la
        # vista previa instantánea en el navegador (ver JS). La fuente de verdad
        # es frente_aprox/fondo_aprox.
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
                    nombre_archivo = (
                        f"relevamiento_{manzana}_{lote_sirt}_{slug}_{indice}{ext}"
                    )

                    content_file = self._preparar_archivo(archivo, nombre_archivo, ext)

                    foto = FotoRelevamiento(
                        relevamiento=relevamiento,
                        encuestador=usuario,
                        tipo_foto=tipo,
                        descripcion=descripcion,
                    )
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
    def _preparar_archivo(archivo, nombre_archivo, ext):
        if ext in ('.jpg', '.jpeg', '.png', '.gif'):
            try:
                img = Image.open(archivo)

                # Aplanar transparencia sobre fondo blanco
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
                buffer.seek(0)
                return ContentFile(buffer.read(), name=nombre_archivo)

            except Exception as img_error:
                print(f"Error al procesar imagen {archivo.name}: {img_error}")
                archivo.seek(0)
                return ContentFile(archivo.read(), name=nombre_archivo)

        # Otros tipos (pdf, etc.): tal cual
        archivo.seek(0)
        return ContentFile(archivo.read(), name=nombre_archivo)
    

# ─────────────────────────────────────────────
# NUEVOS FORMULARIOS (modelos implementados 26-08)
# ─────────────────────────────────────────────

class PretendienteForm(forms.ModelForm):
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Pretendiente
        fields = [
            "nombre_pretendiente", "ci_pretendiente", "sexo_pretendiente", "estado_civil_pretendiente",
            "condicion_vivienda", "vive_en_lote",
            "residencia_manzana", "residencia_lote",
            "quien_es_el_ocupante", "parentesco",
            "produccion_agricola_ha", "produccion_ganadera_ha",
            "reforestado_ha", "bosque_natural_ha", "barbecho_ha",
            "mejoras", "observaciones",
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
            else:
                widget.attrs["class"] = (existing + " form-control").strip()

    def clean_mejoras(self):
        return list(self.cleaned_data.get("mejoras", []))

    def clean(self):
        cleaned_data = super().clean()
        # Regla automática: condicion_vivienda == presente fuerza vive_en_lote = True
        if cleaned_data.get("condicion_vivienda") == "presente":
            cleaned_data["vive_en_lote"] = True
        # Regla automática: condicion_vivienda == sin_vivienda o ausente fuerza vive_en_lote = false
        if cleaned_data.get("condicion_vivienda") in ["sin_vivienda", "ausente", "servicio", "en_construccion"]:
            cleaned_data["vive_en_lote"] = False
       
        return cleaned_data


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["relevamiento", "tipo", "archivo", "nombre_archivo", "pretendiente"]
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
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = (existing + " form-control").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()


# ─────────────────────────────────────────────
# FORMSETS
# ─────────────────────────────────────────────

PretendienteFormSet = inlineformset_factory(
    Relevamiento, Pretendiente, form=PretendienteForm, extra=0, can_delete=True
)

# Viviendas asociadas a un Relevamiento (modo ocupante/fraccionamiento)
ViviendaFormSet = inlineformset_factory(
    Relevamiento, Vivienda, form=ViviendaForm, extra=0, can_delete=True,
    fk_name='relevamiento'
)

# Viviendas asociadas a un Pretendiente (modo conflicto)
ViviendaPretendienteFormSet = inlineformset_factory(
    Pretendiente, Vivienda, form=ViviendaForm, extra=0, can_delete=True,
    fk_name='pretendiente'
)

MiembroFormSet = inlineformset_factory(
    Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True,
    fk_name='vivienda'
)
PrincipalesFormSet = inlineformset_factory(
    Relevamiento, Miembro, form=MiembroForm, extra=0, can_delete=True, 
    fk_name='relevamiento'
)

CultivoFormSet = inlineformset_factory(
    Relevamiento, Cultivo, form=CultivoForm, can_delete=True,
    fk_name='relevamiento'
)

CultivoPretendienteFormSet = inlineformset_factory(
    Pretendiente, Cultivo, form=CultivoForm, extra=0, can_delete=True,
    fk_name='pretendiente'
)

ProduccionGanaderaFormSet = inlineformset_factory(
    Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True,
    fk_name='relevamiento'
)

ProduccionGanaderaPretendienteFormSet = inlineformset_factory(
    Pretendiente, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True,
    fk_name='pretendiente'
)

InstitucionEnLoteFormSet = inlineformset_factory(
    Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=0, can_delete=True,
    fk_name='relevamiento'
)
