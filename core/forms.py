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
    patron = r"^[A-Za-zÁÉÍÓÚáéíóúÑñ\s]+$"
    if not re.match(patron, nombre):
        raise ValidationError("El nombre solo puede contener letras, espacios.")
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
        error_messages = {
            'nombre': {
                'required': "El nombre del departamento es obligatorio.",
            },
            'codigo': {
                'required': "El código del departamento es obligatorio.",
            },
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        
        if not nombre:
            raise ValidationError("El nombre del departamento es obligatorio.")
        
        # Validar que tenga al menos 3 caracteres
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        
        # Validar que solo contenga letras, espacios.
        nombre = validar_nombre_letras(nombre)
        
        # Validar unicidad
        if Departamento.objects.filter(nombre__iexact=nombre).exclude(id=self.instance.id).exists():
            raise ValidationError(f'El Departamento "{nombre}" ya existe.')
        
        return nombre

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        
        if codigo is None:
            raise ValidationError("El código es obligatorio.")
            
        codigo = validar_codigo_numerico(codigo)
        
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
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre del Distrito'
            }),
            'codigo': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código único dentro del departamento'
            }),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
        }
        error_messages = {
            'nombre': {
                'required': "El nombre del distrito es obligatorio.",
                'max_length': "El nombre no puede tener más de 200 caracteres."
            },
            'codigo': {
                'required': "El código del distrito es obligatorio.",
            },
            'departamento': {
                'required': "El departamento es obligatorio.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizar el label del campo departamento
        self.fields['departamento'].label = "Departamento"
        self.fields['departamento'].empty_label = "-- Seleccione un Departamento --"

    def clean_departamento(self):
        departamento = self.cleaned_data.get('departamento')
        if not departamento:
            raise ValidationError("Debe seleccionar un departamento.")
        return departamento

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        
        if not nombre:
            raise ValidationError("El nombre del distrito es obligatorio.")
        
        # Validar que tenga al menos 3 caracteres
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        
        # Validar que solo contenga letras, números, espacios y apóstrofes
        patron = r"^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s']+$"
        if not re.match(patron, nombre):
            raise ValidationError("El nombre solo puede contener letras, números, espacios y apóstrofes.")
        
        return nombre.upper()

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        
        if codigo is None:
            raise ValidationError("El código es obligatorio.")
            
        # Validar que sea positivo
        if codigo < 1:
            raise ValidationError("El código debe ser un número positivo.")
        
        return codigo

    def clean(self):
        """
        Validaciones cruzadas: nombre + departamento y código + departamento.
        """
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        codigo = cleaned_data.get('codigo')
        departamento = cleaned_data.get('departamento')

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
        widget=forms.CheckboxSelectMultiple(),
        required=True,
        error_messages={
            'required': 'Debe seleccionar al menos un distrito.',
        }
    )

    class Meta:
        model = Colonia
        fields = ['nombre', 'codigo', 'distritos']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre de la Colonia'
            }),
            'codigo': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código'
            }),
        }
        error_messages = {
            'nombre': {
                'required': "El nombre de la colonia es obligatorio.",
                'max_length': "El nombre no puede tener más de 250 caracteres."
            },
            'codigo': {
                'required': "El código de la colonia es obligatorio.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Agregar atributos required para evitar validación HTML5
        self.fields['nombre'].required = True
        self.fields['codigo'].required = True
        self.fields['distritos'].required = True

    # Tus métodos clean_nombre, clean_codigo y clean permanecen igual...
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        
        if not nombre:
            raise ValidationError("El nombre de la colonia es obligatorio.")
        
        if len(nombre) < 3:
            raise ValidationError("El nombre debe tener al menos 3 caracteres.")
        
        patron = r"^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ\s']+$"
        if not re.match(patron, nombre):
            raise ValidationError("El nombre solo puede contener letras, números, espacios y apóstrofes.")
        
        return nombre.upper()

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        
        if codigo is None:
            raise ValidationError("El código es obligatorio.")
            
        if codigo < 1:
            raise ValidationError("El código debe ser un número positivo.")
        
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        nombre = cleaned_data.get('nombre')
        codigo = cleaned_data.get('codigo')
        distritos = cleaned_data.get('distritos')

        if nombre and distritos:
            for distrito in distritos:
                existe_nombre = Colonia.objects.filter(
                    nombre__iexact=nombre.strip(),
                    distritos=distrito
                ).exclude(id=self.instance.id).exists()
                
                if existe_nombre:
                    self.add_error(
                        'nombre', 
                        f'Ya existe una colonia llamada "{nombre}" en el distrito "{distrito}".'
                    )

        if codigo and distritos:
            for distrito in distritos:
                existe_codigo = Colonia.objects.filter(
                    codigo=codigo,
                    distritos=distrito
                ).exclude(id=self.instance.id).exists()
                
                if existe_codigo:
                    self.add_error(
                        'codigo', 
                        f'Ya existe una colonia con el código "{codigo}" en el distrito "{distrito}".'
                    )

        return cleaned_data
    
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