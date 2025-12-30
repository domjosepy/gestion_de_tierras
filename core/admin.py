from django.contrib import admin
from .models import Departamento, Distrito, Colonia
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

