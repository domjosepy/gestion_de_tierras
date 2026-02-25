from django.contrib import admin
from .models import (
    Relevamiento,
    Documento,
    Cultivo,
    ProduccionGanadera,
    Vivienda,
    Miembro,
    ProblemaSalud,
    OcupanteAnterior,
    FotoRelevamiento,
    ArchivoSubcoordinador
)


@admin.register(Relevamiento)
class RelevamientoAdmin(admin.ModelAdmin):
    list_display = ['id', 'colonia', 'manzana', 'lote_indert', 'encuestador', 'orden_trabajo', 'creado_en']
    list_filter = ['estado_entrevista', 'tipo_lote', 'condicion_vivienda', 'creado_en']
    search_fields = ['colonia__nombre', 'lote_indert', 'manzana', 'encuestador__username']
    raw_id_fields = ['orden_trabajo', 'encuestador', 'departamento', 'distrito', 'colonia']
    date_hierarchy = 'creado_en'


@admin.register(FotoRelevamiento)
class FotoRelevamientoAdmin(admin.ModelAdmin):
    list_display = ['id', 'relevamiento', 'tipo_foto', 'encuestador', 'fecha_captura', 'preview_foto']
    list_filter = ['tipo_foto', 'fecha_captura', 'encuestador']
    search_fields = ['relevamiento__colonia__nombre', 'descripcion', 'encuestador__username']
    raw_id_fields = ['relevamiento', 'encuestador']
    date_hierarchy = 'fecha_captura'
    readonly_fields = ['fecha_captura', 'preview_foto']
    
    def preview_foto(self, obj):
        if obj.foto:
            return f'<img src="{obj.foto.url}" style="max-height: 50px; max-width: 100px;" />'
        return '-'
    preview_foto.short_description = 'Vista Previa'
    preview_foto.allow_tags = True


@admin.register(ArchivoSubcoordinador)
class ArchivoSubcoordinadorAdmin(admin.ModelAdmin):
    list_display = ['id', 'nombre_archivo', 'orden_trabajo', 'subido_por', 'fecha_subida']
    list_filter = ['fecha_subida']
    search_fields = ['nombre_archivo', 'orden_trabajo__colonia__nombre', 'subido_por__username']
    raw_id_fields = ['orden_trabajo', 'subido_por']
    date_hierarchy = 'fecha_subida'
    readonly_fields = ['fecha_subida']


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ['id', 'relevamiento', 'tipo', 'nombre_archivo']
    list_filter = ['tipo']
    search_fields = ['nombre_archivo', 'relevamiento__colonia__nombre']
    raw_id_fields = ['relevamiento']


class CultivoInline(admin.TabularInline):
    model = Cultivo
    extra = 1


class ProduccionGanaderaInline(admin.TabularInline):
    model = ProduccionGanadera
    extra = 1


class MiembroInline(admin.TabularInline):
    model = Miembro
    extra = 1


@admin.register(Vivienda)
class ViviendaAdmin(admin.ModelAdmin):
    list_display = ['id', 'relevamiento', 'paredes', 'piso', 'techo', 'piezas']
    list_filter = ['paredes', 'piso', 'techo', 'tipo_bano']
    raw_id_fields = ['relevamiento']


admin.site.register(Cultivo)
admin.site.register(ProduccionGanadera)
admin.site.register(Miembro)
admin.site.register(ProblemaSalud)
admin.site.register(OcupanteAnterior)
