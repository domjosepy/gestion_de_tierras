from django.contrib import admin
from .models import Departamento, Distrito, Colonia, Area, Objetivo, Solicitud, SolicitudAudit

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "codigo")
    search_fields = ("nombre", "codigo")

@admin.register(Distrito)
class DistritoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "departamento")
    list_filter = ("departamento",)
    search_fields = ("nombre",)

@admin.register(Colonia)
class ColoniaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "estado", "ver_distritos")
    list_filter = ("estado", "distritos__departamento")
    search_fields = ("nombre",)
    filter_horizontal = ("distritos",)

    def ver_distritos(self, obj):
        return ", ".join([str(d) for d in obj.distritos.all()])
    ver_distritos.short_description = "Distritos"

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)

@admin.register(Objetivo)
class ObjetivoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "area")
    list_filter = ("area",)
    search_fields = ("nombre",)

@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("id", "colonia", "tipo", "estado", "creado_por", "fecha_creacion")
    list_filter = ("estado", "tipo")
    search_fields = ("colonia__nombre", "creado_por__username")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

@admin.register(SolicitudAudit)
class SolicitudAuditAdmin(admin.ModelAdmin):
    list_display = ("solicitud", "previo", "nuevo", "cambiado_por", "fecha")
    readonly_fields = ("solicitud", "previo", "nuevo", "cambiado_por", "fecha", "comentario")
    
