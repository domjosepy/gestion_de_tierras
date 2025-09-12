from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Rol, User

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'permisos_count')
    filter_horizontal = ('permisos',)  # Para selección fácil de permisos

    def permisos_count(self, obj):
        return obj.permisos.count()
    permisos_count.short_description = 'Permisos'

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'ci', 'rol', 'estado', 'is_active')
    list_filter = ('estado', 'rol', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'email', 'ci', 'telefono')}),
        ('Permisos', {'fields': ('estado', 'rol', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login', 'date_joined', 'fecha_actualizacion')}),
    )
    actions = ['aprobar_usuarios']

    def aprobar_usuarios(self, request, queryset):
        queryset.update(estado='ACTIVO', is_active=True)
    aprobar_usuarios.short_description = "Aprobar usuarios seleccionados"