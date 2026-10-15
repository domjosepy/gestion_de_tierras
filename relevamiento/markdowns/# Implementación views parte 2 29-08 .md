# Documento de Implementación para Formulario de Relevamiento

**Versión:** 1.1  
**Fecha:** 2026-08-29  
**Autor:** Equipo de Desarrollo

---
Manejo de viviendas adicionales y pretendientes en la vista
Para soportar el formulario dinámico donde el encuestador puede agregar múltiples viviendas (la principal y adicionales) y cada una con su propia lista de miembros, necesitamos una estrategia que combine formsets anidados con prefijos dinámicos.

A continuación desarrollo una solución completa para el modo Ocupante (sin pretendientes) y luego explico cómo adaptarla al modo Conflicto con pretendientes.

# 1. Enfoque general
El formulario principal RelevamientoForm guarda los datos del lote y del ocupante.

Un ViviendaFormSet gestiona todas las viviendas del relevamiento (principal y adicionales). La primera se marca como es_principal=True.

Para cada vivienda mostrada en el formset, se genera un sub-formset de miembros con un prefijo único: miembros_viv_0, miembros_viv_1, etc. El índice coincide con la posición de la vivienda en el formset.

En el template, mediante JavaScript, al agregar una nueva vivienda se crea también su bloque de miembros correspondiente con el prefijo correcto.

En la vista, después de validar el vivienda_formset, se itera sobre cada formulario de vivienda válido y se procesa el formset de miembros correspondiente, asignando la vivienda guardada.

# 2. Modificación de la vista de creación
```python
@login_required
@encuestador_required
def formulario_desde_orden(request, orden_id):
    orden = get_object_or_404(OrdenTrabajo, pk=orden_id)
    if not orden.formulario_habilitado:
        messages.warning(request, 'El formulario no está habilitado.')
        return redirect('relevamiento:encuestador_dashboard')
    
    datos_geo = _datos_geograficos_desde_orden(orden)
    initial = {
        'colonia': datos_geo['colonia'],
        'distrito': datos_geo['distrito'],
        'departamento': datos_geo['departamento'],
    }

    # Formsets
    ViviendaFormSet = inlineformset_factory(
        Relevamiento, Vivienda, form=ViviendaForm, extra=1, can_delete=True
    )
    # Miembros: se usa un formset por cada vivienda, se crea dinámicamente
    MiembroFormSet = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=1, can_delete=True
    )
    CultivoFormSet = inlineformset_factory(Relevamiento, Cultivo, form=CultivoForm, extra=1, can_delete=True)
    ProduccionGanaderaFormSet = inlineformset_factory(Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=1, can_delete=True)
    InstitucionFormSet = inlineformset_factory(Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=1, can_delete=True)
    PretendienteFormSet = inlineformset_factory(Relevamiento, Pretendiente, form=PretendienteForm, extra=0, can_delete=True)
    DocumentoFormSet = inlineformset_factory(Relevamiento, Documento, form=DocumentoForm, extra=0, can_delete=True)

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, initial=initial)
        vivienda_formset = ViviendaFormSet(request.POST, request.FILES, prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(request.POST, request.FILES, prefix='pretendientes')
        cultivo_formset = CultivoFormSet(request.POST, request.FILES, prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(request.POST, request.FILES, prefix='ganaderia')
        institucion_formset = InstitucionFormSet(request.POST, request.FILES, prefix='instituciones')
        documento_formset = DocumentoFormSet(request.POST, request.FILES, prefix='documentos')

        # Lista para guardar formsets de miembros por vivienda
        miembros_formsets = []

        if form.is_valid() and vivienda_formset.is_valid() and pretendiente_formset.is_valid() \
            and cultivo_formset.is_valid() and produccion_formset.is_valid() \
            and institucion_formset.is_valid() and documento_formset.is_valid():
            
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.distrito = datos_geo['distrito']
                    relevamiento.departamento = datos_geo['departamento']
                    relevamiento.orden_trabajo = orden
                    relevamiento.encuestador = request.user
                    relevamiento.save()
                    form.save_m2m()

                    # Guardar pretendientes (si los hay, en modo conflicto)
                    for pret_form in pretendiente_formset:
                        if pret_form.cleaned_data and not pret_form.cleaned_data.get('DELETE', False):
                            pretendiente = pret_form.save(commit=False)
                            pretendiente.relevamiento = relevamiento
                            pretendiente.save()
                            pret_form.save_m2m()
                            # Aquí podríamos manejar viviendas y miembros del pretendiente (similar, pero con otro prefijo)

                    # Guardar viviendas y sus miembros anidados
                    vivienda_index = 0
                    for viv_form in vivienda_formset:
                        if viv_form.cleaned_data and not viv_form.cleaned_data.get('DELETE', False):
                            vivienda = viv_form.save(commit=False)
                            vivienda.relevamiento = relevamiento
                            # Marcar la primera vivienda como principal
                            if vivienda_index == 0 and not vivienda.es_principal:
                                vivienda.es_principal = True
                            vivienda.save()
                            viv_form.save_m2m()

                            # Procesar miembros de esta vivienda usando prefijo dinámico
                            prefijo_miembros = f'miembros_viv_{vivienda_index}'
                            miembro_formset = MiembroFormSet(
                                request.POST, request.FILES,
                                instance=vivienda,
                                prefix=prefijo_miembros
                            )
                            if miembro_formset.is_valid():
                                miembro_formset.save()
                            else:
                                # Si hay errores, se registran
                                for mf in miembro_formset:
                                    for field, errors in mf.errors.items():
                                        for error in errors:
                                            messages.error(request, f"Error en miembro: {error}")
                            vivienda_index += 1

                    # Guardar cultivos, producción, instituciones, documentos
                    for cultivo_form in cultivo_formset:
                        if cultivo_form.cleaned_data and not cultivo_form.cleaned_data.get('DELETE', False):
                            cultivo = cultivo_form.save(commit=False)
                            cultivo.relevamiento = relevamiento
                            cultivo.save()
                    for prod_form in produccion_formset:
                        if prod_form.cleaned_data and not prod_form.cleaned_data.get('DELETE', False):
                            prod = prod_form.save(commit=False)
                            prod.relevamiento = relevamiento
                            prod.save()
                    for inst_form in institucion_formset:
                        if inst_form.cleaned_data and not inst_form.cleaned_data.get('DELETE', False):
                            inst = inst_form.save(commit=False)
                            inst.relevamiento = relevamiento
                            inst.save()
                    for doc_form in documento_formset:
                        if doc_form.cleaned_data and not doc_form.cleaned_data.get('DELETE', False):
                            doc = doc_form.save(commit=False)
                            doc.relevamiento = relevamiento
                            doc.save()

                messages.success(request, 'Relevamiento creado correctamente.')
                return redirect('relevamiento:resumen_relevamiento', pk=relevamiento.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            # Mostrar errores de formsets
            messages.error(request, 'Hay errores en el formulario. Revise los campos.')
    else:
        form = RelevamientoForm(initial=initial)
        vivienda_formset = ViviendaFormSet(prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(prefix='pretendientes')
        cultivo_formset = CultivoFormSet(prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(prefix='ganaderia')
        institucion_formset = InstitucionFormSet(prefix='instituciones')
        documento_formset = DocumentoFormSet(prefix='documentos')
        # Para el GET, creamos un formset de miembros vacío para la primera vivienda
        # (se puede manejar en el template, no es necesario aquí)

    context = {
        'form': form,
        'vivienda_formset': vivienda_formset,
        'pretendiente_formset': pretendiente_formset,
        'cultivo_formset': cultivo_formset,
        'produccion_formset': produccion_formset,
        'institucion_formset': institucion_formset,
        'documento_formset': documento_formset,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Nueva Encuesta — {orden}',
    }
    return render(request, 'includes/relevamiento/encuestador/formulario_relevamiento.html', context)
```
Nota: En este código, los formsets de miembros se crean después de guardar cada vivienda, usando el instance de esa vivienda. Esto evita la necesidad de manejar los prefijos en la validación principal. Sin embargo, en el template debemos asegurarnos de que los campos de miembros de cada vivienda tengan el prefijo correcto (miembros_viv_0, miembros_viv_1, etc.).

# 3. Estructura del template (fragmento relevante)
En el template, dentro del formulario, tendremos un contenedor para viviendas. Cada vivienda estará representada por un bloque con los campos de ViviendaForm y una tabla de miembros (generada a partir de un MiembroFormSet con el prefijo adecuado).

Usaremos JavaScript para clonar el bloque de vivienda y actualizar los prefijos de los campos.

Ejemplo simplificado de HTML/JS:

html
<div id="viviendas-container">
  {{ vivienda_formset.management_form }}
  {% for viv_form in vivienda_formset %}
    <div class="vivienda-block">
      <h4>Vivienda {{ forloop.counter }}</h4>
      {{ viv_form.as_p }}
      <!-- Miembros de esta vivienda -->
      <div class="miembros-container" data-index="{{ forloop.counter0 }}">
        <!-- Aquí se inyectará el formset de miembros con prefijo miembros_viv_{{ forloop.counter0 }} -->
        <div id="miembros_viv_{{ forloop.counter0 }}">
          <!-- En el GET, generamos un MiembroFormSet vacío con ese prefijo -->
          {% with miembro_formset=miembro_formsets|get_item:forloop.counter0 %}
            {{ miembro_formset.management_form }}
            {% for m_form in miembro_formset %}
              {{ m_form.as_p }}
            {% endfor %}
          {% endwith %}
        </div>
      </div>
    </div>
  {% endfor %}
</div>
<button type="button" id="add-vivienda">Agregar vivienda adicional</button>
JavaScript para agregar vivienda:

Al hacer clic en "Agregar vivienda", se clona el último bloque de vivienda, se actualizan los índices de todos los campos (atributos name y id) y se añade un nuevo bloque de miembros con prefijo incremental.

Este es un enfoque complejo pero manejable con jQuery o vanilla JS. Se pueden usar librerías como django-dynamic-formset (si estás en jQuery) o implementación manual.

# 4. Manejo de pretendientes
Para el modo Conflicto, cada pretendiente puede tener su propia vivienda y miembros. Podemos simplificar asumiendo que cada pretendiente tendrá una sola vivienda principal (la mayoría de los casos). Entonces:

El PretendienteFormSet se renderiza normalmente.

Por cada pretendiente, se incluye un bloque de vivienda (inline) y dentro un formset de miembros.

Usamos prefijos: pret_vivienda_0, pret_miembros_0, etc.

En la vista, después de guardar cada pretendiente, guardamos su vivienda y sus miembros.

Ejemplo de guardado de pretendiente con su vivienda:

``` python
pret_index = 0
for pret_form in pretendiente_formset:
    if pret_form.cleaned_data and not pret_form.cleaned_data.get('DELETE', False):
        pretendiente = pret_form.save(commit=False)
        pretendiente.relevamiento = relevamiento
        pretendiente.save()
        pret_form.save_m2m()

        # Guardar vivienda del pretendiente (prefijo pret_viv_<index>)
        # Se asume que en el template se incluyen los campos de ViviendaForm con ese prefijo.
        # Alternativamente, se puede usar un ViviendaFormSet con instance=pretendiente
        viv_prefijo = f'pret_viv_{pret_index}'
        vivienda_pret_formset = ViviendaFormSet(
            request.POST, request.FILES,
            instance=pretendiente,
            prefix=viv_prefijo
        )
        if vivienda_pret_formset.is_valid():
            vivienda_pret = vivienda_pret_formset.save()
            # Ahora guardar miembros de esa vivienda
            miembro_prefijo = f'pret_miembros_{pret_index}'
            miembro_pret_formset = MiembroFormSet(
                request.POST, request.FILES,
                instance=vivienda_pret[0] if vivienda_pret else None,
                prefix=miembro_prefijo
            )
            if miembro_pret_formset.is_valid():
                miembro_pret_formset.save()
    pret_index += 1
```
Nota: ViviendaFormSet es un inlineformset_factory con parent Relevamiento, pero también puede instanciarse con instance=pretendiente si se define un formset con parent Pretendiente. Es mejor definir un formset específico para pretendientes:

```python
ViviendaPretendienteFormSet = inlineformset_factory(
    Pretendiente, Vivienda, form=ViviendaForm, extra=1, can_delete=True
)
```
# 5. Conclusión
El manejo de viviendas adicionales y pretendientes requiere:

Formsets anidados con prefijos dinámicos.

JavaScript para clonar bloques y actualizar índices.

Procesamiento en la vista que itere sobre las viviendas y construya los formsets de miembros correspondientes usando los prefijos enviados.

Recomiendo implementar primero el modo Ocupante con múltiples viviendas y miembros, y luego extender al modo Conflicto con la misma lógica.