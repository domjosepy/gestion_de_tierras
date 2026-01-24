from django.contrib import admin
from .models import PrecatArchivo


@admin.register(PrecatArchivo)
class PrecatArchivoAdmin(admin.ModelAdmin):
    list_display = ('solicitud', 'tipo_archivo', 'get_nombre_archivo',
                    'get_tamanio_mb', 'subido_por', 'fecha_subida')
    list_filter = ('tipo_archivo', 'fecha_subida', 'solicitud__estado')
    search_fields = ('solicitud__colonia__nombre',
                     'solicitud__id', 'observaciones')
    readonly_fields = ('fecha_subida', 'fecha_modificacion', 'get_tamanio_mb')
    fieldsets = (
        ('Información General', {
            'fields': ('solicitud', 'tipo_archivo', 'subido_por')
        }),
        ('Archivo', {
            'fields': ('archivo', 'get_tamanio_mb', 'observaciones')
        }),
        ('Fechas', {
            'fields': ('fecha_subida', 'fecha_modificacion')
        }),
    )
