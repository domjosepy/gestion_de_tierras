# Documento de Implementación para Formulario de Relevamiento

**Versión:** 1.1  
**Fecha:** 2026-08-7  
**Autor:** Equipo de Desarrollo

---
- Ahora es necesario adaptar las vistas para que puedan manejar correctamente la creación y edición de un Relevamiento con todos sus objetos relacionados (viviendas, miembros, cultivos, ganado, instituciones, pretendientes, documentos, fotos). Te propongo una reestructuración de las vistas principales:

## formulario_desde_orden (crear)

## editar_encuesta_relevamiento (editar)

## agregar_fotos (ahora adaptada al nuevo FotoRelevamientoForm)

- Además, incluiré un manejo de transacciones para asegurar la integridad de los datos al guardar varios formularios a la vez.

# 1. Vista para crear un relevamiento desde una orden
Debe:
- Inicializar RelevamientoForm con los datos geográficos precargados.

- Inicializar formsets para:
- ViviendaFormSet (viviendas asociadas al Relevamiento)
- MiembroFormSet (miembros asociados a cada vivienda)
- CultivoFormSet (cultivos del relevamiento)
- ProduccionGanaderaFormSet (producción ganadera)
- InstitucionEnLoteFormSet (instituciones en el lote)
- PretendienteFormSet (para modo conflicto; puede estar vacío)
- DocumentoFormSet (si se quieren adjuntar documentos en el mismo formulario, opcional)
- Como el formulario en el frontend es dinámico, los formsets se procesarán con prefix para identificar cada grupo.

## A continuación un ejemplo de implementación:

``` python
from django.forms import inlineformset_factory
from .forms import (
    RelevamientoForm, PretendienteForm, ViviendaForm, MiembroForm,
    CultivoForm, ProduccionGanaderaForm, InstitucionEnLoteForm, DocumentoForm
)
from .models import Relevamiento, Pretendiente, Vivienda, Miembro, Cultivo, ProduccionGanadera, InstitucionEnLote, Documento

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

    # Formsets para objetos relacionados
    ViviendaFormSet = inlineformset_factory(
        Relevamiento, Vivienda, form=ViviendaForm, extra=1, can_delete=True
    )
    MiembroFormSet = inlineformset_factory(
        Vivienda, Miembro, form=MiembroForm, extra=1, can_delete=True
    )
    CultivoFormSet = inlineformset_factory(
        Relevamiento, Cultivo, form=CultivoForm, extra=1, can_delete=True
    )
    ProduccionGanaderaFormSet = inlineformset_factory(
        Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=1, can_delete=True
    )
    InstitucionFormSet = inlineformset_factory(
        Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=1, can_delete=True
    )
    PretendienteFormSet = inlineformset_factory(
        Relevamiento, Pretendiente, form=PretendienteForm, extra=1, can_delete=True
    )
    DocumentoFormSet = inlineformset_factory(
        Relevamiento, Documento, form=DocumentoForm, extra=1, can_delete=True
    )

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, initial=initial)
        vivienda_formset = ViviendaFormSet(request.POST, request.FILES, prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(request.POST, request.FILES, prefix='pretendientes')
        cultivo_formset = CultivoFormSet(request.POST, request.FILES, prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(request.POST, request.FILES, prefix='ganaderia')
        institucion_formset = InstitucionFormSet(request.POST, request.FILES, prefix='instituciones')
        documento_formset = DocumentoFormSet(request.POST, request.FILES, prefix='documentos')
        # Miembros: se manejarán por cada vivienda, pero por simplicidad usamos un solo formset
        # asociado a la vivienda principal o a todas? 
        # Alternativa: usar un formset independiente con vivienda seleccionable en el template
        # pero eso es más complejo. Para empezar, podemos guardar los miembros después de guardar viviendas.
        # Lo dejamos como un formset global que luego asignamos a la vivienda principal.
        miembro_formset = MiembroFormSet(request.POST, request.FILES, prefix='miembros')

        if form.is_valid() and vivienda_formset.is_valid() and pretendiente_formset.is_valid() \
            and cultivo_formset.is_valid() and produccion_formset.is_valid() \
            and institucion_formset.is_valid() and documento_formset.is_valid() and miembro_formset.is_valid():
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

                    # Guardar pretendientes (si hay)
                    for pret_form in pretendiente_formset:
                        if pret_form.cleaned_data and not pret_form.cleaned_data.get('DELETE', False):
                            pretendiente = pret_form.save(commit=False)
                            pretendiente.relevamiento = relevamiento
                            pretendiente.save()
                            pret_form.save_m2m()

                    # Guardar viviendas (principal y adicionales)
                    # Aquí asumimos que la primera vivienda es la principal
                    vivienda_principal = None
                    for i, viv_form in enumerate(vivienda_formset):
                        if viv_form.cleaned_data and not viv_form.cleaned_data.get('DELETE', False):
                            vivienda = viv_form.save(commit=False)
                            vivienda.relevamiento = relevamiento
                            if i == 0 and not vivienda.es_principal:
                                vivienda.es_principal = True
                            vivienda.save()
                            viv_form.save_m2m()
                            if vivienda.es_principal:
                                vivienda_principal = vivienda

                    # Guardar miembros, asociándolos a la vivienda principal si existe
                    if vivienda_principal:
                        for miembro_form in miembro_formset:
                            if miembro_form.cleaned_data and not miembro_form.cleaned_data.get('DELETE', False):
                                miembro = miembro_form.save(commit=False)
                                miembro.vivienda = vivienda_principal
                                miembro.relevamiento = relevamiento
                                miembro.save()
                    else:
                        # Si no hay vivienda, guardamos miembros asociados solo al relevamiento
                        for miembro_form in miembro_formset:
                            if miembro_form.cleaned_data and not miembro_form.cleaned_data.get('DELETE', False):
                                miembro = miembro_form.save(commit=False)
                                miembro.relevamiento = relevamiento
                                miembro.save()

                    # Cultivos
                    for cultivo_form in cultivo_formset:
                        if cultivo_form.cleaned_data and not cultivo_form.cleaned_data.get('DELETE', False):
                            cultivo = cultivo_form.save(commit=False)
                            cultivo.relevamiento = relevamiento
                            cultivo.save()

                    # Producción ganadera
                    for prod_form in produccion_formset:
                        if prod_form.cleaned_data and not prod_form.cleaned_data.get('DELETE', False):
                            prod = prod_form.save(commit=False)
                            prod.relevamiento = relevamiento
                            prod.save()

                    # Instituciones
                    for inst_form in institucion_formset:
                        if inst_form.cleaned_data and not inst_form.cleaned_data.get('DELETE', False):
                            inst = inst_form.save(commit=False)
                            inst.relevamiento = relevamiento
                            inst.save()

                    # Documentos
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
            messages.error(request, 'Hay errores en el formulario. Revise los campos.')
    else:
        form = RelevamientoForm(initial=initial)
        vivienda_formset = ViviendaFormSet(prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(prefix='pretendientes')
        cultivo_formset = CultivoFormSet(prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(prefix='ganaderia')
        institucion_formset = InstitucionFormSet(prefix='instituciones')
        documento_formset = DocumentoFormSet(prefix='documentos')
        miembro_formset = MiembroFormSet(prefix='miembros')

    context = {
        'form': form,
        'vivienda_formset': vivienda_formset,
        'pretendiente_formset': pretendiente_formset,
        'cultivo_formset': cultivo_formset,
        'produccion_formset': produccion_formset,
        'institucion_formset': institucion_formset,
        'documento_formset': documento_formset,
        'miembro_formset': miembro_formset,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Nueva Encuesta — {orden}',
    }
    return render(request, 'includes/relevamiento/encuestador/formulario_relevamiento.html', context)
``` 
Nota: Este código asume que los formsets para Miembro usan Vivienda como parent, pero en realidad queremos asociar miembros a una vivienda específica. En el template, cada vivienda tendrá su propio sub-formset de miembros. Por simplicidad, en la vista solo guardamos los miembros de la vivienda principal. Para soportar miembros en viviendas adicionales, necesitaríamos anidar formsets, lo cual es más complejo. Una alternativa es usar JavaScript para crear múltiples formsets de miembros con prefijos dinámicos (ej. miembros_viv_0, miembros_viv_1) y procesarlos en la vista. Por ahora, se puede comenzar con la vivienda principal y luego extender.

# 2. Vista para editar un relevamiento

Debe seguir la misma lógica, pero cargando los formsets con la instancia existente.

```python
@login_required
@encuestador_required
def editar_encuesta_relevamiento(request, pk):
    rel = get_object_or_404(Relevamiento, pk=pk)
    orden = rel.orden_trabajo
    if not orden:
        messages.error(request, 'Este relevamiento no tiene orden asociada.')
        return redirect('relevamiento:encuestador_dashboard')
    datos_geo = _datos_geograficos_desde_orden(orden)

    # Verificar permisos (igual que antes)
    es_encuestador_asignado = rel.encuestador == request.user
    esta_en_equipo = orden.equipos_asignados.filter(encuestadores=request.user).exists()
    if not (es_encuestador_asignado or esta_en_equipo or request.user.is_superuser):
        messages.error(request, 'No tiene permisos para editar este relevamiento.')
        return redirect('relevamiento:encuestador_dashboard')

    ViviendaFormSet = inlineformset_factory(Relevamiento, Vivienda, form=ViviendaForm, extra=0, can_delete=True)
    MiembroFormSet = inlineformset_factory(Vivienda, Miembro, form=MiembroForm, extra=0, can_delete=True)
    CultivoFormSet = inlineformset_factory(Relevamiento, Cultivo, form=CultivoForm, extra=0, can_delete=True)
    ProduccionGanaderaFormSet = inlineformset_factory(Relevamiento, ProduccionGanadera, form=ProduccionGanaderaForm, extra=0, can_delete=True)
    InstitucionFormSet = inlineformset_factory(Relevamiento, InstitucionEnLote, form=InstitucionEnLoteForm, extra=0, can_delete=True)
    PretendienteFormSet = inlineformset_factory(Relevamiento, Pretendiente, form=PretendienteForm, extra=0, can_delete=True)
    DocumentoFormSet = inlineformset_factory(Relevamiento, Documento, form=DocumentoForm, extra=0, can_delete=True)

    if request.method == 'POST':
        form = RelevamientoForm(request.POST, request.FILES, instance=rel)
        vivienda_formset = ViviendaFormSet(request.POST, request.FILES, instance=rel, prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(request.POST, request.FILES, instance=rel, prefix='pretendientes')
        cultivo_formset = CultivoFormSet(request.POST, request.FILES, instance=rel, prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(request.POST, request.FILES, instance=rel, prefix='ganaderia')
        institucion_formset = InstitucionFormSet(request.POST, request.FILES, instance=rel, prefix='instituciones')
        documento_formset = DocumentoFormSet(request.POST, request.FILES, instance=rel, prefix='documentos')
        # Para miembros, usamos un approach: obtener la vivienda principal
        vivienda_principal = rel.viviendas.filter(es_principal=True).first()
        if vivienda_principal:
            miembro_formset = MiembroFormSet(request.POST, request.FILES, instance=vivienda_principal, prefix='miembros')
        else:
            # Si no hay vivienda principal, usamos un formset vacío
            miembro_formset = MiembroFormSet(request.POST, request.FILES, queryset=Miembro.objects.none(), prefix='miembros')

        if form.is_valid() and all(fs.is_valid() for fs in [vivienda_formset, pretendiente_formset, cultivo_formset, produccion_formset, institucion_formset, documento_formset, miembro_formset]):
            try:
                with transaction.atomic():
                    relevamiento = form.save(commit=False)
                    relevamiento.colonia = datos_geo['colonia']
                    relevamiento.distrito = datos_geo['distrito']
                    relevamiento.departamento = datos_geo['departamento']
                    relevamiento.orden_trabajo = orden
                    relevamiento.save()
                    form.save_m2m()

                    pretendiente_formset.save()
                    vivienda_formset.save()
                    cultivo_formset.save()
                    produccion_formset.save()
                    institucion_formset.save()
                    documento_formset.save()
                    miembro_formset.save()

                messages.success(request, 'Relevamiento actualizado correctamente.')
                return redirect('relevamiento:resumen_relevamiento', pk=relevamiento.pk)
            except Exception as e:
                messages.error(request, f'Error al guardar: {str(e)}')
        else:
            messages.error(request, 'Hay errores en el formulario.')
    else:
        form = RelevamientoForm(instance=rel)
        vivienda_formset = ViviendaFormSet(instance=rel, prefix='viviendas')
        pretendiente_formset = PretendienteFormSet(instance=rel, prefix='pretendientes')
        cultivo_formset = CultivoFormSet(instance=rel, prefix='cultivos')
        produccion_formset = ProduccionGanaderaFormSet(instance=rel, prefix='ganaderia')
        institucion_formset = InstitucionFormSet(instance=rel, prefix='instituciones')
        documento_formset = DocumentoFormSet(instance=rel, prefix='documentos')
        vivienda_principal = rel.viviendas.filter(es_principal=True).first()
        if vivienda_principal:
            miembro_formset = MiembroFormSet(instance=vivienda_principal, prefix='miembros')
        else:
            miembro_formset = MiembroFormSet(queryset=Miembro.objects.none(), prefix='miembros')

    context = {
        'form': form,
        'vivienda_formset': vivienda_formset,
        'pretendiente_formset': pretendiente_formset,
        'cultivo_formset': cultivo_formset,
        'produccion_formset': produccion_formset,
        'institucion_formset': institucion_formset,
        'documento_formset': documento_formset,
        'miembro_formset': miembro_formset,
        'relevamiento': rel,
        'orden': orden,
        'datos_geo': datos_geo,
        'title': f'Editar Relevamiento #{rel.pk}',
    }
    return render(request, 'includes/relevamiento/encuestador/formulario_relevamiento.html', context)
```

# 3. Actualización de agregar_fotos
La vista actual usa FotosRelevamientoForm con categorías. Ahora debes usar el nuevo FotoRelevamientoForm (ModelForm de FotoRelevamiento) que ya incluye el campo vivienda. Permite subir varias fotos a la vez, asociándolas a una vivienda específica o al relevamiento.

```python
@login_required
def agregar_fotos(request, pk):
    rel = get_object_or_404(Relevamiento, pk=pk)
    
    if request.method == 'POST':
        form = FotoRelevamientoForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Obtener la vivienda seleccionada (si se envía)
                    vivienda_id = request.POST.get('vivienda')
                    vivienda = None
                    if vivienda_id:
                        vivienda = get_object_or_404(Vivienda, pk=vivienda_id, relevamiento=rel)
                    
                    # Procesar múltiples archivos
                    fotos = request.FILES.getlist('foto')
                    for foto in fotos:
                        foto_obj = form.save(commit=False)
                        foto_obj.relevamiento = rel
                        foto_obj.vivienda = vivienda
                        foto_obj.encuestador = request.user
                        foto_obj.foto = foto
                        foto_obj.save()
                messages.success(request, f'Se subieron {len(fotos)} foto(s).')
            except Exception as e:
                messages.error(request, f'Error al subir fotos: {str(e)}')
            return redirect('relevamiento:resumen_relevamiento', pk=rel.pk)
    else:
        form = FotoRelevamientoForm()
    
    # Obtener viviendas del relevamiento para el selector
    viviendas = rel.viviendas.all()
    context = {
        'form': form,
        'relevamiento': rel,
        'viviendas': viviendas,
    }
    return render(request, 'relevamiento/agregar_fotos.html', context)
```
- Nota: El campo foto en FotoRelevamientoForm debe ser un FileField con widget que permita múltiples archivos (puedes adaptar el MultipleFileField que ya tenías). O simplemente usar el formulario para una foto y en el template agregar un input múltiple que envíe una lista. La vista anterior usa request.FILES.getlist('foto'), por lo que el campo debe llamarse foto y permitir múltiples archivos. Puedes reutilizar MultipleFileField para eso.
