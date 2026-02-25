from django.contrib import admin
from .models import SolicitudRelevamiento, SolicitudRelevamientoAudit, Objetivo


@admin.register(SolicitudRelevamiento)
class SolicitudRelevamientoAdmin(admin.ModelAdmin):
    list_display = ['id', 'colonia', 'tipo', 'estado',
                    'grupo_asignado', 'usuario_asignado', 'fecha_creacion']
    list_filter = ['tipo', 'estado', 'grupo_asignado']
    search_fields = ['colonia__nombre', 'observaciones']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']


@admin.register(SolicitudRelevamientoAudit)
class SolicitudRelevamientoAuditAdmin(admin.ModelAdmin):
    list_display = ['solicitud', 'campo', 'valor_anterior_short',
                    'valor_nuevo_short', 'cambiado_por', 'fecha']
    list_filter = ['campo', 'cambiado_por', 'fecha']
    search_fields = ['solicitud__id', 'campo', 'valor_anterior', 'valor_nuevo']
    readonly_fields = ['solicitud', 'campo', 'valor_anterior',
                       'valor_nuevo', 'cambiado_por', 'fecha', 'comentario', 'ip_address']
    date_hierarchy = 'fecha'

    def valor_anterior_short(self, obj):
        if obj.valor_anterior and len(obj.valor_anterior) > 20:
            return f"{obj.valor_anterior[:20]}..."
        return obj.valor_anterior
    valor_anterior_short.short_description = "Valor Anterior"

    def valor_nuevo_short(self, obj):
        if obj.valor_nuevo and len(obj.valor_nuevo) > 20:
            return f"{obj.valor_nuevo[:20]}..."
        return obj.valor_nuevo
    valor_nuevo_short.short_description = "Valor Nuevo"


@admin.register(Objetivo)
class ObjetivoAdmin(admin.ModelAdmin):
    list_display = ['id', 'grupo', 'tipo_objetivo', 'anio', 'meta', 'avance_actual', 'porcentaje_avance', 'activo', 'creado_por']
    list_filter = ['grupo', 'tipo_objetivo', 'anio', 'activo']
    search_fields = ['descripcion']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion', 'porcentaje_avance']
    date_hierarchy = 'fecha_creacion'
    ordering = ['-anio', 'grupo', 'tipo_objetivo']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('grupo', 'tipo_objetivo', 'anio')
        }),
        ('Metas y Avance', {
            'fields': ('meta', 'avance_actual', 'porcentaje_avance')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'activo')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )
