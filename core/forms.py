from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Departamento, Distrito, Colonia, Solicitud


# ===============================
# VALIDACIÓN AUXILIAR (reutilizable)
# ===============================
def validar_nombre_letras(nombre):
    """
    Permite letras, espacios y tildes.
    Rechaza números y símbolos especiales.
    """
    patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s']+$"
    if not re.match(patron, nombre):
        raise ValidationError("El nombre solo puede contener letras, espacios y apóstrofes.")
    return nombre.strip().upper()

def validar_nombre_general(nombre):
    """
    Permite letras, números, espacios y tildes.
    Para Distrito y Colonia.
    """
    patron = r"^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s']+$"
    if not re.match(patron, nombre):
        raise ValidationError("El nombre solo puede contener letras, números, espacios y apóstrofes.")
    return nombre.strip().upper()

def validar_codigo_numerico(codigo):
    """
    Valida que el código sea numérico y positivo.
    """
    if codigo is None or codigo < 0:
        raise ValidationError("El código debe ser un número positivo.")
    return codigo


# ===============================
# FORMULARIO: DEPARTAMENTO
# ===============================
class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nombre', 'codigo']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del departamento'
            }),
            'codigo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 01'
            }),
        }

    def clean_nombre(self):
        nombre = validar_nombre_letras(self.cleaned_data.get('nombre', ''))
        if Departamento.objects.filter(nombre__iexact=nombre).exclude(id=self.instance.id).exists():
            raise ValidationError(f'El Departamento "{nombre}" ya existe.')
        return nombre

    def clean_codigo(self):
        codigo = validar_codigo_numerico(self.cleaned_data.get('codigo'))
        if Departamento.objects.filter(codigo=codigo).exclude(id=self.instance.id).exists():
            raise ValidationError(f'El código "{codigo}" ya está asignado a otro departamento.')
        return codigo


# ===============================
# FORMULARIO: DISTRITO
# ===============================
class DistritoForm(forms.ModelForm):
    class Meta:
        model = Distrito
        fields = ['nombre', 'codigo', 'departamento']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Distrito'}),
            'codigo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Código único dentro del departamento'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip().upper()
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        return nombre

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        departamento = self.cleaned_data.get('departamento')

        if codigo is None or codigo < 1:
            raise forms.ValidationError("El código debe ser un número positivo.")

        # 🔑 Validación: único solo dentro del mismo departamento
        if codigo and departamento:
            existe_codigo = Distrito.objects.filter(
                codigo=codigo,
                departamento=departamento
            ).exclude(id=self.instance.id).exists()

            if existe_codigo:
                raise forms.ValidationError(
                    f'El código {codigo} ya está asignado en el departamento "{departamento}".'
                )
        return codigo

    def clean(self):
        """
        Validaciones cruzadas: nombre + departamento y código + departamento.
        """
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        codigo = cleaned_data.get('codigo')
        departamento = cleaned_data.get('departamento')

        if not departamento:
            raise forms.ValidationError("Debe seleccionar un departamento.")

        # Verificar nombre único por departamento
        if nombre and departamento:
            existe_nombre = Distrito.objects.filter(
                nombre__iexact=nombre.strip(),
                departamento=departamento
            ).exclude(id=self.instance.id).exists()
            if existe_nombre:
                self.add_error('nombre', f'Ya existe un distrito llamado "{nombre}" en el departamento "{departamento}".')

        # Verificar código único por departamento
        if codigo and departamento:
            existe_codigo = Distrito.objects.filter(
                codigo=codigo,
                departamento=departamento
            ).exclude(id=self.instance.id).exists()
            if existe_codigo:
                self.add_error('codigo', f'El código {codigo} ya está asignado en el departamento "{departamento}".')

        return cleaned_data


# =============================
#  FORMULARIO COLONIA
# =============================
class ColoniaForm(forms.ModelForm):
    distritos = forms.ModelMultipleChoiceField(
        queryset=Distrito.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=True
    )

    class Meta:
        model = Colonia
        fields = ['nombre', 'codigo', 'distritos', 'estado', 'finca_matriz', 'padron_matriz']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Colonia'}),
            'codigo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Código único'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'finca_matriz': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Finca matriz'}),
            'padron_matriz': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Padrón matriz'}),
        }

    def clean_nombre(self):
        nombre = validar_nombre_general(self.cleaned_data.get('nombre', ''))
        if len(nombre) < 3:
            raise forms.ValidationError("El nombre debe tener al menos 3 caracteres.")
        if Colonia.objects.filter(nombre__iexact=nombre).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(f'La Colonia "{nombre}" ya existe.')
        return nombre
    
    def clean_codigo(self):
        codigo = validar_codigo_numerico(self.cleaned_data.get('codigo'))
        if Colonia.objects.filter(codigo=codigo).exclude(id=self.instance.id).exists():
            raise forms.ValidationError(f"Ya existe una colonia con el código {codigo}.")
        return codigo


# =============================
#  FORMULARIO SOLICITUD
# =============================
class SolicitudForm(forms.ModelForm):
    class Meta:
        model = Solicitud
        fields = ["colonia", "tipo", "observaciones"]
        widgets = {
            'colonia': forms.Select(attrs={'class': 'form-select'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observaciones'}),
        }

    def clean(self):
        cleaned = super().clean()
        try:
            self.instance.colonia = cleaned.get('colonia')
            self.instance.tipo = cleaned.get('tipo')
            self.instance.observaciones = cleaned.get('observaciones')
            self.instance.full_clean(exclude=None)
        except forms.ValidationError as e:
            raise forms.ValidationError(e.messages)
        return cleaned