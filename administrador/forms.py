from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Rol

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
        fields = ('username', 'email', 'password1', 'password2', 'rol', 'estado')