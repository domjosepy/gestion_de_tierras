Preparar Formulario de Relevamiento en 4 Templates
Objetivo
Dividir el actual formulario_relevamiento.html (que contiene todos los modos en un solo archivo con secciones ocultas mediante data-modes) en cuatro plantillas separadas:

ocupante_formulario_relevamiento.html

conflicto_formulario_relevamiento.html

servicio_formulario_relevamiento.html

fraccionamiento_formulario_relevamiento.html

Cada plantilla debe contener únicamente los campos y secciones relevantes para su modo, eliminando la necesidad de data-modes y el botón selector de modo. La vista principal (formulario_desde_orden y editar_encuesta_relevamiento) deberá detectar el modo (según un parámetro o el estado del relevamiento) y renderizar la plantilla correspondiente.

Requisitos técnicos
Framework: Django con Bootstrap 5.

Los formsets ya existentes (vivienda_formset, vivienda_miembro_formsets, pretendiente_formset, cultivo_formset, produccion_formset, institucion_formset, documento_formset) se mantienen.

El JavaScript compartido (manejo de formsets dinámicos, modal de cónyuge, etc.) debe estar en un archivo externo relevamiento_form_common.js para evitar duplicación.

Las plantillas deben heredar de base.html y cargar static, relevamiento_tags.

La variable datos_geo y orden siguen disponibles.

Cambios en las vistas
Detectar el modo:

En la vista formulario_desde_orden, añadir un parámetro modo (por defecto 'ocupante') que puede venir por URL (?modo=ocupante) o por POST.

En editar_encuesta_relevamiento, el modo se infiere del relevamiento existente:

Si relevamiento.pretendientes.exists() → 'conflicto'

Si relevamiento.uso_lote incluye 'institucion_organizacion' o condicion_vivienda == 'servicio' → 'servicio'

Si relevamiento.parent_lote no es nulo o se está creando un sub‑lote → 'fraccionamiento'

En caso contrario → 'ocupante'

Guardar el modo en un campo oculto tipo_relevamiento dentro de cada template (value fijo).

Renderizar el template correcto:

Mapear modo → template:

python
TEMPLATE_MAP = {
    'ocupante': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_ocupante.html',
    'conflicto': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_conflicto.html',
    'servicio': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_servicio.html',
    'fraccionamiento': 'includes/relevamiento/encuestador/formulario_relevamiento/formulario_fraccionamiento.html',
}
En la vista, después de preparar el contexto común, seleccionar el template y hacer render(request, template, context).

Contexto común (independiente del modo):

form, orden, datos_geo, vivienda_formset, vivienda_miembro_formsets, cultivo_formset, produccion_formset, institucion_formset, documento_formset, pretendiente_formset (solo para conflicto), pretendiente_vivienda_formsets y pretendiente_miembro_formsets (solo conflicto).

Estructura de cada plantilla
1. ocupante_formulario_relevamiento.html
Contiene:

Banner de orden (si existe).

Cabecera.

Sección 1: Datos Geográficos (bloqueados).

Sección 2: Datos del Ocupante (incluye botón cónyuge y campos de residencia).

Sección 3: Datos del Lote (sin parent_lote, con checkboxes de uso de lote).

Sección 4: Datos Productivos.

Sección 5: Mejoras e Infraestructura (solo mejoras, sin equipamientos).

Sección 6: Modificaciones Post‑titulación (si form.is_relevamiento).

Sección 7: Información de la Encuesta.

Sección Viviendas del Lote (con formsets anidados de miembros).

Sección Cultivos.

Sección Producción Ganadera.

Sección Instituciones en el Lote.

Sección Documentos Adjuntos.

Botones de acción.

Modal de cónyuge.

2. conflicto_formulario_relevamiento.html
Contiene:

Banner de orden.

Cabecera.

Sección 1: Datos Geográficos (bloqueados).

Sección 3: Datos del Lote (sin ocupante, solo datos del lote y uso).

Sección Pretendientes (formset de pretendientes, cada uno con su botón cónyuge, su vivienda y población anidada).

Sección Instituciones en el Lote.

Sección Documentos Adjuntos.

Sección Información de la Encuesta.

Botones de acción.

Modal de cónyuge.

No incluye las secciones de Ocupante, Datos Productivos, Mejoras, Cultivos, Ganadería porque en conflicto esos datos van por pretendiente (aunque se podrían agregar por pretendiente si se desea, se deja para más adelante).

3. servicio_formulario_relevamiento.html
Contiene:

Banner de orden.

Cabecera.

Sección 1: Datos Geográficos.

Sección 3: Datos del Lote (con uso_lote preseleccionado, sin campos de ocupante).

Sección Instituciones en el Lote (una o más instituciones).

Sección Documentos Adjuntos.

Sección Información de la Encuesta.

Botones de acción.

No incluye viviendas, población, cultivos, etc.

4. fraccionamiento_formulario_relevamiento.html
Es similar al de ocupante, pero incluye:

Sección Datos del Ocupante.

Sección Datos del Lote, con el campo parent_lote visible.

Sección Viviendas y población.

Sección Cultivos y Ganadería.

Sección Fraccionamiento (listado de sub‑lotes existentes si el relevamiento ya está guardado, y botón "Realizar Fraccionamiento" que crea un sub‑lote).

Sección Documentos, Instituciones, etc.

Además, si se está editando un sub‑lote, el campo parent_lote se muestra con el lote padre.

JavaScript común
Crear archivo relevamiento/js/relevamiento_form_common.js con las siguientes funciones:

addFlatForm(containerEl, emptyHtml, prefix)

markForDelete(blockEl)

Event listeners para .add-block-btn, .remove-block-btn, .remove-vivienda-btn

Manejo de .add-miembro-btn y .add-miembro-pret-btn

addViviendaAdicional()

addPretendiente()

guardarConyuge() (con lógica para detectar el target)

Inicialización de modal de cónyuge y campos de residencia.

En cada template, incluir al final:

django
{% block extra_js %}
<script src="{% static 'relevamiento/js/relevamiento_form_common.js' %}"></script>
{% endblock %}
Notas adicionales
El botón selector de modo desaparece de las plantillas; en su lugar, la vista decide qué plantilla mostrar.

El campo oculto tipo_relevamiento se mantiene en cada template con su valor fijo ('ocupante', 'conflicto', 'servicio', 'fraccionamiento').

Si el usuario quiere cambiar de modo en mitad de la carga, se puede añadir un enlace en cada template para volver a la vista con otro ?modo= (opcional).

Asegurarse de que las URLs de agregar_fotos y crear_sublote sigan funcionando.

Pasos para implementar
Crear los cuatro archivos en templates/includes/relevamiento/encuestador/.

Extraer las secciones correspondientes del template actual y pegarlas en cada archivo.

Crear relevamiento_form_common.js con el JavaScript compartido.

Modificar formulario_desde_orden y editar_encuesta_relevamiento en views.py para seleccionar el template según el modo.

Probar cada modo con datos de ejemplo.