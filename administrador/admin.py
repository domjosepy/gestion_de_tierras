from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Rol, User, Grupo


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
        ('Información Personal', {
         'fields': ('first_name', 'last_name', 'email', 'ci', 'telefono')}),
        ('Permisos', {'fields': ('estado',
         'rol', 'groups', 'user_permissions')}),
        ('Fechas', {'fields': ('last_login',
         'date_joined', 'fecha_actualizacion')}),
    )
    actions = ['aprobar_usuarios']

    def aprobar_usuarios(self, request, queryset):
        queryset.update(estado='ACTIVO', is_active=True)
    aprobar_usuarios.short_description = "Aprobar usuarios seleccionados"


@admin.register(Grupo)
class GrupoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'lider', 'cantidad_usuarios',
                    'es_departamento', 'activo', 'fecha_creacion')
    list_filter = ('es_departamento', 'activo', 'fecha_creacion')
    filter_horizontal = ('usuarios', 'roles_asociados')
    search_fields = ('nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'creado_por')

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion', 'color', 'es_departamento', 'activo')
        }),
        ('Relaciones', {
            'fields': ('lider', 'usuarios', 'roles_asociados')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'fecha_actualizacion')
        }),
    )

    def cantidad_usuarios(self, obj):
        return obj.cantidad_usuarios
    cantidad_usuarios.short_description = 'Usuarios'

    def save_model(self, request, obj, form, change):
        if not obj.creado_por:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
