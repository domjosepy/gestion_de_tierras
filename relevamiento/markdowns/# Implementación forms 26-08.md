# Documento de Implementación para Formulario de Relevamiento

**Versión:** 1.1  
**Fecha:** 2026-08-26  
**Autor:** Equipo de Desarrollo

---
- Es necesario actualizar forms.py para mantener coherencia con los nuevos modelos y poder construir los templates dinámicos que requiere el formulario.

- A continuación te propongo una estructura de formularios basada en los cambios que ya implementaste en models.py. La idea es dividir los formularios por entidad y usar formsets para manejar la creación múltiple (p. ej., varios pretendientes, varias viviendas, varios miembros, etc.).

# 1. Formulario principal: `RelevamientoForm`
Debe actualizarse para:

- Incluir el nuevo campo parent_lote (para fraccionamiento).

- Asegurar que condicion_vivienda incluya la opción "en_construccion".

- Quitar campos que ahora pertenecen a modelos relacionados (como equipamientos que ya está en Vivienda). Si se mantienen por conveniencia, deben mapearse correctamente.

- Ejemplo de actualización:
```python
class RelevamientoForm(forms.ModelForm):
    uso_lote = forms.MultipleChoiceField(
        choices=USO_LOTE_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )
    modificaciones_post = forms.MultipleChoiceField(
        choices=MOD_POST_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Relevamiento
        fields = [
            "departamento", "distrito", "colonia",
            "manzana", "lote_indert", "lote_sirt", "formulario",
            "observacion_encuesta", "uso_lote", "nro_titulo",
            "tipo_lote", "condicion_vivienda", "condicion_encuestado",
            "superficie_ha", "dimensiones", "vive_en_lote",
            "residencia_manzana", "residencia_lote",
            "quien_es_el_ocupante", "cedula_ocupante", "sexo_ocupante",
            "parentesco", "produccion_agricola_ha",
            "produccion_ganadera_ha", "reforestado_ha",
            "bosque_natural_ha", "barbecho_ha", "mejoras",
            "estado_entrevista", "firmo_solicitud",
            "modificaciones_post", "parent_lote",  # <-- nuevo
        ]
``` 
- Nota: equipamientos se elimina de aquí porque ahora pertenece a Vivienda. Si por alguna razón lo necesitas en Relevamiento, habría que mantenerlo en el modelo, pero la recomendación es que viva solo en Vivienda.

# 2. Formularios para modelos `nuevos/modificados`
`PretendienteForm`
```python
class PretendienteForm(forms.ModelForm):
    mejoras = forms.MultipleChoiceField(
        choices=MEJORAS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Pretendiente
        fields = [
            "nombre", "ci", "sexo", "estado_civil",
            "condicion_vivienda", "vive_en_lote",
            "residencia_manzana", "residencia_lote",
            "quien_es_el_ocupante", "parentesco",
            "produccion_agricola_ha", "produccion_ganadera_ha",
            "reforestado_ha", "bosque_natural_ha", "barbecho_ha",
            "mejoras", "observaciones",
        ]
```
`ViviendaForm`
- Ahora debe permitir asociarse a Relevamiento o Pretendiente y llevar es_principal y numero.

``` python
class ViviendaForm(forms.ModelForm):
    equipamientos = forms.MultipleChoiceField(
        choices=EQUIPAMIENTOS_CHOICES, required=False, widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Vivienda
        fields = [
            "relevamiento", "pretendiente", "es_principal", "numero",
            "paredes", "piso", "techo", "piezas",
            "agua_proviene", "tipo_bano", "equipamientos",
        ]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }
```
`MiembroForm`
``` python
class MiembroForm(forms.ModelForm):
    class Meta:
        model = Miembro
        fields = [
            "nombre", "ci", "edad", "sexo",
            "parentesco", "relacion_con_lote",
            "escolaridad", "grado_ano",
            "vivienda", "pretendiente", "relevamiento",  # solo si quieres exponerlos
        ]
        widgets = {
            "vivienda": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
            "relevamiento": forms.HiddenInput(),
        }
```
## `CultivoForm` (con selección)
```python
CULTIVOS_CHOICES = [
    ("maiz_tupi", "Maíz Tupí"),
    ("maiz_chipa", "Maíz Chipá"),
    ("mandioca", "Mandioca"),
    # ... completa con la lista acordada
]

class CultivoForm(forms.ModelForm):
    tipo_cultivo = forms.ChoiceField(choices=CULTIVOS_CHOICES, required=True)

    class Meta:
        model = Cultivo
        fields = ["tipo_cultivo", "tipo_siembra", "hectareas", "relevamiento", "pretendiente"]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }
``` 
## `ProduccionGanaderaForm`
```python
GANADO_CHOICES = [
    ("bovinos", "Bovinos (vacas, toros)"),
    ("porcinos", "Porcinos (cerdos)"),
    ("aves", "Aves (pollos, gallinas)"),
    # ... agregar faltantes
]

class ProduccionGanaderaForm(forms.ModelForm):
    tipo_ganado = forms.ChoiceField(choices=GANADO_CHOICES, required=True)

    class Meta:
        model = ProduccionGanadera
        fields = ["tipo_ganado", "cantidad", "relevamiento", "pretendiente"]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }
```
## `InstitucionEnLoteForm`
``` python
class InstitucionEnLoteForm(forms.ModelForm):
    class Meta:
        model = InstitucionEnLote
        fields = ["nombre", "ruc", "descripcion", "relevamiento", "pretendiente"]
        widgets = {
            "relevamiento": forms.HiddenInput(),
            "pretendiente": forms.HiddenInput(),
        }
```
## `DocumentoForm` (si lo usas en formularios)
Similar a los anteriores, incluyendo pretendiente como HiddenInput.

# 3. Formsets recomendados
- Para manejar colecciones dinámicas:
- PretendienteFormSet → inlineformset_factory(Relevamiento, Pretendiente, form=PretendienteForm, extra=1, can_delete=True)

- ViviendaFormSet → inlineformset_factory(Relevamiento, Vivienda, form=ViviendaForm, extra=1, can_delete=True) (también se puede hacer para Pretendiente)

-MiembroFormSet → inlineformset_factory(Vivienda, Miembro, form=MiembroForm, extra=1, can_delete=True)

- CultivoFormSet → inlineformset_factory(Relevamiento, Cultivo, form=CultivoForm, extra=1, can_delete=True)

- ProduccionGanaderaFormSet → similar

- InstitucionEnLoteFormSet → similar

- Estos formsets permitirán agregar/quitar filas desde el frontend (con JavaScript) y procesarlos en la vista.

# 4. Ajustes en el formulario de fotos
- FotosRelevamientoForm puede mantenerse, pero si las fotos van asociadas a una vivienda específica, conviene crear un formulario para FotoRelevamiento:

``` python
class FotoRelevamientoForm(forms.ModelForm):
    class Meta:
        model = FotoRelevamiento
        fields = ["foto", "tipo_foto", "descripcion", "vivienda", "relevamiento"]
        widgets = {
            "vivienda": forms.HiddenInput(),
            "relevamiento": forms.HiddenInput(),
        }
```
# 5. Estrategia general
- Vista principal que maneje la creación/edición del Relevamiento.

- Dependiendo del modo (obtenido por URL o parámetro), se renderizan los formsets correspondientes.

- El frontend enviará los datos de forma anidada (p. ej., pretendientes, viviendas, miembros, cultivos, etc.).

- En la vista, se procesan los formsets y se asocian los ForeignKey automáticamente.