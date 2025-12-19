from django.contrib import admin
from .models import SolicitudRelevamiento, SolicitudRelevamientoAudit

@admin.register(SolicitudRelevamiento)
class SolicitudRelevamientoAdmin(admin.ModelAdmin):
    list_display = ("id", "colonia", "tipo", "estado", "creado_por", "fecha_creacion")
    list_filter = ("estado", "tipo")
    search_fields = ("colonia__nombre", "creado_por__username")
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

@admin.register(SolicitudRelevamientoAudit)
class SolicitudRelevamientoAuditAdmin(admin.ModelAdmin):
    list_display = ("solicitud", "previo", "nuevo", "cambiado_por", "fecha")
    readonly_fields = ("solicitud", "previo", "nuevo", "cambiado_por", "fecha", "comentario")
