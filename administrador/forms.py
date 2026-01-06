from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Rol
from django.contrib.auth.models import Permission
import re

User = get_user_model()
# FORMULARIO PERSONALIZADO DE CREACION DE USUARIO CON ROL INVITADO POR DEFECTO


class CustomUserCreationForm(UserCreationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.creado_por = 'usuario'
        if commit:
            user.save()
        return user

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',
                  'first_name', 'last_name', 'ci', 'telefono')
        widgets = {
            'email': forms.EmailInput(attrs={
                'placeholder': 'Correo electrónico',
                'class': 'form-control'
            }),
            'first_name': forms.TextInput(attrs={
                'placeholder': 'Nombre',
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'Apellido',
                'class': 'form-control'
            }),
            'ci': forms.TextInput(attrs={
                'placeholder': 'Ej: 12345678',
                'pattern': '[0-9]{6,8}',
                'title': '6 a 8 dígitos sin guiones',
                'inputmode': 'numeric',
                'maxlength': '8',
                'class': 'form-control',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '');"
            }),
            'telefono': forms.TextInput(attrs={
                'placeholder': 'Ej: 0999999999',
                'pattern': '[0-9]{10}',
                'title': '10 dígitos, sin guiones ni espacios',
                'inputmode': 'numeric',
                'maxlength': '10',
                'class': 'form-control',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '');"
            })
        }

        help_texts = {
            'username': 'Puede contener letras, números y @/./+/-/_',
            'ci': 'Cédula de identidad sin puntos ni guiones (6-8 dígitos)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos no requeridos PASAR A TRUE DESPUES DE LA PRUEBA
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['ci'].required = False
        self.fields['telefono'].required = False
        self.fields['email'].required = False

        # Mejora los placeholders y clases para los campos de contraseña
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        })


# FORMULARIO PERSONALIZADO DE CAMBIO DE CONTRASEÑA
class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personaliza los campos del formulario
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Ingrese su {field.replace("_", " ")}'
            })

# FORMULARIO SIMPLIFICADO DE CREACION DE USUARIO


class SimpleUserCreationForm(UserCreationForm):
    def save(self, commit=True):
        user = super().save(commit=False)
        user.creado_por = 'admin'
        if commit:
            user.save()
        return user
    ESTADOS = (
        ('ACTIVO', 'Activo'),
        ('INACTIVO', 'Inactivo'),
    )

    estado = forms.ChoiceField(
        choices=ESTADOS,
        initial='ACTIVO',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1',
                  'password2', 'rol', 'estado')

# FORMULARIO PERSONALIZADO DE CAMBIO DE USUARIO


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name',
                  'last_name', 'ci', 'telefono')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'ci': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cédula de identidad'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
        }


# FORMULARIO DE GESTIÓN DE ROLES
class RolForm(forms.ModelForm):
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        error_messages={
            'invalid_choice': 'Permiso no válido.',
            'invalid_pk_value': 'Valor de permiso no válido.'
        }
    )

    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion', 'color', 'permisos']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del rol',
                'autocomplete': 'off'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del rol',
                'maxlength': '500'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control form-control-color',
                'style': 'width: 50px; height: 50px;'
            }),
        }
        error_messages = {
            'nombre': {
                'required': 'El nombre del rol es obligatorio.',
                'unique': 'Ya existe un rol con este nombre.',
                'max_length': 'El nombre no puede tener más de 50 caracteres.'
            },
            'descripcion': {
                'max_length': 'La descripción no puede tener más de 500 caracteres.'
            }
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar permisos por app y luego por nombre
        self.fields['permisos'].queryset = Permission.objects.select_related(
            'content_type'
        ).order_by('content_type__app_label', 'name')

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()

        if not nombre:
            raise forms.ValidationError("El nombre del rol es obligatorio.")

        if len(nombre) < 3:
            raise forms.ValidationError(
                "El nombre debe tener al menos 3 caracteres.")

        # Validar que solo contenga letras, espacios y algunos caracteres especiales
        patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s\-_]+$"
        if not re.match(patron, nombre):
            raise forms.ValidationError(
                "El nombre solo puede contener letras, espacios, guiones y guiones bajos."
            )

        # Verificar unicidad (si estamos editando, excluir el rol actual)
        queryset = Rol.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                f'Ya existe un rol con el nombre "{nombre}".')

        return nombre.upper()

    def clean_descripcion(self):
        descripcion = self.cleaned_data.get('descripcion', '').strip()

        if descripcion and len(descripcion) < 10:
            raise forms.ValidationError(
                "La descripción debe tener al menos 10 caracteres si se proporciona."
            )

        return descripcion

    def clean_color(self):
        color = self.cleaned_data.get('color', '').strip()

        if color:
            # Validar formato hexadecimal (ej: #FF0000)
            patron = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
            if not re.match(patron, color):
                raise forms.ValidationError(
                    "El color debe estar en formato hexadecimal válido (ej: #FF0000 o #F00)."
                )
        else:
            color = '#6c757d'  # Color por defecto (bootstrap secondary)

        return color


class AsignacionPermisosForm(forms.Form):
    """Formulario para asignar permisos masivamente"""
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(estado='ACTIVO'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'list-group'}),
        required=True
    )
    permisos = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean(self):
        cleaned_data = super().clean()
        permisos = cleaned_data.get('permisos')
        rol = cleaned_data.get('rol')

        if not permisos and not rol:
            raise forms.ValidationError(
                "Debe seleccionar permisos o un rol para asignar."
            )

        return cleaned_data


class BusquedaUsuariosForm(forms.Form):
    """Formulario para buscar usuarios"""
    buscar = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por nombre, email o cédula...'
        })
    )
    estado = forms.ChoiceField(
        choices=[('', 'Todos')] + list(User.ESTADOS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    rol = forms.ModelChoiceField(
        queryset=Rol.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
