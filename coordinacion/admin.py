from django.contrib import admin
from .models import EquipoRelevamiento, OrdenTrabajo, RegistroCampo, Monitoreo


@admin.register(EquipoRelevamiento)
class EquipoRelevamientoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'estado',
                    'coordinador_campo', 'activo', 'total_miembros')
    list_filter = ('tipo', 'estado', 'activo')
    search_fields = ('nombre', 'coordinador_campo__username',
                     'coordinador_campo__first_name')
    filter_horizontal = ('subcoordinadores', 'encuestadores', 'choferes')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'tipo', 'estado', 'activo')
        }),
        ('Liderazgo', {
            'fields': ('coordinador_campo', 'subcoordinadores')
        }),
        ('Miembros', {
            'fields': ('encuestadores', 'choferes', 'max_encuestadores')
        }),
        ('Recursos', {
            'fields': ('vehiculos', 'equipos')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'solicitud', 'estado', 'prioridad',
                    'coordinador_responsable', 'progreso', 'atrasada')
    list_filter = ('estado', 'prioridad', 'fecha_creacion')
    search_fields = ('numero_orden', 'solicitud__colonia__nombre',
                     'coordinador_responsable__username')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion',
                       'progreso', 'atrasada')

    fieldsets = (
        ('Información General', {
            'fields': ('solicitud', 'numero_orden', 'estado', 'prioridad')
        }),
        ('Asignaciones', {
            'fields': ('coordinador_responsable', 'equipos_asignados')
        }),
        ('Planificación', {
            'fields': ('fecha_inicio_planeada', 'fecha_fin_planeada',
                       'fecha_inicio_real', 'fecha_fin_real')
        }),
        ('Metas y Seguimiento', {
            'fields': ('meta_encuestas', 'encuestas_completadas', 'progreso')
        }),
        ('Información Adicional', {
            'fields': ('observaciones', 'instrucciones_especiales')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RegistroCampo)
class RegistroCampoAdmin(admin.ModelAdmin):
    list_display = ('orden_trabajo', 'equipo', 'tipo', 'fecha_registro',
                    'registrado_por', 'encuestas_completadas')
    list_filter = ('tipo', 'fecha_registro')
    search_fields = ('orden_trabajo__numero_orden', 'equipo__nombre',
                     'registrado_por__username')
    readonly_fields = ('fecha_creacion',)

    fieldsets = (
        ('Información Básica', {
            'fields': ('orden_trabajo', 'equipo', 'tipo', 'registrado_por')
        }),
        ('Ubicación', {
            'fields': ('latitud', 'longitud', 'ubicacion_texto')
        }),
        ('Actividades', {
            'fields': ('actividades_realizadas', 'encuestas_completadas',
                       'problemas_encontrados')
        }),
        ('Tiempos', {
            'fields': ('fecha_registro', 'hora_inicio', 'hora_fin')
        }),
        ('Multimedia', {
            'fields': ('fotos',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Monitoreo)
class MonitoreoAdmin(admin.ModelAdmin):
    list_display = ('equipo', 'estado_actual',
                    'timestamp', 'bateria_dispositivo')
    list_filter = ('timestamp', 'estado_actual')
    search_fields = ('equipo__nombre', 'estado_actual')
    readonly_fields = ('timestamp',)

    fieldsets = (
        ('Información Básica', {
            'fields': ('orden_trabajo', 'equipo', 'estado_actual')
        }),
        ('Ubicación', {
            'fields': ('latitud', 'longitud', 'precision')
        }),
        ('Estado del Dispositivo', {
            'fields': ('bateria_dispositivo', 'senal_celular')
        }),
        ('Tiempo', {
            'fields': ('timestamp',)
        }),
    )
