from django import forms
from django.core.validators import FileExtensionValidator
from .models import PrecatArchivo


class PrecatSubirForm(forms.Form):
    """
    Formulario para subir archivos de Precat y Planos
    """
    archivo_precat = forms.FileField(
        label='Archivo Precat Final',
        required=True,
        validators=[FileExtensionValidator(['zip', 'rar'])],
        help_text='Formato .zip o .rar (Máx. 200MB)'
    )
    archivo_planos = forms.FileField(
        label='Planos de Referencia',
        required=True,
        validators=[FileExtensionValidator(['pdf'])],
        help_text='Formato .pdf (Máx. 50MB por archivo)'
    )
    observaciones = forms.CharField(
        label='Observaciones / Descripción',
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Describa el trabajo realizado, observaciones importantes, etc.'
        }),
        help_text='Descripción detallada del trabajo de digitalización'
    )

    def limpiar_archivo_precat(self):
        archivo = self.cleaned_data.get('archivo_precat')
        if archivo:
            # Validar tamaño máximo (200MB)
            max_size = 200 * 1024 * 1024  # 200MB
            if archivo.size > max_size:
                raise forms.ValidationError(
                    f'El archivo Precat no puede superar los 200MB. Tamaño actual: {archivo.size/(1024*1024):.2f}MB'
                )
        return archivo

    def limpiar_archivo_planos(self):
        archivo = self.cleaned_data.get('archivo_planos')
        if archivo:
            # Validar tamaño máximo (50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if archivo.size > max_size:
                raise forms.ValidationError(
                    f'Los planos no pueden superar los 50MB. Tamaño actual: {archivo.size/(1024*1024):.2f}MB'
                )
        return archivo
